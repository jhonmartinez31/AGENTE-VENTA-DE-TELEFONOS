"""
Orquestador Comercial y Máquina de Estados de Ventas — CEL RED
Asesor Comercial Multimodal IA (Tienda de Celulares y Accesorios - Mocoa, Putumayo)

Integra las 72 referencias oficiales reales de contado:
- Android Nuevos (Infinix, Samsung, Oppo, Redmi, POCO, Honor, Tecno, Itel)
- iPhone Nuevos Activos / Sellados, Samsung Gama Alta (S25 Ultra, S26 Ultra, A57 5G), MacBook Neo e iPad A16
- iPhone Open Box (Seminuevos garantizados con valor menor frente al equipo nuevo)
"""

import os
import sys
import re
import time
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from database import (  # type: ignore
        Producto, Incidente, Interaccion, PrioridadIncidente, EstadoIncidente,
        CanalAtencion, TipoEvento, IncidenteResponse, ProtocoloRAG, utc_now
    )
    from vector_store import search_relevant_protocols, format_rag_context  # type: ignore
    from tts_service import synthesize_speech  # type: ignore
    from platform_prices import get_platform_info, format_platform_summary_markdown  # type: ignore
except ImportError:
    from backend.database import (  # type: ignore
        Producto, Incidente, Interaccion, PrioridadIncidente, EstadoIncidente,
        CanalAtencion, TipoEvento, IncidenteResponse, ProtocoloRAG, utc_now
    )
    from backend.vector_store import search_relevant_protocols, format_rag_context  # type: ignore
    from backend.tts_service import synthesize_speech  # type: ignore
    from backend.platform_prices import get_platform_info, format_platform_summary_markdown  # type: ignore

logger = logging.getLogger("orchestrator_celred")
logger.setLevel(logging.INFO)

CLAUSULA_COMERCIAL_CELRED = (
    "REGLA COMERCIAL E INVIOLABLE DE CEL RED: Eres el asesor comercial oficial de Cel Red. "
    "NUNCA inventes precios, existencias de inventario ni autorices descuentos fuera del sistema SysCafé/PostgreSQL. "
    "Aclara siempre cuando un iPhone sea Open Box (Seminuevo garantizado, razón por la cual su precio es menor frente al nuevo)."
)


def format_cop(valor: int) -> str:
    """Formatea un entero en pesos colombianos: 1150000 -> '$1.150.000'"""
    return "$" + f"{int(valor):,}".replace(",", ".")


def _hundreds_to_spanish(n: int) -> str:
    """Convierte un número entre 1 y 999 a español hablado natural."""
    if n == 0:
        return ""
    if n == 100:
        return "cien"

    centenas = [
        "", "ciento", "doscientos", "trescientos", "cuatrocientos",
        "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos"
    ]
    especiales = {
        1: "un", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco",
        6: "seis", 7: "siete", 8: "ocho", 9: "nueve", 10: "diez",
        11: "once", 12: "doce", 13: "trece", 14: "catorce", 15: "quince",
        16: "dieciséis", 17: "diecisiete", 18: "dieciocho", 19: "diecinueve",
        20: "veinte", 21: "veintiún", 22: "veintidós", 23: "veintitrés",
        24: "veinticuatro", 25: "veinticinco", 26: "veintiséis", 27: "veintisiete",
        28: "veintiocho", 29: "veintinueve"
    }
    decenas = [
        "", "", "", "treinta", "cuarenta", "cincuenta",
        "sesenta", "setenta", "ochenta", "noventa"
    ]

    c = n // 100
    resto = n % 100
    partes = []
    if c > 0:
        partes.append(centenas[c])

    if resto in especiales:
        partes.append(especiales[resto])
    elif resto >= 30:
        d = resto // 10
        u = resto % 10
        if u == 0:
            partes.append(decenas[d])
        else:
            partes.append(f"{decenas[d]} y {especiales[u]}")

    return " ".join(partes).strip()


def price_to_spoken_spanish(valor: int) -> str:
    """
    Convierte cualquier valor numérico en COP a su lectura hablada natural en español
    (ej. 1840000 -> 'un millón ochocientos cuarenta mil pesos').
    """
    valor = int(valor)
    if valor <= 0:
        return "cero pesos"

    millones = valor // 1000000
    miles = (valor % 1000000) // 1000
    partes = []

    if millones == 1:
        partes.append("un millón")
    elif millones > 1:
        partes.append(f"{_hundreds_to_spanish(millones)} millones")

    if miles == 1:
        partes.append("mil")
    elif miles > 1:
        partes.append(f"{_hundreds_to_spanish(miles)} mil")

    return " ".join(partes) + " pesos"


