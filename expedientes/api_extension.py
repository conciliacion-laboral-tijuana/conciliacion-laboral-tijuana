"""
API REST para la Extensión de Chrome.

La extensión se comunica con la app para:

1. GET  /api/extension/tareas/            → tareas de conciliación pendientes
                                           (con todos los datos del cliente/expediente
                                           necesarios para llenar el portal)
2. POST /api/extension/tareas/<id>/reportar/ → reportar el resultado del llenado
                                           (folio, acuse PDF en base64, screenshots)

Autenticación: header `Authorization: Token <token>` donde el token es el
`api_token` del perfil del usuario (se ve en la página de configuración de la
extensión). No requiere CSRF ni sesión: es una API de máquina a máquina.
"""
import base64
import json
import logging
from datetime import date, timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import Documento, TareaConciliacion
from .signals import registrar_movimiento

logger = logging.getLogger(__name__)

# Límites de tamaño (misma política que la subida manual: acuse ≤ 2 MB)
MAX_ACUSE_BYTES = 2 * 1024 * 1024      # 2 MB
MAX_SCREENSHOT_BYTES = 1 * 1024 * 1024  # 1 MB cada uno
MAX_SCREENSHOTS = 5                     # máximo de capturas por reporte


# ─── Autenticación por token ──────────────────────────────────────────────

def _usuario_por_token(request):
    """Retorna el usuario autenticado por el header Authorization: Token, o None."""
    header = request.headers.get('Authorization', '')
    if not header.startswith('Token '):
        return None
    token = header[6:].strip()
    from accounts.models import UserProfile
    try:
        profile = UserProfile.objects.select_related('user').get(api_token=token)
        return profile.user
    except UserProfile.DoesNotExist:
        return None


def _tiene_acceso(user, expediente_id):
    """Verifica que el usuario tenga acceso al expediente (misma regla que la web)."""
    from .views import get_expedientes_queryset
    qs = get_expedientes_queryset(user)
    return qs.filter(pk=expediente_id).exists()


# ─── Datos para llenar el portal ──────────────────────────────────────────

# Mapeo de valores del modelo → IDs del portal BC (igual que en la automatización)
GENERO_PORTAL_IDS = {'masculino': '1', 'femenino': '2'}
PERIODICIDAD_PORTAL_IDS = {'diario': '1', 'mensual': '2', 'quincenal': '3', 'semanal': '4'}
JORNADA_PORTAL_IDS = {'diurna': '1', 'nocturna': '2', 'mixta': '3'}
TIPO_PERSONA_PORTAL_IDS = {'fisica': '1', 'moral': '2'}


def _fmt_fecha(f):
    return f.strftime('%d/%m/%Y') if f else ''


