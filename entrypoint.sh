#!/bin/sh
set -e

echo "=== Despacho Laboral - Iniciando ==="

# 1. Migraciones
echo ">>> Ejecutando migraciones..."
uv run python manage.py migrate --noinput

# 2. Migrar datos de SQLite a PostgreSQL (si hay cambio de base de datos)
echo ">>> Verificando migración SQLite → PostgreSQL..."
uv run python manage.py migrate_sqlite_to_pg 2>&1 || echo ">>> (Aviso: no se pudo migrar datos de SQLite — consulta logs para más detalles)"

# 3. Crear superusuario admin (si no existe)
echo ">>> Verificando superusuario..."
export DJANGO_SUPERUSER_PASSWORD="${DJANGO_SUPERUSER_PASSWORD:-Admin123!}"
uv run python manage.py createsuperuser --noinput \
    --username "${DJANGO_SUPERUSER_USERNAME:-admin}" \
    --email "${DJANGO_SUPERUSER_EMAIL:-admin@despacho.com}" \
    || echo ">>> (Superusuario ya existe u otro error ignorado)"

# Actualizar el rol del superusuario a superadmin
# (el signal post_save crea el perfil con rol='asesor' por defecto)
echo ">>> Actualizando rol del superusuario a superadmin..."
uv run python manage.py shell -c "
from django.contrib.auth.models import User
username = '${DJANGO_SUPERUSER_USERNAME:-admin}'
try:
    user = User.objects.get(username=username)
    if hasattr(user, 'profile'):
        if user.profile.rol != 'superadmin':
            user.profile.rol = 'superadmin'
            user.profile.save()
            print(f'>>> Perfil de {username} actualizado a superadmin')
        else:
            print(f'>>> Perfil de {username} ya es superadmin')
    else:
        print(f'>>> Advertencia: {username} no tiene perfil')
except User.DoesNotExist:
    print(f'>>> Advertencia: usuario {username} no encontrado')
" || echo ">>> (Aviso: no se pudo actualizar el rol del superusuario)"

# 4. Resincronizar sequences de PostgreSQL
# Después de migrar datos desde SQLite, los auto-increment sequences
# de PostgreSQL pueden quedar desincronizados. Esto previene errores
# de "duplicate key value violates unique constraint" al crear registros.
echo ">>> Resincronizando sequences..."
uv run python manage.py shell -c "
from django.apps import apps
from django.core.management import call_command
from io import StringIO
from django.db import connection

app_labels = [app.label for app in apps.get_app_configs()]
out = StringIO()
call_command('sqlsequencereset', *app_labels, stdout=out)
sql = out.getvalue()
if sql.strip():
    with connection.cursor() as cursor:
        cursor.execute(sql)
    print('>>> Sequences resincronizadas correctamente.')
else:
    print('>>> No se necesita resincronización.')
" || echo ">>> (Aviso: no se pudieron resincronizar sequences, ignorando)"

