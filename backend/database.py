"""
Módulo de Base de Datos Transaccional y Vectorial — CEL RED (Tienda de Celulares y Accesorios)
Asesor Comercial Multimodal IA (Catálogo Oficial Contado: Android Nuevos, iPhone Nuevos y Open Box Seminuevos)

Administra la conexión aislada a PostgreSQL (`celred_db`) con soporte pgvector,
las tablas transaccionales de inventario (`productos_celred`), órdenes de venta/separados (`ordenes_celred`),
historial de conversación (`interacciones_celred`) y conocimiento semántico (`conocimiento_rag_celred`).
"""

import os
import sys
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, select, text, func, delete
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from pydantic import BaseModel, Field, ConfigDict

try:
    from pgvector.sqlalchemy import Vector  # type: ignore
except ImportError:
    from sqlalchemy.types import UserDefinedType
    class Vector(UserDefinedType):
        def __init__(self, dim=2048):
            self.dim = dim
        def get_col_spec(self, **kw):
            return f"vector({self.dim})"

# =====================================================================
# Configuración de Conexión Aislada (celred_db)
# =====================================================================
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "celred_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgrespassword")

VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "2048"))

DATABASE_URL_ASYNC = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
DATABASE_URL_ADMIN = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres"
DATABASE_URL_SYNC = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def utc_now():
    return datetime.now(timezone.utc)


