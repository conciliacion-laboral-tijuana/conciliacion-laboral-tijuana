"""
WhatsApp Utility Module
=======================
Provee dos formas de integración:
1. Deep Links (wa.me) — abre WhatsApp web/app con mensaje pre-llenado (gratuito)
2. Twilio API — envío automatizado desde el servidor (requiere cuenta Twilio)

Configuración en settings.py:
    TWILIO_ACCOUNT_SID = 'your_account_sid'
    TWILIO_AUTH_TOKEN = 'your_auth_token'
    TWILIO_WHATSAPP_NUMBER = '+14155238886'  # Número sandbox de Twilio
"""

import logging
from urllib.parse import quote

from django.conf import settings

logger = logging.getLogger(__name__)


def limpiar_numero(telefono):
    """
    Limpia y normaliza un número telefónico.
    - Elimina espacios, guiones, paréntesis
    - Agrega código de país de México (52) si es necesario
    - Retorna el número sin el prefijo +
    """
    if not telefono:
        return ''

    # Limpiar
    numero = telefono.replace('+', '').replace(' ', '').replace('-', '')
    numero = numero.replace('(', '').replace(')', '').replace('.', '')

    # Si solo tiene 10 dígitos, asumir México
    if len(numero) == 10 and numero.isdigit():
        numero = '52' + numero

    # Si empieza con 1 después de 52 (caso común en México), quitar el 1
    if numero.startswith('521') and len(numero) == 13:
        numero = '52' + numero[3:]

    return numero


def formatear_numero_para_enlace(telefono):
    """
    Formatea número para link wa.me (sin +, sin espacios).
    """
    return limpiar_numero(telefono)


def formatear_numero_para_twilio(telefono):
    """
    Formatea número para Twilio (con prefijo whatsapp:).
    """
    numero = limpiar_numero(telefono)
    if numero:
        return f'whatsapp:+{numero}'
    return ''


def generar_deep_link(telefono, mensaje):
    """
    Genera un enlace wa.me para abrir WhatsApp con mensaje pre-llenado.
    Ejemplo: https://wa.me/526641234567?text=Hola%2C%20buenos%20d%C3%ADas

    Args:
        telefono: Número telefónico del destinatario
        mensaje: Texto del mensaje a pre-llenar

    Returns:
        str: URL completa de wa.me
    """
    numero = formatear_numero_para_enlace(telefono)
    if not numero:
        return '#'
    mensaje_codificado = quote(mensaje)
    return f'https://wa.me/{numero}?text={mensaje_codificado}'


def enviar_via_twilio(telefono, mensaje):
    """
    Envía un mensaje de WhatsApp usando la API de Twilio.
    Requiere TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN y TWILIO_WHATSAPP_NUMBER configurados.

    Args:
        telefono: Número telefónico del destinatario
        mensaje: Texto del mensaje a enviar

    Returns:
        tuple: (success: bool, detail: str)
    """
    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
    twilio_number = getattr(settings, 'TWILIO_WHATSAPP_NUMBER', None)

    if not all([account_sid, auth_token, twilio_number]):
        return False, 'Twilio no está configurado. Configura TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN y TWILIO_WHATSAPP_NUMBER en settings.py'

    try:
        from twilio.rest import Client

        destino = formatear_numero_para_twilio(telefono)
        origen = f'whatsapp:{twilio_number}'

        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=mensaje,
            from_=origen,
            to=destino,
        )

        logger.info(f'WhatsApp enviado via Twilio: {message.sid}')
        return True, f'Enviado (SID: {message.sid})'

    except ImportError:
        return False, 'La librería twilio no está instalada. Ejecuta: pip install twilio'
    except Exception as e:
        logger.error(f'Error enviando WhatsApp via Twilio: {e}')
        return False, f'Error: {str(e)}'