def _serializar_tarea(tarea):
    """Serializa una tarea con TODOS los datos que la extensión necesita para llenar el portal."""
    expediente = tarea.expediente
    cliente = expediente.cliente

    fecha_conflicto = cliente.fecha_salida or expediente.fecha_tramite or date.today()
    fecha_nac = cliente.fecha_nacimiento or (cliente.fecha_ingreso or date.today()) - timedelta(days=365 * 30)
    fecha_ing = cliente.fecha_ingreso or date.today().replace(year=date.today().year - 2)
    fecha_sal = cliente.fecha_salida or date.today()

    # Misma narrativa que la automatización (FASE 6)
    hechos = [f'El día {_fmt_fecha(fecha_conflicto)} fui despedido injustificadamente']
    if cliente.empresa:
        hechos[0] += f' de mi empleo en {cliente.empresa}'
    if cliente.puesto:
        hechos.append(f'Donde laboraba como {cliente.puesto}.')
    else:
        hechos[0] += '.'
    if cliente.salario:
        hechos.append(f'Mi salario mensual era de ${float(cliente.salario):.2f}.')
    if cliente.fecha_ingreso:
        hechos.append(f'Ingresé a laborar el {_fmt_fecha(cliente.fecha_ingreso)}.')
    hechos.append('Solicito el pago de mis prestaciones de ley.')

    return {
        'id': tarea.pk,
        'estado': tarea.estado,
        'expediente': {
            'id': expediente.pk,
            'numero': expediente.numero,
            'folio': expediente.folio,
            'tipo_despido': expediente.tipo_despido,
        },
        'portal': {
            'url_solicitud': 'https://app.conciliacionbc.gob.mx/solicitudes/create-public?solicitud=1',
        },
        'cliente': {
            'nombre': cliente.nombre or '',
            'curp': (cliente.curp or '').strip().upper(),
            'genero': GENERO_PORTAL_IDS.get(cliente.genero, '1'),
            'telefono': cliente.telefono or '',
            'fecha_nacimiento': _fmt_fecha(fecha_nac),
            'fecha_ingreso': _fmt_fecha(fecha_ing),
            'fecha_salida': _fmt_fecha(fecha_sal),
            'fecha_conflicto': _fmt_fecha(fecha_conflicto),
            # Domicilio particular
            'direccion_calle': cliente.direccion_calle or '',
            'direccion_numero': cliente.direccion_numero or '',
            'direccion_cp': cliente.direccion_cp or '',
            # Laborales
            'puesto': cliente.puesto or 'Trabajador',
            'salario': float(cliente.salario or 10000),  # mismo default que la automatización
            'periodicidad': PERIODICIDAD_PORTAL_IDS.get(cliente.periodo_pago, '2'),
            'horas_semanales': str(cliente.horas_semanales or 40),
            'jornada': JORNADA_PORTAL_IDS.get(cliente.jornada, '1'),
            # Empresa / patrón (citado)
            'empresa_nombre': cliente.empresa_razon_social or cliente.empresa or 'Empresa SA de CV',
            'tipo_persona': TIPO_PERSONA_PORTAL_IDS.get(cliente.tipo_persona_citado, '1'),
            'empresa_calle': cliente.empresa_calle or cliente.direccion_calle or '',
            'empresa_numero': cliente.empresa_numero or cliente.direccion_numero or '',
            'empresa_cp': cliente.empresa_cp or cliente.direccion_cp or '',
            'empresa_telefono': cliente.empresa_telefono or cliente.telefono or '',
            'empresa_rfc': cliente.empresa_rfc or cliente.rfc or '',
            'empresa_curp': (cliente.empresa_curp or '').strip().upper(),
            'empresa_email': cliente.email or '',
        },
        'hechos': ' '.join(hechos),
    }


# ─── Vista: tareas pendientes ─────────────────────────────────────────────

@csrf_exempt
def tareas_pendientes(request):
    """
    GET /api/extension/tareas/

    Retorna las tareas de conciliación pendientes a las que el usuario tiene
    acceso, con todos los datos para que la extensión llene el portal.
    """
    user = _usuario_por_token(request)
    if user is None:
        return JsonResponse({'error': 'Token inválido'}, status=401)

    from .views import get_expedientes_queryset
    expedientes_accesibles = get_expedientes_queryset(user)

    # Solo tareas creadas para la extensión (modo='extension'). Evita que una
    # tarea headless en su breve estado 'pendiente' sea tomada por la extensión.
    tareas = (
        TareaConciliacion.objects
        .filter(expediente__in=expedientes_accesibles, estado='pendiente', modo='extension')
        .select_related('expediente', 'expediente__cliente')
        .order_by('-created_at')[:20]
    )

    return JsonResponse({
        'tareas': [_serializar_tarea(t) for t in tareas],
    })


# ─── Vista: reportar resultado ────────────────────────────────────────────

