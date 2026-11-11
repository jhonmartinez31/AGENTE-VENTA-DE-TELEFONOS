"""
Punto de Entrada Principal - API REST y WebSockets con FastAPI
CEL RED — Asesor Comercial y de Ventas IA (Tienda de Celulares y Accesorios - Mocoa)
"""

import os
import sys
import logging
from typing import List, Optional
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Query, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, desc, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
import hmac

try:
    from database import (  # type: ignore
        get_db, init_db, AsyncSessionLocal, Producto, ProductoResponse,
        Incidente, IncidenteResponse, IncidenteUpdate,
        ChatTextRequest, ChatResponse, ProtocoloRAG
    )
    from orchestrator import emergency_orchestrator  # type: ignore
    from stt_service import transcribe_audio, get_whisper_model  # type: ignore
    from vector_store import search_relevant_protocols, get_embedding, chunk_text  # type: ignore
    from tts_service import AUDIO_OUTPUT_DIR  # type: ignore
except ImportError:
    from backend.database import (  # type: ignore
        get_db, init_db, AsyncSessionLocal, Producto, ProductoResponse,
        Incidente, IncidenteResponse, IncidenteUpdate,
        ChatTextRequest, ChatResponse, ProtocoloRAG
    )
    from backend.orchestrator import emergency_orchestrator  # type: ignore
    from backend.stt_service import transcribe_audio, get_whisper_model  # type: ignore
    from backend.vector_store import search_relevant_protocols, get_embedding, chunk_text  # type: ignore
    from backend.tts_service import AUDIO_OUTPUT_DIR  # type: ignore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("celred_api")

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


