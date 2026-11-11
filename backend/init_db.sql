-- Script de inicialización de Base de Datos para CEL RED (Asesor Comercial y Ventas IA)
-- Habilita la extensión vectorial pgvector en PostgreSQL 16
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verificación de versión y extensiones activas
SELECT extname, extversion FROM pg_extension;

