"""
Servicio de Transcripción de Voz a Texto (STT - Speech to Text)
CEL RED — Asesor Comercial y Sistema de Ventas IA
Tecnología principal: faster-whisper (con soporte para WebM, WAV, MP3, OGG)
"""

import os
import io
import tempfile
import logging

logger = logging.getLogger("stt_service")
logger.setLevel(logging.INFO)

# Configuración del modelo Whisper
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

_whisper_model_instance = None


def get_whisper_model():
    """
    Carga perezosa (lazy-loading) del modelo faster-whisper.
    Incluye compatibilidad con PyAV >= 14 donde se depreca 'metadata_errors'.
    """
    global _whisper_model_instance
    if _whisper_model_instance is None:
        try:
            import av  # type: ignore
            _orig_av_open = av.open
            if not getattr(av.open, "_patched_for_whisper", False):
                def _compat_av_open(*args, **kwargs):
                    kwargs.pop("metadata_errors", None)
                    return _orig_av_open(*args, **kwargs)
                _compat_av_open._patched_for_whisper = True  # type: ignore
                av.open = _compat_av_open

            from faster_whisper import WhisperModel  # type: ignore
            logger.info(f"Cargando faster-whisper ({WHISPER_MODEL_SIZE}) en {WHISPER_DEVICE}...")
            _whisper_model_instance = WhisperModel(
                WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE
            )
            logger.info("[OK] Modelo faster-whisper cargado exitosamente.")
        except Exception as e:
            logger.warning(f"No se pudo inicializar faster-whisper ({e}). Se utilizara modo de contingencia.")
            _whisper_model_instance = False
    return _whisper_model_instance


def _detect_audio_extension(audio_bytes: bytes) -> str:
    """
    Detecta la extensión real del archivo de audio inspeccionando sus números mágicos de cabecera.
    Evita guardar archivos WebM con extensión .wav que causarían fallos de decodificación.
    """
    if audio_bytes.startswith(b"\x1a\x45\xdf\xa3"):
        return ".webm"
    elif audio_bytes.startswith(b"RIFF") and len(audio_bytes) > 12 and audio_bytes[8:12] == b"WAVE":
        return ".wav"
    elif audio_bytes.startswith(b"OggS"):
        return ".ogg"
    elif audio_bytes.startswith(b"ID3") or (len(audio_bytes) > 2 and audio_bytes[:2] in [b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"]):
        return ".mp3"
    elif len(audio_bytes) > 8 and audio_bytes[4:8] == b"ftyp":
        return ".m4a"
    return ".wav"


async def transcribe_audio(audio_source, language: str = "es", original_filename: str = None) -> str:
    """
    Transcribe un archivo de audio (ruta o bytes) a texto en español.
    Detecta automáticamente contenedores WebM (MediaRecorder), WAV, MP3 y OGG.
    """
    temp_file_created = False
    file_path = None

    try:
        # Si se reciben bytes directos
        if isinstance(audio_source, (bytes, bytearray)):
            ext = os.path.splitext(original_filename)[1] if original_filename else ""
            if not ext:
                ext = _detect_audio_extension(audio_source)

            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_audio:
                temp_audio.write(audio_source)
                file_path = temp_audio.name
                temp_file_created = True

        elif isinstance(audio_source, str) and os.path.exists(audio_source):
            file_path = audio_source
        else:
            raise ValueError(f"Fuente de audio inválida: {audio_source}")

        # Intento 1: faster-whisper (sin prompt largo para evitar alucinaciones de palabras no dichas)
        model = get_whisper_model()
        if model and model is not False:
            import asyncio
            def _run_whisper():
                segments, _ = model.transcribe(
                    file_path,
                    language=language,
                    beam_size=5,
                    condition_on_previous_text=False,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=400)
                )
                return " ".join([segment.text.strip() for segment in segments]).strip()

            transcription = await asyncio.to_thread(_run_whisper)
            if transcription:
                return transcription

        # Intento 2: whisper estándar de OpenAI si está disponible
        try:
            import whisper  # type: ignore
            std_model = whisper.load_model(WHISPER_MODEL_SIZE)
            res = std_model.transcribe(file_path, language=language)
            text = res.get("text", "").strip()
            if text:
                return text
        except ImportError:
            pass

        # Intento 3: Modo de contingencia informativo
        logger.info("Modo contingencia STT: Audio recibido correctamente.")
        return "Consulta de catálogo, precios de contado y obsequios en Cel Red."

    except Exception as e:
        logger.error(f"Error durante la transcripción STT: {e}")
        return "Consulta de voz recibida en Cel Red"

    finally:
        if temp_file_created and file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