def enviar_whatsapp(telefono, mensaje, via='auto'):
    """
    Envía un mensaje de WhatsApp por el método disponible.

    Args:
        telefono: Número telefónico del destinatario
        mensaje: Texto del mensaje
        via: Método de envío ('auto', 'deep_link', 'twilio')

    Returns:
        dict: {
            'success': bool,
            'detail': str,
            'link': str | None,  # Link wa.me si aplica
            'via': str,
        }
    """
    if via == 'auto':
        # Intentar Twilio primero, si no está configurado, usar deep link
        success, detail = enviar_via_twilio(telefono, mensaje)
        if success:
            return {
                'success': True,
                'detail': detail,
                'link': None,
                'via': 'twilio',
            }
        # Fallback a deep link
        link = generar_deep_link(telefono, mensaje)
        return {
            'success': True,
            'detail': 'Enlace generado (Twilio no disponible)',
            'link': link,
            'via': 'deep_link',
        }

    elif via == 'twilio':
        success, detail = enviar_via_twilio(telefono, mensaje)
        return {
            'success': success,
            'detail': detail,
            'link': None,
            'via': 'twilio',
        }

    else:  # deep_link
        link = generar_deep_link(telefono, mensaje)
        return {
            'success': True,
            'detail': 'Enlace generado',
            'link': link,
            'via': 'deep_link',
        }


# ─── Estado de Expediente → Plantilla de Mensaje ──────────────────────────

ESTADO_A_TIPO_MENSAJE = {
    # estado_expediente: (tipo_whatsapp, nombre_template_o_None, mensaje_personalizado_o_None)
    'nuevo': ('seguimiento', None,
        '👋 ¡Hola {cliente}!\n\nTe informamos que tu caso ({numero}) ha sido registrado en nuestro despacho. '
        'En breve nos pondremos en contacto contigo para dar inicio al proceso.\n\n'
        'Si tienes alguna duda, no dudes en escribirnos.\n\n'
        'Saludos,\n{asesor}'),
    'solicitud': ('seguimiento', None,
        '📋 Hola {cliente}, te informamos que se ha creado la solicitud de conciliación '
        'para tu caso ({numero}) en el Centro de Conciliación Laboral. '
        'Estaremos al pendiente de la fecha de audiencia asignada.\n\n'
        'Saludos,\n{asesor}'),
    'citatorio': ('citatorio', 'citatorio', None),
    'audiencia': ('recordatorio_audiencia', 'recordatorio_audiencia', None),
    'no_notificado': ('seguimiento', None,
        '⚠️ Hola {cliente}, lamentamos informarte que la notificación de tu audiencia '
        'no pudo realizarse. Estamos gestionando una nueva fecha. '
        'Te mantendremos informado.\n\n'
        'Saludos,\n{asesor}'),
    'reprogramacion': ('seguimiento', None,
        '🔄 Hola {cliente}, te informamos que tu audiencia ha sido reprogramada. '
        'Te notificaremos la nueva fecha en cuanto esté disponible.\n\n'
        'Agradecemos tu paciencia.\n\n'
        'Saludos,\n{asesor}'),
    'convenio': ('convenio', 'convenio', None),
    'sin_conciliacion': ('seguimiento', None,
        '📑 Hola {cliente}, te informamos que en la audiencia de conciliación '
        'no se llegó a un acuerdo. Estaremos preparando tu demanda laboral '
        'para presentarla ante el tribunal correspondiente.\n\n'
        'Saludos,\n{asesor}'),
    'demanda': ('seguimiento', None,
        '⚡ Hola {cliente}, te informamos que se ha presentado la demanda laboral '
        'en tu caso ({numero}). Seguiremos con el proceso legal. '
        'Te mantendremos al tanto de los avances.\n\n'
        'Saludos,\n{asesor}'),
    'cerrado': ('seguimiento', None,
        '✅ Hola {cliente}, te informamos que tu caso ({numero}) ha sido cerrado. '
        'Agradecemos la confianza depositada en nuestro despacho.\n\n'
        'Si requieres asistencia legal en el futuro, no dudes en contactarnos.\n\n'
        'Saludos,\n{asesor}'),
}