# =====================================================================
# Ciclo de Vida de la Aplicación y Semillado RAG de CEL RED
# =====================================================================
async def _seed_initial_protocols_if_needed():
    """Verifica y actualiza la base de conocimientos RAG de Cel Red con las políticas reales y tabla de obsequios."""
    try:
        async with AsyncSessionLocal() as db:
            # Verificar si ya existe el documento del Directorio Oficial de las 14 Sedes de Cel Red
            check_obs = await db.execute(
                select(func.count(ProtocoloRAG.id)).where(
                    ProtocoloRAG.titulo == "Directorio Oficial de las 14 Sedes y Direcciones de Cel Red"
                )
            )
            has_obs = (check_obs.scalar() or 0) > 0
            if not has_obs:
                logger.info("Actualizando base de conocimiento RAG de Cel Red (Catálogo Real, Obsequios iPhone, Plataformas y 14 Sedes)...")
                await db.execute(delete(ProtocoloRAG).where(ProtocoloRAG.fuente != "Asesor Jhon - Cel Red"))
                pdf_path = os.path.join(DATA_DIR, "catalogo_y_politicas_celred.pdf")
                inserted = 0

                if os.path.exists(pdf_path):
                    try:
                        from pypdf import PdfReader
                        reader = PdfReader(pdf_path)
                        full_text = ""
                        for page in reader.pages:
                            text = page.extract_text()
                            if text:
                                full_text += text + "\n\n"

                        chunks = chunk_text(full_text, chunk_size=400, overlap=60)
                        for chunk in chunks:
                            emb = await get_embedding(chunk)
                            proto = ProtocoloRAG(
                                titulo="Manual Comercial y Políticas Oficiales - Cel Red",
                                categoria="Políticas y Catálogo Cel Red",
                                contenido=chunk,
                                fuente="Gerencia Comercial Cel Red - SysCafé",
                                embedding=emb
                            )
                            db.add(proto)
                            inserted += 1
                        logger.info(f"✓ {inserted} fragmentos comerciales sembrados desde PDF.")
                    except Exception as e:
                        logger.warning(f"Error extrayendo del PDF comercial: {e}")

                documentos_celred = [
                    {
                        "titulo": "Directorio Oficial de las 14 Sedes y Direcciones de Cel Red",
                        "categoria": "Sedes y Ubicaciones Cel Red",
                        "contenido": (
                            "Direcciones exactas de las 14 sedes oficiales de Cel Red por ciudad: "
                            "1) Puerto Asís / Putumayo: CALLE 10 NO 24 - 18 BARRIO EL CARMEN. "
                            "2) Mocoa / Putumayo: CRA 9 # 10 - 30 AVENIDA COLOMBIA. "
                            "3) La Hormiga - Valle del Guamuez: BARRIO CENTRAL LAS AMERICAS CARRERA 5 - #7-16 A UN COSTADO DE LA ALCALDÍA MUNICIPAL. "
                            "4) Orito / Putumayo: CALLE 8 # 10 - 47 BARRIO MARCO FIDEL SUAREZ AL LADO DE DISTRISUR. "
                            "5) Ipiales / Nariño (Sede 1): CRA 6 NO 13 - 05 ESQUINA ED MARKUS. "
                            "6) Ipiales / Nariño (Sede 2): CRA 6 NO 11 - 51 CC ZAFIRO LOCAL 123. "
                            "7) Ipiales / Nariño (Sede 3): CRA 7 NO 9 - 56 CC VICTORIA PLAZA LOCAL 101A. "
                            "8) Pasto / Nariño (Sede 1): CALLE 16 NO 23 - 82 LOCAL 1 - CENTRO. "
                            "9) Pasto / Nariño (Sede 2): CALLE 17 # 26 - 60 CC PASAJE EL LICEO LOCAL 103. "
                            "10) Pasto / Nariño (Sede 3): CC SEBASTIAN DE BELALCAZAR LOCAL 6A. "
                            "11) Túquerres / Nariño: CRA 14 - CLL 20 ESQUINA - TUQUERRES. "
                            "12) Medellín / Antioquia: CENTRO COMERCIAL PREMIUM PLAZA LOCAL 1301. "
                            "13) Neiva / Huila: CRA.2 # 6 - 26 - LOCAL 5 - CENTRO. "
                            "14) La Unión / Nariño: CRA 1 # 11- 81 – FRENTE AL PARQUE CUEVAS LEIVA."
                        ),
                        "fuente": "Directorio Oficial de Sedes Cel Red"
                    },
                    {
                        "titulo": "Sistema de Separados y Reserva de Equipos - Cel Red",
                        "categoria": "Separados y Pagos",
                        "contenido": (
                            "En la tienda Cel Red el cliente puede separar cualquier celular Android o iPhone con un abono inicial mínimo del 20% "
                            "del valor del equipo. El precio queda congelado y la unidad se reserva con su número de IMEI en bóveda hasta por "
                            "45 días calendario para pagar en cuotas libres sin intereses."
                        ),
                        "fuente": "Reglamento de Ventas Cel Red - SysCafé"
                    },
                    {
                        "titulo": "Tabla Oficial de Obsequios y Combos iPhone - Cel Red",
                        "categoria": "Obsequios y Promociones iPhone",
                        "contenido": (
                            "En Cel Red solo se comercializa desde el iPhone 13 en adelante (se omiten iPhone 11 y 12). "
                            "Obsequios incluidos por modelo: "
                            "iPhone 13 128GB incluye ESTUCHE Y VIDRIO. "
                            "iPhone 13 Pro Max 128GB, iPhone 14 Pro 128GB, iPhone 14 Pro Max 128GB, iPhone 15 128GB, iPhone 15 Pro 128GB e iPhone 15 Pro Max 256GB "
                            "incluyen COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods) a elección. "
                            "iPhone 16 128GB incluye COMBO 4 (Cubo, Cable, Estuche, Vidrio y AirPods). "
                            "iPhone 16 Pro 128GB, iPhone 16 Pro 256GB e iPhone 16 Pro Max 256GB incluyen COMBO 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche)."
                        ),
                        "fuente": "Promociones Oficiales iPhone Cel Red"
                    },
                    {
                        "titulo": "Plataformas de Financiación Cel Red: Addi, Sistecrédito, Banco de Bogotá, Krediya, Credimóvil y Renting",
                        "categoria": "Financiación y Crédito",
                        "contenido": (
                            "En Cel Red financiamos celulares Android y iPhone según el perfil del cliente: "
                            "1) Addi y Sistecrédito: precio de desembolso directo sin cuota inicial obligatoria según cupo aprobado. "
                            "2) Banco de Bogotá: precio de desembolso preferencial bancario para Android y iPhone. "
                            "3) Krediya (Android): financiación con cuota inicial según aprobación del estudio al 30% (estándar en tabla) o 20% del precio plataforma. "
                            "4) Credimóvil (Android): financiación con cuota inicial súper baja del 10% o del 15% según aprobación. "
                            "5) Renting (Exclusivo iPhone desde iPhone 13 en adelante): plataforma ideal para clientes con poco historial crediticio o reportados en centrales de riesgo, "
                            "con cuota inicial aprobada al 20% o al 30% sobre el valor de plataforma."
                        ),
                        "fuente": "Convenios Financieros Oficiales Cel Red"
                    },
                    {
                        "titulo": "Política de Garantía Oficial y Diferencia Nuevo vs Open Box Seminuevo",
                        "categoria": "Garantías y Soporte",
                        "contenido": (
                            "Los equipos Nuevos vendidos en Cel Red cuentan con 12 meses de garantía directa, factura legal en SysCafé y registro de IMEI. "
                            "Los equipos Open Box son seminuevos garantizados (por eso su precio de contado es menor que el nuevo) y cuentan con 6 meses de garantía. "
                            "No cubre humedad, pantallas rotas por golpes ni sobrecargas."
                        ),
                        "fuente": "Servicio Técnico y Garantías Cel Red"
                    },
                    {
                        "titulo": "Guía Comparativa de Equipos en Stock por Cámara, Gaming y Presupuesto",
                        "categoria": "Catálogo de Equipos",
                        "contenido": (
                            "Recomendaciones reales en stock Cel Red: "
                            "Económicos desde $350.000: Samsung A05 128/4 ($350.000), Redmi A5 128/4 ($350.000), Tecno Spark Go2 ($360.000), Itel A100C ($370.000). "
                            "Mejor cámara gama media: Redmi Note 15 Pro 256/8 ($970.000), Samsung A37 5G 256/8 ($1.160.000), Tecno Camon 50 Ultra 256/8 ($1.280.000). "
                            "Mejor para gaming: Tecno Pova Curve 2 ($1.040.000), POCO F8 Pro 256/12 ($1.860.000) y POCO X8 Pro Max 512/12 ($1.960.000). "
                            "Gama Alta Samsung y Apple: Samsung S25 Ultra ($2.980.000 / $3.300.000), S26 Ultra ($3.340.000 / $3.800.000), "
                            "iPhone Open Box desde iPhone 13 128GB ($1.150.000) hasta iPhone 17 Pro Max ($4.000.000), e iPhone Nuevos hasta iPhone 18 Pro Max ($5.350.000)."
                        ),
                        "fuente": "Catálogo Oficial de Contado Cel Red"
                    }
                ]

                for doc in documentos_celred:
                    emb = await get_embedding(doc["contenido"])
                    proto = ProtocoloRAG(
                        titulo=doc["titulo"],
                        categoria=doc["categoria"],
                        contenido=doc["contenido"],
                        fuente=doc["fuente"],
                        embedding=emb
                    )
                    db.add(proto)

                await db.commit()
                logger.info("✓ Conocimiento comercial y tabla de obsequios de Cel Red sembrados exitosamente en pgvector.")
    except Exception as e:
        logger.warning(f"No se pudo completar el semillado RAG automático: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización de la base de datos aislada `celred_db`, pgvector y modelo STT al arrancar"""
    logger.info("Iniciando Agente Comercial CEL RED — Tienda de Celulares y Accesorios...")
    try:
        await init_db()
        await _seed_initial_protocols_if_needed()
        logger.info("[OK] Base de datos PostgreSQL (`celred_db`) y pgvector conectadas exitosamente.")
    except Exception as e:
        logger.error(f"Error al conectar con la base de datos PostgreSQL: {e}")

    try:
        import asyncio
        await asyncio.to_thread(get_whisper_model)
    except Exception as e:
        logger.warning(f"No se pudo pre-cargar faster-whisper al inicio: {e}")

    yield
    logger.info("Deteniendo Agente Comercial CEL RED...")


app = FastAPI(
    title="CEL RED — Agente Comercial y de Ventas IA",
    description="API conversacional multimodal para asesoría, cotización, separados y cierre de ventas en Cel Red.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def disable_static_cache(request, call_next):
    """Evita que el navegador guarde en caché versiones antiguas de CSS, JS o HTML"""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.get("/api/health", summary="Estado operativo del Agente Comercial Cel Red")
async def health_check():
    return {"status": "ok", "sistema": "CEL RED - Asesor Comercial IA", "database": "celred_db"}


# =====================================================================
# Rutas Principales de Conversación Comercial (Texto y Voz)
# =====================================================================
@app.post("/api/chat/text", response_model=ChatResponse, summary="Interacción comercial por texto")
async def chat_text(
    payload: ChatTextRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await emergency_orchestrator.process_interaction(
            db=db,
            session_id=payload.session_id,
            user_message=payload.mensaje,
            channel="Texto",
            incidente_id=payload.incidente_id,
            generate_audio=True
        )
        return result
    except Exception as e:
        logger.error(f"Error procesando consulta comercial: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error en orquestación comercial: {str(e)}"
        )


@app.post("/api/chat/audio", response_model=ChatResponse, summary="Interacción comercial por voz (STT -> RAG/DB -> TTS)")
async def chat_audio(
    audio: UploadFile = File(..., description="Archivo de audio hablado por el cliente"),
    session_id: Optional[str] = Form(None),
    incidente_id: Optional[int] = Form(None),
    transcripcion_cliente: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        audio_bytes = await audio.read()
        clean_client_text = (transcripcion_cliente or "").strip()

        # Respetar exactamente lo que el cliente dijo y vio en pantalla sin sobrescribirlo
        if clean_client_text:
            transcription = clean_client_text
            logger.info(f"Texto exacto dicho por el cliente: '{transcription}'")
        else:
            whisper_text = await transcribe_audio(
                audio_bytes,
                language="es",
                original_filename=audio.filename
            )
            transcription = (whisper_text or "").strip() or "Consulta de catálogo y precios en Cel Red."
            logger.info(f"Transcripción STT faster-whisper de respaldo: '{transcription}'")

        result = await emergency_orchestrator.process_interaction(
            db=db,
            session_id=session_id,
            user_message=transcription,
            channel="Voz",
            incidente_id=incidente_id,
            generate_audio=True,
            texto_transcrito=transcription
        )
        return result
    except Exception as e:
        logger.error(f"Error en flujo multimodal de audio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error procesando audio STT/TTS: {str(e)}")


# =====================================================================
# Rutas de Catálogo de Productos y Órdenes de Venta (SysCafé / PostgreSQL)
# =====================================================================
@app.get("/api/productos", response_model=List[ProductoResponse], summary="Listar catálogo en stock de Cel Red")
async def list_productos(
    categoria: Optional[str] = Query(None, description="Filtrar por Celular o Accesorio"),
    marca: Optional[str] = Query(None, description="Filtrar por marca (Samsung, Apple, Xiaomi, etc.)"),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Producto).order_by(Producto.precio_cop.desc())
    if categoria:
        stmt = stmt.where(Producto.categoria == categoria)
    if marca:
        stmt = stmt.where(Producto.marca.ilike(f"%{marca}%"))
    result = await db.execute(stmt)
    return result.scalars().all()


@app.get("/api/ordenes", response_model=List[IncidenteResponse], summary="Listar órdenes de venta y separados")
@app.get("/api/incidentes", response_model=List[IncidenteResponse], summary="Listar órdenes de venta y cotizaciones (alias compatible)")
async def list_ordenes(
    prioridad: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Incidente).order_by(desc(Incidente.creado_en)).offset(offset).limit(limit)
    if prioridad:
        stmt = stmt.where(Incidente.prioridad == prioridad)
    if estado:
        stmt = stmt.where(Incidente.estado == estado)

    result = await db.execute(stmt)
    return result.scalars().all()


@app.get("/api/ordenes/{orden_id}", response_model=IncidenteResponse)
@app.get("/api/incidentes/{orden_id}", response_model=IncidenteResponse)
async def get_orden(orden_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Incidente).where(Incidente.id == orden_id)
    result = await db.execute(stmt)
    orden = result.scalar_one_or_none()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return orden


@app.patch("/api/incidentes/{orden_id}/estado", response_model=IncidenteResponse)
async def update_orden_estado(
    orden_id: int,
    payload: IncidenteUpdate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Incidente).where(Incidente.id == orden_id)
    result = await db.execute(stmt)
    orden = result.scalar_one_or_none()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    if payload.estado:
        orden.estado = payload.estado
    if payload.prioridad:
        orden.prioridad = payload.prioridad
    if payload.escalado_a:
        orden.escalado_a = payload.escalado_a
    if payload.acciones_recomendadas:
        orden.acciones_recomendadas = payload.acciones_recomendadas

    await db.commit()
    await db.refresh(orden)
    return orden


# =====================================================================
# Rutas de RAG y Conocimiento Comercial con pgvector
# =====================================================================
@app.get("/api/rag/search", summary="Búsqueda semántica en políticas y catálogo de Cel Red")
async def test_rag_search(
    q: str = Query(..., description="Consulta comercial en lenguaje natural"),
    top_k: int = Query(3, ge=1, le=10),
    db: AsyncSession = Depends(get_db)
):
    results = await search_relevant_protocols(db, query=q, top_k=top_k)
    return {"query": q, "resultados": results}


@app.post("/api/rag/ingest", summary="Indexar manual comercial y políticas de Cel Red en pgvector")
async def ingest_protocols(db: AsyncSession = Depends(get_db)):
    await _seed_initial_protocols_if_needed()
    result = await db.execute(select(func.count(ProtocoloRAG.id)))
    total = result.scalar() or 0
    return {"status": "ok", "total_protocolos_en_base": total}


# =====================================================================
# Apartado Exclusivo de Entrenamiento del Agente — Asesor Jhon
# =====================================================================
ADVISOR_USER = "jhon"
ADVISOR_PASS = "celred12345*"
ADVISOR_FUENTE = "Asesor Jhon - Cel Red"
_ADVISOR_SECRET = b"celred_jhon_exclusive_training_secret_2026"


def _generate_advisor_token(username: str) -> str:
    return hmac.new(_ADVISOR_SECRET, username.lower().encode("utf-8"), hashlib.sha256).hexdigest()


def _verify_advisor_token(token: Optional[str]) -> None:
    expected = _generate_advisor_token(ADVISOR_USER)
    if not token or not hmac.compare_digest(token.strip(), expected):
        raise HTTPException(
            status_code=401,
            detail="Acceso restringido: Inicia sesión con el usuario y contraseña exclusivos del asesor Jhon."
        )


class AdvisorLoginRequest(BaseModel):
    username: str
    password: str


class AdvisorTipCreate(BaseModel):
    titulo: str
    categoria: str = "Tip Comercial / Cierre de Ventas"
    contenido: str


@app.post("/api/advisor/login", summary="Inicio de sesión exclusivo del Asesor Jhon para entrenar al agente")
async def advisor_login(payload: AdvisorLoginRequest):
    user_clean = (payload.username or "").strip().lower()
    pass_clean = payload.password or ""
    if user_clean == ADVISOR_USER and pass_clean == ADVISOR_PASS:
        return {
            "authenticated": True,
            "advisor": "Jhon",
            "token": _generate_advisor_token(ADVISOR_USER),
            "mensaje": "¡Bienvenido, Asesor Jhon! Panel de entrenamiento del agente desbloqueado."
        }
    raise HTTPException(
        status_code=401,
        detail="Usuario o contraseña incorrectos. Este apartado es exclusivo para el asesor Jhon."
    )


@app.get("/api/advisor/tips", summary="Listar tips y enseñanzas registradas por el Asesor Jhon")
async def list_advisor_tips(
    x_advisor_token: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    _verify_advisor_token(x_advisor_token)
    stmt = (
        select(ProtocoloRAG)
        .where(ProtocoloRAG.fuente == ADVISOR_FUENTE)
        .order_by(desc(ProtocoloRAG.id))
    )
    res = await db.execute(stmt)
    rows = res.scalars().all()
    return [
        {
            "id": r.id,
            "titulo": r.titulo,
            "categoria": r.categoria,
            "contenido": r.contenido,
            "fuente": r.fuente,
            "creado_en": r.creado_en.isoformat() if r.creado_en else None
        }
        for r in rows
    ]


@app.post("/api/advisor/tips", summary="Guardar nuevo tip o enseñanza del Asesor Jhon en el Agente IA")
async def create_advisor_tip(
    payload: AdvisorTipCreate,
    x_advisor_token: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    _verify_advisor_token(x_advisor_token)
    titulo = (payload.titulo or "").strip()
    categoria = (payload.categoria or "Tip Comercial / Cierre de Ventas").strip()
    contenido = (payload.contenido or "").strip()
    if len(titulo) < 3 or len(contenido) < 5:
        raise HTTPException(
            status_code=400,
            detail="Por favor ingresa un título claro y el contenido detallado del tip para enseñarle al agente."
        )

    texto_vector = f"Tip del Asesor Jhon ({categoria}) - {titulo}: {contenido}"
    emb = await get_embedding(texto_vector)
    nuevo_tip = ProtocoloRAG(
        titulo=titulo,
        categoria=categoria,
        contenido=contenido,
        fuente=ADVISOR_FUENTE,
        embedding=emb
    )
    db.add(nuevo_tip)
    await db.commit()
    await db.refresh(nuevo_tip)
    logger.info(f"✓ Nuevo tip de entrenamiento agregado por Jhon: '{titulo}' (ID={nuevo_tip.id})")
    return {
        "status": "ok",
        "mensaje": "El agente ha aprendido tu nuevo tip comercial y ya lo aplicará en texto y voz.",
        "tip": {
            "id": nuevo_tip.id,
            "titulo": nuevo_tip.titulo,
            "categoria": nuevo_tip.categoria,
            "contenido": nuevo_tip.contenido,
            "fuente": nuevo_tip.fuente,
            "creado_en": nuevo_tip.creado_en.isoformat() if nuevo_tip.creado_en else None
        }
    }


@app.delete("/api/advisor/tips/{tip_id}", summary="Eliminar un tip de entrenamiento del Asesor Jhon")
async def delete_advisor_tip(
    tip_id: int,
    x_advisor_token: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    _verify_advisor_token(x_advisor_token)
    stmt = select(ProtocoloRAG).where(
        ProtocoloRAG.id == tip_id,
        ProtocoloRAG.fuente == ADVISOR_FUENTE
    )
    res = await db.execute(stmt)
    tip = res.scalar_one_or_none()
    if not tip:
        raise HTTPException(status_code=404, detail="Tip no encontrado.")
    await db.delete(tip)
    await db.commit()
    return {"status": "ok", "deleted_id": tip_id}


# =====================================================================
# Servir Archivos de Audio Sintetizados (TTS)
# =====================================================================
@app.get("/api/audio/{filename}", summary="Reproducir audio sintetizado")
async def get_audio_file(filename: str):
    safe_filename = os.path.basename(filename)
    filepath = os.path.join(AUDIO_OUTPUT_DIR, safe_filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Archivo de audio no encontrado")
    media_type = "audio/mpeg" if filename.endswith(".mp3") else "audio/wav"
    return FileResponse(filepath, media_type=media_type)


# =====================================================================
# WebSocket Bidireccional Comercial
# =====================================================================
@app.websocket("/ws/emergency")
async def websocket_sales_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    await websocket.accept()
    session_id = f"ws_{os.urandom(4).hex()}"

    try:
        await websocket.send_json({
            "tipo": "bienvenida",
            "mensaje": "Conexión activa con el Asesor Comercial de Cel Red.",
            "session_id": session_id
        })

        while True:
            data = await websocket.receive_json()
            user_text = data.get("mensaje", "")
            incidente_id = data.get("incidente_id")

            if user_text:
                res = await emergency_orchestrator.process_interaction(
                    db=db,
                    session_id=session_id,
                    user_message=user_text,
                    channel="WebSocket",
                    incidente_id=incidente_id,
                    generate_audio=True
                )
                await websocket.send_json({
                    "tipo": "respuesta",
                    "data": res
                })
    except WebSocketDisconnect:
        logger.info(f"WebSocket desconectado: session_id={session_id}")
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")


# =====================================================================
# Servir Frontend Web Estático
# =====================================================================
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", summary="Consola Comercial y de Ventas - Cel Red")
    async def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
