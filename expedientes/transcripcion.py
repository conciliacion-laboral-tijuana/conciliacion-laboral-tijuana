"""Transcripción local del audio de la captura por voz.

El audio del dictado se transcribe **en el servidor del despacho**, no en el
navegador ni en un servicio externo. El modelo se carga una sola vez por
proceso (la primera vez descarga los pesos, ~150 MB para `base`) y el archivo
temporal se borra en cuanto termina la transcripción: el audio no se guarda.

Si `faster-whisper` no está instalado, `disponible()` devuelve False y la
pantalla sigue funcionando con el dictado del navegador. Así el despliegue no
se rompe por una dependencia pesada que sólo se usa en la captura por voz.
"""

import logging
import os
import tempfile
import threading
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

_modelo = None
_candado = threading.Lock()


def disponible() -> bool:
    """¿Se puede transcribir en el servidor con la configuración actual?"""
    if str(getattr(settings, 'TRANSCRIPCION_BACKEND', 'auto')).lower() == 'browser':
        return False
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def _cargar_modelo():
    """Carga perezosa y única del modelo (thread-safe)."""
    global _modelo
    if _modelo is not None:
        return _modelo
    with _candado:
        if _modelo is None:
            from faster_whisper import WhisperModel

            cache = str(getattr(settings, 'WHISPER_CACHE', '') or '')
            if cache:
                Path(cache).mkdir(parents=True, exist_ok=True)
            logger.info(
                'Cargando modelo de transcripción %s (%s/%s)',
                settings.WHISPER_MODEL, settings.WHISPER_DEVICE,
                settings.WHISPER_COMPUTE_TYPE)
            _modelo = WhisperModel(
                settings.WHISPER_MODEL,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
                download_root=cache or None,
            )
    return _modelo


def transcribir_archivo(ruta) -> str:
    """Transcribe un archivo de audio local y devuelve el texto."""
    modelo = _cargar_modelo()
    prompt = str(getattr(settings, 'WHISPER_PROMPT', '') or '').strip() or None
    segmentos, _ = modelo.transcribe(
        str(ruta),
        language=getattr(settings, 'WHISPER_IDIOMA', 'es'),
        beam_size=1,
        vad_filter=True,
        condition_on_previous_text=False,
        without_timestamps=True,
        initial_prompt=prompt,
    )
    return ' '.join(segmento.text.strip() for segmento in segmentos).strip()


def transcribir_audio(archivo) -> str:
    """Transcribe un `UploadedFile` y borra el temporal pase lo que pase."""
    sufijo = Path(getattr(archivo, 'name', '') or 'audio.webm').suffix or '.webm'
    ruta = ''
    try:
        with tempfile.NamedTemporaryFile(suffix=sufijo, delete=False) as temporal:
            ruta = temporal.name
            for trozo in archivo.chunks():
                temporal.write(trozo)
        return transcribir_archivo(ruta)
    finally:
        if ruta:
            try:
                os.unlink(ruta)
            except OSError:
                logger.warning('No se pudo borrar el audio temporal %s', ruta)
