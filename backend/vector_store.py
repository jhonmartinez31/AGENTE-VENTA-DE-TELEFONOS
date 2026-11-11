"""
Módulo de Recuperación Semántica (RAG) con pgvector y Embedding Gemma 2
CEL RED — Tienda de Celulares y Accesorios (Mocoa - Putumayo)

Genera embeddings para fichas técnicas, políticas de garantía, sistema de separados y medios de pago,
indexa fragmentos en PostgreSQL (`conocimiento_rag_celred`) y realiza búsquedas por similitud de cosenos.
"""

import os
import re
import math
import time
import hashlib
import httpx
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from database import ProtocoloRAG, VECTOR_DIMENSION  # type: ignore
except ImportError:
    from backend.database import ProtocoloRAG, VECTOR_DIMENSION  # type: ignore

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemma2")
_ollama_offline_until: float = 0.0


# =====================================================================
# Generación de Embeddings (Ollama con gemma2 + Fallback determinista)
# =====================================================================
async def get_embedding(text: str) -> List[float]:
    """
    Obtiene el vector de embedding para un texto dado utilizando la API local de Ollama (gemma2).
    Si Ollama no está disponible, utiliza un generador vectorial semántico-determinista de respaldo
    ponderado para el dominio comercial de Cel Red.
    """
    global _ollama_offline_until
    cleaned_text = text.strip()
    if not cleaned_text:
        return [0.0] * VECTOR_DIMENSION

    if time.monotonic() >= _ollama_offline_until:
        try:
            timeout_cfg = httpx.Timeout(4.0, connect=0.35)
            async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                response = await client.post(
                    f"{OLLAMA_BASE_URL}/api/embed",
                    json={"model": EMBEDDING_MODEL, "input": cleaned_text}
                )
                if response.status_code == 200:
                    data = response.json()
                    embeddings = data.get("embeddings", [])
                    if embeddings and len(embeddings[0]) > 0:
                        return _normalize_or_resize_vector(embeddings[0], VECTOR_DIMENSION)

                response_legacy = await client.post(
                    f"{OLLAMA_BASE_URL}/api/embeddings",
                    json={"model": EMBEDDING_MODEL, "prompt": cleaned_text}
                )
                if response_legacy.status_code == 200:
                    data = response_legacy.json()
                    vec = data.get("embedding", [])
                    if vec:
                        return _normalize_or_resize_vector(vec, VECTOR_DIMENSION)
        except Exception:
            _ollama_offline_until = time.monotonic() + 30.0

    return _generate_fallback_embedding(cleaned_text, VECTOR_DIMENSION)


def _normalize_or_resize_vector(vector: List[float], target_dim: int) -> List[float]:
    """Ajusta la dimensión del vector al tamaño de columna pgvector y normaliza la norma L2"""
    current_dim = len(vector)
    if current_dim < target_dim:
        vector = vector + [0.0] * (target_dim - current_dim)
    elif current_dim > target_dim:
        vector = vector[:target_dim]

    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0:
        return [x / norm for x in vector]
    return vector


def _generate_fallback_embedding(text: str, dim: int) -> List[float]:
    """
    Genera un vector denso normalizado de dimensión fija a partir del texto.
    Ponderado con el vocabulario comercial de CEL RED (marcas, cámaras, precios, separados, garantías).
    """
    vec = [0.0] * dim
    words = re.findall(r"\w+", text.lower())

    commercial_weights = {
        "samsung": 10, "galaxy": 9, "iphone": 11, "apple": 10,
        "xiaomi": 10, "redmi": 10, "poco": 10, "tecno": 9, "infinix": 9, "oppo": 9, "honor": 9, "itel": 9,
        "camara": 10, "fotos": 9, "video": 8, "bateria": 9, "carga": 8,
        "gamer": 10, "juegos": 10, "rendimiento": 9, "ram": 8, "almacenamiento": 8,
        "separado": 12, "separar": 12, "abono": 11, "cuotas": 10, "plazo": 9,
        "sistecredito": 12, "addi": 12, "credito": 10, "financiacion": 10,
        "garantia": 12, "imei": 10, "factura": 9, "syscafe": 10,
        "precio": 10, "economico": 9, "barato": 9, "presupuesto": 9,
        "obsequio": 12, "obsequios": 12, "combo": 12, "regalo": 11,
        "airpods": 11, "reloj": 11, "cubo": 9, "estuche": 9, "vidrio": 9,
        "open": 10, "seminuevo": 11, "seminuevos": 11
    }

    for word in words:
        weight = commercial_weights.get(word, 1.0)
        for i in range(4):
            seed_str = f"{word}_{i}"
            h = int(hashlib.sha256(seed_str.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            sign = 1.0 if ((h >> 8) % 2 == 0) else -1.0
            vec[idx] += sign * weight

    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        vec[0] = 1.0
        return vec
    return [x / norm for x in vec]


# =====================================================================
# División de Documentos en Chunks
# =====================================================================
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = ""

    for p in paragraphs:
        if len(current_chunk) + len(p) <= chunk_size:
            current_chunk = f"{current_chunk}\n\n{p}".strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            words = current_chunk.split()
            overlap_text = " ".join(words[-max(1, overlap // 6):]) if words else ""
            current_chunk = f"{overlap_text} {p}".strip()

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


# =====================================================================
# Búsqueda Semántica RAG con pgvector
# =====================================================================
async def search_relevant_protocols(
    db: AsyncSession,
    query: str,
    top_k: int = 3,
    categoria_filtro: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Realiza una búsqueda semántica de las políticas, guías de compra y fichas técnicas de Cel Red
    usando pgvector (<=> distancia de cosenos).
    """
    query_vector = await get_embedding(query)

    stmt = select(
        ProtocoloRAG,
        ProtocoloRAG.embedding.cosine_distance(query_vector).label("distance")
    )

    if categoria_filtro:
        stmt = stmt.where(ProtocoloRAG.categoria == categoria_filtro)

    stmt = stmt.order_by("distance").limit(top_k)

    result = await db.execute(stmt)
    rows = result.all()

    results = []
    for proto, distance in rows:
        similarity = max(0.0, 1.0 - float(distance))
        results.append({
            "id": proto.id,
            "titulo": proto.titulo,
            "categoria": proto.categoria,
            "contenido": proto.contenido,
            "fuente": proto.fuente,
            "similitud": round(similarity, 4)
        })

    return results


def format_rag_context(protocols: List[Dict[str, Any]]) -> str:
    """
    Formatea los fragmentos recuperados para inyectarlos en el prompt comercial del LLM.
    """
    if not protocols:
        return "No se encontraron políticas o fichas específicas adicionales en la base vectorial."

    context_parts = []
    for i, p in enumerate(protocols, 1):
        context_parts.append(
            f"--- DOCUMENTO CEL RED [{i}]: {p['titulo']} (Categoría: {p['categoria']} | Similitud: {p['similitud']*100:.1f}%) ---\n"
            f"{p['contenido']}\n"
            f"Fuente: {p['fuente']}"
        )

    return "\n\n".join(context_parts)
