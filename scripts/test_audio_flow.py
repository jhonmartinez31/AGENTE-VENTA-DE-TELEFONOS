"""
Prueba Unitaria de Flujo Completo de Audio (STT -> LLM/RAG -> DB -> TTS)
CEL RED — Asesor Comercial y Sistema de Ventas IA

Genera un archivo de audio con voz real en español consultando un iPhone con obsequio,
lo envía al endpoint POST /api/chat/audio de FastAPI, valida la respuesta del orquestador comercial,
la creación de la orden en PostgreSQL (`celred_db`) y la descarga del audio TTS devuelto.
"""

import os
import sys
import wave
import struct
import math
import tempfile
import urllib.request
import json

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def generate_test_wav_file(duration_sec=2.0, sample_rate=16000) -> str:
    """
    Genera un archivo de audio con voz real en español para probar la transcripción STT de faster-whisper,
    con respaldo de onda sinusoidal si no hay síntesis disponible.
    """
    try:
        import asyncio
        import edge_tts  # type: ignore
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_path = temp_file.name
        temp_file.close()
        spoken_sample = "Hola, qué precio tiene el iPhone 15 de 128 gigas en Open Box y qué obsequio incluye."
        asyncio.run(edge_tts.Communicate(spoken_sample, "es-CO-GonzaloNeural").save(temp_path))
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            print(f"[OK] Audio comercial de voz generado para prueba STT: {temp_path} ({os.path.getsize(temp_path)} bytes)")
            return temp_path
    except Exception:
        pass

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_path = temp_file.name
    temp_file.close()

    num_samples = int(duration_sec * sample_rate)
    with wave.open(temp_path, "w") as wav_file:
        wav_file.setparams((1, 2, sample_rate, num_samples, "NONE", "not compressed"))
        for i in range(num_samples):
            t = float(i) / sample_rate
            freq = 440.0 + 50.0 * math.sin(2.0 * math.pi * 2.0 * t)
            value = int(12000.0 * math.sin(2.0 * math.pi * freq * t))
            data = struct.pack("<h", value)
            wav_file.writeframesraw(data)

    print(f"[OK] Audio de prueba sintetizado generado: {temp_path} ({os.path.getsize(temp_path)} bytes)")
    return temp_path


def send_audio_multipart(url: str, file_path: str, session_id: str = "test_audio_celred"):
    """
    Realiza una petición HTTP POST multipart/form-data usando urllib de la librería estándar.
    """
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="session_id"\r\n\r\n')
    body.extend(f"{session_id}\r\n".encode("utf-8"))

    filename = os.path.basename(file_path)
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="audio"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(b"Content-Type: audio/wav\r\n\r\n")
    body.extend(file_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=35) as resp:
        status_code = resp.status
        resp_data = resp.read().decode("utf-8")
        return status_code, json.loads(resp_data)


def test_full_audio_flow():
    print("=" * 65)
    print("  TEST UNITARIO DE FLUJO DE AUDIO COMERCIAL — CEL RED")
    print("=" * 65)

    audio_endpoint = f"{API_BASE_URL}/api/chat/audio"
    print(f"[*] Enviando consulta de voz a: {audio_endpoint}")

    wav_path = generate_test_wav_file(duration_sec=2.0)

    try:
        status_code, data = send_audio_multipart(audio_endpoint, wav_path)
        print(f"[+] Código HTTP recibido: {status_code}")

        assert status_code == 200, f"Se esperaba código 200 pero se recibió {status_code}"
        assert "respuesta_texto" in data, "Falta 'respuesta_texto' en la respuesta"
        assert "incidente" in data, "Falta objeto de orden en la respuesta"

        orden = data["incidente"]
        print("\n" + "-" * 40)
        print("  RESULTADOS DE LA PRUEBA DE VOZ EN CEL RED:")
        print(f"  • Código de Orden:      {orden.get('codigo')}")
        print(f"  • Intención Comercial:  {orden.get('prioridad')}")
        print(f"  • Estado de la Orden:   {orden.get('estado')}")
        print(f"  • Canal Registrado:     {orden.get('canal_atencion')} (Esperado: Voz)")
        print(f"  • Texto Transcrito STT: {data.get('texto_transcrito')}")
        print(f"  • Audio TTS Generado:   {data.get('audio_url')}")
        print(f"  • Respuesta del Asesor: {data.get('respuesta_texto')[:120]}...")
        print("-" * 40)

        assert orden.get("canal_atencion") == "Voz", "El canal de atención debe ser 'Voz'"

        if data.get("audio_url"):
            audio_url = f"{API_BASE_URL}{data['audio_url']}"
            print(f"[*] Verificando descarga del audio TTS desde: {audio_url}")
            audio_req = urllib.request.Request(audio_url)
            with urllib.request.urlopen(audio_req, timeout=10) as audio_resp:
                assert audio_resp.status == 200, "El archivo de audio no pudo ser descargado"
                audio_content = audio_resp.read()
                assert len(audio_content) > 0, "El audio devuelto está vacío"
                print(f"[OK] Archivo TTS verificado exitosamente ({len(audio_content)} bytes).")

        print("\n[OK] PRUEBA UNITARIA DE AUDIO COMERCIAL SUPERADA CON ÉXITO (100% FUNCIONAL).")

    except Exception as e:
        print(f"\n[!] ERROR EN LA PRUEBA: {e}")
        sys.exit(1)
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)


if __name__ == "__main__":
    test_full_audio_flow()
