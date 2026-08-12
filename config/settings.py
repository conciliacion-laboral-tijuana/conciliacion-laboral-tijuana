import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, 'django-insecure-c(4s5!2f&8s@9m=^x5t7*9z#0k@h1j$2q3w4e5r6t7y8u9i0o1p'),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    CSRF_TRUSTED_ORIGINS=(list, []),
    DATABASE_URL=(str, f'sqlite:///{BASE_DIR / "db.sqlite3"}'),
    EMAIL_HOST=(str, ''),
    EMAIL_PORT=(int, 587),
    EMAIL_HOST_USER=(str, ''),
    EMAIL_HOST_PASSWORD=(str, ''),
    EMAIL_USE_TLS=(bool, True),
    DEFAULT_FROM_EMAIL=(str, 'Conciliacion Laboral Tijuana <noreply@despacho.com>'),
    EMAIL_BACKEND=(str, 'django.core.mail.backends.console.EmailBackend'),
)

environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')

# DEBUG ahora se controla por entorno (env var DEBUG, default False).
# En Railway se debe dejar sin definir o en False para producción.
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env('ALLOWED_HOSTS')

CSRF_TRUSTED_ORIGINS = env('CSRF_TRUSTED_ORIGINS')

# ─── Railway auto-detection ────────────────────
# Railway inyecta RAILWAY_PUBLIC_DOMAIN automáticamente
_RAILWAY_DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
if _RAILWAY_DOMAIN:
    if _RAILWAY_DOMAIN not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_RAILWAY_DOMAIN)
    _railway_origin = f'https://{_RAILWAY_DOMAIN}'
    if _railway_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_railway_origin)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'accounts',
    'expedientes',
    'finanzas',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'expedientes.context_processors.notificaciones_globales',
                'expedientes.context_processors.aviso_obligatorio_global',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# Soporta DATABASE_URL directa o variables individuales de Railway (PGHOST, PGUSER, etc.)
_DATABASE_URL = os.environ.get('DATABASE_URL')
if not _DATABASE_URL and os.environ.get('PGHOST'):
    # Construir DATABASE_URL desde variables que Railway inyecta automáticamente
    _DATABASE_URL = "postgres://{user}:{password}@{host}:{port}/{db}".format(
        user=os.environ['PGUSER'],
        password=os.environ['PGPASSWORD'],
        host=os.environ['PGHOST'],
        port=os.environ.get('PGPORT', '5432'),
        db=os.environ['PGDATABASE'],
    )
    os.environ['DATABASE_URL'] = _DATABASE_URL  # Para que django-environ lo lea

DATABASES = {
    'default': env.db_url('DATABASE_URL')
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

# Static files (Whitenoise para servir en producción sin Nginx)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    ('svg', BASE_DIR / 'svg'),
]
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Seguridad en producción
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# Login/Logout redirects
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard_redirect'
LOGOUT_REDIRECT_URL = 'login'

# Email config (for password reset)
EMAIL_BACKEND = env('EMAIL_BACKEND')
if EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
    EMAIL_HOST = env('EMAIL_HOST')
    EMAIL_PORT = env('EMAIL_PORT')
    EMAIL_USE_TLS = env('EMAIL_USE_TLS')
    EMAIL_HOST_USER = env('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')

# ─── Celery / Redis ────────────────────────────────────
# Railway inyecta REDIS_URL automáticamente al agregar Redis
# Si no hay Redis configurado, Celery se desactiva y se usa threading como fallback
# (útil para desarrollo local sin Redis)
_REDIS_URL = os.environ.get('REDIS_URL', '')
CELERY_BROKER_URL = _REDIS_URL or 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = _REDIS_URL or 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Mexico_City'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 5 * 60  # 5 minutos máximo para tareas

# Flag para saber si Celery está disponible
def _celery_disponible():
    """
    Verifica si hay un worker de Celery disponible.

    El worker se inicia automáticamente en entrypoint.sh cuando:
      - Redis está presente (REDIS_URL o REDISHOST), Y
      - CELERY_WORKER_ENABLED no está explicitamente en 'false'

    Railway inyecta REDIS_URL al agregar el servicio Redis, y el entrypoint
    levanta el worker automáticamente. Con Redis, asumimos que el worker
    está disponible (o lo estará en segundos).

    Sin Redis → threading como fallback.
    CELERY_WORKER_ENABLED=false → threading (usuario deshabilitó explícitamente).
    """
    has_redis = bool(os.environ.get('REDIS_URL') or os.environ.get('REDISHOST'))
    if not has_redis:
        return False
    # Si el usuario deshabilitó explícitamente Celery, respetarlo
    if os.environ.get('CELERY_WORKER_ENABLED', '').lower() == 'false':
        return False
    return True


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
