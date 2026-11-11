"""
Script de Verificación Integral del Entorno de Ejecución
CEL RED — Asesor Comercial y Sistema de Ventas IA
Tienda de Celulares y Accesorios (PostgreSQL `celred_db` + pgvector)
"""

import sys
import os
import socket
import importlib.util
import urllib.request
import json


def print_step(title):
    print("\n" + "=" * 60)
    print(f"[*] {title}")
    print("=" * 60)


def check_python():
    print_step("1. Verificando Versión de Python")
    version = sys.version.split()[0]
    print(f"[+] Python detectado: {version}")
    if sys.version_info < (3, 10):
        print("[!] ADVERTENCIA: Se recomienda Python 3.10 o superior.")
    else:
        print("[OK] Versión de Python compatible.")


def check_python_dependencies():
    print_step("2. Verificando Dependencias de requirements.txt")
    packages = [
        ("fastapi", "FastAPI (Framework Web)"),
        ("uvicorn", "Uvicorn (Servidor ASGI)"),
        ("sqlalchemy", "SQLAlchemy (ORM)"),
        ("asyncpg", "asyncpg (Driver asíncrono PostgreSQL)"),
        ("pgvector", "pgvector (Soporte vectorial PostgreSQL)"),
        ("pydantic", "Pydantic (Validación de esquemas)"),
        ("httpx", "HTTPX (Cliente HTTP asíncrono)"),
        ("pypdf", "pypdf (Lector de documentos PDF)"),
        ("faster_whisper", "faster-whisper (STT Speech-to-Text)"),
        ("edge_tts", "edge-tts (TTS Voz neuronal)"),
        ("pyttsx3", "pyttsx3 (TTS Voz offline local)"),
    ]

    missing = []
    for pkg_name, desc in packages:
        spec = importlib.util.find_spec(pkg_name)
        if spec is not None:
            print(f"  [OK] {desc}")
        else:
            print(f"  [!] Falta: {desc} ({pkg_name})")
            missing.append(pkg_name)

    if missing:
        print("\n[*] Para instalar las dependencias faltantes ejecute:")
        print("    pip install -r requirements.txt")
    else:
        print("\n[OK] Todas las dependencias principales están instaladas.")


def check_postgres_and_vector():
    print_step("3. Verificando Conectividad con PostgreSQL `celred_db` (Puerto 5432)")
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.5)
    result = sock.connect_ex((host, port))
    sock.close()

    if result == 0:
        print(f"[OK] Puerto {port} en '{host}' está ABIERTO y respondiendo.")
        return True
    else:
        print(f"[!] PostgreSQL no responde en {host}:{port}.")
        print("[*] Acción requerida: Inicie el contenedor Docker con:")
        print("    docker compose up -d postgres_vector")
        return False


def check_ollama():
    print_step("4. Verificando Instancia de Ollama (LLM y Embeddings gemma2)")
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        req = urllib.request.Request(f"{ollama_url}/api/tags", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=2.0) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                models = [m.get("name") for m in data.get("models", [])]
                print(f"[OK] Ollama activo en {ollama_url}.")
                print(f"[*] Modelos locales disponibles: {', '.join(models) if models else 'Ninguno descargado aún'}")
                return True
    except Exception as e:
        print(f"[i] Ollama no detectado en {ollama_url} ({e}).")
        print("[i] El sistema utilizará el motor semántico determinista de contingencia comercial.")
        return False


def main():
    print("=" * 60)
    print("  VERIFICADOR DE ENTORNO - CEL RED ASESOR COMERCIAL IA")
    print("=" * 60)

    check_python()
    check_python_dependencies()
    check_postgres_and_vector()
    check_ollama()

    print("\n" + "=" * 60)
    print("[*] GUÍA RÁPIDA PARA INICIAR CEL RED:")
    print("  1. Levantar DB pgvector:  docker compose up -d postgres_vector")
    print("  2. Iniciar Servidor:      .venv\\Scripts\\python.exe -m uvicorn backend.main:app --port 8000")
    print("  3. Abrir en Navegador:    http://localhost:8000")
    print("=" * 60)


if __name__ == "__main__":
    main()