@csrf_exempt
def reportar_tarea(request, task_pk):
    """
    POST /api/extension/tareas/<id>/reportar/

    Body JSON:
    {
        "estado": "completado" | "fallido",
        "folio": "CCL-1234",
        "error": "mensaje si falló",
        "detalle": "texto libre",
        "acuse_pdf": "<base64>",        # opcional
        "acuse_nombre": "acuse.pdf",    # opcional
        "screenshots": ["<base64>", ...]  # opcional (PNG)
    }

    - 'completado' → actualiza la tarea, guarda el folio en el expediente,
      guarda el PDF del acuse como Documento y registra el movimiento.
    - 'fallido' → guarda el error para que el asesor lo vea.
    """
    user = _usuario_por_token(request)
    if user is None:
        return JsonResponse({'error': 'Token inválido'}, status=401)

    try:
        tarea = TareaConciliacion.objects.select_related(
            'expediente', 'expediente__cliente'
        ).get(pk=task_pk)
    except TareaConciliacion.DoesNotExist:
        return JsonResponse({'error': 'Tarea no encontrada'}, status=404)

    if not _tiene_acceso(user, tarea.expediente_id):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    try:
        data = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    estado = data.get('estado', 'fallido')
    folio = (data.get('folio') or '').strip()
    error = (data.get('error') or '').strip()
    detalle = (data.get('detalle') or '').strip()
    acuse_b64 = data.get('acuse_pdf', '')
    acuse_nombre = (data.get('acuse_nombre') or 'acuse_conciliacion.pdf').strip()
    screenshots = data.get('screenshots', []) or []

    # Protección anti abuso: la tarea ya no está pendiente → no aceptar doble reporte
    if tarea.estado in ('completado', 'fallido'):
        return JsonResponse({'ok': False, 'error': 'La tarea ya fue reportada'}, status=409)

    tarea.detalle = detalle or ''
    tarea.completed_at = timezone.now()

    if estado == 'completado':
        tarea.estado = 'completado'
        tarea.folio = folio
        expediente = tarea.expediente

        # Guardar folio en el expediente
        if folio:
            expediente.folio = folio
            expediente.fecha_tramite = timezone.now().date()
            expediente.save(update_fields=['folio', 'fecha_tramite'])

        # Guardar el PDF del acuse como Documento (con límite de tamaño)
        if acuse_b64:
            try:
                contenido = base64.b64decode(acuse_b64)
                if len(contenido) > MAX_ACUSE_BYTES:
                    logger.warning('Acuse demasiado grande (%d bytes) para expediente %s',
                                   len(contenido), expediente.numero)
                    return JsonResponse({'ok': False, 'error': 'El acuse supera los 2 MB'}, status=413)
                doc = Documento(
                    expediente=expediente,
                    descripcion=f'Acuse de Conciliación - Folio: {folio or "N/A"}',
                    tipo='citatorio',
                    subido_por=user,
                )
                doc.archivo.save(acuse_nombre, ContentFile(contenido), save=True)
                logger.info('Acuse de la extensión guardado para expediente %s: %s',
                            expediente.numero, acuse_nombre)
            except Exception as e:
                logger.warning('No se pudo guardar el acuse de la extensión: %s', e)

        registrar_movimiento(
            expediente=expediente,
            usuario=user,
            accion='actualizacion',
            detalle=f'Solicitud de conciliación enviada desde la extensión de Chrome. '
                    f'Folio: {folio or "N/A"}'
        )

        # Guardar screenshots (espejo en vivo)
        _guardar_screenshots(tarea, screenshots)

        tarea.save(update_fields=['estado', 'folio', 'detalle', 'screenshots_json', 'completed_at'])
        return JsonResponse({'ok': True, 'estado': tarea.estado, 'folio': folio})

    # Fallido
    tarea.estado = 'fallido'
    tarea.error = error or 'La solicitud no se completó desde la extensión.'
    tarea.save(update_fields=['estado', 'error', 'detalle', 'completed_at'])
    return JsonResponse({'ok': True, 'estado': tarea.estado})


def _guardar_screenshots(tarea, screenshots_b64):
    """Guarda screenshots (base64) de la extensión en el directorio de la tarea."""
    if not screenshots_b64:
        return
    from pathlib import Path
    directorio = Path(settings.MEDIA_ROOT) / 'conciliacion' / f'tarea_{tarea.pk}'
    directorio.mkdir(parents=True, exist_ok=True)
    urls = []
    for i, b64 in enumerate(screenshots_b64[:MAX_SCREENSHOTS]):
        if not b64:
            continue
        try:
            contenido = base64.b64decode(b64)
            if len(contenido) > MAX_SCREENSHOT_BYTES:
                logger.warning('Screenshot demasiado grande (%d bytes), omitido', len(contenido))
                continue
            nombre = f'ext_{i:02d}.png'
            (directorio / nombre).write_bytes(contenido)
            urls.append(f'{settings.MEDIA_URL}conciliacion/tarea_{tarea.pk}/{nombre}')
        except Exception as e:
            logger.warning('Screenshot inválido de la extensión: %s', e)
    if urls:
        tarea.screenshots_json = json.dumps(urls)
