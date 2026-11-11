"""
Servicio de Síntesis de Voz a Audio (TTS - Text to Speech)
CEL RED — Asesor Comercial y Sistema de Ventas IA
Motores soportados: edge-tts (voz neuronal AlvaroNeural — cadencia fluida y natural),
                   pyttsx3 (100% local/offline como respaldo)
"""

import os
import uuid
import asyncio
import logging
from typing import Optional

logger = logging.getLogger("tts_service")
logger.setLevel(logging.INFO)

# Directorio donde se guardan los archivos de audio sintetizados
AUDIO_OUTPUT_DIR = os.getenv("AUDIO_OUTPUT_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "temp_audio")))
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

# Voz J.A.R.V.I.S.: es-ES-AlvaroNeural (o configurable vía TTS_VOICE, ej. es-CO-GonzaloNeural)
# Sin distorsión de pitch (0Hz) y con cadencia fluida (+4%) para máxima naturalidad neuronal.
DEFAULT_VOICE = os.getenv("TTS_VOICE", "es-ES-AlvaroNeural")
DEFAULT_RATE = os.getenv("TTS_RATE", "+4%")
DEFAULT_PITCH = os.getenv("TTS_PITCH", "+0Hz")


async def synthesize_speech(text: str, voice: Optional[str] = None) -> Optional[str]:
    """
    Convierte el texto de respuesta del agente a un archivo de audio (.mp3 o .wav).
    Prioriza edge-tts con prosodia natural sin distorsión de fase y utiliza pyttsx3 como respaldo local.

    Parámetros:
        text: Mensaje conversacional fluido que el agente dirá por voz.
        voice: Voz específica o idioma.

    Retorna:
        str: Nombre del archivo de audio generado (ej. 'speech_abc123.mp3') o None si falla.
    """
    if not text or not text.strip():
        return None

    voice = voice or DEFAULT_VOICE
    filename = f"speech_{uuid.uuid4().hex[:10]}.mp3"
    filepath = os.path.join(AUDIO_OUTPUT_DIR, filename)

    # Intento 1: edge-tts (Voz neuronal pura, ritmo conversacional fluido)
    try:
        import edge_tts  # type: ignore
        communicate = edge_tts.Communicate(text, voice, rate=DEFAULT_RATE, pitch=DEFAULT_PITCH)
        await communicate.save(filepath)
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            logger.info(f"✓ Audio sintetizado exitosamente con edge-tts ({voice}, rate={DEFAULT_RATE}): {filename}")
            return filename
    except Exception as e:
        logger.warning(f"edge-tts no disponible ({e}), intentando motor local pyttsx3...")

    # Intento 2: pyttsx3 (Motor 100% local sin requerir conexión a internet)
    try:
        wav_filename = f"speech_{uuid.uuid4().hex[:10]}.wav"
        wav_filepath = os.path.join(AUDIO_OUTPUT_DIR, wav_filename)

        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(None, _synthesize_pyttsx3, text, wav_filepath)
        if success and os.path.exists(wav_filepath) and os.path.getsize(wav_filepath) > 0:
            logger.info(f"✓ Audio sintetizado exitosamente con pyttsx3 local: {wav_filename}")
            return wav_filename
    except Exception as e:
        logger.warning(f"pyttsx3 no disponible ({e}).")

    logger.error("No se pudo generar el audio TTS con ninguno de los motores configurados.")
    return None


def _synthesize_pyttsx3(text: str, output_path: str) -> bool:
    """Función síncrona para ejecutar pyttsx3 en un hilo separado"""
    try:
        import pyttsx3  # type: ignore
        engine = pyttsx3.init()
        # Ajustar velocidad y volumen para emergencias (voz clara y moderada)
        engine.setProperty("rate", 160)
        engine.setProperty("volume", 1.0)

        # Seleccionar voz en español si está disponible en el SO
        voices = engine.getProperty("voices")
        for v in voices:
            if "spanish" in v.name.lower() or "es" in v.id.lower() or "sabina" in v.name.lower() or "helena" in v.name.lower():
                engine.setProperty("voice", v.id)
                break

        engine.save_to_file(text, output_path)
        engine.runAndWait()
        return True
    except Exception as ex:
        logger.error(f"Error en pyttsx3: {ex}")
        return False