# 5. Datos de prueba — SOLO en base de datos vacía (primer deploy)
#    Si la BD ya tiene datos reales (expedientes), se omiten usuarios y
#    datos de prueba para no contaminar producción.
echo ">>> Verificando si la base de datos tiene datos reales..."
HAS_EXPEDIENTES=$(uv run python manage.py shell -c "
from expedientes.models import Expediente
print(Expediente.objects.count())
" 2>/dev/null | tail -1)
HAS_EXPEDIENTES="${HAS_EXPEDIENTES:-0}"

if [ "${HAS_EXPEDIENTES}" = "0" ]; then
    echo ">>> Base de datos vacía — sembrando datos de prueba..."
    # 5a. Crear usuarios de prueba (idempotente — omite si ya existen)
    uv run python manage.py crear_usuarios_prueba 2>&1 || echo ">>> (Aviso: no se pudieron crear usuarios de prueba)"
    # 5b. Sembrar datos de prueba (idempotente — omite si ya existen)
    uv run python manage.py seed_datos 2>&1 || echo ">>> (Aviso: no se pudieron sembrar datos de prueba)"
else
    echo ">>> BD con datos reales (${HAS_EXPEDIENTES} expedientes) — se omiten usuarios y datos de prueba"
fi

# 6b. Reset de contraseñas de asesores (solo si RESET_ASESOR_PASSWORDS=true)
if [ "${RESET_ASESOR_PASSWORDS:-}" = "true" ]; then
    echo ">>> [reset] Reseteando contraseñas de asesores..."
    uv run python manage.py reset_asesor_passwords --password "${RESET_ASESOR_PASSWORD:-Asesor2026!}" 2>&1 || echo ">>> (Aviso: no se pudieron resetear contraseñas)"
else
    echo ">>> [reset] Contraseñas de asesores no modificadas (define RESET_ASESOR_PASSWORDS=true para resetear)"
fi

# ══════════════════════════════════════════════════════════════════════
#  7. Iniciar SERVICIOS (Gunicorn + Celery Worker en el mismo contenedor)
# ══════════════════════════════════════════════════════════════════════
#
# ESTRATEGIA:
#   - Gunicorn corre en foreground (es el proceso principal).
#   - Celery Worker corre en background si CELERY_WORKER_ENABLED=true.
#   - Railway usa el health check HTTP contra Gunicorn (puerto 8000).
#   - Al recibir SIGTERM, se detienen ambos procesos limpiamente.
#
# ══════════════════════════════════════════════════════════════════════

# ─── Celery Worker ──────────────────────────────────────────
# ESTRATEGIA:
#   - Si hay Redis configurado (REDIS_URL o REDISHOST), iniciar Celery Worker
#     automáticamente. Railway inyecta REDIS_URL al agregar el servicio Redis.
#   - CELERY_WORKER_ENABLED=false explícitamente lo deshabilita.
#   - CELERY_WORKER_ENABLED=true lo fuerza incluso sin Redis (fallará).
# ─────────────────────────────────────────────────────────────────

_celery_redis="${REDIS_URL:-${REDISHOST:-}}"
_celery_worker_force="${CELERY_WORKER_ENABLED:-}"

should_start_celery=false
if [ "$_celery_worker_force" = "true" ]; then
    should_start_celery=true
    echo ">>> [worker] Celery forzado por CELERY_WORKER_ENABLED=true"
elif [ -n "$_celery_redis" ] && [ "$_celery_worker_force" != "false" ]; then
    should_start_celery=true
    echo ">>> [worker] Redis detectado, iniciando Celery Worker automáticamente"
fi

if [ "$should_start_celery" = true ]; then
    echo ">>> [worker] Iniciando Celery Worker..."
    uv run celery -A config worker --loglevel=info --concurrency=1 &
    CELERY_PID=$!
    echo ">>> [worker] Celery Worker PID: $CELERY_PID"
else
    echo ">>> [worker] Celery Worker deshabilitado (sin Redis o CELERY_WORKER_ENABLED=false)"
fi

# Trap para shutdown graceful
cleanup() {
    echo ">>> Deteniendo servicios..."
    [ -n "$CELERY_PID" ] && kill "$CELERY_PID" 2>/dev/null
    [ -n "$GUNICORN_PID" ] && kill "$GUNICORN_PID" 2>/dev/null
    exit 0
}
# Signal names WITHOUT 'SIG' prefix (dash/POSIX compatible)
trap cleanup TERM INT

# Iniciar Gunicorn (foreground — proceso principal)
echo ">>> [web] Iniciando Gunicorn en 0.0.0.0:${PORT:-8000}..."
uv run gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 3 \
    --timeout 300 &
GUNICORN_PID=$!
echo ">>> [web] Gunicorn PID: $GUNICORN_PID"

# Esperar a que Gunicorn termine (proceso principal)
# Si Gunicorn muere, detener Celery Worker y salir
wait $GUNICORN_PID
echo ">>> Gunicorn terminó. Deteniendo servicios secundarios..."
[ -n "$CELERY_PID" ] && kill "$CELERY_PID" 2>/dev/null && wait "$CELERY_PID" 2>/dev/null
echo ">>> Todos los servicios detenidos."