class EmergencyOrchestrator:
    """
    Orquestador Comercial de CEL RED con el catálogo real de 72 equipos de contado
    (Android Nuevos, iPhone/Samsung Nuevos y Open Box Seminuevos).
    """

    def __init__(self):
        self.system_prompt = (
            f"Eres el Asesor Comercial Inteligente de 'CEL RED', tienda de celulares y tecnología.\n"
            f"{CLAUSULA_COMERCIAL_CELRED}"
        )

    async def process_interaction(
        self,
        db: AsyncSession,
        session_id: str,
        user_message: str,
        channel: str = "Texto",
        incidente_id: Optional[int] = None,
        generate_audio: bool = True,
        texto_transcrito: Optional[str] = None
    ) -> Dict[str, Any]:
        session_id = session_id or str(uuid.uuid4())

        orden = None
        if incidente_id:
            res = await db.execute(select(Incidente).where(Incidente.id == incidente_id))
            orden = res.scalar_one_or_none()

        prod_res = await db.execute(select(Producto).order_by(Producto.precio_cop.asc()))
        catalogo: List[Producto] = list(prod_res.scalars().all())

        rag_results = await search_relevant_protocols(db, user_message, top_k=2)
        rag_context = format_rag_context(rag_results)

        analysis = await self._analyze_sales_input(user_message, catalogo, orden)

        intencion = analysis["prioridad"]
        linea_producto = analysis["tipo_evento"]
        modalidad_pago = analysis["ubicacion"]
        estado_orden = analysis["estado_sugerido"]
        es_cierre_confirmado = estado_orden in [EstadoIncidente.ESCALADO.value, EstadoIncidente.CERRADO.value]
        ahora = utc_now()

        if (
            orden is not None
            and analysis.get("cambio_explicito_modelo", False)
            and analysis.get("producto_principal") is not None
            and analysis["producto_principal"].modelo not in (orden.tipo_evento or "")
        ):
            orden = None

        if orden is None:
            codigo = f"ORD-{ahora.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
            escalado_entidad = analysis.get("sede_asignada") or (
                "Caja SysCafé / Facturación y Entrega Cel Red" if es_cierre_confirmado else "Candado de Confirmación Activo"
            )

            orden = Incidente(
                codigo=codigo,
                descripcion=user_message,
                ubicacion=modalidad_pago,
                municipio=analysis.get("sede_asignada") or "Sede Principal Cel Red - Mocoa",
                hora_incidente=ahora,
                tipo_evento=linea_producto,
                prioridad=intencion,
                estado=estado_orden,
                canal_atencion=channel,
                detalles_victimas=analysis.get("resumen_financiero") or None,
                acciones_recomendadas=analysis.get("acciones_recomendadas", ""),
                escalado_a=escalado_entidad,
                creado_en=ahora,
                actualizado_en=ahora
            )
            db.add(orden)
            await db.flush()
        else:
            orden.prioridad = intencion
            orden.estado = estado_orden
            if linea_producto and linea_producto != TipoEvento.OTRO.value:
                orden.tipo_evento = linea_producto
            if modalidad_pago:
                orden.ubicacion = modalidad_pago
            if analysis.get("sede_asignada"):
                orden.municipio = analysis["sede_asignada"]
                orden.escalado_a = analysis["sede_asignada"]
            elif es_cierre_confirmado:
                orden.escalado_a = "Caja SysCafé / Facturación y Entrega Cel Red"
            if analysis.get("resumen_financiero"):
                orden.detalles_victimas = analysis["resumen_financiero"]
            if analysis.get("acciones_recomendadas"):
                orden.acciones_recomendadas = analysis["acciones_recomendadas"]
            orden.descripcion = f"{orden.descripcion} | Cliente: {user_message}"
            orden.actualizado_en = ahora

        agent_reply = await self._generate_sales_response(
            user_message=user_message,
            analysis=analysis,
            rag_context=rag_context,
            orden=orden
        )

        # Inyectar dinámicamente enseñanzas/tips del Asesor Jhon si aplican a la consulta del cliente (excepto en saludos iniciales)
        jhon_tip = None
        if analysis.get("etapa_conversacion") != "saludo_inicial":
            jhon_tip = await self._find_matching_advisor_tip(db, user_message, rag_results)
        if jhon_tip:
            agent_reply += (
                f"\n\n💡 **Tip de nuestro Asesor Comercial Jhon ({jhon_tip['titulo']}):** "
                f"{jhon_tip['contenido']}"
            )
            if jhon_tip["titulo"] not in [p["titulo"] for p in rag_results]:
                rag_results.append({
                    "titulo": f"Tip Asesor Jhon: {jhon_tip['titulo']}",
                    "categoria": jhon_tip["categoria"],
                    "contenido": jhon_tip["contenido"],
                    "fuente": "Asesor Jhon - Cel Red",
                    "similitud": 0.99
                })

        audio_filename = None
        if generate_audio:
            spoken_text = self._build_conversational_spoken_script(
                orden=orden,
                analysis=analysis
            )
            if jhon_tip:
                tip_spoken = self._prepare_spoken_text(
                    f"Además, te comparto este consejo especial de nuestro asesor Jhon: {jhon_tip['contenido']}"
                )
                spoken_text = f"{spoken_text} {tip_spoken}".strip()
            audio_filename = await synthesize_speech(spoken_text)

        audio_url = f"/api/audio/{audio_filename}" if audio_filename else None

        interaccion_user = Interaccion(
            incidente_id=orden.id,
            session_id=session_id,
            rol="usuario",
            mensaje=user_message,
            canal=channel,
            creado_en=ahora
        )
        db.add(interaccion_user)

        interaccion_agente = Interaccion(
            incidente_id=orden.id,
            session_id=session_id,
            rol="agente",
            mensaje=agent_reply,
            canal=channel,
            audio_path=audio_filename,
            creado_en=ahora
        )
        db.add(interaccion_agente)

        await db.commit()
        await db.refresh(orden)

        return {
            "session_id": session_id,
            "respuesta_texto": agent_reply,
            "texto_transcrito": texto_transcrito or (user_message if channel == "Voz" else None),
            "incidente": IncidenteResponse.model_validate(orden),
            "audio_url": audio_url,
            "protocolos_utilizados": [p["titulo"] for p in rag_results],
            "prioridad_detectada": orden.prioridad,
            "estado_incidente": orden.estado,
            "alerta_escalamiento": es_cierre_confirmado
        }

    async def _find_matching_advisor_tip(
        self,
        db: AsyncSession,
        user_message: str,
        rag_results: List[Dict[str, Any]]
    ) -> Optional[Dict[str, str]]:
        """
        Busca si alguno de los tips enseñados por el Asesor Jhon (`fuente == 'Asesor Jhon - Cel Red'`)
        guarda relación con lo que el cliente está preguntando, para aplicarlo de inmediato.
        """
        try:
            stmt = (
                select(ProtocoloRAG)
                .where(ProtocoloRAG.fuente == "Asesor Jhon - Cel Red")
                .order_by(ProtocoloRAG.id.desc())
            )
            res = await db.execute(stmt)
            tips = list(res.scalars().all())
            if not tips:
                return None

            msg_low = user_message.lower()
            stopwords = {
                "para", "como", "cual", "cuál", "este", "esta", "estos", "estas", "tiene", "tienen",
                "quiero", "quisiera", "puedo", "puede", "hola", "buenas", "buenos", "donde", "dónde",
                "cuando", "cuándo", "porque", "porqué", "celular", "celulares", "tienda", "cliente"
            }

            best_tip = None
            best_score = 0
            for t in tips:
                texto_tip = f"{t.titulo} {t.categoria} {t.contenido}".lower()
                palabras = [
                    w for w in re.findall(r"[a-záéíóúñ0-9]{4,}", f"{t.titulo} {t.contenido}".lower())
                    if w not in stopwords
                ]
                score = sum(2 for w in set(palabras) if w in msg_low)
                if t.titulo.lower() in msg_low:
                    score += 5
                if score > best_score:
                    best_score = score
                    best_tip = t

            if best_tip and best_score >= 2:
                return {
                    "titulo": best_tip.titulo,
                    "categoria": best_tip.categoria,
                    "contenido": best_tip.contenido
                }
        except Exception as e:
            logger.warning(f"Error consultando tips del asesor Jhon: {e}")
        return None

    def _get_colombia_greeting(self) -> str:
        """
        Retorna el saludo horario correspondiente a la hora actual en Colombia (UTC-5):
        - 05:00 a 11:59 -> 'buenos días'
        - 12:00 a 18:59 -> 'buenas tardes'
        - 19:00 a 04:59 -> 'buenas noches'
        """
        hora_col = (datetime.now(timezone.utc) - timedelta(hours=5)).hour
        if 5 <= hora_col < 12:
            return "buenos días"
        elif 12 <= hora_col < 19:
            return "buenas tardes"
        else:
            return "buenas noches"

    def _detect_sede_cercana(self, text_lower: str) -> Optional[Dict[str, str]]:
        """
        Detecta cualquiera de las 14 sedes oficiales de Cel Red según la ciudad, barrio o centro comercial mencionado.
        """
        horario_general = "Lunes a Sábado de 8:30 a.m. a 7:30 p.m. (Jornada continua)"

        # 1. PUERTO ASÍS / PUTUMAYO
        if re.search(r"\b(puerto\s*as[ií]s|barrio\s*el\s*carmen|calle\s*10\s*no\s*24|sede\s*1)\b", text_lower):
            return {
                "nombre": "Sede Puerto Asís — Putumayo",
                "direccion": "CALLE 10 NO 24 - 18 BARRIO EL CARMEN (PUERTO ASÍS / PUTUMAYO)",
                "horario": horario_general
            }

        # 2. MOCOA / PUTUMAYO
        if re.search(r"\b(mocoa|avenida\s*colombia|av\.?\s*colombia|cra\.?\s*9\s*#\s*10|sede\s*2)\b", text_lower):
            return {
                "nombre": "Sede Mocoa — Putumayo",
                "direccion": "CRA 9 # 10 - 30 AVENIDA COLOMBIA (MOCOA / PUTUMAYO)",
                "horario": horario_general
            }

        # 3. LA HORMIGA - VALLE DEL GUAMUEZ / PUTUMAYO
        if re.search(r"\b(hormiga|la\s*hormiga|valle\s*del\s*guamuez|guamuez|las\s*am[eé]ricas|alcald[ií]a\s*municipal|sede\s*3)\b", text_lower):
            return {
                "nombre": "Sede La Hormiga — Valle del Guamuez",
                "direccion": "BARRIO CENTRAL LAS AMERICAS CARRERA 5 - #7-16 A UN COSTADO DE LA ALCALDÍA MUNICIPAL (HORMIGA VALLE DEL GUAMUEZ)",
                "horario": horario_general
            }

        # 4. ORITO / PUTUMAYO
        if re.search(r"\b(orito|marco\s*fidel|distrisur|calle\s*8\s*#\s*10|sede\s*4)\b", text_lower):
            return {
                "nombre": "Sede Orito — Putumayo",
                "direccion": "CALLE 8 # 10 - 47 BARRIO MARCO FIDEL SUAREZ AL LADO DE DISTRISUR (ORITO / PUTUMAYO)",
                "horario": horario_general
            }

        # 5, 6 y 7. IPIALES / NARIÑO (3 Sedes: Ed. Markus, CC Zafiro Local 123, CC Victoria Plaza Local 101A)
        if re.search(r"\b(zafiro|local\s*123|cra\s*6\s*no\s*11|sede\s*6)\b", text_lower):
            return {
                "nombre": "Sede Ipiales — CC Zafiro Local 123 (Nariño)",
                "direccion": "CRA 6 NO 11 - 51 CC ZAFIRO LOCAL 123 (IPIALES / NARIÑO)",
                "horario": horario_general
            }
        if re.search(r"\b(victoria\s*plaza|local\s*101a?|cra\s*7\s*no\s*9|sede\s*7)\b", text_lower):
            return {
                "nombre": "Sede Ipiales — CC Victoria Plaza Local 101A (Nariño)",
                "direccion": "CRA 7 NO 9 - 56 CC VICTORIA PLAZA LOCAL 101A (IPIALES / NARIÑO)",
                "horario": horario_general
            }
        if re.search(r"\b(markus|ed\s*markus|edificio\s*markus|cra\s*6\s*no\s*13|sede\s*5)\b", text_lower):
            return {
                "nombre": "Sede Ipiales — Esquina Edificio Markus (Nariño)",
                "direccion": "CRA 6 NO 13 - 05 ESQUINA ED MARKUS (IPIALES / NARIÑO)",
                "horario": horario_general
            }
        if re.search(r"\b(ipiales)\b", text_lower):
            return {
                "nombre": "Sedes Ipiales — Nariño (3 Puntos de Atención)",
                "direccion": (
                    "1) CRA 6 NO 13 - 05 ESQUINA ED MARKUS | "
                    "2) CRA 6 NO 11 - 51 CC ZAFIRO LOCAL 123 | "
                    "3) CRA 7 NO 9 - 56 CC VICTORIA PLAZA LOCAL 101A (IPIALES / NARIÑO)"
                ),
                "horario": horario_general
            }

        # 8, 9 y 10. PASTO / NARIÑO (3 Sedes: Calle 16 Centro, CC Pasaje El Liceo Local 103, CC Sebastián de Belalcázar Local 6A)
        if re.search(r"\b(pasaje\s*el\s*liceo|el\s*liceo|liceo|local\s*103|calle\s*17\s*#\s*26|sede\s*9)\b", text_lower):
            return {
                "nombre": "Sede Pasto — CC Pasaje El Liceo Local 103 (Nariño)",
                "direccion": "CALLE 17 # 26 - 60 CC PASAJE EL LICEO LOCAL 103 (PASTO / NARIÑO)",
                "horario": horario_general
            }
        if re.search(r"\b(sebasti[aá]n\s*de\s*belalc[aá]zar|belalc[aá]zar|local\s*6a|sede\s*10)\b", text_lower):
            return {
                "nombre": "Sede Pasto — CC Sebastián de Belalcázar Local 6A (Nariño)",
                "direccion": "CC SEBASTIAN DE BELALCAZAR LOCAL 6A (PASTO / NARIÑO)",
                "horario": horario_general
            }
        if re.search(r"\b(calle\s*16\s*no\s*23|23\s*-\s*82|sede\s*8)\b", text_lower):
            return {
                "nombre": "Sede Pasto — Calle 16 Centro Local 1 (Nariño)",
                "direccion": "CALLE 16 NO 23 - 82 LOCAL 1 - CENTRO (PASTO / NARIÑO)",
                "horario": horario_general
            }
        if re.search(r"\b(pasto)\b", text_lower):
            return {
                "nombre": "Sedes Pasto — Nariño (3 Puntos de Atención)",
                "direccion": (
                    "1) CALLE 16 NO 23 - 82 LOCAL 1 - CENTRO | "
                    "2) CALLE 17 # 26 - 60 CC PASAJE EL LICEO LOCAL 103 | "
                    "3) CC SEBASTIAN DE BELALCAZAR LOCAL 6A (PASTO / NARIÑO)"
                ),
                "horario": horario_general
            }

        # 11. TÚQUERRES / NARIÑO
        if re.search(r"\b(t[uú]querres|cra\s*14\s*-\s*cll\s*20|sede\s*11)\b", text_lower):
            return {
                "nombre": "Sede Túquerres — Nariño",
                "direccion": "CRA 14 - CLL 20 ESQUINA - TUQUERRES (TUQUERRES / NARIÑO)",
                "horario": horario_general
            }

        # 12. MEDELLÍN / ANTIOQUIA
        if re.search(r"\b(medell[ií]n|antioqu[ií]a|premium\s*plaza|local\s*1301|sede\s*12)\b", text_lower):
            return {
                "nombre": "Sede Medellín — CC Premium Plaza Local 1301 (Antioquia)",
                "direccion": "CENTRO COMERCIAL PREMIUM PLAZA LOCAL 1301 (MEDELLÍN / ANTIOQUÍA)",
                "horario": horario_general
            }

        # 13. NEIVA / HUILA
        if re.search(r"\b(neiva|huila|cra\.?\s*2\s*#\s*6|local\s*5|sede\s*13)\b", text_lower):
            return {
                "nombre": "Sede Neiva — Centro Local 5",
                "direccion": "CRA.2 # 6 - 26 - LOCAL 5 - CENTRO (NEIVA)",
                "horario": horario_general
            }

        # 14. LA UNIÓN / NARIÑO
        if re.search(r"\b(la\s*uni[oó]n|cuevas\s*leiva|parque\s*cuevas|cra\s*1\s*#\s*11|sede\s*14)\b", text_lower):
            return {
                "nombre": "Sede La Unión — Frente al Parque Cuevas Leiva",
                "direccion": "CRA 1 # 11- 81 – FRENTE AL PARQUE CUEVAS LEIVA (LA UNION)",
                "horario": horario_general
            }

        return None

    def _get_iphone_obsequio(self, prod: Optional[Producto]) -> Optional[str]:
        """
        Retorna el obsequio o combo oficial incluido según la tabla de Obsequios de Cel Red.
        """
        if not prod:
            return None
        mapa_obsequios = {
            "OBX-APL-IP13-128": "Estuche y Vidrio templado",
            "NEW-APL-IP13-128": "Estuche y Vidrio templado",
            "OBX-APL-IP13PM-128": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
            "OBX-APL-IP14P-128": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
            "OBX-APL-IP14PM-128": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
            "OBX-APL-IP15-128": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
            "NEW-APL-IP15-128": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
            "OBX-APL-IP15P-128": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
            "OBX-APL-IP15PM-256": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
            "OBX-APL-IP16-128": "COMBO 4 (Cubo, Cable, Estuche, Vidrio y AirPods)",
            "NEW-APL-IP16-128": "COMBO 4 (Cubo, Cable, Estuche, Vidrio y AirPods)",
            "OBX-APL-IP16P-128": "COMBO 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche)",
            "OBX-APL-IP16P-256": "COMBO 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche)",
            "OBX-APL-IP16PM-256": "COMBO 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche)",
        }
        return mapa_obsequios.get(prod.sku)

    def _match_products_from_catalog(self, text_lower: str, catalogo: List[Producto]) -> List[Producto]:
        """
        Busca coincidencias exactas en las 69 referencias reales de Cel Red (iPhone desde el 13 en adelante):
        distingue modelos (ej. iPhone 15 vs 15 Pro vs 15 Pro Max), capacidad (128/256/512)
        y estado (Nuevo vs Open Box Seminuevo).
        """
        menciona_open_box = bool(re.search(r"\b(open\s*box|seminuevo\w*|semi\s*nuevo\w*|segunda|usado\w*)\b", text_lower))
        menciona_nuevo = bool(re.search(r"(?<!semi\s)\b(nuevo\w*|sellado\w*|activo\w*)\b", text_lower))
        pide_open_box = menciona_open_box and not menciona_nuevo
        pide_nuevo = menciona_nuevo and not menciona_open_box

        # Detectar capacidad específica si el usuario la menciona
        cap_512 = bool(re.search(r"\b512\s*(?:gb|gigas)?\b", text_lower))
        cap_256 = bool(re.search(r"\b256\s*(?:gb|gigas)?\b", text_lower))
        cap_128 = bool(re.search(r"\b128\s*(?:gb|gigas)?\b", text_lower))

        candidates: List[Producto] = []

        # 1. Búsqueda específica de modelos iPhone (únicamente desde el iPhone 13 hasta el 17, Base / Pro / Pro Max)
        # Soporta con o sin la palabra 'iphone' cuando dice 'pro max', 'promax' o 'pro' (ej. '15 pro max', 'iphone 15 promax')
        pide_iphone_plus_o_mini = bool(re.search(
            r"\b(?:iphone\s*)?(13|14|15|16|17)\s*(plus|mini)\b",
            text_lower
        ))
        ip_match = None if pide_iphone_plus_o_mini else re.search(
            r"\biphone\s*(13|14|15|16|17)(?:\s*(pro\s*max|promax|pro))?\b"
            r"|(?<!note\s)(?<!redmi\s)(?<!spark\s)(?<!camon\s)(?<!hot\s)\b(13|14|15|16|17)\s*(pro\s*max|promax|pro)\b",
            text_lower
        )
        if ip_match:
            num = ip_match.group(1) or ip_match.group(3)
            raw_var = (ip_match.group(2) or ip_match.group(4) or "").strip()
            if "max" in raw_var:
                variante = "pro max"
            elif "pro" in raw_var:
                variante = "pro"
            else:
                variante = ""
            for p in catalogo:
                m = p.modelo.lower()
                if f"iphone {num}" not in m:
                    continue
                es_pm = "pro max" in m
                es_p = (" pro " in m or m.endswith(" pro")) and not es_pm
                if variante == "pro max" and not es_pm:
                    continue
                if variante == "pro" and not es_p:
                    continue
                if variante == "" and (es_pm or es_p):
                    continue
                candidates.append(p)

        # 2. Búsqueda de MacBook o iPad
        if not candidates and ("macbook" in text_lower or "mac " in text_lower or "portatil" in text_lower or "portátil" in text_lower):
            candidates = [p for p in catalogo if "macbook" in p.modelo.lower()]
        if not candidates and ("ipad" in text_lower or "tablet" in text_lower):
            candidates = [p for p in catalogo if "ipad" in p.modelo.lower()]

        # 3. Búsqueda de modelos Android específicos por referencia exacta (soportando espacios como '15 c', '14 c', 'a 5x', '60 i')
        if not candidates:
            patrones_android = [
                (r"\bhot\s*70\b", "hot 70"),
                (r"\bhot\s*60\s*pro\s*(?:plus|\+)\b", "hot 60 pro plus"),
                (r"\bhot\s*60\s*pro\b", "hot 60 pro ("),
                (r"\bhot\s*60\s*i\b|\b60\s*i\b", "hot 60i"),
                (r"\bhot\s*60(?!\s*i|\s*pro)\b", "hot 60 ("),
                (r"\bsmart\s*10\b", "smart 10"),
                (r"\bnote\s*edge\b", "note edge"),
                (r"\ba\s*5\s*x\b", "a5x"),
                (r"\boppo\s*a\s*5(?!\s*x)\b", "oppo a5 ("),
                (r"\bredmi\s*a\s*5\b", "redmi a5"),
                (r"\bsamsung\s*a\s*0?5\b|\ba\s*05\b", "a05"),
                (r"\ba\s*0?7(?!\s*pro)\b", "a07"),
                (r"\ba\s*16\b", "a16"),
                (r"\ba\s*17\b", "a17"),
                (r"\ba\s*26\b", "a26"),
                (r"\ba\s*36\b", "a36"),
                (r"\ba\s*37\b", "a37"),
                (r"\ba\s*56\b", "a56"),
                (r"\ba\s*57\b", "a57"),
                (r"\bs\s*25\b", "s25 ultra"),
                (r"\bs\s*26\b", "s26 ultra"),
                (r"\ba\s*60\b", "a60"),
                (r"\ba\s*80\b", "a80"),
                (r"\ba\s*7\s*pro\b|\bredmi\s*a\s*7\b", "a7 pro"),
                (r"\b14\s*c\b", "14c"),
                (r"\b15\s*c\b", "15c"),
                (r"\bnote\s*14\s*pro\b", "note 14 pro"),
                (r"\bnote\s*14(?!\s*pro)\b", "note 14 4g"),
                (r"\bnote\s*17\b", "note 17"),
                (r"\bnote\s*15\s*pro\b", "note 15 pro"),
                (r"\bnote\s*15(?!\s*pro)\b", "redmi note 15 ("),
                (r"\bredmi\s*15(?!\s*c)\b", "redmi 15 ("),
                (r"\bredmi\s*17\b", "redmi 17 ("),
                (r"\bf\s*8\s*pro\b|\bpoco\s*f\s*8\b", "f8 pro"),
                (r"\bx\s*8\s*pro\s*max\b|\bpoco\s*x\s*8\s*pro\s*max\b", "x8 pro max"),
                (r"\bx\s*8\s*pro(?!\s*max)\b|\bpoco\s*x\s*8\s*pro(?!\s*max)\b", "poco x8 pro ("),
                (r"\bx\s*8\b|\bpoco\s*x\s*8\b", "x8 pro max"),
                (r"\bhonor\s*400\b|\b400\s*smart\b|\bsmart\s*400\b", "honor 400"),
                (r"\bc\s*75\b", "c75"),
                (r"\b60\s*x\b|\bnote\s*60\s*x\b", "note 60x"),
                (r"\bnote\s*70\b", "note 70"),
                (r"\bcamon\s*50\s*ultra\b", "camon 50 ultra"),
                (r"\bcamon\s*50\s*pro\b", "camon 50 pro"),
                (r"\bcamon\s*50\b", "camon 50"),
                (r"\bpova\s*curve\s*2\b|\bcurve\s*2\b", "pova curve 2"),
                (r"\bpop\s*5\b", "pop 5 go"),
                (r"\bspark\s*go\s*2\b|\bgo\s*2\b", "spark go 2"),
                (r"\bspark\s*go\s*3\b|\bgo\s*3\b", "spark go 3"),
                (r"\bspark\s*40\s*pro\b", "spark 40 pro plus"),
                (r"\bspark\s*40(?!\s*pro)\b", "spark 40 ("),
                (r"\bspark\s*50\b", "spark 50"),
                (r"\bitel\s*a\s*100\s*c?\b|\ba\s*100\s*c?\b|\b100\s*c\b", "itel a100c"),
            ]
            for regex_pat, sub_str in patrones_android:
                if re.search(regex_pat, text_lower):
                    candidates = [p for p in catalogo if sub_str in p.modelo.lower()]
                    if candidates:
                        break

        # Aplicar filtros de capacidad (128 / 256 / 512) si hay varios candidatos del mismo modelo
        if len(candidates) > 1:
            if cap_512:
                filt = [p for p in candidates if "512" in p.modelo.lower()]
                if filt:
                    candidates = filt
            elif cap_256:
                filt = [p for p in candidates if "256" in p.modelo.lower()]
                if filt:
                    candidates = filt
            elif cap_128:
                filt = [p for p in candidates if "128" in p.modelo.lower()]
                if filt:
                    candidates = filt

        # Aplicar filtro de Nuevo vs Open Box (Seminuevo) si el cliente lo especificó
        if len(candidates) > 1:
            if pide_open_box:
                filt = [p for p in candidates if "open box" in p.categoria.lower() or "open box" in p.modelo.lower()]
                if filt:
                    candidates = filt
            elif pide_nuevo:
                filt = [p for p in candidates if "nuevo" in p.categoria.lower() and "open box" not in p.modelo.lower()]
                if filt:
                    candidates = filt

        return candidates

    def _detect_unavailable_model(
        self,
        text_lower: str,
        catalogo: List[Producto]
    ) -> Optional[Dict[str, Any]]:
        """
        Detecta cuando el cliente pregunta por un celular o marca que NO manejamos en Cel Red
        (ej. Motorola, Huawei, Vivo, ZTE, Pixel, o referencias de Samsung, Redmi, POCO, Tecno,
        Infinix, Oppo, Honor, Realme o iPhone que no están en nuestro catálogo), y retorna
        el nombre del modelo consultado junto con las opciones similares disponibles.
        """
        # 1. iPhone 18, 19, 20 o superior (no los tenemos; manejamos del iPhone 13 al iPhone 17)
        m_ip_18 = re.search(
            r"\b(?:iphone\s*)(18|19|20)(?:\s*(pro\s*max|promax|pro|plus|mini|ultra|air))?\b"
            r"|(?<!note\s)(?<!redmi\s)(?<!spark\s)(?<!camon\s)(?<!hot\s)\b(18|19|20)\s*(pro\s*max|promax|pro)\b",
            text_lower
        )
        if m_ip_18:
            num = m_ip_18.group(1) or m_ip_18.group(3)
            var_raw = (m_ip_18.group(2) or m_ip_18.group(4) or "").strip()
            if "max" in var_raw:
                var_str = " Pro Max"
                skus_sim = ["OBX-APL-IP17PM-256", "NEW-APL-IP17PM-256", "OBX-APL-IP16PM-256"]
            elif "pro" in var_raw:
                var_str = " Pro"
                skus_sim = ["OBX-APL-IP17P-256", "NEW-APL-IP17P-256", "OBX-APL-IP16P-256"]
            else:
                var_str = f" {var_raw.title()}" if var_raw else ""
                skus_sim = ["NEW-APL-IP17-256", "OBX-APL-IP17P-256", "OBX-APL-IP16-128", "OBX-APL-IP16PM-256"]
            similares = [p for p in catalogo if p.sku in skus_sim]
            if not similares:
                similares = [p for p in catalogo if p.sku in ["OBX-APL-IP16PM-256", "OBX-APL-IP16-128", "OBX-APL-IP15PM-256"]]
            return {
                "modelo_pedido": f"iPhone {num}{var_str}",
                "similares": similares[:3]
            }

        # 1B. Versiones Plus, Mini o SE de iPhone (no las manejamos; manejamos Normal, Pro y Pro Max del 13 al 17)
        m_ip_plus = re.search(r"\b(?:iphone\s*)?(13|14|15|16|17)\s*(plus|mini)\b|\biphone\s*(se(?:\s*\d+)?)\b", text_lower)
        if m_ip_plus:
            if m_ip_plus.group(3):
                modelo_str = f"iPhone {m_ip_plus.group(3).upper()}"
                skus_sim = ["OBX-APL-IP13-128", "NEW-APL-IP13-128", "OBX-APL-IP15-128"]
            else:
                num = m_ip_plus.group(1)
                var = m_ip_plus.group(2).capitalize()
                modelo_str = f"iPhone {num} {var}"
                skus_sim = [f"OBX-APL-IP{num}-128", f"NEW-APL-IP{num}-128", f"OBX-APL-IP{num}PM-256", f"OBX-APL-IP{num}PM-128"]
            similares = [p for p in catalogo if p.sku in skus_sim]
            if not similares:
                similares = [p for p in catalogo if p.sku in ["OBX-APL-IP15-128", "OBX-APL-IP15PM-256", "OBX-APL-IP13-128"]]
            return {
                "modelo_pedido": modelo_str,
                "similares": similares[:3]
            }

        # 2. Marcas que no manejamos (Motorola/Moto, Huawei, Vivo, ZTE, Nokia, Pixel, OnePlus, Alcatel, Kalley, TCL)
        m_marca = re.search(
            r"\b(motorola(?:\s+(?:edge|moto|g|e)?\s*[a-z0-9]{1,6})?|moto\s*(?:g|e|edge)\s*[a-z0-9]{0,5}|huawei(?:\s+[a-z0-9]{1,8})?|vivo(?:\s+[a-z0-9]{1,6})?|zte(?:\s+[a-z0-9]{1,6})?|nokia(?:\s+[a-z0-9]{1,6})?|(?:google\s+)?pixel(?:\s+[a-z0-9]{1,6})?|one\s*plus(?:\s+[a-z0-9]{1,6})?|alcatel(?:\s+[a-z0-9]{1,6})?|kalley(?:\s+[a-z0-9]{1,6})?|tcl(?:\s+[a-z0-9]{1,6})?)\b",
            text_lower
        )
        if m_marca:
            nombre_m = m_marca.group(1).strip().title()
            similares = [p for p in catalogo if p.sku in ["AND-SAM-A17-256", "AND-RED-N15P-256", "AND-OPPO-A80-256", "AND-TEC-CAM50P-256"]]
            return {
                "modelo_pedido": nombre_m,
                "similares": similares
            }

        # 3. Referencias de Samsung que no manejamos (ej. A14, A15, A24, A25, A34, A35, A54, A55, S21, S22, S23, S24, Z Flip, Z Fold)
        m_sam = re.search(
            r"\b(?:samsung\s*(?:galaxy\s*)?|galaxy\s*)?(a\s*(?:0[12346]|1[0123458]|2[012345]|3[012345]|5[012345]|7[0123])|s\s*(?:10|20|21|22|23|24)(?:\s*(?:ultra|plus|\+|fe))?|z\s*(?:flip|fold)\s*\d*)\b",
            text_lower
        )
        if m_sam:
            mod = re.sub(r"\s+", "", m_sam.group(1)).upper()
            if mod.startswith(("S", "Z", "A5")):
                skus_s = ["NEW-SAM-A57-256", "NEW-SAM-S25U-256", "NEW-SAM-S26U-256"]
            elif mod.startswith(("A3", "A2")):
                skus_s = ["AND-SAM-A26-256", "AND-SAM-A36-256", "AND-SAM-A37-256"]
            else:
                skus_s = ["AND-SAM-A05-128", "AND-SAM-A07-128", "AND-SAM-A16-128", "AND-SAM-A17-256"]
            return {
                "modelo_pedido": f"Samsung Galaxy {m_sam.group(1).upper()}",
                "similares": [p for p in catalogo if p.sku in skus_s]
            }

        # 4. Referencias de Xiaomi / Redmi que no manejamos (ej. Note 10, Note 11, Note 12, Note 13, Note 16, Redmi 12, 13C, 12C, Xiaomi 13T/14T)
        m_red = re.search(
            r"\b(?:xiaomi\s*|redmi\s*)?(note\s*(?:8|9|10|11|12|13|16)(?:\s*pro)?(?:\s*max|\s*plus|\s*5g)?|(?:10|12|13)\s*c|redmi\s*(?:9|10|11|12|13|a[123])|xiaomi\s*(?:11|12|13|14)(?:\s*t)?(?:\s*pro)?)\b",
            text_lower
        )
        if m_red:
            raw_r = m_red.group(1).strip().title()
            label_r = raw_r if ("Redmi" in raw_r or "Xiaomi" in raw_r) else f"Redmi {raw_r}"
            if "note" in raw_r.lower() or "pro" in raw_r.lower() or "xiaomi" in raw_r.lower():
                skus_r = ["AND-RED-N15-256", "AND-RED-N15P-256", "AND-RED-N17-256-8"]
            else:
                skus_r = ["AND-RED-A5-128", "AND-RED-15C-256", "AND-RED-15-256"]
            return {
                "modelo_pedido": label_r,
                "similares": [p for p in catalogo if p.sku in skus_r]
            }

        # 5. Referencias de POCO que no manejamos (ej. POCO X3, X4, X5, X6, X7, F3, F4, F5, F6, F7, M4, M5, M6)
        m_poco = re.search(
            r"\b(?:poco\s*)?(x\s*[34567]|f\s*[34567]|m\s*[3456])\s*(?:pro)?(?:\s*max)?\b",
            text_lower
        )
        if m_poco:
            return {
                "modelo_pedido": f"POCO {m_poco.group(0).replace('poco', '').strip().upper()}",
                "similares": [p for p in catalogo if p.sku in ["AND-POC-F8P-256", "AND-POC-X8P-256", "AND-POC-X8PM-512"]]
            }

        # 6. Referencias de Tecno, Infinix, Oppo, Honor o Realme que no manejamos
        m_otros = re.search(
            r"\b(tecno\s+(?:spark\s*(?:10|20|30)|camon\s*(?:18|19|20|30|40)|pova\s*[23456])|spark\s*(?:10|20|30)|camon\s*(?:20|30|40)|pova\s*[3456]|infinix\s+(?:hot\s*(?:10|20|30|40|50)|note\s*(?:12|30|40|50)|zero\s*\w+|gt\s*\d+)|hot\s*(?:30|40|50)|oppo\s+(?:reno\s*\w*|a\s*(?:17|18|38|54|57|58|77|78|79|98))|reno\s*\d+|honor\s+(?:x\s*[56789]\w*|magic\s*\w*|90|200)|honor\s*x\w+|realme\s+(?:c\s*(?:11|21|30|33|35|51|53|55|65|67)|10|11|12|gt))\b",
            text_lower
        )
        if m_otros:
            raw_o = m_otros.group(1).strip().title()
            if "tecno" in raw_o.lower() or "spark" in raw_o.lower() or "camon" in raw_o.lower() or "pova" in raw_o.lower():
                skus_o = ["AND-TEC-SP40-256", "AND-TEC-POVAC2", "AND-TEC-CAM50P-256", "AND-TEC-CAM50U-256"]
            elif "infinix" in raw_o.lower() or "hot" in raw_o.lower():
                skus_o = ["AND-INF-HOT70-256", "AND-INF-HOT60PP-256", "AND-INF-NEDGE"]
            elif "oppo" in raw_o.lower() or "reno" in raw_o.lower():
                skus_o = ["AND-OPPO-A5X-128", "AND-OPPO-A60-256", "AND-OPPO-A80-256"]
            elif "honor" in raw_o.lower():
                skus_o = ["AND-HON-400S-256", "AND-RED-N17-256-8", "AND-SAM-A17-256"]
            else:
                skus_o = ["AND-RLM-C75-256", "AND-RLM-N60X-128", "AND-RLM-N70-256"]
            return {
                "modelo_pedido": raw_o,
                "similares": [p for p in catalogo if p.sku in skus_o]
            }

        return None

    async def _analyze_sales_input(
        self,
        text: str,
        catalogo: List[Producto],
        orden_actual: Optional[Incidente] = None
    ) -> Dict[str, Any]:
        text_lower = text.lower()

        # 1. Detectar medio de pago o plataforma financiera mencionada en este turno
        medios_pago = []
        if re.search(r"\b(efectivo|contado|plata en mano|billete\w*|en tienda)\b", text_lower):
            medios_pago.append("Efectivo en Tienda")
        if re.search(r"\b(nequi)\b", text_lower):
            medios_pago.append("Transferencia Nequi")
        if re.search(r"\b(daviplata)\b", text_lower):
            medios_pago.append("Daviplata")
        if re.search(r"\b(bancolombia|transferencia)\b", text_lower):
            medios_pago.append("Transferencia Bancolombia")
        if re.search(r"\b(sistecr[eé]dito)\b", text_lower):
            medios_pago.append("Crédito Sistecrédito")
        if re.search(r"\b(addi)\b", text_lower):
            medios_pago.append("Crédito Addi")
        if re.search(r"\b(banco\s*de\s*bogot[aá]|bogot[aá])\b", text_lower):
            medios_pago.append("Crédito Banco de Bogotá")
        if re.search(r"\b(krediya|crediya)\b", text_lower):
            medios_pago.append("Crédito Krediya")
        if re.search(r"\b(credim[oó]vil)\b", text_lower):
            medios_pago.append("Crédito Credimóvil")
        if re.search(r"\b(renting|reportad\w*|sin\s+historial|poco\s+historial|vida\s+crediticia)\b", text_lower):
            medios_pago.append("Plataforma Renting iPhone")
        if re.search(r"\b(tarjeta|d[eé]bito)\b", text_lower):
            medios_pago.append("Tarjeta Débito/Crédito")

        menciona_medio_pago = len(medios_pago) > 0

        medio_pago_previo = ""
        if orden_actual and orden_actual.ubicacion:
            m_prev = re.search(r"Pago(?:\s+Confirmado)?:\s*([^|]+)", orden_actual.ubicacion)
            if m_prev:
                medio_pago_previo = m_prev.group(1).strip()

        medio_pago_str = (
            " / ".join(medios_pago)
            if menciona_medio_pago
            else (medio_pago_previo or "Contado, Addi, Sistecrédito, Banco de Bogotá, Krediya, Credimóvil o Renting")
        )

        # 2. Detectar color elegido
        color_match = re.search(
            r"\b(negro|azul|rosa|rosado|verde|blanco|gris|titanio|amarillo|p[uú]rpura|morado|lila|magenta|naranja|silver|plata|vinotinto|oro|dorado|grafito)\b",
            text_lower
        )
        color_elegido = color_match.group(1).capitalize() if color_match else None

        # 3. Detectar sede o barrio
        sede_detectada = self._detect_sede_cercana(text_lower)

        # 4. Detectar intenciones especiales
        pide_descuento_no_autorizado = bool(re.search(
            r"\b(rebaja\w*|descuento del 50|mitad de precio|regalado|gratis|sin pagar|fiado sin inicial|modificar tabla|cambiar el precio)\b",
            text_lower
        ))
        es_separado_msg = bool(re.search(r"\b(separad\w*|separar\w*|abono|abonar|apartar\w*)\b", text_lower))
        es_compra_msg = bool(re.search(
            r"\b(lo compro|me lo llevo|me llevo|comprar\w*|confirmo|confirmar|factur\w*|hagamos el pedido|quiero llevarme|cerrar venta|listo|de una)\b",
            text_lower
        ))
        es_consulta_garantia = bool(re.search(r"\b(garant[ií]a\w*|imei|pol[ií]tica\w*|qu[eé] cubre|servicio t[eé]cnico)\b", text_lower))
        es_consulta_obsequios = bool(re.search(r"\b(obsequio\w*|regalo\w*|combo\w*|airpods|reloj|estuche|vidrio)\b", text_lower))
        es_consulta_plataformas = bool(re.search(
            r"\b(plataforma\w*|krediya|crediya|credim[oó]vil|renting|reportad\w*|historial\s*crediticio|vida\s*crediticia|banco\s*de\s*bogot[aá]|desembolso\w*)\b",
            text_lower
        ))
        es_consulta_sedes = bool(re.search(
            r"\b(direcci[oó]n\w*|sede\w*|ubicad\w*|ubicaci[oó]n\w*|d[oó]nde\s+quedan|d[oó]nde\s+est[aá]n|en\s+qu[eé]\s+ciudad\w*|sucursal\w*|punto\w*\s+de\s+atenci[oó]n|local\w*)\b",
            text_lower
        ))
        pide_iphone_omitido = bool(re.search(r"\biphone\s*(8|x|xr|xs|10|11|12)\b", text_lower))
        pide_open_box = bool(re.search(r"\b(open\s*box|seminuevo\w*|semi\s*nuevo\w*|segunda|usado\w*)\b", text_lower))

        menciona_credito_o_plataforma = bool(re.search(
            r"\b(cr[eé]dito\w*|financ\w*|cuota\w*|addi|sistecr[eé]dito|banco\s*de\s*bogot[aá]|bogot[aá]|krediya|crediya|credim[oó]vil|renting|reportad\w*|historial|inicial|plataforma\w*|separad\w*|separar\w*|abono)\b",
            text_lower
        ))
        menciona_contado_o_efectivo = bool(re.search(
            r"\b(contado|efectivo|de\s+contado|al\s+contado|en\s+efectivo|pago\s+de\s+contado)\b",
            text_lower
        ))
        pide_solo_contado = menciona_contado_o_efectivo and not menciona_credito_o_plataforma

        # 5. Buscar coincidencias exactas de producto en las 88 referencias reales
        equipos_mencionados = self._match_products_from_catalog(text_lower, catalogo)
        cambio_explicito_modelo = len(equipos_mencionados) > 0

        producto_en_orden: Optional[Producto] = None
        if orden_actual and orden_actual.tipo_evento:
            for p in catalogo:
                if p.modelo in orden_actual.tipo_evento:
                    producto_en_orden = p
                    break

        equipos_sugeridos: List[Producto] = list(equipos_mencionados)
        modelo_no_disponible: Optional[str] = None

        if pide_iphone_omitido and not equipos_sugeridos:
            equipos_sugeridos = [p for p in catalogo if p.sku in ["OBX-APL-IP13-128", "NEW-APL-IP13-128"]]

        if not equipos_sugeridos and not pide_iphone_omitido:
            info_no_disp = self._detect_unavailable_model(text_lower, catalogo)
            if info_no_disp:
                modelo_no_disponible = info_no_disp["modelo_pedido"]
                equipos_sugeridos = info_no_disp["similares"]

        if not equipos_sugeridos and producto_en_orden and (
            menciona_medio_pago or sede_detectada is not None or color_elegido is not None or es_compra_msg or es_separado_msg
        ):
            equipos_sugeridos = [producto_en_orden]

        # Si el cliente preguntó por una categoría/marca general o presupuesto
        if not equipos_sugeridos:
            if "renting" in text_lower or "reportad" in text_lower or "historial" in text_lower or "vida crediticia" in text_lower:
                equipos_sugeridos = [p for p in catalogo if p.sku in ["OBX-APL-IP13-128", "OBX-APL-IP15-128", "NEW-APL-IP15-128", "OBX-APL-IP16-128"]]
            elif "krediya" in text_lower or "crediya" in text_lower:
                equipos_sugeridos = [p for p in catalogo if p.sku in ["AND-SAM-A16-128", "AND-SAM-A05-128", "AND-RED-N15P-256", "AND-RED-N17-256-8"]]
            elif "credimovil" in text_lower or "credimóvil" in text_lower:
                equipos_sugeridos = [p for p in catalogo if p.sku in ["AND-SAM-A05-128", "AND-RED-15-256", "AND-RED-N17-256-8", "AND-SAM-A17-256"]]
            elif es_consulta_obsequios:
                equipos_sugeridos = [p for p in catalogo if p.sku in ["OBX-APL-IP13-128", "OBX-APL-IP15-128", "OBX-APL-IP16-128", "OBX-APL-IP16PM-256"]]
            elif pide_open_box:
                # Mostrar iPhones Open Box destacados desde el iPhone 13 en adelante
                equipos_sugeridos = [p for p in catalogo if p.sku in ["OBX-APL-IP13-128", "OBX-APL-IP14-128", "OBX-APL-IP15-128", "OBX-APL-IP16-128"]]
            elif "iphone" in text_lower:
                equipos_sugeridos = [p for p in catalogo if p.sku in ["OBX-APL-IP13-128", "NEW-APL-IP13-128", "OBX-APL-IP15-128", "NEW-APL-IP15-128"]]
            elif "samsung" in text_lower:
                equipos_sugeridos = [p for p in catalogo if p.sku in ["AND-SAM-A05-128", "AND-SAM-A17-256", "AND-SAM-A37-256", "NEW-SAM-S25U-256"]]
            elif "xiaomi" in text_lower or "redmi" in text_lower:
                equipos_sugeridos = [p for p in catalogo if p.sku in ["AND-RED-A5-128", "AND-RED-15-256", "AND-RED-N17-256-8", "AND-RED-N15P-256"]]
            elif "poco" in text_lower:
                equipos_sugeridos = [p for p in catalogo if "poco" in p.marca.lower()]
            elif "realme" in text_lower:
                equipos_sugeridos = [p for p in catalogo if "realme" in p.marca.lower()]
            elif "tecno" in text_lower:
                equipos_sugeridos = [p for p in catalogo if p.sku in ["AND-TEC-SP40-256", "AND-TEC-POVAC2", "AND-TEC-CAM50P-256", "AND-TEC-CAM50U-256"]]
            elif "infinix" in text_lower:
                equipos_sugeridos = [p for p in catalogo if "infinix" in p.marca.lower()]
            elif "oppo" in text_lower:
                equipos_sugeridos = [p for p in catalogo if "oppo" in p.marca.lower()]

        es_saludo_puro = bool(re.search(
            r"^\s*(hola+|buenos\s+d[ií]as|buen\s+d[ií]a|buenas\s+tardes|buenas\s+noches|buenas|saludos|qu[eé]\s+tal|c[oó]mo\s+est[aá]s?|hey|al[oó]|hay\s+alguien)[,\.\!\?\s]*$",
            text_lower
        ))
        pide_catalogo_general = bool(re.search(
            r"\b(cat[aá]logo\w*|recomend\w*|recomi[eé]nd\w*|qu[eé]\s+celulares|qu[eé]\s+equipos|mostrar\s+celulares|ver\s+celulares|opciones|lista\s+de\s+precios|android)\b",
            text_lower
        ))

        # Filtrado por presupuesto o perfil (cámara, gaming, económico)
        if not equipos_sugeridos and not es_saludo_puro:
            busca_camara = bool(re.search(r"\b(c[aá]mara\w*|foto\w*|fotograf[ií]a|video\w*|tiktok|redes)\b", text_lower))
            busca_gamer = bool(re.search(r"\b(juego\w*|jugar|gamer|gaming|potente|procesador|free fire|call of duty)\b", text_lower))
            busca_economico = bool(re.search(r"\b(econ[oó]mico\w*|barato\w*|bajo presupuesto|sencillo|350|400|500)\b", text_lower))
            busca_menos_1200 = bool(re.search(r"\b(1\.?200\.?000|mill[oó]n doscientos|1200000|menos de (?:un )?mill[oó]n)\b", text_lower))

            if busca_camara and busca_menos_1200:
                equipos_sugeridos = [p for p in catalogo if p.sku in ["AND-RED-N15P-256", "AND-SAM-A37-256", "OBX-APL-IP13-128"]]
            elif busca_camara:
                equipos_sugeridos = [p for p in catalogo if p.sku in ["AND-RED-N15P-256", "AND-TEC-CAM50U-256", "OBX-APL-IP15-128", "NEW-SAM-S25U-256"]]
            elif busca_gamer:
                equipos_sugeridos = [p for p in catalogo if p.sku in ["AND-TEC-POVAC2", "AND-POC-F8P-256", "AND-POC-X8PM-512"]]
            elif busca_economico:
                equipos_sugeridos = [p for p in catalogo if p.sku in ["AND-SAM-A05-128", "AND-RED-A5-128", "AND-TEC-SPGO2-128", "AND-SAM-A07-128"]]
            elif pide_catalogo_general:
                equipos_sugeridos = [p for p in catalogo if p.sku in ["AND-RED-N15P-256", "AND-SAM-A37-256", "OBX-APL-IP13-128", "NEW-APL-IP15-128"]]

        producto_principal: Optional[Producto] = (
            None if es_saludo_puro else (equipos_sugeridos[0] if equipos_sugeridos else producto_en_orden)
        )

        # 6. Determinar etapa de la conversación
        orden_ya_era_separado = bool(orden_actual and orden_actual.prioridad == PrioridadIncidente.ALTA.value)
        orden_ya_estaba_confirmada = bool(
            orden_actual and orden_actual.estado in [EstadoIncidente.ESCALADO.value, EstadoIncidente.CERRADO.value]
        )

        es_separado = es_separado_msg or (orden_ya_era_separado and not es_compra_msg)
        confirma_medio_pago_para_cierre = bool(
            producto_principal is not None
            and menciona_medio_pago
            and (es_compra_msg or es_separado_msg or (orden_actual is not None and not cambio_explicito_modelo))
        )
        es_compra_directa = es_compra_msg or confirma_medio_pago_para_cierre or (orden_ya_estaba_confirmada and not es_separado)

        etapa_conversacion = "asesoria"
        if es_saludo_puro:
            etapa_conversacion = "saludo_inicial"
        elif pide_descuento_no_autorizado:
            etapa_conversacion = "descuento_bloqueado"
        elif pide_iphone_omitido and not cambio_explicito_modelo:
            etapa_conversacion = "iphone_omitido"
        elif modelo_no_disponible and not cambio_explicito_modelo:
            etapa_conversacion = "modelo_no_disponible"
        elif (es_consulta_sedes or (sede_detectada is not None and orden_actual is None)) and not cambio_explicito_modelo and not es_compra_msg and not es_separado_msg:
            etapa_conversacion = "consulta_sedes"
        elif es_consulta_obsequios and not cambio_explicito_modelo and not es_compra_msg and not es_separado_msg:
            etapa_conversacion = "consulta_obsequios"
        elif es_consulta_plataformas and not cambio_explicito_modelo and orden_actual is None and not es_compra_msg and not es_separado_msg:
            etapa_conversacion = "consulta_plataformas"
        elif sede_detectada is not None and producto_principal is not None:
            etapa_conversacion = "sede_confirmada"
        elif menciona_medio_pago and producto_principal is not None and not cambio_explicito_modelo:
            etapa_conversacion = "pedir_sede_pago"
        elif (es_compra_msg or es_separado_msg) and producto_principal is not None:
            if menciona_medio_pago and sede_detectada is None:
                etapa_conversacion = "pedir_sede_pago"
            else:
                etapa_conversacion = "cierre_inicial"
        elif es_consulta_garantia and not cambio_explicito_modelo:
            etapa_conversacion = "garantia"
        elif len(equipos_sugeridos) == 1 and producto_principal is not None:
            etapa_conversacion = "cotizacion_equipo"
        elif len(equipos_sugeridos) > 1:
            etapa_conversacion = "comparativa"
        else:
            etapa_conversacion = "saludo_inicial"

        if etapa_conversacion == "descuento_bloqueado":
            prioridad = PrioridadIncidente.BAJA.value
            estado_sugerido = EstadoIncidente.REGISTRADO.value
        elif etapa_conversacion in ["sede_confirmada", "pedir_sede_pago", "cierre_inicial"]:
            prioridad = PrioridadIncidente.ALTA.value if es_separado else PrioridadIncidente.CRITICA.value
            estado_sugerido = EstadoIncidente.ESCALADO.value
        elif etapa_conversacion == "cotizacion_equipo":
            prioridad = PrioridadIncidente.MEDIA.value
            estado_sugerido = EstadoIncidente.EN_REVISION.value
        else:
            prioridad = PrioridadIncidente.MEDIA.value
            estado_sugerido = EstadoIncidente.REGISTRADO.value

        sede_nombre = sede_detectada["nombre"] if sede_detectada else None
        if producto_principal:
            es_iphone_principal = "iphone" in producto_principal.modelo.lower()
            if not menciona_medio_pago and not medio_pago_previo:
                medio_pago_str = (
                    "Contado, Addi, Sistecrédito, Banco de Bogotá o Renting (Exclusivo iPhone)"
                    if es_iphone_principal
                    else "Contado, Addi, Sistecrédito, Banco de Bogotá, Krediya o Credimóvil"
                )
            abono_minimo = int(producto_principal.precio_cop * 0.20)
            color_tag = f" [Color: {color_elegido}]" if color_elegido else ""
            linea_producto = f"{producto_principal.modelo}{color_tag} ({format_cop(producto_principal.precio_cop)})"

            if etapa_conversacion == "sede_confirmada" and sede_detectada:
                modalidad_ubicacion = f"{sede_detectada['nombre']} | Pago: {medio_pago_str}"
                resumen_financiero = f"Listo en Caja ({sede_detectada['nombre']}): {format_cop(producto_principal.precio_cop)}"
                acciones_recomendadas = (
                    f"Unidad reservada en {sede_detectada['nombre']} ({sede_detectada['direccion']}). "
                    f"Horario: {sede_detectada['horario']}. Presentar código de orden en caja para pago ({medio_pago_str})."
                )
            elif etapa_conversacion == "pedir_sede_pago":
                modalidad_ubicacion = f"Pago Confirmado: {medio_pago_str} | Seleccionando Sede Cel Red"
                resumen_financiero = f"Total a pagar ({medio_pago_str}): {format_cop(producto_principal.precio_cop)}"
                acciones_recomendadas = (
                    f"Medio de pago registrado ({medio_pago_str}). Pendiente que el cliente indique su ciudad o sede más cercana "
                    f"(Puerto Asís, Mocoa, La Hormiga, Orito, Ipiales, Pasto, Túquerres, Medellín, Neiva o La Unión) para alistar el equipo en caja."
                )
            elif es_separado:
                modalidad_ubicacion = f"Plan Separado Cel Red (Inicial 20%: {format_cop(abono_minimo)}) | Pago: {medio_pago_str}"
                resumen_financiero = f"Precio congelado: {format_cop(producto_principal.precio_cop)} | Inicial 20%: {format_cop(abono_minimo)}"
                acciones_recomendadas = (
                    f"Separado registrado para {producto_principal.modelo}. Abono inicial mínimo de {format_cop(abono_minimo)} (20%), "
                    f"plazo de 45 días sin intereses y reserva en sede Cel Red."
                )
            elif es_compra_directa:
                modalidad_ubicacion = f"Venta Directa en Tienda Cel Red | Pago: {medio_pago_str}"
                resumen_financiero = f"Total a facturar en SysCafé: {format_cop(producto_principal.precio_cop)} ({producto_principal.stock} und. en stock)"
                acciones_recomendadas = (
                    f"Orden lista para facturación en SysCafé: {producto_principal.modelo} por {format_cop(producto_principal.precio_cop)}. "
                    f"Incluye {producto_principal.garantia_meses} meses de garantía directa y registro gratuito de IMEI."
                )
            else:
                modalidad_ubicacion = f"Cotización Activa en Tienda | Medios: {medio_pago_str}"
                resumen_financiero = f"Contado: {format_cop(producto_principal.precio_cop)} | Separado desde: {format_cop(abono_minimo)}"
                acciones_recomendadas = (
                    f"Candado de Confirmación: Confirme color ({producto_principal.colores_disponibles}) y si desea Compra Directa, "
                    f"Plan Separado con {format_cop(abono_minimo)} o crédito con Sistecrédito / Addi."
                )
        else:
            linea_producto = TipoEvento.OTRO.value
            modalidad_ubicacion = f"Asesoría en Tienda Cel Red | Medios: {medio_pago_str}"
            resumen_financiero = "Catálogo oficial de contado desde $350.000 hasta $5.350.000"
            acciones_recomendadas = "Indicar modelo, presupuesto o marca (Android Nuevo, iPhone Nuevo u Open Box Seminuevo)."

        return {
            "prioridad": prioridad,
            "tipo_evento": linea_producto,
            "ubicacion": modalidad_ubicacion,
            "estado_sugerido": estado_sugerido,
            "etapa_conversacion": etapa_conversacion,
            "producto_principal": producto_principal,
            "equipos_sugeridos": equipos_sugeridos[:4],
            "cambio_explicito_modelo": cambio_explicito_modelo,
            "es_separado": es_separado,
            "es_compra_directa": es_compra_directa,
            "es_consulta_garantia": es_consulta_garantia,
            "pide_descuento_no_autorizado": pide_descuento_no_autorizado,
            "menciona_medio_pago": menciona_medio_pago,
            "pide_solo_contado": pide_solo_contado,
            "modelo_no_disponible": modelo_no_disponible,
            "medio_pago": medio_pago_str,
            "color_elegido": color_elegido,
            "sede_detectada": sede_detectada,
            "sede_asignada": sede_nombre,
            "resumen_financiero": resumen_financiero,
            "acciones_recomendadas": acciones_recomendadas
        }

    def _resolve_platform_payment_text_and_voice(
        self,
        prod: Producto,
        medio_pago: str,
        es_separado: bool
    ) -> tuple[str, str]:
        """
        Calcula el texto exacto de desembolso o cuota inicial (y su versión hablada)
        según la plataforma elegida por el cliente en `editada.xlsx`.
        """
        pinfo = get_platform_info(prod.sku)
        mp_low = medio_pago.lower()

        if "renting" in mp_low:
            if pinfo.get("renting"):
                r = pinfo["renting"]
                txt = (
                    f"Valor plataforma Renting iPhone (ideal para reportados o poco historial crediticio): **{format_cop(r['plataforma'])}** "
                    f"— **Inicial al 20%: {format_cop(r['inicial_20'])}** | **Inicial al 30%: {format_cop(r['inicial_30'])}**"
                )
                voz = (
                    f"un valor en plataforma Renting de {price_to_spoken_spanish(r['plataforma'])}, "
                    f"dando una cuota inicial al veinte por ciento de {price_to_spoken_spanish(r['inicial_20'])}, "
                    f"o al treinta por ciento de {price_to_spoken_spanish(r['inicial_30'])}"
                )
                return txt, voz
            elif "iphone" not in prod.modelo.lower():
                txt = (
                    f"⚠️ *Nota: La plataforma **Renting es exclusiva para iPhone**.* "
                    f"Para este **{prod.modelo}** puedes llevarlo de contado (**{format_cop(prod.precio_cop)}**) "
                    f"o financiarlo por **Krediya, Credimóvil, Addi, Sistecrédito o Banco de Bogotá**"
                )
                voz = (
                    f"teniendo en cuenta que Renting es exclusivo para iPhone, por lo que para este {prod.modelo} "
                    f"puedes usar Krediya, Credimóvil, Addi, Sistecrédito o pago de contado por {price_to_spoken_spanish(prod.precio_cop)}"
                )
                return txt, voz

        if ("krediya" in mp_low or "crediya" in mp_low) and pinfo.get("krediya"):
            k = pinfo["krediya"]
            ini20 = int(k["plataforma"] * 0.20)
            txt = (
                f"Valor plataforma Krediya: **{format_cop(k['plataforma'])}** — "
                f"**Inicial aprobada al 30%: {format_cop(k['inicial_30'])}** *(o si te aprueban al 20%: {format_cop(ini20)})*"
            )
            voz = (
                f"un valor en plataforma Krediya de {price_to_spoken_spanish(k['plataforma'])}, "
                f"con cuota inicial aprobada al treinta por ciento de {price_to_spoken_spanish(k['inicial_30'])}, "
                f"o al veinte por ciento de {price_to_spoken_spanish(ini20)}"
            )
            return txt, voz

        if ("credimóvil" in mp_low or "credimovil" in mp_low) and pinfo.get("credimovil"):
            c = pinfo["credimovil"]
            txt = (
                f"Valor plataforma Credimóvil: **{format_cop(c['plataforma'])}** — "
                f"**Inicial al 10%: {format_cop(c['inicial_10'])}** | **Inicial al 15%: {format_cop(c['inicial_15'])}**"
            )
            voz = (
                f"un valor en plataforma Credimóvil de {price_to_spoken_spanish(c['plataforma'])}, "
                f"con cuota inicial al diez por ciento de {price_to_spoken_spanish(c['inicial_10'])}, "
                f"o al quince por ciento de {price_to_spoken_spanish(c['inicial_15'])}"
            )
            return txt, voz

        if "bogotá" in mp_low or "bogota" in mp_low:
            bog_val = pinfo.get("banco_bogota")
            if bog_val:
                txt = f"Desembolso oficial por **Banco de Bogotá**: **{format_cop(bog_val)}**"
                voz = f"un desembolso por Banco de Bogotá de {price_to_spoken_spanish(bog_val)}"
                return txt, voz

        if "addi" in mp_low or "sistecrédito" in mp_low or "sistecredito" in mp_low:
            addi_val = pinfo.get("addi_sistecredito")
            if addi_val:
                txt = f"Desembolso oficial por **{medio_pago}**: **{format_cop(addi_val)}**"
                voz = f"un desembolso por {medio_pago.lower()} de {price_to_spoken_spanish(addi_val)}"
                return txt, voz

        if es_separado:
            abono = int(prod.precio_cop * 0.20)
            txt = f"Abono inicial mínimo del 20%: **{format_cop(abono)}** (Plan Separado sobre {format_cop(prod.precio_cop)})"
            voz = f"el abono inicial de {price_to_spoken_spanish(abono)}"
            return txt, voz

        txt = f"Valor oficial de contado: **{format_cop(prod.precio_cop)}**"
        voz = price_to_spoken_spanish(prod.precio_cop)
        return txt, voz

    async def _generate_sales_response(
        self,
        user_message: str,
        analysis: Dict[str, Any],
        rag_context: str,
        orden: Incidente
    ) -> str:
        etapa = analysis.get("etapa_conversacion", "asesoria")
        prod: Optional[Producto] = analysis.get("producto_principal")
        sugeridos: List[Producto] = analysis.get("equipos_sugeridos", [])
        es_separado = analysis.get("es_separado", False)
        medio_pago = analysis.get("medio_pago", "Efectivo en Tienda")
        color_elegido = analysis.get("color_elegido")
        sede = analysis.get("sede_detectada")
        saludo_hora = self._get_colombia_greeting()

        if etapa == "saludo_inicial":
            return (
                f"¡Hola, {saludo_hora}! 😊 Bienvenido a **Cel Red**, hablas con tu asesor comercial.\n\n"
                f"Cuéntame, **¿cómo puedo ayudarte hoy?** Puedo asesorarte con:\n"
                f"- 📱 **Precios de contado** en celulares **Android Nuevos** e **iPhone Nuevos u Open Box (Seminuevos)** desde el iPhone 13 en adelante (con sus **Combos de Obsequio**).\n"
                f"- 💳 **Financiación y desembolsos** por **Addi, Sistecrédito, Banco de Bogotá, Krediya, Credimóvil** o **Renting iPhone** *(ideal para personas con poco historial crediticio o reportadas)*.\n"
                f"- 📍 **Ubicación de nuestras 14 sedes** (Putumayo, Nariño, Neiva y Medellín).\n\n"
                f"👉 *¿Qué celular, marca o modalidad de pago estás buscando?*"
            )

        if etapa == "descuento_bloqueado":
            texto = (
                f"¡Bienvenido a **Cel Red**! He registrado tu consulta bajo la referencia **{orden.codigo}**.\n\n"
                f"🔒 **Verificador Comercial Activo (Regla de Integridad SysCafé):** Como asesor oficial de **Cel Red**, "
                f"no tengo permisos para modificar precios de lista, otorgar descuentos del 50% ni entregar equipos sin respaldo en caja. "
                f"Todos nuestros precios de contado y de desembolso en plataformas son oficiales y verificados en nuestra base de datos PostgreSQL.\n\n"
                f"💡 **Alternativas para ahorrar o financiar fácil hoy mismo:**\n"
                f"- **Línea Open Box (Seminuevos Garantizados):** Tenemos iPhone desde el **iPhone 13 128GB en $1.150.000** (con obsequio de Estuche y Vidrio) o el **iPhone 15 128GB Open Box en $1.790.000**.\n"
                f"- **Plataformas de Financiación:** Manejamos **Addi**, **Sistecrédito**, **Banco de Bogotá**, **Krediya** (inicial del 20% o 30%), **Credimóvil** (inicial del 10% o 15%) y **Renting para iPhone** (ideal para clientes con poco historial crediticio o reportados, con inicial del 20% o 30%).\n"
                f"- **Sistema de Separado Cel Red:** Separa cualquier equipo con el **20% de abono inicial** y págalo hasta en 45 días sin intereses."
            )
            return texto

        if etapa == "iphone_omitido":
            return (
                f"¡Hola! 😊 Te comento que ese modelo **no lo estamos manejando** actualmente en **Cel Red** "
                f"(en nuestra tienda comercializamos equipos Apple **únicamente desde el iPhone 13 en adelante**, no manejamos iPhone 11 ni iPhone 12). "
                f"**¡Pero si gustas, te puedo dar una opción similar disponible para entrega inmediata!**\n\n"
                f"✨ **Opciones similares disponibles en iPhone 13 de 128GB (Cotización {orden.codigo}):**\n"
                f"- **iPhone 13 de 128GB (Open Box - Seminuevo):**\n"
                f"  - Contado: **$1.150.000** | 🎁 **Obsequio: Estuche y Vidrio**\n"
                f"  - Desembolso **Addi / Sistecrédito**: **$1.750.000** | **Banco de Bogotá**: **$1.500.000**\n"
                f"  - **Renting iPhone *(Reportados o poco historial)*:** Plataforma **$1.850.000** (*Inicial 20%: **$370.000*** | *Inicial 30%: **$555.000***)\n"
                f"- **iPhone 13 128GB Activo (Nuevo):**\n"
                f"  - Contado: **$1.840.000** | 🎁 **Obsequio: Estuche y Vidrio**\n"
                f"  - Desembolso **Addi / Sistecrédito**: **$2.470.000** | **Banco de Bogotá**: **$2.240.000**\n"
                f"  - **Renting iPhone *(Reportados o poco historial)*:** Plataforma **$2.450.000** (*Inicial 20%: **$490.000*** | *Inicial 30%: **$735.000***)\n\n"
                f"🔒 *¿Te gustaría llevar alguna de estas opciones similares en **iPhone 13 de 128GB** de contado o por plataforma?*"
            )

        if etapa == "modelo_no_disponible":
            modelo_no_disp = analysis.get("modelo_no_disponible") or "ese modelo"
            pide_solo_contado = analysis.get("pide_solo_contado", False)
            lineas_sim = []
            for p in sugeridos:
                abono_p = int(p.precio_cop * 0.20)
                etiqueta_cat = " *(Seminuevo Open Box — valor menor)*" if "open box" in p.categoria.lower() else " *(Nuevo)*"
                obsequio_p = self._get_iphone_obsequio(p)
                nota_obs = f"\n  🎁 **Obsequio incluido:** **{obsequio_p}**" if obsequio_p else ""
                if pide_solo_contado:
                    lineas_sim.append(
                        f"- **{p.modelo}** — **Precio de contado: {format_cop(p.precio_cop)}**{etiqueta_cat}{nota_obs}"
                    )
                else:
                    plat_md = format_platform_summary_markdown(p.sku)
                    bloque_plat = f"\n{plat_md}" if plat_md else ""
                    lineas_sim.append(
                        f"- **{p.modelo}** — Contado: **{format_cop(p.precio_cop)}**{etiqueta_cat} | *Plan Separado (20%): {format_cop(abono_p)}*{nota_obs}{bloque_plat}"
                    )
            lista_sim_str = "\n\n".join(lineas_sim)
            return (
                f"¡Hola! 😊 Te comento que el **{modelo_no_disp}** **no lo estamos manejando** actualmente en nuestro inventario de **Cel Red**. "
                f"**¡Pero si gustas, te puedo dar una opción similar disponible para entrega inmediata!**\n\n"
                f"✨ **Opciones similares recomendadas para ti en Cel Red (Cotización {orden.codigo}):**\n\n"
                f"{lista_sim_str}\n\n"
                f"🔒 *¿Te gustaría que te aparte alguna de estas opciones similares o prefieres consultar otra referencia?*"
            )

        if etapa == "consulta_obsequios":
            return (
                f"🎁 **Tabla Oficial de Obsequios y Combos por Compra de iPhone en Cel Red** (Referencia **{orden.codigo}**):\n\n"
                f"Recuerda que comercializamos **desde el iPhone 13 en adelante** y estos son los obsequios incluidos según la referencia:\n\n"
                f"1. **Estuche y Vidrio Templado:**\n"
                f"   - **iPhone 13 de 128GB** (*$1.150.000 Open Box* / *$1.840.000 Nuevo*)\n"
                f"2. **COMBO 2 (Cubo, Cable, Estuche y Vidrio) o COMBO 3 (AirPods) — A elección del cliente:**\n"
                f"   - **iPhone 13 Pro Max 128GB** (*$1.890.000 Open Box*)\n"
                f"   - **iPhone 14 Pro 128GB** (*$1.820.000 Open Box*)\n"
                f"   - **iPhone 14 Pro Max 128GB** (*$1.980.000 Open Box*)\n"
                f"   - **iPhone 15 de 128GB** (*$1.790.000 Open Box* / *$2.200.000 Nuevo*)\n"
                f"   - **iPhone 15 Pro de 128GB** (*$2.050.000 Open Box*)\n"
                f"   - **iPhone 15 Pro Max de 256GB** (*$2.530.000 Open Box*)\n"
                f"3. **COMBO 4 (Cubo, Cable, Estuche, Vidrio y AirPods):**\n"
                f"   - **iPhone 16 de 128GB** (*$2.180.000 Open Box* / *$2.600.000 Nuevo*)\n"
                f"4. **COMBO 5 (Reloj Inteligente, Cable, Cubo, AirPods, Vidrio y Estuche):**\n"
                f"   - **iPhone 16 Pro 128GB** (*$2.580.000 Open Box*)\n"
                f"   - **iPhone 16 Pro 256GB** (*$2.650.000 Open Box*)\n"
                f"   - **iPhone 16 Pro Max 256GB** (*$2.950.000 Open Box*)\n\n"
                f"📱 *¿Cuál de estos modelos de iPhone te gustaría cotizar hoy (de contado, Addi, Sistecrédito, Banco de Bogotá o Renting)?*"
            )

        if etapa == "consulta_plataformas":
            return (
                f"💳 **Plataformas Oficiales de Financiación y Desembolso en Cel Red** (Referencia **{orden.codigo}**):\n\n"
                f"En **Cel Red** manejamos **5 modalidades de crédito** según tu perfil y el equipo que elijas (Android o iPhone desde el 13 en adelante):\n\n"
                f"1. **Addi y Sistecrédito (Android e iPhone):**\n"
                f"   - Se realiza por el **valor de desembolso** correspondiente a cada referencia (ej. *Samsung A05*: **$710.000**, *Redmi Note 15 Pro*: **$1.420.000**, *iPhone 13 128GB Open Box*: **$1.750.000**, *iPhone 15 128GB Open Box*: **$2.580.000**).\n"
                f"2. **Banco de Bogotá (Android e iPhone):**\n"
                f"   - Desembolso directo con tasa preferencial (ej. *Samsung A05*: **$650.000**, *Redmi Note 15 Pro*: **$1.270.000**, *iPhone 13 128GB Open Box*: **$1.500.000**, *iPhone 15 128GB Open Box*: **$2.230.000**).\n"
                f"3. **Krediya (Especial Android):**\n"
                f"   - Según aprobación das una **cuota inicial del 30% o del 20%** (ej. *Samsung A16*: Plataforma $1.050.000 con **inicial 30% de solo $40.000**; *Samsung A05*: Plataforma $770.000 con **inicial 30% de $51.000**; *Redmi Note 15 Pro*: Plataforma $1.800.000 con **inicial 30% de $160.000**).\n"
                f"4. **Credimóvil (Especial Android):**\n"
                f"   - Llevas tu equipo dando solo el **10% o el 15% de cuota inicial** según aprobación (ej. *Samsung A05*: Plataforma $600.000 con **inicial 10% de $60.000** o **15% de $90.000**; *Redmi 15*: Plataforma $980.000 con **inicial 10% de $98.000** o **15% de $147.000**).\n"
                f"5. **Renting iPhone *(Exclusivo para iPhone — Ideal para personas reportadas o con poco historial crediticio)*:**\n"
                f"   - Te aprobamos tu iPhone dando una **cuota inicial del 20% o del 30%** según el estudio:\n"
                f"     - **iPhone 13 128GB Open Box:** Valor plataforma **$1.850.000** | **Inicial 20%: $370.000** | **Inicial 30%: $555.000**\n"
                f"     - **iPhone 15 128GB Open Box:** Valor plataforma **$2.500.000** | **Inicial 20%: $500.000** | **Inicial 30%: $750.000**\n"
                f"     - **iPhone 16 128GB Open Box:** Valor plataforma **$3.200.000** | **Inicial 20%: $640.000** | **Inicial 30%: $960.000**\n\n"
                f"👉 *Dime **qué celular te interesa** y **por cuál plataforma** quieres cotizarlo para darte el valor exacto.*"
            )

        if etapa == "consulta_sedes":
            if sede:
                return (
                    f"📍 **Ubicación Oficial de {sede['nombre']} — Cel Red** (Referencia **{orden.codigo}**):\n\n"
                    f"- **Sede:** **{sede['nombre']}**\n"
                    f"- **Dirección exacta:** **{sede['direccion']}**\n"
                    f"- **Horario de atención:** {sede['horario']}\n\n"
                    f"📱 *¿Qué celular Android o iPhone (de contado o por Addi, Sistecrédito, Banco de Bogotá, Krediya, Credimóvil o Renting) te gustaría dejar apartado en esta sede?*"
                )
            return (
                f"📍 **Directorio Oficial de las 14 Sedes de Cel Red** (Referencia **{orden.codigo}**):\n\n"
                f"**Putumayo:**\n"
                f"1. **Puerto Asís / Putumayo:** `CALLE 10 NO 24 - 18 BARRIO EL CARMEN`\n"
                f"2. **Mocoa / Putumayo:** `CRA 9 # 10 - 30 AVENIDA COLOMBIA`\n"
                f"3. **La Hormiga — Valle del Guamuez:** `BARRIO CENTRAL LAS AMERICAS CARRERA 5 - #7-16 A UN COSTADO DE LA ALCALDÍA MUNICIPAL`\n"
                f"4. **Orito / Putumayo:** `CALLE 8 # 10 - 47 BARRIO MARCO FIDEL SUAREZ AL LADO DE DISTRISUR`\n\n"
                f"**Nariño:**\n"
                f"5. **Ipiales / Nariño (Ed. Markus):** `CRA 6 NO 13 - 05 ESQUINA ED MARKUS`\n"
                f"6. **Ipiales / Nariño (CC Zafiro):** `CRA 6 NO 11 - 51 CC ZAFIRO LOCAL 123`\n"
                f"7. **Ipiales / Nariño (CC Victoria Plaza):** `CRA 7 NO 9 - 56 CC VICTORIA PLAZA LOCAL 101A`\n"
                f"8. **Pasto / Nariño (Centro):** `CALLE 16 NO 23 - 82 LOCAL 1 - CENTRO`\n"
                f"9. **Pasto / Nariño (CC Pasaje El Liceo):** `CALLE 17 # 26 - 60 CC PASAJE EL LICEO LOCAL 103`\n"
                f"10. **Pasto / Nariño (CC Sebastián de Belalcázar):** `CC SEBASTIAN DE BELALCAZAR LOCAL 6A`\n"
                f"11. **Túquerres / Nariño:** `CRA 14 - CLL 20 ESQUINA - TUQUERRES`\n"
                f"14. **La Unión / Nariño:** `CRA 1 # 11- 81 – FRENTE AL PARQUE CUEVAS LEIVA`\n\n"
                f"**Antioquia y Huila:**\n"
                f"12. **Medellín / Antioquia:** `CENTRO COMERCIAL PREMIUM PLAZA LOCAL 1301`\n"
                f"13. **Neiva / Huila:** `CRA.2 # 6 - 26 - LOCAL 5 - CENTRO`\n\n"
                f"👉 *¿En cuál ciudad te encuentras y qué celular te gustaría cotizar o dejar reservado hoy?*"
            )

        if etapa == "sede_confirmada" and prod and sede:
            detalle_plat, _ = self._resolve_platform_payment_text_and_voice(prod, medio_pago, es_separado)
            color_txt = f"Color **{color_elegido}**" if color_elegido else f"Colores disponibles ({prod.colores_disponibles})"
            condicion_eq = "Equipo Seminuevo Open Box Garantizado" if "open box" in prod.categoria.lower() else "Equipo Nuevo Sellado / Activo"
            obsequio = self._get_iphone_obsequio(prod)
            linea_obsequio = f"- **🎁 Obsequio oficial incluido:** **{obsequio}**\n" if obsequio else ""
            return (
                f"📍 **¡Listo! Tu equipo ya quedó asignado en {sede['nombre']}**\n\n"
                f"He enviado la orden **{orden.codigo}** directamente a la caja de esa sede para que solo llegues a realizar el pago o desembolso y reclamar tu equipo:\n\n"
                f"- **Sede de entrega:** **{sede['nombre']}**\n"
                f"- **Dirección exacta:** **{sede['direccion']}**\n"
                f"- **Horario de atención:** {sede['horario']}\n"
                f"- **Equipo reservado:** {prod.modelo} ({condicion_eq}) — {color_txt}\n"
                f"{linea_obsequio}"
                f"- **Modalidad registrada ({medio_pago}):** {detalle_plat}\n"
                f"- **Respaldo Cel Red:** Factura legal SysCafé, **{prod.garantia_meses} meses de garantía directa** y registro gratuito de IMEI.\n\n"
                f"✅ *Solo presenta el código **{orden.codigo}** y tu cédula original al asesor en la caja de **{sede['nombre']}** y te entregaremos tu equipo de inmediato.*"
            )

        if etapa == "pedir_sede_pago" and prod:
            detalle_plat, _ = self._resolve_platform_payment_text_and_voice(prod, medio_pago, es_separado)
            color_nota = f" en color **{color_elegido}**" if color_elegido else ""
            obsequio = self._get_iphone_obsequio(prod)
            nota_regalo = f" junto con su obsequio oficial (**{obsequio}**)" if obsequio else ""
            return (
                f"💵 **¡Perfecto! Modalidad confirmada: {medio_pago} (Orden {orden.codigo})**\n\n"
                f"Ya dejé registrado tu **{prod.modelo}**{color_nota}{nota_regalo}:\n"
                f"- **Condición aplicada:** {detalle_plat}\n\n"
                f"📍 **¿En cuál de nuestras 14 sedes de Cel Red te queda más cercano realizar el pago o desembolso en tienda y reclamar tu equipo?**\n"
                f"- **1. Puerto Asís / Putumayo:** `CALLE 10 NO 24 - 18 BARRIO EL CARMEN`\n"
                f"- **2. Mocoa / Putumayo:** `CRA 9 # 10 - 30 AVENIDA COLOMBIA`\n"
                f"- **3. La Hormiga (Valle del Guamuez):** `BARRIO CENTRAL LAS AMERICAS CARRERA 5 - #7-16 A UN COSTADO DE LA ALCALDÍA MUNICIPAL`\n"
                f"- **4. Orito / Putumayo:** `CALLE 8 # 10 - 47 BARRIO MARCO FIDEL SUAREZ AL LADO DE DISTRISUR`\n"
                f"- **5, 6 y 7. Ipiales / Nariño:** `CRA 6 NO 13 - 05 ESQUINA ED MARKUS` | `CRA 6 NO 11 - 51 CC ZAFIRO LOCAL 123` | `CRA 7 NO 9 - 56 CC VICTORIA PLAZA LOCAL 101A`\n"
                f"- **8, 9 y 10. Pasto / Nariño:** `CALLE 16 NO 23 - 82 LOCAL 1 - CENTRO` | `CALLE 17 # 26 - 60 CC PASAJE EL LICEO LOCAL 103` | `CC SEBASTIAN DE BELALCAZAR LOCAL 6A`\n"
                f"- **11. Túquerres / Nariño:** `CRA 14 - CLL 20 ESQUINA - TUQUERRES`\n"
                f"- **12. Medellín / Antioquia:** `CENTRO COMERCIAL PREMIUM PLAZA LOCAL 1301`\n"
                f"- **13. Neiva / Huila:** `CRA.2 # 6 - 26 - LOCAL 5 - CENTRO`\n"
                f"- **14. La Unión / Nariño:** `CRA 1 # 11- 81 – FRENTE AL PARQUE CUEVAS LEIVA`\n\n"
                f"👉 *Dime **en qué ciudad o sede** te encuentras y el **color** que deseas ({prod.colores_disponibles}) para dejarte la unidad apartada en esa caja.*"
            )

        if etapa == "cierre_inicial" and prod:
            es_iphone_prod = "iphone" in prod.modelo.lower()
            plataformas_cierre_txt = (
                "**Addi, Sistecrédito, Banco de Bogotá o Renting (exclusivo iPhone)**"
                if es_iphone_prod
                else "**Addi, Sistecrédito, Banco de Bogotá, Krediya o Credimóvil**"
            )
            detalle_plat, _ = self._resolve_platform_payment_text_and_voice(prod, medio_pago, es_separado)
            modalidad_titulo = "PLAN SEPARADO CONFIRMADO" if es_separado else "ORDEN DE VENTA CONFIRMADA"
            nota_openbox = (
                "\n- **Condición:** *Open Box (Seminuevo garantizado en excelente estado, por eso su valor es menor frente al nuevo).*"
                if "open box" in prod.categoria.lower() else ""
            )
            obsequio = self._get_iphone_obsequio(prod)
            linea_obsequio = f"- **🎁 Obsequio oficial incluido:** **{obsequio}**\n" if obsequio else ""
            resumen_plat = format_platform_summary_markdown(prod.sku)
            bloque_plat = f"\n💳 **Valores de Desembolso e Iniciales por Plataforma:**\n{resumen_plat}\n" if resumen_plat else ""
            return (
                f"✅ **¡Excelente elección! {modalidad_titulo} EN CEL RED**\n"
                f"He generado la orden oficial **{orden.codigo}** lista para facturación en **SysCafé**:\n\n"
                f"- **Equipo reservado:** {prod.modelo} (SKU: `{prod.sku}`){nota_openbox}\n"
                f"- **Precio oficial de contado:** {format_cop(prod.precio_cop)} — *Stock verificado: {prod.stock} unidades*\n"
                f"{linea_obsequio}"
                f"- **Colores disponibles:** {prod.colores_disponibles}\n"
                f"- **Condición seleccionada:** {detalle_plat}\n"
                f"{bloque_plat}"
                f"- **Respaldo Cel Red:** {prod.garantia_meses} meses de garantía directa + Registro gratuito de IMEI.\n\n"
                f"📍 **Paso final para alistar tu entrega en tienda:**\n"
                f"¿Lo llevarás **de contado (Efectivo/Nequi)** o por alguna plataforma ({plataformas_cierre_txt}), y en cuál ciudad o sede te queda más cerca recogerlo (**Puerto Asís, Mocoa, La Hormiga, Orito, Ipiales, Pasto, Túquerres, Medellín, Neiva o La Unión**)?"
            )

        if etapa == "garantia":
            return (
                f"¡Con mucho gusto! En **Cel Red** (Referencia **{orden.codigo}**) manejamos nuestro inventario oficial con pago de contado y **5 plataformas de crédito**:\n\n"
                f"- **Android Nuevos Sellados (desde $350.000 de contado):** Financiación inmediata por **Addi**, **Sistecrédito**, **Banco de Bogotá**, **Krediya** (inicial al 20% o 30%) y **Credimóvil** (inicial al 10% o 15%) con **12 meses de garantía**.\n"
                f"- **iPhone Nuevos y Open Box Seminuevos (únicamente desde el iPhone 13 en adelante):** Disponibles de contado, por **Addi / Sistecrédito**, **Banco de Bogotá**, y por **Renting iPhone** (la plataforma exclusiva de iPhone para clientes con **poco historial crediticio o reportados**, dando el **20% o 30% de inicial**), además de sus **Combos de Obsequio**.\n\n"
                f"📱 *¿Qué modelo o plataforma te gustaría consultar hoy?*"
            )

        if len(sugeridos) > 1:
            pide_solo_contado = analysis.get("pide_solo_contado", False)
            tiene_iphone = any("iphone" in p.modelo.lower() for p in sugeridos)
            tiene_android = any("iphone" not in p.modelo.lower() for p in sugeridos)
            lineas_equipos = []
            for p in sugeridos:
                abono_p = int(p.precio_cop * 0.20)
                etiqueta_cat = " *(Seminuevo Open Box — valor menor)*" if "open box" in p.categoria.lower() else " *(Nuevo)*"
                obsequio_p = self._get_iphone_obsequio(p)
                nota_obs = f"\n  🎁 **Obsequio incluido:** **{obsequio_p}**" if obsequio_p else ""
                if pide_solo_contado:
                    lineas_equipos.append(
                        f"- **{p.modelo}** — **Precio de contado: {format_cop(p.precio_cop)}**{etiqueta_cat}{nota_obs}"
                    )
                else:
                    plat_md = format_platform_summary_markdown(p.sku)
                    bloque_plat = f"\n{plat_md}" if plat_md else ""
                    lineas_equipos.append(
                        f"- **{p.modelo}** — Contado: **{format_cop(p.precio_cop)}**{etiqueta_cat} | *Plan Separado (20%): {format_cop(abono_p)}*{nota_obs}{bloque_plat}"
                    )
            lista_str = "\n\n".join(lineas_equipos)
            if pide_solo_contado:
                return (
                    f"¡Claro que sí! Aquí tienes nuestros **precios oficiales de contado** en **Cel Red** (Cotización **{orden.codigo}**):\n\n"
                    f"{lista_str}\n\n"
                    f"🔒 **Paso para cerrar tu compra de contado:** ¿Cuál de estas referencias prefieres y en cuál de nuestras **14 sedes** te queda más cerca recogerlo?"
                )
            if tiene_android and not tiene_iphone:
                nota_plataformas_comp = (
                    "💡 *Recuerda:* Los precios en **Addi, Sistecrédito y Banco de Bogotá** corresponden al valor de desembolso de la plataforma; "
                    "y en **Krediya** (inicial del 20% o 30%) y **Credimóvil** (inicial del 10% o 15%) das únicamente la cuota inicial aprobada."
                )
            elif tiene_iphone and not tiene_android:
                nota_plataformas_comp = (
                    "💡 *Recuerda:* Los precios en **Addi, Sistecrédito y Banco de Bogotá** corresponden al valor de desembolso de la plataforma; "
                    "y **Renting** es nuestra plataforma **exclusiva para iPhone** para quienes tienen **poco historial crediticio o están reportados** (inicial del 20% o 30%)."
                )
            else:
                nota_plataformas_comp = (
                    "💡 *Recuerda:* En **Addi, Sistecrédito y Banco de Bogotá** el valor corresponde al desembolso; "
                    "**Krediya y Credimóvil** aplican para Android con cuota inicial; y **Renting es exclusivo para iPhone** (poco historial o reportados, inicial del 20% o 30%)."
                )
            return (
                f"¡Claro que sí! He consultado nuestras listas oficiales de **Contado y Plataformas de Crédito** en **Cel Red** (Cotización **{orden.codigo}**):\n\n"
                f"{lista_str}\n\n"
                f"{nota_plataformas_comp}\n\n"
                f"🔒 **Paso para cerrar tu pedido:** ¿Cuál de estos equipos prefieres y con qué medio de pago o plataforma deseas llevarlo?"
            )

        if prod:
            pide_solo_contado = analysis.get("pide_solo_contado", False)
            es_iphone_prod = "iphone" in prod.modelo.lower()
            opciones_candado = (
                "por **Addi / Sistecrédito / Banco de Bogotá**, con cuota inicial en **Renting (exclusivo para iPhone)**"
                if es_iphone_prod
                else "por **Addi / Sistecrédito / Banco de Bogotá**, con cuota inicial en **Krediya / Credimóvil**"
            )
            abono = int(prod.precio_cop * 0.20)
            nota_ob = (
                " *(Equipo Seminuevo Open Box garantizado, por eso su valor es menor que el nuevo)*"
                if "open box" in prod.categoria.lower() else " *(Equipo Nuevo)*"
            )
            obsequio = self._get_iphone_obsequio(prod)
            linea_obsequio = f"- **🎁 Obsequio oficial incluido:** **{obsequio}**\n" if obsequio else ""
            if pide_solo_contado:
                return (
                    f"¡Excelente elección! Tenemos disponible en **Cel Red** el **{prod.modelo}**{nota_ob} "
                    f"(Cotización **{orden.codigo}**):\n\n"
                    f"- **💵 Precio oficial de contado:** **{format_cop(prod.precio_cop)}** *(Disponibles: {prod.stock} unidades)*\n"
                    f"{linea_obsequio}"
                    f"- **Colores en tienda:** {prod.colores_disponibles}\n"
                    f"- **Garantía:** {prod.garantia_meses} meses de garantía directa + factura SysCafé.\n\n"
                    f"🔒 **Candado de Confirmación (Pago de Contado):** ¿Deseas dejarlo reservado de contado hoy mismo? Dime qué **color** prefieres y en cuál de nuestras **14 sedes de Cel Red** te queda más cerca recogerlo."
                )
            plat_md = format_platform_summary_markdown(prod.sku)
            bloque_plat = f"\n💳 **Precios de Desembolso y Cuotas Iniciales por Plataforma Oficial:**\n{plat_md}\n" if plat_md else ""
            return (
                f"¡Excelente elección! Tenemos disponible en **Cel Red** el **{prod.modelo}**{nota_ob} "
                f"(Cotización **{orden.codigo}**):\n\n"
                f"- **💵 Precio oficial de contado:** **{format_cop(prod.precio_cop)}** *(Disponibles: {prod.stock} unidades)*\n"
                f"- **🔒 Plan Separado Cel Red (20% inicial):** Sepáralo con **{format_cop(abono)}** a 45 días sin intereses\n"
                f"{linea_obsequio}"
                f"{bloque_plat}\n"
                f"- **Colores en tienda:** {prod.colores_disponibles}\n"
                f"- **Garantía:** {prod.garantia_meses} meses de garantía directa + factura SysCafé.\n\n"
                f"🔒 **Candado de Confirmación:** ¿Deseas llevarlo **de contado**, {opciones_candado}, o en **Plan Separado**? Confírmame para asignarte la sede más cercana."
            )

        return (
            f"¡Hola, {saludo_hora}! 😊 Bienvenido a **Cel Red**, hablas con tu asesor comercial. "
            f"Cuéntame, **¿cómo puedo ayudarte hoy?** ¿Estás buscando algún celular Android o iPhone en especial, "
            f"deseas consultar precios de contado o financiarlo por alguna de nuestras plataformas?"
        )

    def _build_conversational_spoken_script(
        self,
        orden: Incidente,
        analysis: Dict[str, Any]
    ) -> str:
        etapa = analysis.get("etapa_conversacion", "asesoria")
        prod: Optional[Producto] = analysis.get("producto_principal")
        sugeridos: List[Producto] = analysis.get("equipos_sugeridos", [])
        es_separado = analysis.get("es_separado", False)
        medio_pago = analysis.get("medio_pago", "efectivo")
        color_elegido = analysis.get("color_elegido")
        sede = analysis.get("sede_detectada")
        saludo_hora = self._get_colombia_greeting()

        if etapa == "saludo_inicial":
            guion = (
                f"Hola, {saludo_hora}. Bienvenido a Cel Red, hablas con tu asesor comercial. "
                f"Cuéntame, ¿cómo puedo ayudarte hoy?"
            )
            return self._prepare_spoken_text(guion)

        if etapa == "descuento_bloqueado":
            guion = (
                "Te comento que por política oficial de Cel Red nuestros precios son fijos en sistema. "
                "Si buscas un precio menor o facilidades de pago, tenemos la línea Open Box desde el iPhone trece, "
                "y financiación por Addi, Sistecrédito, Banco de Bogotá, Krediya, Credimóvil, o Renting para iPhone si estás reportado o tienes poco historial crediticio."
            )
            return self._prepare_spoken_text(guion)

        if etapa == "iphone_omitido":
            guion = (
                "Te comento que ese modelo no lo estamos manejando en Cel Red, ya que solo comercializamos desde el iPhone trece en adelante, "
                "pero si gustas te puedo dar una opción similar como el iPhone trece de ciento veintiocho gigas seminuevo Open Box por un millón ciento cincuenta mil pesos de contado, "
                "o por la plataforma Renting con una inicial del veinte por ciento de trescientos setenta mil pesos, e incluye estuche y vidrio de obsequio."
            )
            return self._prepare_spoken_text(guion)

        if etapa == "modelo_no_disponible":
            modelo_no_disp = analysis.get("modelo_no_disponible") or "ese modelo"
            partes_sim = []
            for p in sugeridos[:3]:
                nombre_limpio = re.sub(r"\([^\)]+\)", "", p.modelo).strip()
                partes_sim.append(f"el {nombre_limpio} en {price_to_spoken_spanish(p.precio_cop)} de contado")
            listado_voz = "; ".join(partes_sim) if partes_sim else "nuestras referencias disponibles de entrega inmediata"
            guion = (
                f"Te comento que el {modelo_no_disp} no lo estamos manejando en Cel Red, "
                f"pero si gustas te puedo dar una opción muy similar disponible para entrega inmediata, como {listado_voz}. "
                f"¿Te gustaría conocer más detalles de alguna de estas opciones?"
            )
            return self._prepare_spoken_text(guion)

        if etapa == "consulta_obsequios":
            guion = (
                "Claro que sí. En Cel Red manejamos desde el iPhone trece en adelante con obsequios especiales. "
                "El iPhone trece de ciento veintiocho gigas incluye estuche y vidrio. "
                "Los modelos trece Pro Max, catorce Pro, catorce Pro Max y toda la línea iPhone quince incluyen a tu elección el Combo dos con cubo, cable, estuche y vidrio, o el Combo tres con AirPods. "
                "El iPhone dieciséis normal incluye el Combo cuatro con cubo, cable, estuche, vidrio y AirPods, "
                "y los iPhone dieciséis Pro y dieciséis Pro Max incluyen el Combo cinco completo con reloj inteligente, AirPods, cubo, cable, vidrio y estuche. ¿Cuál modelo te gustaría cotizar?"
            )
            return self._prepare_spoken_text(guion)

        if etapa == "consulta_plataformas":
            guion = (
                "En Cel Red manejamos cinco plataformas de crédito además del pago de contado. "
                "Con Addi, Sistecrédito y Banco de Bogotá financias el valor de desembolso del equipo. "
                "Para Android tenemos Krediya con cuota inicial del veinte o treinta por ciento, y Credimóvil con inicial del diez o quince por ciento. "
                "Y para iPhone, si tienes poco historial crediticio o estás reportado, manejamos la plataforma Renting dando el veinte o treinta por ciento de cuota inicial. "
                "¿Qué celular te gustaría cotizar hoy?"
            )
            return self._prepare_spoken_text(guion)

        if etapa == "consulta_sedes":
            if sede:
                guion = (
                    f"Claro que sí. Nuestra {sede['nombre']} está ubicada en {sede['direccion']}. "
                    f"¿Qué celular Android o iPhone te gustaría cotizar o dejar apartado en esta sede?"
                )
            else:
                guion = (
                    "En Cel Red contamos con catorce sedes oficiales en Putumayo, Nariño, Antioquia y Huila. "
                    "Estamos en Puerto Asís, Mocoa, La Hormiga, Orito, tres sedes en Ipiales, tres sedes en Pasto, Túquerres, La Unión, Neiva y Medellín. "
                    "¿En cuál ciudad te encuentras y qué celular te gustaría cotizar hoy?"
                )
            return self._prepare_spoken_text(guion)

        if etapa == "sede_confirmada" and prod and sede:
            nombre_limpio = re.sub(r"\([^\)]+\)", "", prod.modelo).strip()
            _, monto_voz = self._resolve_platform_payment_text_and_voice(prod, medio_pago, es_separado)
            color_hablado = f" en color {color_elegido.lower()}" if color_elegido else ""
            guion = (
                f"Listo, ya envié tu orden del {nombre_limpio}{color_hablado} directamente a nuestra {sede['nombre']}, ubicada en {sede['direccion']}. "
                f"Puedes acercarte hoy mismo con tu cédula para realizar el proceso por {medio_pago.lower()} con {monto_voz} "
                f"y reclamar tu equipo con su factura y garantía. Te esperamos en Cel Red."
            )
            return self._prepare_spoken_text(guion)

        if etapa == "pedir_sede_pago" and prod:
            nombre_limpio = re.sub(r"\([^\)]+\)", "", prod.modelo).strip()
            _, monto_voz = self._resolve_platform_payment_text_and_voice(prod, medio_pago, es_separado)
            color_hablado = f" en color {color_elegido.lower()}" if color_elegido else ""
            guion = (
                f"Perfecto, ya registré tu solicitud mediante {medio_pago.lower()} con {monto_voz} para el {nombre_limpio}{color_hablado}. "
                f"Para dejarte el equipo listo en caja, dime en cuál de nuestras sedes te encuentras: "
                f"Puerto Asís, Mocoa, La Hormiga, Orito, Ipiales, Pasto, Túquerres, Medellín, Neiva o La Unión."
            )
            return self._prepare_spoken_text(guion)

        if etapa == "cierre_inicial" and prod:
            nombre_limpio = re.sub(r"\([^\)]+\)", "", prod.modelo).strip()
            _, monto_voz = self._resolve_platform_payment_text_and_voice(prod, medio_pago, es_separado)
            obsequio = self._get_iphone_obsequio(prod)
            obs_voz = f" Además te incluye de obsequio {obsequio}." if obsequio else ""
            if es_separado:
                guion = (
                    f"Perfecto, ya dejé registrado tu plan separado en Cel Red para el {nombre_limpio} con {monto_voz}.{obs_voz} "
                    f"¿En cuál de nuestras sedes en Puerto Asís, Mocoa, La Hormiga, Orito, Ipiales, Pasto, Túquerres, Medellín, Neiva o La Unión te queda más cerca pasar a realizar el abono?"
                )
            else:
                es_iphone_prod = "iphone" in prod.modelo.lower()
                plats_voz = (
                    "Addi, Sistecrédito, Banco de Bogotá o Renting para iPhone"
                    if es_iphone_prod
                    else "Addi, Sistecrédito, Banco de Bogotá, Krediya o Credimóvil"
                )
                guion = (
                    f"Excelente elección. Ya dejé confirmada tu orden en Cel Red por el {nombre_limpio}, con {monto_voz}.{obs_voz} "
                    f"¿Deseas llevarlo de contado o por plataforma como {plats_voz}, y en cuál ciudad o sede te encuentras?"
                )
            return self._prepare_spoken_text(guion)

        if len(sugeridos) > 1:
            pide_solo_contado = analysis.get("pide_solo_contado", False)
            tiene_iphone = any("iphone" in p.modelo.lower() for p in sugeridos)
            tiene_android = any("iphone" not in p.modelo.lower() for p in sugeridos)
            if tiene_android and not tiene_iphone:
                plats_comp_voz = "Addi, Sistecrédito, Banco de Bogotá, Krediya y Credimóvil"
            elif tiene_iphone and not tiene_android:
                plats_comp_voz = "Addi, Sistecrédito, Banco de Bogotá y Renting exclusivo para iPhone"
            else:
                plats_comp_voz = "Addi, Sistecrédito, Banco de Bogotá, Krediya y Credimóvil para Android, o Renting para iPhone"
            p1 = sugeridos[0]
            p2 = sugeridos[1]
            n1 = re.sub(r"\([^\)]+\)", "", p1.modelo).strip()
            n2 = re.sub(r"\([^\)]+\)", "", p2.modelo).strip()
            pr1 = price_to_spoken_spanish(p1.precio_cop)
            pr2 = price_to_spoken_spanish(p2.precio_cop)
            cond1 = " en versión seminuevo Open Box" if "open box" in p1.categoria.lower() else ""
            cond2 = " en versión seminuevo Open Box" if "open box" in p2.categoria.lower() else ""
            obs1 = self._get_iphone_obsequio(p1)
            obs_txt = f" Recuerda que incluye de obsequio {obs1}." if obs1 else ""
            if pide_solo_contado:
                guion = (
                    f"Claro que sí. En Cel Red tenemos disponibles de contado el {n1}{cond1} en {pr1}, "
                    f"y el {n2}{cond2} por {pr2}.{obs_txt} "
                    f"¿Cuál de estas opciones prefieres y en cuál de nuestras sedes te queda más cerca recogerlo?"
                )
            else:
                guion = (
                    f"Claro que sí. En Cel Red tenemos disponibles el {n1}{cond1} en {pr1} de contado, "
                    f"y el {n2}{cond2} por {pr2}, además de los precios de desembolso e iniciales en {plats_comp_voz} que ves en pantalla.{obs_txt} "
                    f"¿Cuál de estas opciones prefieres y por qué medio deseas llevarlo?"
                )
            return self._prepare_spoken_text(guion)

        if prod:
            pide_solo_contado = analysis.get("pide_solo_contado", False)
            nombre_limpio = re.sub(r"\([^\)]+\)", "", prod.modelo).strip()
            precio_hablado = price_to_spoken_spanish(prod.precio_cop)
            cond = " en modalidad Open Box seminuevo garantizado" if "open box" in prod.categoria.lower() else " totalmente nuevo"
            obsequio = self._get_iphone_obsequio(prod)
            obs_voz = f" Además te incluye de obsequio {obsequio}." if obsequio else ""
            if pide_solo_contado:
                guion = (
                    f"Tenemos disponible en Cel Red el {nombre_limpio}{cond}, por un precio oficial de contado de {precio_hablado}.{obs_voz} "
                    f"¿En cuál de nuestras sedes te queda más cerca recogerlo?"
                )
                return self._prepare_spoken_text(guion)
            pinfo = get_platform_info(prod.sku)
            extra_plat_voz = ""
            if pinfo.get("renting"):
                r = pinfo["renting"]
                extra_plat_voz = (
                    f" También puedes llevarlo por Addi o Sistecrédito en {price_to_spoken_spanish(pinfo['addi_sistecredito'])}, "
                    f"o por Renting si tienes poco historial crediticio o estás reportado dando una inicial del veinte por ciento de {price_to_spoken_spanish(r['inicial_20'])}."
                )
            elif pinfo.get("krediya"):
                k = pinfo["krediya"]
                extra_plat_voz = (
                    f" Por Addi o Sistecrédito queda en {price_to_spoken_spanish(pinfo['addi_sistecredito'])}, "
                    f"y por Krediya lo sacas con una inicial al treinta por ciento de {price_to_spoken_spanish(k['inicial_30'])}."
                )
            elif pinfo.get("addi_sistecredito"):
                extra_plat_voz = f" Por Addi o Sistecrédito su valor de desembolso es de {price_to_spoken_spanish(pinfo['addi_sistecredito'])}."
            guion = (
                f"Tenemos disponible en Cel Red el {nombre_limpio}{cond}, por un precio de contado de {precio_hablado}.{extra_plat_voz}{obs_voz} "
                f"¿Deseas llevarlo de contado o por alguna de nuestras plataformas de crédito?"
            )
            return self._prepare_spoken_text(guion)

        return self._prepare_spoken_text(
            f"Hola, {saludo_hora}. Bienvenido a Cel Red, hablas con tu asesor comercial. Cuéntame, ¿cómo puedo ayudarte hoy?"
        )

    def _prepare_spoken_text(self, full_text: str) -> str:
        text = full_text
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"(?m)^\s*#{1,6}\s+", "", text)

        text = re.sub(r"\b(\d+)\s*GB\b", r"\1 gigas", text, flags=re.IGNORECASE)
        text = re.sub(r"\b(\d+)\s*MP\b", r"\1 megapíxeles", text, flags=re.IGNORECASE)
        text = re.sub(r"\b(\d+)\s*mAh\b", r"\1 miliamperios", text, flags=re.IGNORECASE)
        text = re.sub(r"\b5G\b", "cinco G", text)
        text = re.sub(r"\bIMEI\b", "I M E I", text)
        text = re.sub(r"\bORD-\d{8}-[A-Z0-9]{4}\b", "", text)

        text = re.sub(r"\s*//\s*", ", ", text)
        text = re.sub(r"\s*/\s*", " o ", text)
        text = re.sub(r"\s*\|\s*", ", ", text)

        text = re.sub(r"\n\s*[\-•]\s*", ". ", text)
        text = re.sub(r"\n+", ". ", text)
        text = re.sub(r"\s*;\s*", ", ", text)
        text = re.sub(r"\s+[\-—–]\s+", ", ", text)

        text = re.sub(r"\s*\(([^\)]+)\)", r", \1,", text)
        text = re.sub(r"[\(\)\[\]\{\}<>_~`]", " ", text)
        text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
        text = re.sub(r"[🚨⚠️ℹ️📍🔥🚗🌊⚡•⟳✅🔒💡📱💳💵👉]", "", text)

        text = re.sub(r",\s*:", ":", text)
        text = re.sub(r":\s*\.", ":", text)
        text = re.sub(r"([,\.])\s*[,\.]+", r"\1", text)
        text = re.sub(r"\s+([,\.\?!:])", r"\1", text)
        text = re.sub(r"\s+", " ", text).strip()

        return text


emergency_orchestrator = EmergencyOrchestrator()