async_engine = create_async_engine(
    DATABASE_URL_ASYNC,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

Base = declarative_base()


# =====================================================================
# Enumeraciones Comerciales de CEL RED
# =====================================================================
class PrioridadIncidente(str, Enum):
    BAJA = "Consulta"
    MEDIA = "Cotización"
    ALTA = "Separado"
    CRITICA = "Compra Inmediata"


class EstadoIncidente(str, Enum):
    REGISTRADO = "En asesoría"
    EN_REVISION = "Candado de Confirmación"
    ESCALADO = "Venta / Separado Confirmado"
    CERRADO = "Facturada"


class CanalAtencion(str, Enum):
    VOZ = "Voz"
    TEXTO = "Texto"
    WEBSOCKET = "WebSocket"


class TipoEvento(str, Enum):
    GAMA_ALTA = "Celular Gama Alta / Flagship"
    GAMA_MEDIA = "Celular Gama Media-Alta"
    GAMER = "Celular Alto Rendimiento / Gaming"
    ECONOMICO = "Celular Gama Económica"
    OPEN_BOX = "Equipo Open Box (Seminuevo Garantizado)"
    APPLE_ECOSYSTEM = "Ecosistema Apple (MacBook / iPad)"
    PLAN_SEPARADO = "Sistema de Separado / Financiación"
    GARANTIA_SOPORTE = "Garantía y Servicio Técnico"
    OTRO = "Asesoría General de Catálogo"


# =====================================================================
# Modelos SQLAlchemy
# =====================================================================
class Producto(Base):
    """
    Tabla de Inventario y Catálogo Oficial de CEL RED (Android Nuevos, iPhone/Samsung Nuevos y Open Box Seminuevos).
    """
    __tablename__ = "productos_celred"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sku = Column(String(50), unique=True, index=True, nullable=False)
    marca = Column(String(60), index=True, nullable=False)
    modelo = Column(String(160), index=True, nullable=False)
    categoria = Column(String(60), default="Celular Nuevo", nullable=False)  # Celular Nuevo, Open Box (Seminuevo), Computador / Tablet
    gama = Column(String(60), default="Gama Media")
    especificaciones = Column(Text, nullable=False)
    precio_cop = Column(Integer, nullable=False)
    stock = Column(Integer, default=5, nullable=False)
    colores_disponibles = Column(String(160), default="Según disponibilidad en vitrina")
    garantia_meses = Column(Integer, default=12)
    destacado_para = Column(String(180), default="Uso general y redes sociales")
    creado_en = Column(DateTime(timezone=True), default=utc_now)

    def __repr__(self):
        return f"<Producto(sku={self.sku}, modelo={self.modelo}, precio={self.precio_cop}, categoria={self.categoria})>"


class Incidente(Base):
    """
    Tabla transaccional de Órdenes de Venta, Cotizaciones y Separados de CEL RED.
    """
    __tablename__ = "ordenes_celred"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo = Column(String(50), unique=True, index=True, nullable=False)
    descripcion = Column(Text, nullable=False)
    ubicacion = Column(String(255), nullable=False)
    municipio = Column(String(100), default="Sede Principal Cel Red - Mocoa")
    hora_incidente = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    tipo_evento = Column(String(160), default=TipoEvento.OTRO.value, nullable=False)
    prioridad = Column(String(40), default=PrioridadIncidente.MEDIA.value, nullable=False)
    estado = Column(String(50), default=EstadoIncidente.REGISTRADO.value, nullable=False)
    canal_atencion = Column(String(20), default=CanalAtencion.TEXTO.value, nullable=False)
    nombre_reportante = Column(String(150), nullable=True)
    telefono_reportante = Column(String(50), nullable=True)
    detalles_victimas = Column(Text, nullable=True)
    acciones_recomendadas = Column(Text, nullable=True)
    escalado_a = Column(String(150), nullable=True)
    creado_en = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    actualizado_en = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    interacciones = relationship("Interaccion", back_populates="incidente", cascade="all, delete-orphan")


class Interaccion(Base):
    __tablename__ = "interacciones_celred"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incidente_id = Column(Integer, ForeignKey("ordenes_celred.id", ondelete="CASCADE"), nullable=True)
    session_id = Column(String(100), index=True, nullable=False)
    rol = Column(String(20), nullable=False)
    mensaje = Column(Text, nullable=False)
    canal = Column(String(20), default=CanalAtencion.TEXTO.value)
    audio_path = Column(String(255), nullable=True)
    duracion_audio_seg = Column(Float, nullable=True)
    creado_en = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    incidente = relationship("Incidente", back_populates="interacciones")


class ProtocoloRAG(Base):
    __tablename__ = "conocimiento_rag_celred"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    titulo = Column(String(255), index=True, nullable=False)
    categoria = Column(String(100), index=True, nullable=False)
    contenido = Column(Text, nullable=False)
    fuente = Column(String(255), nullable=True)
    embedding = Column(Vector(VECTOR_DIMENSION), nullable=False)
    creado_en = Column(DateTime(timezone=True), default=utc_now)


# =====================================================================
# Esquemas Pydantic
# =====================================================================
class ProductoResponse(BaseModel):
    id: int
    sku: str
    marca: str
    modelo: str
    categoria: str
    gama: Optional[str] = None
    especificaciones: str
    precio_cop: int
    stock: int
    colores_disponibles: str
    garantia_meses: int
    destacado_para: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class IncidenteBase(BaseModel):
    descripcion: str
    ubicacion: str
    municipio: Optional[str] = "Sede Principal Cel Red - Mocoa"
    tipo_evento: Optional[str] = TipoEvento.OTRO.value
    prioridad: Optional[str] = PrioridadIncidente.MEDIA.value
    canal_atencion: Optional[str] = CanalAtencion.TEXTO.value
    nombre_reportante: Optional[str] = None
    telefono_reportante: Optional[str] = None
    detalles_victimas: Optional[str] = None


class IncidenteCreate(IncidenteBase):
    hora_incidente: Optional[datetime] = None


class IncidenteUpdate(BaseModel):
    descripcion: Optional[str] = None
    ubicacion: Optional[str] = None
    tipo_evento: Optional[str] = None
    prioridad: Optional[str] = None
    estado: Optional[str] = None
    acciones_recomendadas: Optional[str] = None
    escalado_a: Optional[str] = None


class IncidenteResponse(IncidenteBase):
    id: int
    codigo: str
    hora_incidente: datetime
    estado: str
    acciones_recomendadas: Optional[str] = None
    escalado_a: Optional[str] = None
    creado_en: datetime
    actualizado_en: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProtocoloResult(BaseModel):
    id: int
    titulo: str
    categoria: str
    contenido: str
    fuente: Optional[str] = None
    similitud: float


class ChatTextRequest(BaseModel):
    session_id: Optional[str] = None
    mensaje: str = Field(..., min_length=1, description="Consulta o mensaje del cliente en Cel Red")
    incidente_id: Optional[int] = None
    nombre_reportante: Optional[str] = None
    telefono_reportante: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    respuesta_texto: str
    texto_transcrito: Optional[str] = None
    incidente: Optional[IncidenteResponse] = None
    audio_url: Optional[str] = None
    protocolos_utilizados: List[str] = []
    prioridad_detectada: Optional[str] = None
    estado_incidente: Optional[str] = None
    alerta_escalamiento: bool = False


# =====================================================================
# CATÁLOGO OFICIAL REAL DE CEL RED (72 REFERENCIAS EXACTAS DE CONTADO)
# Tabla 1: Android Nuevos | Tabla 2: iPhone/Samsung/Apple Nuevos | Tabla 3: Open Box (Seminuevos)
# =====================================================================
CATALOGO_INICIAL_CELRED = [
    # -----------------------------------------------------------------
    # TABLA 1: ANDROID NUEVOS (29 Referencias)
    # -----------------------------------------------------------------
    {
        "sku": "AND-INF-HOT70-256",
        "marca": "Infinix",
        "modelo": "Infinix Hot 70 (256GB / 4GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Económica",
        "especificaciones": "Equipo Nuevo Sellado. 256GB de almacenamiento interno y 4GB RAM, gran pantalla fluida y batería de 5000mAh.",
        "precio_cop": 675000,
        "stock": 8,
        "colores_disponibles": "Negro, Azul, Verde",
        "garantia_meses": 12,
        "destacado_para": "Gran almacenamiento de 256GB a precio económico"
    },
    {
        "sku": "AND-INF-HOT60PP-256",
        "marca": "Infinix",
        "modelo": "Infinix Hot 60 Pro Plus (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media",
        "especificaciones": "Equipo Nuevo Sellado. 256GB de almacenamiento y 8GB RAM, pantalla de alta tasa de refresco y carga rápida.",
        "precio_cop": 870000,
        "stock": 6,
        "colores_disponibles": "Negro, Titanio, Verde",
        "garantia_meses": 12,
        "destacado_para": "Fluidez multitarea con 8GB RAM y 256GB por menos de $900.000"
    },
    {
        "sku": "AND-INF-NOTEEDGE",
        "marca": "Infinix",
        "modelo": "Infinix Note Edge Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media-Alta",
        "especificaciones": "Equipo Nuevo Sellado. Pantalla curva premium tipo Edge, alto rendimiento, carga rápida y diseño elegante.",
        "precio_cop": 1020000,
        "stock": 5,
        "colores_disponibles": "Negro Obsidiana, Dorado, Verde",
        "garantia_meses": 12,
        "destacado_para": "Diseño de pantalla curva y excelente presencia alrededor del millón de pesos"
    },
    {
        "sku": "AND-SAM-A05-128",
        "marca": "Samsung",
        "modelo": "Samsung Galaxy A05 (128GB / 4GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Económica",
        "especificaciones": "Equipo Nuevo Sellado. 128GB de memoria y 4GB RAM, cámara principal de 50MP, pantalla de 6.7 pulgadas y batería 5000mAh.",
        "precio_cop": 350000,
        "stock": 12,
        "colores_disponibles": "Negro, Plata, Verde Claro",
        "garantia_meses": 12,
        "destacado_para": "El Samsung más económico del catálogo ($350.000) con 128GB para uso diario y WhatsApp"
    },
    {
        "sku": "AND-SAM-A17-256",
        "marca": "Samsung",
        "modelo": "Samsung Galaxy A17 (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media",
        "especificaciones": "Equipo Nuevo Sellado. 256GB de almacenamiento y 8GB RAM, pantalla Super AMOLED y triple cámara de alta definición.",
        "precio_cop": 720000,
        "stock": 9,
        "colores_disponibles": "Azul Oscuro, Negro, Azul Claro",
        "garantia_meses": 12,
        "destacado_para": "Calidad Samsung con 256GB y 8GB RAM a excelente precio ($720.000)"
    },
    {
        "sku": "AND-SAM-A07-128",
        "marca": "Samsung",
        "modelo": "Samsung Galaxy A07 (128GB / 6GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Económica",
        "especificaciones": "Equipo Nuevo Sellado. 128GB de almacenamiento y 6GB RAM, batería de larga duración 5000mAh y cámara de 50MP.",
        "precio_cop": 470000,
        "stock": 10,
        "colores_disponibles": "Negro, Azul, Verde",
        "garantia_meses": 12,
        "destacado_para": "Celular Samsung económico con 6GB de RAM por menos de $500.000"
    },
    {
        "sku": "AND-SAM-A37-256",
        "marca": "Samsung",
        "modelo": "Samsung Galaxy A37 5G (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media-Alta",
        "especificaciones": "Equipo Nuevo Sellado. Conectividad 5G, 256GB de memoria y 8GB RAM, pantalla Super AMOLED 120Hz y cámara con estabilización.",
        "precio_cop": 1160000,
        "stock": 7,
        "colores_disponibles": "Azul Hielo, Negro, Lila",
        "garantia_meses": 12,
        "destacado_para": "Samsung 5G equilibrado en cámara, pantalla y durabilidad por menos de $1.200.000"
    },
    {
        "sku": "AND-OPP-A5X-128",
        "marca": "Oppo",
        "modelo": "Oppo A5X (128GB / 4GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Económica",
        "especificaciones": "Equipo Nuevo Sellado. 128GB de almacenamiento y 4GB RAM, diseño ultrarresistente a salpicaduras y golpes, batería duradera.",
        "precio_cop": 510000,
        "stock": 8,
        "colores_disponibles": "Azul, Negro",
        "garantia_meses": 12,
        "destacado_para": "Resistencia y confiabilidad Oppo en gama de entrada ($510.000)"
    },
    {
        "sku": "AND-OPP-A80-256",
        "marca": "Oppo",
        "modelo": "Oppo A80 5G (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media",
        "especificaciones": "Equipo Nuevo Sellado. Conectividad 5G, 256GB y 8GB RAM, carga rápida SuperVOOC y estructura reforzada antigolpes.",
        "precio_cop": 910000,
        "stock": 6,
        "colores_disponibles": "Negro Estelar, Morado",
        "garantia_meses": 12,
        "destacado_para": "Conectividad 5G, alta resistencia física y 256GB por menos de $950.000"
    },
    {
        "sku": "AND-RED-A5-128",
        "marca": "Xiaomi Redmi",
        "modelo": "Redmi A5 (128GB / 4GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Económica",
        "especificaciones": "Equipo Nuevo Sellado. 128GB de memoria interna y 4GB RAM, pantalla amplia de 90Hz y batería de 5000mAh.",
        "precio_cop": 350000,
        "stock": 14,
        "colores_disponibles": "Negro, Azul, Verde",
        "garantia_meses": 12,
        "destacado_para": "El Xiaomi más económico ($350.000) con 128GB de memoria"
    },
    {
        "sku": "AND-RED-A7P-128",
        "marca": "Xiaomi Redmi",
        "modelo": "Redmi A7 Pro (128GB / 4GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Económica",
        "especificaciones": "Equipo Nuevo Sellado. 128GB de memoria y 4GB RAM, diseño moderno, cámara nítida y batería para todo el día.",
        "precio_cop": 460000,
        "stock": 10,
        "colores_disponibles": "Negro, Azul, Verde",
        "garantia_meses": 12,
        "destacado_para": "Gama económica superior por solo $460.000"
    },
    {
        "sku": "AND-RED-15-256",
        "marca": "Xiaomi Redmi",
        "modelo": "Redmi 15 (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media",
        "especificaciones": "Equipo Nuevo Sellado. 256GB de almacenamiento y 8GB RAM, pantalla FHD+ fluida y excelente autonomía.",
        "precio_cop": 680000,
        "stock": 9,
        "colores_disponibles": "Negro, Azul, Plata",
        "garantia_meses": 12,
        "destacado_para": "256GB y 8GB RAM por menos de $700.000"
    },
    {
        "sku": "AND-RED-17-256",
        "marca": "Xiaomi Redmi",
        "modelo": "Redmi 17 (256GB / 4GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Económica",
        "especificaciones": "Equipo Nuevo Sellado. 256GB de memoria interna y 4GB RAM, gran capacidad para fotos, videos y aplicaciones.",
        "precio_cop": 670000,
        "stock": 8,
        "colores_disponibles": "Negro, Azul",
        "garantia_meses": 12,
        "destacado_para": "Alto almacenamiento de 256GB en línea Redmi ($670.000)"
    },
    {
        "sku": "AND-RED-N17-256-8",
        "marca": "Xiaomi Redmi",
        "modelo": "Redmi Note 17 (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media",
        "especificaciones": "Equipo Nuevo Sellado. 256GB de almacenamiento y 8GB RAM, pantalla AMOLED 120Hz, cámara de alta resolución y carga rápida.",
        "precio_cop": 820000,
        "stock": 10,
        "colores_disponibles": "Negro, Azul Hielo, Verde",
        "garantia_meses": 12,
        "destacado_para": "Uno de los favoritos en calidad-precio con 256GB y 8GB RAM ($820.000)"
    },
    {
        "sku": "AND-RED-N17-256-6",
        "marca": "Xiaomi Redmi",
        "modelo": "Redmi Note 17 (256GB / 6GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media",
        "especificaciones": "Equipo Nuevo Sellado. 256GB de memoria y 6GB RAM, pantalla AMOLED 120Hz y batería de 5000mAh con carga rápida.",
        "precio_cop": 750000,
        "stock": 8,
        "colores_disponibles": "Negro, Azul",
        "garantia_meses": 12,
        "destacado_para": "Línea Redmi Note con 256GB por solo $750.000"
    },
    {
        "sku": "AND-RED-15C-256",
        "marca": "Xiaomi Redmi",
        "modelo": "Redmi 15C (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Económica",
        "especificaciones": "Equipo Nuevo Sellado. 256GB de almacenamiento y 8GB RAM, pantalla grande de 6.74 pulgadas y gran batería.",
        "precio_cop": 620000,
        "stock": 11,
        "colores_disponibles": "Negro, Azul, Verde Menta",
        "garantia_meses": 12,
        "destacado_para": "El 256GB con 8GB RAM más económico de Xiaomi ($620.000)"
    },
    {
        "sku": "AND-RED-N15P-256",
        "marca": "Xiaomi Redmi",
        "modelo": "Redmi Note 15 Pro (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media-Alta",
        "especificaciones": "Equipo Nuevo Sellado. Versión Pro con cámara profesional de alta nitidez, 256GB / 8GB RAM, pantalla AMOLED 120Hz y carga turbo.",
        "precio_cop": 970000,
        "stock": 7,
        "colores_disponibles": "Negro Medianoche, Lavanda, Verde",
        "garantia_meses": 12,
        "destacado_para": "Excelente cámara versión Pro por menos de $1.000.000 ($970.000)"
    },
    {
        "sku": "AND-RED-N15-256",
        "marca": "Xiaomi Redmi",
        "modelo": "Redmi Note 15 (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media",
        "especificaciones": "Equipo Nuevo Sellado. 256GB de almacenamiento y 8GB RAM, pantalla AMOLED y gran rendimiento diario.",
        "precio_cop": 780000,
        "stock": 9,
        "colores_disponibles": "Negro, Azul, Verde",
        "garantia_meses": 12,
        "destacado_para": "Equilibrio total en gama media por $780.000"
    },
    {
        "sku": "AND-POC-F8P-256",
        "marca": "Xiaomi POCO",
        "modelo": "POCO F8 Pro (256GB / 12GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gaming / Gama Alta",
        "especificaciones": "Equipo Nuevo Sellado. Procesador de gama alta extrema, 12GB RAM + 256GB, pantalla Flow AMOLED 120Hz y carga ultrarrápida.",
        "precio_cop": 1860000,
        "stock": 5,
        "colores_disponibles": "Negro, Blanco, Titanio",
        "garantia_meses": 12,
        "destacado_para": "Potencia bruta para gaming competitivo y multitarea pesada ($1.860.000)"
    },
    {
        "sku": "AND-POC-X8PM-512",
        "marca": "Xiaomi POCO",
        "modelo": "POCO X8 Pro Max (512GB / 12GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gaming / Gama Alta",
        "especificaciones": "Equipo Nuevo Sellado. Máxima capacidad de 512GB y 12GB RAM, procesador gamer de última generación y refrigeración líquida.",
        "precio_cop": 1960000,
        "stock": 5,
        "colores_disponibles": "Negro, Amarillo POCO, Gris",
        "garantia_meses": 12,
        "destacado_para": "El rey del gaming y almacenamiento con 512GB y 12GB RAM ($1.960.000)"
    },
    {
        "sku": "AND-HON-400S-256",
        "marca": "Honor",
        "modelo": "Honor 400 Smart (256GB / 6GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media",
        "especificaciones": "Equipo Nuevo Sellado. 256GB de memoria y 6GB RAM, diseño ultraligero y resistente con excelente autonomía de batería.",
        "precio_cop": 700000,
        "stock": 7,
        "colores_disponibles": "Negro, Verde Esmeralda, Plata",
        "garantia_meses": 12,
        "destacado_para": "Confiabilidad Honor con 256GB exactos en $700.000"
    },
    {
        "sku": "AND-TEC-CAM50P-256",
        "marca": "Tecno",
        "modelo": "Tecno Camon 50 Pro (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media-Alta",
        "especificaciones": "Equipo Nuevo Sellado. Serie Camon especializada en fotografía profesional y retrato, 256GB / 8GB RAM y pantalla AMOLED.",
        "precio_cop": 1250000,
        "stock": 6,
        "colores_disponibles": "Negro, Blanco Perla, Verde",
        "garantia_meses": 12,
        "destacado_para": "Especialista en cámaras y fotografía nocturna ($1.250.000)"
    },
    {
        "sku": "AND-TEC-SPGO2-128",
        "marca": "Tecno",
        "modelo": "Tecno Spark Go 2 (128GB / 4GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Económica",
        "especificaciones": "Equipo Nuevo Sellado. 128GB de almacenamiento y 4GB RAM, batería de 5000mAh y lector de huella lateral.",
        "precio_cop": 360000,
        "stock": 12,
        "colores_disponibles": "Negro, Azul, Verde",
        "garantia_meses": 12,
        "destacado_para": "Celular muy económico ($360.000) con 128GB de almacenamiento"
    },
    {
        "sku": "AND-TEC-SP40-256",
        "marca": "Tecno",
        "modelo": "Tecno Spark 40 (256GB / 4GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Económica",
        "especificaciones": "Equipo Nuevo Sellado. 256GB de memoria interna y 4GB RAM, cámara clara y batería duradera.",
        "precio_cop": 550000,
        "stock": 9,
        "colores_disponibles": "Negro, Azul, Dorado",
        "garantia_meses": 12,
        "destacado_para": "El equipo de 256GB más económico del catálogo ($550.000)"
    },
    {
        "sku": "AND-TEC-SP50-256",
        "marca": "Tecno",
        "modelo": "Tecno Spark 50 (256GB / 4GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Económica",
        "especificaciones": "Equipo Nuevo Sellado. 256GB de memoria y 4GB RAM, diseño renovado, pantalla fluida de 90Hz y carga rápida.",
        "precio_cop": 690000,
        "stock": 8,
        "colores_disponibles": "Negro, Azul, Blanco",
        "garantia_meses": 12,
        "destacado_para": "Gran espacio de 256GB y diseño moderno por $690.000"
    },
    {
        "sku": "AND-TEC-CAM50U-256",
        "marca": "Tecno",
        "modelo": "Tecno Camon 50 Ultra (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media-Alta",
        "especificaciones": "Equipo Nuevo Sellado. Versión Ultra con sistema de cámaras avanzado, 256GB / 8GB RAM y acabados de lujo.",
        "precio_cop": 1280000,
        "stock": 5,
        "colores_disponibles": "Negro, Verde Cuero, Titanio",
        "garantia_meses": 12,
        "destacado_para": "Fotografía avanzada versión Ultra en la línea Tecno ($1.280.000)"
    },
    {
        "sku": "AND-TEC-POVAC2",
        "marca": "Tecno",
        "modelo": "Tecno Pova Curve 2 Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gaming / Gama Media-Alta",
        "especificaciones": "Equipo Nuevo Sellado. Pantalla curva AMOLED, súper batería de larga duración, diseño gamer futurista y carga rápida.",
        "precio_cop": 1040000,
        "stock": 6,
        "colores_disponibles": "Negro, Plata, Azul",
        "garantia_meses": 12,
        "destacado_para": "Batería extrema y pantalla curva por $1.040.000"
    },
    {
        "sku": "AND-TEC-SPGO3-128",
        "marca": "Tecno",
        "modelo": "Tecno Spark Go 3 (128GB / 4GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Económica",
        "especificaciones": "Equipo Nuevo Sellado. 128GB de almacenamiento y 4GB RAM, nueva generación Spark Go con gran autonomía.",
        "precio_cop": 420000,
        "stock": 10,
        "colores_disponibles": "Negro, Azul",
        "garantia_meses": 12,
        "destacado_para": "Nueva generación económica en $420.000"
    },
    {
        "sku": "AND-ITE-A100C-128",
        "marca": "Itel",
        "modelo": "Itel A100C (128GB / 4GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Económica",
        "especificaciones": "Equipo Nuevo Sellado. 128GB de memoria y 4GB RAM, práctico, resistente y económico.",
        "precio_cop": 370000,
        "stock": 10,
        "colores_disponibles": "Negro, Azul",
        "garantia_meses": 12,
        "destacado_para": "Equipo económico de 128GB por solo $370.000"
    },

    # -----------------------------------------------------------------
    # TABLA 2: PRECIOS IPHONE NUEVOS + SAMSUNG GAMA ALTA + APPLE (20 Referencias)
    # -----------------------------------------------------------------
    {
        "sku": "NEW-APL-IP13-128",
        "marca": "Apple",
        "modelo": "iPhone 13 128GB Activo (Nuevo)",
        "categoria": "Celular Nuevo",
        "gama": "Gama Alta",
        "especificaciones": "Equipo iPhone Nuevo Activo de 128GB. Chip A15 Bionic, doble cámara 12MP con Modo Cine, Face ID y pantalla Super Retina XDR.",
        "precio_cop": 1840000,
        "stock": 5,
        "colores_disponibles": "Medianoche, Blanco Estelar, Azul, Rosa",
        "garantia_meses": 12,
        "destacado_para": "iPhone 13 Nuevo de contado ($1.840.000) con garantía completa"
    },
    {
        "sku": "NEW-APL-IP14-128",
        "marca": "Apple",
        "modelo": "iPhone 14 128GB Activo (Nuevo)",
        "categoria": "Celular Nuevo",
        "gama": "Gama Alta",
        "especificaciones": "Equipo iPhone Nuevo Activo de 128GB. Chip A15 Bionic con GPU de 5 núcleos, Modo Acción en video, Photonic Engine y Face ID.",
        "precio_cop": 2100000,
        "stock": 5,
        "colores_disponibles": "Medianoche, Blanco Estelar, Morado, Azul",
        "garantia_meses": 12,
        "destacado_para": "iPhone 14 Nuevo de 128GB ($2.100.000)"
    },
    {
        "sku": "NEW-APL-IP15-128",
        "marca": "Apple",
        "modelo": "iPhone 15 128GB Activo (Nuevo)",
        "categoria": "Celular Nuevo",
        "gama": "Gama Alta",
        "especificaciones": "Equipo iPhone Nuevo Activo de 128GB. Isla Dinámica (Dynamic Island), cámara de 48MP con zoom 2x, puerto USB-C y Chip A16 Bionic.",
        "precio_cop": 2200000,
        "stock": 6,
        "colores_disponibles": "Negro, Azul, Rosa, Verde",
        "garantia_meses": 12,
        "destacado_para": "iPhone 15 Nuevo con Isla Dinámica y USB-C ($2.200.000)"
    },
    {
        "sku": "NEW-APL-IP16-128",
        "marca": "Apple",
        "modelo": "iPhone 16 128GB Activo (Nuevo)",
        "categoria": "Celular Nuevo",
        "gama": "Gama Alta",
        "especificaciones": "Equipo iPhone Nuevo Activo de 128GB. Botón de Control de Cámara, Chip A18 compatible con Apple Intelligence y cámara Fusion de 48MP.",
        "precio_cop": 2600000,
        "stock": 5,
        "colores_disponibles": "Negro, Blanco, Azul Ultramar, Rosa, Verde Azulado",
        "garantia_meses": 12,
        "destacado_para": "iPhone 16 Nuevo con Control de Cámara y Chip A18 ($2.600.000)"
    },
    {
        "sku": "NEW-APL-IP17-256",
        "marca": "Apple",
        "modelo": "iPhone 17 256GB (Nuevo)",
        "categoria": "Celular Nuevo",
        "gama": "Gama Alta",
        "especificaciones": "Equipo iPhone 17 Nuevo Sellado de 256GB. Pantalla ProMotion OLED de nueva generación, cámaras avanzadas de 48MP y máxima batería.",
        "precio_cop": 3300000,
        "stock": 4,
        "colores_disponibles": "Negro, Plata, Azul, Verde",
        "garantia_meses": 12,
        "destacado_para": "iPhone 17 Nuevo de 256GB ($3.300.000)"
    },
    {
        "sku": "NEW-APL-IP17P-256",
        "marca": "Apple",
        "modelo": "iPhone 17 Pro 256GB (Nuevo)",
        "categoria": "Celular Nuevo",
        "gama": "Gama Alta Flagship",
        "especificaciones": "Equipo iPhone 17 Pro Nuevo Sellado de 256GB. Chasis en titanio, triple cámara profesional ProRAW/ProRes y pantalla 120Hz.",
        "precio_cop": 4120000,
        "stock": 4,
        "colores_disponibles": "Titanio Natural, Titanio Negro, Titanio Blanco",
        "garantia_meses": 12,
        "destacado_para": "Potencia Pro en formato compacto de 256GB ($4.120.000)"
    },
    {
        "sku": "NEW-APL-IP17PM-256-AN",
        "marca": "Apple",
        "modelo": "iPhone 17 Pro Max 256GB Azul y Naranja (Nuevo)",
        "categoria": "Celular Nuevo",
        "gama": "Gama Alta Flagship",
        "especificaciones": "Equipo iPhone 17 Pro Max Nuevo Sellado de 256GB en colores exclusivos Azul y Naranja. Pantalla gigante de 6.9 pulgadas y máxima autonomía.",
        "precio_cop": 4250000,
        "stock": 3,
        "colores_disponibles": "Azul, Naranja",
        "garantia_meses": 12,
        "destacado_para": "iPhone 17 Pro Max 256GB en tonos Azul y Naranja ($4.250.000)"
    },
    {
        "sku": "NEW-APL-IP17PM-256-SIL",
        "marca": "Apple",
        "modelo": "iPhone 17 Pro Max 256GB Silver (Nuevo)",
        "categoria": "Celular Nuevo",
        "gama": "Gama Alta Flagship",
        "especificaciones": "Equipo iPhone 17 Pro Max Nuevo Sellado de 256GB acabado Silver (Plata). Pantalla ProMotion 6.9\" y teleobjetivo tetraprisma.",
        "precio_cop": 4300000,
        "stock": 3,
        "colores_disponibles": "Silver (Plata)",
        "garantia_meses": 12,
        "destacado_para": "iPhone 17 Pro Max 256GB edición Silver ($4.300.000)"
    },
    {
        "sku": "NEW-SAM-A57-256",
        "marca": "Samsung",
        "modelo": "Samsung Galaxy A57 5G (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media-Alta",
        "especificaciones": "Equipo Nuevo Sellado. Conectividad 5G, 256GB y 8GB RAM, resistencia al agua IP67, cámaras con Galaxy AI y chasis metálico.",
        "precio_cop": 1990000,
        "stock": 5,
        "colores_disponibles": "Negro, Azul, Plata",
        "garantia_meses": 12,
        "destacado_para": "El mejor gama media-alta de Samsung con 5G ($1.990.000)"
    },
    {
        "sku": "NEW-SAM-S25U-512",
        "marca": "Samsung",
        "modelo": "Samsung Galaxy S25 Ultra (512GB / 12GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Alta Flagship",
        "especificaciones": "Equipo Nuevo Sellado. S-Pen integrado, cámara de 200MP con zoom óptico avanzado, Snapdragon Elite, 512GB y 12GB RAM.",
        "precio_cop": 3300000,
        "stock": 4,
        "colores_disponibles": "Titanio Negro, Titanio Gris, Titanio Azul",
        "garantia_meses": 12,
        "destacado_para": "Flagship Samsung S25 Ultra con 512GB y S-Pen ($3.300.000)"
    },
    {
        "sku": "NEW-SAM-S25U-256",
        "marca": "Samsung",
        "modelo": "Samsung Galaxy S25 Ultra (256GB / 12GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Alta Flagship",
        "especificaciones": "Equipo Nuevo Sellado. Cámara 200MP, S-Pen integrado, chasis de titanio, Galaxy AI, 256GB de memoria y 12GB RAM.",
        "precio_cop": 2980000,
        "stock": 4,
        "colores_disponibles": "Titanio Negro, Titanio Gris, Titanio Plata",
        "garantia_meses": 12,
        "destacado_para": "Gama Ultra de Samsung por debajo de 3 millones ($2.980.000)"
    },
    {
        "sku": "NEW-SAM-S26U-512",
        "marca": "Samsung",
        "modelo": "Samsung Galaxy S26 Ultra (512GB / 12GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Alta Flagship",
        "especificaciones": "Equipo Nuevo Sellado. Última generación S26 Ultra con 512GB y 12GB RAM, cámara profesional 200MP y pantalla antirreflejo Gorilla Armor.",
        "precio_cop": 3800000,
        "stock": 3,
        "colores_disponibles": "Titanio Negro, Titanio Plata, Titanio Verde",
        "garantia_meses": 12,
        "destacado_para": "Lo más poderoso de Samsung en 512GB ($3.800.000)"
    },
    {
        "sku": "NEW-SAM-S26U-256",
        "marca": "Samsung",
        "modelo": "Samsung Galaxy S26 Ultra (256GB / 12GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Alta Flagship",
        "especificaciones": "Equipo Nuevo Sellado. Última generación S26 Ultra de 256GB / 12GB RAM con S-Pen y zoom telescópico.",
        "precio_cop": 3340000,
        "stock": 4,
        "colores_disponibles": "Titanio Negro, Titanio Gris",
        "garantia_meses": 12,
        "destacado_para": "Samsung S26 Ultra de última generación en 256GB ($3.340.000)"
    },
    {
        "sku": "NEW-APL-MACNEO-256",
        "marca": "Apple",
        "modelo": "MacBook Neo 256GB (Nuevo)",
        "categoria": "Computador / Tablet",
        "gama": "Ecosistema Apple",
        "especificaciones": "Portátil Apple MacBook Neo Nuevo con unidad SSD de 256GB, pantalla Retina de alta resolución y batería para todo el día.",
        "precio_cop": 2480000,
        "stock": 3,
        "colores_disponibles": "Gris Espacial, Plata, Medianoche",
        "garantia_meses": 12,
        "destacado_para": "Portátil MacBook Nuevo para universidad, diseño y trabajo ($2.480.000)"
    },
    {
        "sku": "NEW-APL-IPADA16-128",
        "marca": "Apple",
        "modelo": "iPad A16 128GB WiFi (Nuevo)",
        "categoria": "Computador / Tablet",
        "gama": "Ecosistema Apple",
        "especificaciones": "Tablet Apple iPad con potente Chip A16, 128GB de almacenamiento, conectividad WiFi y pantalla Liquid Retina.",
        "precio_cop": 1550000,
        "stock": 5,
        "colores_disponibles": "Azul, Plata, Rosa, Amarillo",
        "garantia_meses": 12,
        "destacado_para": "Estudio, notas digitales y entretenimiento Apple ($1.550.000)"
    },

    # -----------------------------------------------------------------
    # TABLA 3: PRECIOS OPEN BOX — SEMINUEVOS DESDE IPHONE 13 EN ADELANTE (20 Referencias)
    # (Se omiten iPhone 11 y 12; incluye Combos de Obsequio oficiales según referencia)
    # -----------------------------------------------------------------
    {
        "sku": "OBX-APL-IP13-128",
        "marca": "Apple",
        "modelo": "iPhone 13 de 128GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box garantizado (valor menor frente al nuevo de $1.840.000). Chip A15 Bionic, 128GB y Modo Cine. 🎁 OBSEQUIO INCLUIDO: Estuche y Vidrio templado.",
        "precio_cop": 1150000,
        "stock": 6,
        "colores_disponibles": "Medianoche, Blanco Estelar, Azul, Rosa",
        "garantia_meses": 6,
        "destacado_para": "iPhone 13 128GB Seminuevo ($1.150.000) + Obsequio: Estuche y Vidrio"
    },
    {
        "sku": "OBX-APL-IP13P-128",
        "marca": "Apple",
        "modelo": "iPhone 13 Pro de 128GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box. Pantalla ProMotion de 120Hz, triple cámara con modo macro y teleobjetivo, 128GB.",
        "precio_cop": 1590000,
        "stock": 4,
        "colores_disponibles": "Azul Sierra, Grafito, Plata, Verde Alpino",
        "garantia_meses": 6,
        "destacado_para": "Pantalla 120Hz y triple cámara Pro en $1.590.000 (Seminuevo)"
    },
    {
        "sku": "OBX-APL-IP13P-256",
        "marca": "Apple",
        "modelo": "iPhone 13 Pro de 256GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box con doble de capacidad (256GB), pantalla 120Hz ProMotion y triple cámara profesional.",
        "precio_cop": 1680000,
        "stock": 4,
        "colores_disponibles": "Azul Sierra, Grafito, Plata",
        "garantia_meses": 6,
        "destacado_para": "iPhone 13 Pro con 256GB por solo $1.680.000 (Seminuevo)"
    },
    {
        "sku": "OBX-APL-IP13PM-128",
        "marca": "Apple",
        "modelo": "iPhone 13 Pro Max 128GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box. Pantalla grande de 6.7\" 120Hz, batería de larguísima duración y triple cámara Pro. 🎁 OBSEQUIO INCLUIDO (a elegir): COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods).",
        "precio_cop": 1890000,
        "stock": 4,
        "colores_disponibles": "Azul Sierra, Grafito, Plata",
        "garantia_meses": 6,
        "destacado_para": "iPhone 13 Pro Max 128GB ($1.890.000) + Obsequio: Combo 2 (Cubo, Cable, Estuche, Vidrio) o Combo 3 (AirPods)"
    },
    {
        "sku": "OBX-APL-IP13PM-256",
        "marca": "Apple",
        "modelo": "iPhone 13 Pro Max 256GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box de 256GB. Pantalla 6.7\" ProMotion 120Hz y sistema de cámaras Pro.",
        "precio_cop": 1990000,
        "stock": 3,
        "colores_disponibles": "Grafito, Azul Sierra, Oro",
        "garantia_meses": 6,
        "destacado_para": "iPhone 13 Pro Max de 256GB por debajo de 2 millones ($1.990.000)"
    },
    {
        "sku": "OBX-APL-IP14-128",
        "marca": "Apple",
        "modelo": "iPhone 14 de 128GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box garantizado (frente a $2.100.000 nuevo). 128GB, Modo Acción y excelente cámara nocturna.",
        "precio_cop": 1300000,
        "stock": 6,
        "colores_disponibles": "Medianoche, Morado, Blanco Estelar, Azul",
        "garantia_meses": 6,
        "destacado_para": "iPhone 14 128GB Seminuevo en $1.300.000 (ahorras $800.000 frente al nuevo)"
    },
    {
        "sku": "OBX-APL-IP14P-128",
        "marca": "Apple",
        "modelo": "iPhone 14 Pro 128GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box. Isla Dinámica (Dynamic Island), cámara principal de 48MP, pantalla Always-On 120Hz y Chip A16. 🎁 OBSEQUIO INCLUIDO (a elegir): COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods).",
        "precio_cop": 1820000,
        "stock": 4,
        "colores_disponibles": "Morado Oscuro, Negro Espacial, Plata",
        "garantia_meses": 6,
        "destacado_para": "iPhone 14 Pro 128GB ($1.820.000) + Obsequio: Combo 2 (Cubo, Cable, Estuche, Vidrio) o Combo 3 (AirPods)"
    },
    {
        "sku": "OBX-APL-IP14P-256",
        "marca": "Apple",
        "modelo": "iPhone 14 Pro 256GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box con 256GB de memoria, Isla Dinámica, triple cámara de 48MP y pantalla 120Hz.",
        "precio_cop": 1900000,
        "stock": 4,
        "colores_disponibles": "Morado Oscuro, Negro Espacial, Plata, Oro",
        "garantia_meses": 6,
        "destacado_para": "iPhone 14 Pro de 256GB por $1.900.000 (Seminuevo)"
    },
    {
        "sku": "OBX-APL-IP14PM-128",
        "marca": "Apple",
        "modelo": "iPhone 14 Pro Max 128GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box. Pantalla ProMotion de 6.7 pulgadas con Isla Dinámica, cámara de 48MP y gran autonomía. 🎁 OBSEQUIO INCLUIDO (a elegir): COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods).",
        "precio_cop": 1980000,
        "stock": 4,
        "colores_disponibles": "Morado Oscuro, Negro Espacial, Plata",
        "garantia_meses": 6,
        "destacado_para": "iPhone 14 Pro Max 128GB ($1.980.000) + Obsequio: Combo 2 (Cubo, Cable, Estuche, Vidrio) o Combo 3 (AirPods)"
    },
    {
        "sku": "OBX-APL-IP14PM-256",
        "marca": "Apple",
        "modelo": "iPhone 14 Pro Max 256GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box con 256GB de almacenamiento, pantalla 6.7\" 120Hz, Isla Dinámica y triple cámara de 48MP.",
        "precio_cop": 2350000,
        "stock": 3,
        "colores_disponibles": "Morado Oscuro, Negro Espacial, Plata",
        "garantia_meses": 6,
        "destacado_para": "iPhone 14 Pro Max de 256GB en estado impecable ($2.350.000)"
    },
    {
        "sku": "OBX-APL-IP15-128",
        "marca": "Apple",
        "modelo": "iPhone 15 de 128GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box (frente a $2.200.000 nuevo). Isla Dinámica, puerto USB-C, cámara de 48MP y Chip A16 Bionic. 🎁 OBSEQUIO INCLUIDO (a elegir): COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods).",
        "precio_cop": 1790000,
        "stock": 5,
        "colores_disponibles": "Negro, Azul, Rosa, Verde",
        "garantia_meses": 6,
        "destacado_para": "iPhone 15 128GB Seminuevo ($1.790.000) + Obsequio: Combo 2 (Cubo, Cable, Estuche, Vidrio) o Combo 3 (AirPods)"
    },
    {
        "sku": "OBX-APL-IP15P-128",
        "marca": "Apple",
        "modelo": "iPhone 15 Pro de 128GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box. Diseño en Titanio grado aeroespacial, Botón de Acción, Chip A17 Pro, USB-C y triple cámara Pro. 🎁 OBSEQUIO INCLUIDO (a elegir): COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods).",
        "precio_cop": 2050000,
        "stock": 4,
        "colores_disponibles": "Titanio Natural, Titanio Azul, Titanio Negro, Titanio Blanco",
        "garantia_meses": 6,
        "destacado_para": "iPhone 15 Pro 128GB ($2.050.000) + Obsequio: Combo 2 (Cubo, Cable, Estuche, Vidrio) o Combo 3 (AirPods)"
    },
    {
        "sku": "OBX-APL-IP15P-256",
        "marca": "Apple",
        "modelo": "iPhone 15 Pro de 256GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box con 256GB, chasis de Titanio, Chip A17 Pro y grabación espacial.",
        "precio_cop": 2200000,
        "stock": 4,
        "colores_disponibles": "Titanio Natural, Titanio Negro, Titanio Azul",
        "garantia_meses": 6,
        "destacado_para": "iPhone 15 Pro de 256GB al mismo precio que el 15 normal nuevo ($2.200.000)"
    },
    {
        "sku": "OBX-APL-IP15PM-256",
        "marca": "Apple",
        "modelo": "iPhone 15 Pro Max de 256GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box de 256GB. Chasis en Titanio, teleobjetivo zoom óptico 5x, pantalla 6.7\" 120Hz y Chip A17 Pro. 🎁 OBSEQUIO INCLUIDO (a elegir): COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods).",
        "precio_cop": 2530000,
        "stock": 4,
        "colores_disponibles": "Titanio Natural, Titanio Negro, Titanio Blanco",
        "garantia_meses": 6,
        "destacado_para": "iPhone 15 Pro Max 256GB ($2.530.000) + Obsequio: Combo 2 (Cubo, Cable, Estuche, Vidrio) o Combo 3 (AirPods)"
    },
    {
        "sku": "OBX-APL-IP16-128",
        "marca": "Apple",
        "modelo": "iPhone 16 128GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box (frente a $2.600.000 nuevo). Chip A18, Control de Cámara y Botón de Acción. 🎁 OBSEQUIO INCLUIDO: COMBO 4 (Cubo, Cable, Estuche, Vidrio y AirPods).",
        "precio_cop": 2180000,
        "stock": 4,
        "colores_disponibles": "Negro, Azul Ultramar, Rosa, Blanco",
        "garantia_meses": 6,
        "destacado_para": "iPhone 16 128GB Seminuevo ($2.180.000) + Obsequio: Combo 4 (Cubo, Cable, Estuche, Vidrio y AirPods)"
    },
    {
        "sku": "OBX-APL-IP16P-128",
        "marca": "Apple",
        "modelo": "iPhone 16 Pro 128GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box. Pantalla de 6.3\" 120Hz, Chip A18 Pro, Control de Cámara, zoom 5x y grabación 4K a 120 fps. 🎁 OBSEQUIO INCLUIDO: COMBO 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche).",
        "precio_cop": 2580000,
        "stock": 3,
        "colores_disponibles": "Titanio del Desierto, Titanio Natural, Titanio Negro",
        "garantia_meses": 6,
        "destacado_para": "iPhone 16 Pro 128GB ($2.580.000) + Obsequio: Combo 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche)"
    },
    {
        "sku": "OBX-APL-IP16P-256",
        "marca": "Apple",
        "modelo": "iPhone 16 Pro 256GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box con 256GB de memoria, Titanio, Chip A18 Pro y triple cámara con ultra gran angular de 48MP. 🎁 OBSEQUIO INCLUIDO: COMBO 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche).",
        "precio_cop": 2650000,
        "stock": 3,
        "colores_disponibles": "Titanio del Desierto, Titanio Natural, Titanio Negro",
        "garantia_meses": 6,
        "destacado_para": "iPhone 16 Pro 256GB ($2.650.000) + Obsequio: Combo 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche)"
    },
    {
        "sku": "OBX-APL-IP16PM-256",
        "marca": "Apple",
        "modelo": "iPhone 16 Pro Max 256GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box. Pantalla inmersiva de 6.9 pulgadas, Chip A18 Pro, batería récord y cámaras profesionales. 🎁 OBSEQUIO INCLUIDO: COMBO 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche).",
        "precio_cop": 2950000,
        "stock": 3,
        "colores_disponibles": "Titanio del Desierto, Titanio Natural, Titanio Negro",
        "garantia_meses": 6,
        "destacado_para": "iPhone 16 Pro Max 256GB ($2.950.000) + Obsequio: Combo 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche)"
    },
    {
        "sku": "OBX-APL-IP17P-256",
        "marca": "Apple",
        "modelo": "iPhone 17 Pro 256GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box (frente a $4.120.000 nuevo). 256GB de memoria, triple cámara Pro y estado estético 10/10.",
        "precio_cop": 3520000,
        "stock": 2,
        "colores_disponibles": "Titanio Natural, Titanio Negro",
        "garantia_meses": 6,
        "destacado_para": "iPhone 17 Pro 256GB Seminuevo en $3.520.000 (ahorras $600.000 frente al nuevo)"
    },
    {
        "sku": "OBX-APL-IP17PM-256",
        "marca": "Apple",
        "modelo": "iPhone 17 Pro Max 256GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box (frente a $4.250.000/$4.300.000 nuevo). 256GB, pantalla 6.9\" y máxima potencia Pro Max.",
        "precio_cop": 4000000,
        "stock": 2,
        "colores_disponibles": "Silver, Azul, Negro",
        "garantia_meses": 6,
        "destacado_para": "iPhone 17 Pro Max 256GB Seminuevo exacto en $4.000.000"
    },
    {
        "sku": "OBX-APL-IP17-256",
        "marca": "Apple",
        "modelo": "iPhone 17 256GB (Open Box - Seminuevo)",
        "categoria": "Open Box (Seminuevo)",
        "gama": "Open Box Seminuevo",
        "especificaciones": "Equipo Seminuevo Open Box de 256GB disponible para financiación por Addi/Sistecrédito ($3.250.000) y Banco de Bogotá ($3.000.000).",
        "precio_cop": 3000000,
        "stock": 2,
        "colores_disponibles": "Negro, Plata, Azul",
        "garantia_meses": 6,
        "destacado_para": "iPhone 17 256GB Open Box disponible en plataformas de crédito"
    },

    # -----------------------------------------------------------------
    # TABLA 4: REFERENCIAS ADICIONALES DE PLATAFORMAS (editada.xlsx)
    # -----------------------------------------------------------------
    {
        "sku": "AND-INF-H60P-256",
        "marca": "Infinix",
        "modelo": "Infinix Hot 60 Pro (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media",
        "especificaciones": "Equipo Nuevo Sellado con 256GB y 8GB RAM. Disponible en Addi/Sistecrédito ($1.060.000), Banco de Bogotá ($1.030.000), Krediya ($1.089.000, Inicial 30%: $112.700) y Credimóvil ($945.000, Inicial 10%: $94.500).",
        "precio_cop": 945000,
        "stock": 5,
        "colores_disponibles": "Negro, Verde, Azul",
        "garantia_meses": 12,
        "destacado_para": "Excelente opción a crédito en Krediya y Credimóvil"
    },
    {
        "sku": "AND-INF-H60I-256",
        "marca": "Infinix",
        "modelo": "Infinix Hot 60i (256GB / 4GB-8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Entrada-Media",
        "especificaciones": "Equipo Nuevo Sellado de 256GB. Disponible en Krediya ($1.045.000 con inicial 30% de $58.500) y Credimóvil ($820.000 con inicial 10% de $82.000 o 15% de $123.000).",
        "precio_cop": 820000,
        "stock": 5,
        "colores_disponibles": "Negro, Azul, Plata",
        "garantia_meses": 12,
        "destacado_para": "Inicial muy baja en Krediya ($58.500) y Credimóvil ($82.000)"
    },
    {
        "sku": "AND-INF-SM10-256",
        "marca": "Infinix",
        "modelo": "Infinix Smart 10 (256GB / 4+4GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Entrada",
        "especificaciones": "Equipo Nuevo Sellado de 256GB. Disponible en Addi/Sistecrédito ($860.000), Banco de Bogotá ($810.000), Krediya ($850.000, Inicial 30%: $85.000) y Credimóvil ($730.000, Inicial 10%: $73.000).",
        "precio_cop": 730000,
        "stock": 6,
        "colores_disponibles": "Negro, Verde, Azul",
        "garantia_meses": 12,
        "destacado_para": "256GB económico en todas las plataformas de crédito"
    },
    {
        "sku": "AND-SAM-A16-128",
        "marca": "Samsung",
        "modelo": "Samsung Galaxy A16 (128GB / 6GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media",
        "especificaciones": "Equipo Nuevo Sellado. Pantalla Super AMOLED 90Hz, 128GB y 6GB RAM. Disponible en Krediya ($1.050.000 con inicial 30% de solo $40.000).",
        "precio_cop": 1050000,
        "stock": 4,
        "colores_disponibles": "Negro, Azul, Gris",
        "garantia_meses": 12,
        "destacado_para": "Inicial mínima en Krediya de solo $40.000"
    },
    {
        "sku": "AND-SAM-A26-256",
        "marca": "Samsung",
        "modelo": "Samsung Galaxy A26 5G (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media",
        "especificaciones": "Equipo Nuevo Sellado con conectividad 5G, 256GB y 8GB RAM. Disponible en Krediya ($1.550.000 con inicial 30% de $85.000).",
        "precio_cop": 1550000,
        "stock": 4,
        "colores_disponibles": "Negro, Azul, Blanco",
        "garantia_meses": 12,
        "destacado_para": "Samsung 5G de 256GB con inicial en Krediya de $85.000"
    },
    {
        "sku": "AND-SAM-A36-256",
        "marca": "Samsung",
        "modelo": "Samsung Galaxy A36 5G (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media-Alta",
        "especificaciones": "Equipo Nuevo Sellado 5G de 256GB y 8GB RAM. Disponible en Addi/Sistecrédito ($1.650.000), Banco de Bogotá ($1.550.000) y Krediya ($1.800.000 con inicial 30% de $167.000).",
        "precio_cop": 1550000,
        "stock": 4,
        "colores_disponibles": "Negro, Azul, Lila, Blanco",
        "garantia_meses": 12,
        "destacado_para": "Samsung A36 5G financiado en Addi, Sistecrédito, Bogotá y Krediya"
    },
    {
        "sku": "AND-SAM-A56-256",
        "marca": "Samsung",
        "modelo": "Samsung Galaxy A56 5G (256GB / 8GB-12GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media-Alta",
        "especificaciones": "Equipo Nuevo Sellado 5G de 256GB. Disponible en Addi/Sistecrédito ($2.070.000), Banco de Bogotá ($1.920.000) y Krediya ($2.300.000 con inicial 30% de $180.000).",
        "precio_cop": 1920000,
        "stock": 4,
        "colores_disponibles": "Negro, Azul, Plata",
        "garantia_meses": 12,
        "destacado_para": "Samsung A56 5G en plataformas de crédito"
    },
    {
        "sku": "AND-OPP-A5-256",
        "marca": "Oppo",
        "modelo": "Oppo A5 (256GB / 4GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media",
        "especificaciones": "Equipo Nuevo Sellado con 256GB de memoria. Disponible en Addi/Sistecrédito ($1.030.000), Banco de Bogotá ($890.000) y Krediya ($1.094.900 con inicial 30% de $113.570).",
        "precio_cop": 890000,
        "stock": 5,
        "colores_disponibles": "Negro, Azul",
        "garantia_meses": 12,
        "destacado_para": "Oppo de 256GB disponible en Addi, Bogotá y Krediya"
    },
    {
        "sku": "AND-OPP-A60-256",
        "marca": "Oppo",
        "modelo": "Oppo A60 (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media",
        "especificaciones": "Equipo Nuevo Sellado con 256GB y 8GB RAM, resistencia militar a golpes. Disponible en Krediya ($1.265.000 con inicial 30% de solo $60.000).",
        "precio_cop": 1265000,
        "stock": 4,
        "colores_disponibles": "Azul, Morado",
        "garantia_meses": 12,
        "destacado_para": "Oppo A60 256/8 en Krediya con inicial de solo $60.000"
    },
    {
        "sku": "AND-POC-X8P-512",
        "marca": "Xiaomi POCO",
        "modelo": "POCO X8 Pro (512GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media-Alta Gaming",
        "especificaciones": "Equipo Nuevo Sellado con 512GB de memoria y 8GB RAM para alto rendimiento. Disponible en Addi/Sistecrédito ($1.800.000) y Banco de Bogotá ($1.700.000).",
        "precio_cop": 1700000,
        "stock": 4,
        "colores_disponibles": "Negro, Amarillo, Gris",
        "garantia_meses": 12,
        "destacado_para": "512GB de almacenamiento para gaming por Addi, Sistecrédito y Bogotá"
    },
    {
        "sku": "AND-RED-14C-128",
        "marca": "Xiaomi Redmi",
        "modelo": "Xiaomi Redmi 14C (128GB / 4GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Entrada",
        "especificaciones": "Equipo Nuevo Sellado con pantalla de 6.88\" 120Hz, 128GB y 4GB RAM. Disponible en Krediya ($850.000 con inicial 30% de $170.000).",
        "precio_cop": 850000,
        "stock": 5,
        "colores_disponibles": "Negro, Azul, Verde",
        "garantia_meses": 12,
        "destacado_para": "Redmi 14C financiado por Krediya"
    },
    {
        "sku": "AND-RED-N14-256",
        "marca": "Xiaomi Redmi",
        "modelo": "Xiaomi Redmi Note 14 4G (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media",
        "especificaciones": "Equipo Nuevo Sellado con 256GB y 8GB RAM. Disponible en Addi/Sistecrédito ($890.000), Banco de Bogotá ($1.040.000) y Krediya ($1.100.000 con inicial 30% de $150.000).",
        "precio_cop": 890000,
        "stock": 5,
        "colores_disponibles": "Negro, Azul, Verde",
        "garantia_meses": 12,
        "destacado_para": "Redmi Note 14 256/8 en Addi/Sistecrédito por $890.000"
    },
    {
        "sku": "AND-RED-N14P-256",
        "marca": "Xiaomi Redmi",
        "modelo": "Xiaomi Redmi Note 14 Pro (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media-Alta",
        "especificaciones": "Equipo Nuevo Sellado con cámara profesional y 256GB. Disponible en Krediya ($1.600.000 con inicial 30% de $190.000).",
        "precio_cop": 1600000,
        "stock": 4,
        "colores_disponibles": "Negro, Morado, Azul",
        "garantia_meses": 12,
        "destacado_para": "Redmi Note 14 Pro 256GB financiado por Krediya"
    },
    {
        "sku": "AND-RLM-C75-256",
        "marca": "Realme",
        "modelo": "Realme C75 (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media",
        "especificaciones": "Equipo Nuevo Sellado ultra resistente con 256GB y 8GB RAM. Disponible en Krediya ($1.150.000 con inicial 30% de $115.000).",
        "precio_cop": 1150000,
        "stock": 4,
        "colores_disponibles": "Negro, Dorado",
        "garantia_meses": 12,
        "destacado_para": "Realme C75 256/8 en Krediya con inicial de $115.000"
    },
    {
        "sku": "AND-RLM-N60X-128",
        "marca": "Realme",
        "modelo": "Realme Note 60X (128GB / 4GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Entrada",
        "especificaciones": "Equipo Nuevo Sellado con chasis ArmorShell, 128GB y 4GB RAM. Disponible en Krediya ($820.000 con inicial 30% de solo $46.000).",
        "precio_cop": 820000,
        "stock": 5,
        "colores_disponibles": "Negro, Verde",
        "garantia_meses": 12,
        "destacado_para": "Inicial súper baja en Krediya de solo $46.000"
    },
    {
        "sku": "AND-RLM-N70-256",
        "marca": "Realme",
        "modelo": "Realme Note 70 (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media",
        "especificaciones": "Equipo Nuevo Sellado con 256GB y 8GB RAM. Disponible en Krediya ($935.000 con inicial 30% de $110.000).",
        "precio_cop": 935000,
        "stock": 5,
        "colores_disponibles": "Negro, Azul",
        "garantia_meses": 12,
        "destacado_para": "Realme Note 70 256/8 financiado por Krediya"
    },
    {
        "sku": "AND-TEC-POP5G-16",
        "marca": "Tecno",
        "modelo": "Tecno Pop 5 Go (16GB / 1GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Básica",
        "especificaciones": "Equipo básico Nuevo Sellado. Disponible en Addi/Sistecrédito ($200.000) y Banco de Bogotá ($400.000).",
        "precio_cop": 200000,
        "stock": 4,
        "colores_disponibles": "Negro, Azul",
        "garantia_meses": 12,
        "destacado_para": "El desembolso más bajo en Addi/Sistecrédito ($200.000)"
    },
    {
        "sku": "AND-TEC-SP40PP-256",
        "marca": "Tecno",
        "modelo": "Tecno Spark 40 Pro Plus (256GB / 8GB RAM) Nuevo",
        "categoria": "Celular Nuevo",
        "gama": "Gama Media",
        "especificaciones": "Equipo Nuevo Sellado con pantalla curva AMOLED, 256GB y 8GB RAM. Disponible en Krediya ($1.300.000, Inicial 30%: $170.000) y Credimóvil ($1.080.000, Inicial 10%: $108.000, Inicial 15%: $162.000).",
        "precio_cop": 1080000,
        "stock": 5,
        "colores_disponibles": "Negro, Verde, Dorado",
        "garantia_meses": 12,
        "destacado_para": "Tecno Spark 40 Pro+ en Krediya y Credimóvil"
    }
]


# =====================================================================
# Inicialización Aislada de Base de Datos y Sincronización del Catálogo Real
# =====================================================================
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def _ensure_database_exists():
    admin_engine = create_async_engine(DATABASE_URL_ADMIN, isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as conn:
            res = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": DB_NAME}
            )
            exists = res.scalar() is not None
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{DB_NAME}"'))
                print(f"[OK] Base de datos aislada '{DB_NAME}' creada exitosamente.")
    except Exception as e:
        print(f"[INFO] Verificación de BD '{DB_NAME}': {e}")
    finally:
        await admin_engine.dispose()


async def init_db():
    """
    Inicializa `celred_db` y sincroniza las 88 referencias oficiales (Contado + Plataformas editada.xlsx).
    """
    await _ensure_database_exists()

    async with async_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)

    try:
        from platform_prices import get_platform_info, _fmt_cop  # type: ignore
    except ImportError:
        from backend.platform_prices import get_platform_info, _fmt_cop  # type: ignore

    # Sincronizar el catálogo oficial de 88 referencias reales de Cel Red
    async with AsyncSessionLocal() as session:
        count_res = await session.execute(select(func.count(Producto.id)))
        total_productos = count_res.scalar() or 0
        if total_productos != len(CATALOGO_INICIAL_CELRED):
            await session.execute(delete(Producto))
            for item in CATALOGO_INICIAL_CELRED:
                item_copy = dict(item)
                pinfo = get_platform_info(item_copy["sku"])
                if pinfo:
                    partes_plat = []
                    if pinfo.get("addi_sistecredito"):
                        partes_plat.append(f"Addi/Sistecrédito: {_fmt_cop(pinfo['addi_sistecredito'])}")
                    if pinfo.get("banco_bogota"):
                        partes_plat.append(f"Banco de Bogotá: {_fmt_cop(pinfo['banco_bogota'])}")
                    if pinfo.get("krediya"):
                        k = pinfo["krediya"]
                        partes_plat.append(f"Krediya: {_fmt_cop(k['plataforma'])} (Inicial 30%: {_fmt_cop(k['inicial_30'])})")
                    if pinfo.get("credimovil"):
                        c = pinfo["credimovil"]
                        partes_plat.append(f"Credimóvil: {_fmt_cop(c['plataforma'])} (Inicial 10%: {_fmt_cop(c['inicial_10'])} / 15%: {_fmt_cop(c['inicial_15'])})")
                    if pinfo.get("renting"):
                        r = pinfo["renting"]
                        partes_plat.append(f"Renting iPhone: {_fmt_cop(r['plataforma'])} (Inicial 20%: {_fmt_cop(r['inicial_20'])} / 30%: {_fmt_cop(r['inicial_30'])})")
                    if partes_plat and "Addi/Sistecrédito:" not in item_copy["especificaciones"]:
                        item_copy["especificaciones"] = item_copy["especificaciones"] + " | 💳 Plataformas: " + " · ".join(partes_plat) + "."
                session.add(Producto(**item_copy))
            await session.commit()
            print(f"[OK] Catálogo oficial de Cel Red actualizado con éxito ({len(CATALOGO_INICIAL_CELRED)} referencias reales en BD)")

    print(f"[OK] Base de datos '{DB_NAME}' y tablas de Cel Red listas (pgvector activo)")