def generar_mensaje_automatico(expediente):
    """
    Genera un mensaje de WhatsApp automático basado en el estado actual del expediente.

    Args:
        expediente: Instancia del modelo Expediente

    Returns:
        dict con:
            - tipo: tipo de mensaje WhatsApp
            - mensaje: texto del mensaje renderizado
            - destino: número de teléfono destino
            - template_used: nombre de template usado (None si es personalizado)
        o None si el estado no tiene mensaje configurado
    """
    mapping = ESTADO_A_TIPO_MENSAJE.get(expediente.estado)
    if not mapping:
        return None

    tipo_whatsapp, template_name, mensaje_personalizado = mapping

    cliente = expediente.cliente
    asesor = expediente.asesor
    asesor_nombre = asesor.get_full_name() or asesor.username

    fecha_str = ''
    if expediente.fecha_audiencia:
        from django.utils import timezone
        fecha_audiencia_local = timezone.localtime(expediente.fecha_audiencia)
        fecha_str = fecha_audiencia_local.strftime('%d/%m/%Y a las %H:%M')

    kwargs = {
        'cliente': cliente.nombre,
        'asesor': asesor_nombre,
        'numero': expediente.numero,
        'fecha': fecha_str,
    }

    # Obtener el texto del mensaje
    if template_name and template_name in MENSAJES_TEMPLATE:
        mensaje = renderizar_plantilla(template_name, **kwargs)
    elif mensaje_personalizado:
        mensaje = mensaje_personalizado.format(**kwargs)
    else:
        mensaje = None

    if not mensaje:
        return None

    # Destino
    destino = cliente.whatsapp or cliente.telefono
    if not destino:
        return None

    return {
        'tipo': tipo_whatsapp,
        'mensaje': mensaje,
        'destino': destino,
        'template_used': template_name,
    }


# ─── Plantillas de mensajes ────────────────────────────────────────────────

MENSAJES_TEMPLATE = {
    'recordatorio_audiencia': (
        "⚖️ *RECORDATORIO DE AUDIENCIA*\n\n"
        "Hola {cliente}, te recordamos que tienes una audiencia de conciliación "
        "programada para el día *{fecha}*.\n\n"
        "Por favor, no olvides llevar tu identificación oficial y los documentos "
        "relacionados con tu caso.\n\n"
        "Si tienes alguna duda, contáctanos.\n\n"
        "Saludos,\n"
        "{asesor}"
    ),
    'citatorio': (
        "📬 *CITATORIO*\n\n"
        "Hola {cliente}, te informamos que se ha generado un citatorio "
        "para tu audiencia de conciliación.\n\n"
        "📅 Fecha: *{fecha}*\n\n"
        "Es importante que asistas puntualmente. Si no puedes asistir, "
        "avísanos con anticipación para reprogramar.\n\n"
        "Saludos,\n"
        "{asesor}"
    ),
    'convenio': (
        "🤝 *CONVENIO DE CONCILIACIÓN*\n\n"
        "Hola {cliente}, te informamos que se ha alcanzado un convenio "
        "en tu caso ({numero}).\n\n"
        "Te compartimos el comprobante con los detalles del acuerdo. "
        "Favor de revisar y confirmar recibido.\n\n"
        "Saludos,\n"
        "{asesor}"
    ),
    'seguimiento': (
        "📞 *SEGUIMIENTO*\n\n"
        "Hola {cliente}, te contactamos para dar seguimiento a tu caso. "
        "¿Cómo vamos?\n\n"
        "Si necesitas algo, estamos para apoyarte.\n\n"
        "Saludos,\n"
        "{asesor}"
    ),
    'documentos': (
        "📎 *SOLICITUD DE DOCUMENTOS*\n\n"
        "Hola {cliente}, para continuar con tu caso necesitamos que nos "
        "proporciones los siguientes documentos:\n\n"
        "- Identificación oficial (INE/IFE)\n"
        "- Comprobante de domicilio\n"
        "- Contrato laboral (si aplica)\n"
        "- Últimos recibos de nómina\n\n"
        "Puedes enviarlos por este medio o llevarlos a nuestras oficinas.\n\n"
        "Saludos,\n"
        "{asesor}"
    ),
}


def renderizar_plantilla(tipo, **kwargs):
    """
    Renderiza una plantilla de mensaje reemplazando las variables.

    Args:
        tipo: Clave del mensaje en MENSAJES_TEMPLATE
        kwargs: Variables a reemplazar (cliente, fecha, asesor, etc.)

    Returns:
        str: Mensaje renderizado o None si no existe la plantilla
    """
    plantilla = MENSAJES_TEMPLATE.get(tipo)
    if not plantilla:
        return None
    try:
        return plantilla.format(**kwargs)
    except KeyError as e:
        logger.warning(f'Falta variable en plantilla {tipo}: {e}')
        return plantilla
