"""
Configuración de Django para ejecutar tests.

Hereda toda la configuración de config.settings y solo ajusta lo necesario
para que los tests corran sin depender del entorno:

- StaticFilesStorage simple: en tests no existe el manifest de collectstatic
  (CompressedManifestStaticFilesStorage lanzaría "Missing staticfiles manifest
  entry" al renderizar {% static %} en los templates).
"""
from .settings import *  # noqa: F401,F403

# Almacenamiento de estáticos SIN manifest (no hay collectstatic en tests)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Correo a consola (nunca enviar emails reales en tests)
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
