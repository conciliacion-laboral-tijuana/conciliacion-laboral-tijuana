from django.db import models
from django.utils import timezone

from .models import Notificacion, Aviso


def notificaciones_globales(request):
    """
    Context processor que agrega las notificaciones no leídas del usuario actual
    para mostrarlas en el icono de campana del header.
    """
    if not request.user.is_authenticated:
        return {}

    notificaciones = Notificacion.objects.filter(
        usuario=request.user
    ).order_by('-created_at')[:10]

    no_leidas = sum(1 for n in notificaciones if not n.leida)

    return {
        'notificaciones': notificaciones,
        'notificaciones_no_leidas': no_leidas,
    }


def aviso_obligatorio_global(request):
    """
    Context processor que detecta el AVISO OBLIGATORIO más reciente que el
    usuario NO ha leído.

    El admin publica avisos (noticias, pendientes, avisos importantes) desde
    su dashboard. Todo aviso activo debe ser leído por los usuarios: se muestra
    como modal bloqueante en TODA la app (base.html) sin forma de cerrarlo
    hasta pulsar "Entendido".
    """
    if not request.user.is_authenticated:
        return {}

    # El aviso activo más reciente que este usuario NO ha leído.
    # Se excluyen los vencidos (fecha_vencimiento en el pasado) para que
    # dejen de ser obligatorios automáticamente al llegar su fecha límite.
    ahora = timezone.now()
    aviso = (
        Aviso.objects.filter(activo=True)
        .filter(models.Q(fecha_vencimiento__isnull=True) | models.Q(fecha_vencimiento__gte=ahora))
        .exclude(leido_por=request.user)
        .order_by('-created_at')
        .first()
    )

    return {
        'aviso_obligatorio': aviso,
    }
