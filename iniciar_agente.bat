@echo off
title CEL RED // Asesor Comercial y Sistema de Ventas IA
color 0B

echo.
echo  ================================================================
echo    CEL RED // ASESOR COMERCIAL Y SISTEMA DE VENTAS IA
echo    Catálogo Oficial Android Nuevos, iPhone Nuevos y Open Box
echo    Base de Datos PostgreSQL (celred_db) + pgvector + SysCafe
echo  ================================================================
echo.

if exist "%~dp0agente_emergencias_9" (
    cd /d "%~dp0agente_emergencias_9"
) else (
    cd /d "%~dp0"
)

echo [*] Directorio de trabajo: %CD%
echo.

echo [*] Paso 1: Verificando base de datos PostgreSQL + pgvector (celred_db)...
docker compose up -d postgres_vector 2>nul
if %errorlevel% equ 0 (
    echo [OK] Contenedor PostgreSQL + pgvector activo en puerto 5432.
) else (
    echo [!] AVISO: Docker no responde. Abra Docker Desktop e intente de nuevo.
)
echo.

echo [*] Paso 2: Verificando entorno virtual de Python...
if not exist ".venv\Scripts\python.exe" (
    echo [*] Creando entorno virtual .venv e instalando dependencias...
    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
) else (
    echo [OK] Entorno virtual .venv detectado correctamente.
)
echo.

echo [*] Paso 3: Limpiando archivos TTS de sesiones anteriores...
if exist "temp_audio" (
    del /q "temp_audio\*.mp3" 2>nul
    del /q "temp_audio\*.wav" 2>nul
    echo [OK] Directorio temp_audio limpiado.
) else (
    mkdir temp_audio
)
echo.

echo [*] Paso 4: Abriendo consola comercial de Cel Red en el navegador en 3 segundos...
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:8000"

echo [*] Paso 5: Iniciando servidor FastAPI en http://localhost:8000 ...
echo.
echo  ================================================================
echo    CONSOLA CEL RED : http://localhost:8000
echo    API DOCS        : http://localhost:8000/docs
echo    PARA DETENER    : Presione Ctrl + C en esta ventana
echo  ================================================================
echo.

.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

echo.
echo [*] Sistema CEL RED detenido.
pause
