"""
Módulo de Marcadores para Documentos Legales
=============================================

Gestiona la inyección de datos del expediente/cliente en plantillas HTML
(machotes) mediante el reemplazo de marcadores {{ variable }}.

Proporciona:
- Reemplazo completo de marcadores con datos reales
- Metadata sobre qué datos están completos y cuáles faltan
- Inyección de cálculos laborales (aguinaldo, vacaciones, etc.)

Autor: Conciliacion Laboral Tijuana - Módulo de Documentos
"""

import re
from decimal import Decimal
from typing import Dict, Any, List, Tuple

from django.utils import timezone

from .models import Expediente, CalculoLaboral
from .laboral_calculator import calcular_desde_expediente


# ─── Meses en español ──────────────────────────────────────────────────────

MESES_ES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _fecha_espanol(fecha) -> str:
    """Formatea una fecha en español: '1 de enero de 2024'."""
    if not fecha:
        return "[FECHA]"
    return f"{fecha.day} de {MESES_ES[fecha.month]} de {fecha.year}"


# ─── Metadata: qué datos son obligatorios para generar documentos ──────────

FIELD_METADATA = {
    # Datos del cliente
    'nombre_cliente': {'label': 'Nombre del cliente', 'section': 'Cliente', 'source': 'cliente.nombre'},
    'curp_cliente': {'label': 'CURP', 'section': 'Cliente', 'source': 'cliente.curp'},
    'rfc_cliente': {'label': 'RFC', 'section': 'Cliente', 'source': 'cliente.rfc'},
    'telefono_cliente': {'label': 'Teléfono', 'section': 'Cliente', 'source': 'cliente.telefono'},
    'email_cliente': {'label': 'Email', 'section': 'Cliente', 'source': 'cliente.email'},
    'direccion_cliente': {'label': 'Dirección del cliente', 'section': 'Cliente', 'source': 'cliente.direccion_completa'},
    'puesto_trabajador': {'label': 'Puesto', 'section': 'Empleo', 'source': 'cliente.puesto'},
    'salario_mensual': {'label': 'Salario mensual', 'section': 'Empleo', 'source': 'cliente.salario'},
    'fecha_ingreso': {'label': 'Fecha de ingreso', 'section': 'Empleo', 'source': 'cliente.fecha_ingreso'},
    'fecha_despido': {'label': 'Fecha de despido/salida', 'section': 'Empleo', 'source': 'cliente.fecha_salida'},
    'periodo_pago': {'label': 'Periodo de pago', 'section': 'Empleo', 'source': 'solicitud.periodo_pago'},

    # Empresa
    'nombre_empresa': {'label': 'Nombre de la empresa', 'section': 'Empresa', 'source': 'cliente.empresa_razon_social'},
    'razon_social': {'label': 'Razón social', 'section': 'Empresa', 'source': 'cliente.empresa_razon_social'},
    'direccion_empresa': {'label': 'Dirección de la empresa', 'section': 'Empresa', 'source': 'direccion_empresa'},
    'empresa_actividad': {'label': 'Actividad económica', 'section': 'Empresa', 'source': 'cliente.empresa_actividad'},

    # Expediente
    'numero_expediente': {'label': 'Número de expediente', 'section': 'Expediente', 'source': 'expediente.numero'},
    'folio_conciliacion': {'label': 'Folio de conciliación', 'section': 'Expediente', 'source': 'expediente.folio'},
    'monto_reclamado': {'label': 'Monto reclamado', 'section': 'Expediente', 'source': 'expediente.monto_reclamado'},
    'fecha_tramite': {'label': 'Fecha de trámite', 'section': 'Expediente', 'source': 'expediente.fecha_tramite'},
    'tipo_despido': {'label': 'Tipo de despido', 'section': 'Expediente', 'source': 'expediente.tipo_despido'},
}


# ─── Generación de marcadores ─────────────────────────────────────────────

def get_marcadores(expediente: Expediente, calculo: Dict[str, Any] | None = None) -> Dict[str, str]:
    """
    Genera el diccionario completo de marcadores → valores reales
    a partir de un Expediente y su cálculo laboral.

    Args:
        expediente: Instancia de Expediente
        calculo: Dict opcional con resultados de calcular_desde_expediente().
                 Si es None, se calcula automáticamente.

    Returns:
        Dict[str, str]: Mapeo de nombre_marcador → valor (string)
    """
    cliente = expediente.cliente

    if calculo is None:
        calculo = calcular_desde_expediente(expediente)

    hoy = timezone.now()
    hoy_str = _fecha_espanol(hoy)
    mes_actual = MESES_ES[hoy.month]
    anio_actual = str(hoy.year)
    asesor = expediente.asesor.get_full_name() or expediente.asesor.username

    # ─── Salarios ─────────────────────────────────────────────────────
    if cliente.salario:
        salario_mensual = f"${cliente.salario:,.2f}"
        salario_diario = f"${float(cliente.salario) / 30:,.2f}"
    else:
        salario_mensual = "[SALARIO MENSUAL]"
        salario_diario = "[SALARIO DIARIO]"

    # ─── Monto total (de cálculo o del expediente) ────────────────────
    if calculo.get('success') and calculo['total'] > 0:
        monto_total = f"${calculo['total']:,.2f}"
    elif expediente.monto_reclamado:
        monto_total = f"${expediente.monto_reclamado:,.2f}"
    else:
        monto_total = "[MONTO A DETERMINAR]"

    # ─── Prestaciones individuales ─────────────────────────────────────
    def fmt(val):
        try:
            return f"${float(val):,.2f}"
        except (TypeError, ValueError):
            return '[MONTO]'

    if calculo.get('success'):
        aguinaldo_val = fmt(calculo['aguinaldo']['monto'])
        vacaciones_val = fmt(calculo['vacaciones']['monto'])
        dias_vacaciones = str(calculo['vacaciones']['dias_segun_antiguedad'])
        prima_vacacional_val = fmt(calculo['prima_vacacional']['monto'])
        prima_antiguedad_val = fmt(calculo['prima_antiguedad']['monto'])
        tope_aplicado = ' (con tope)' if calculo['prima_antiguedad']['tope_aplicado'] else ''
        indemnizacion_val = fmt(calculo['indemnizacion']['monto'])
        dias_trabajados = str(calculo.get('dias_trabajados', ''))
    else:
        aguinaldo_val = '[MONTO]'
        vacaciones_val = '[MONTO]'
        dias_vacaciones = '6'
        prima_vacacional_val = '[MONTO]'
        prima_antiguedad_val = '[MONTO]'
        tope_aplicado = ''
        indemnizacion_val = '[MONTO]'
        dias_trabajados = ''

    # ─── Dirección empresa ────────────────────────────────────────────
    partes_dir_empresa = []
    if cliente.empresa_calle:
        partes_dir_empresa.append(cliente.empresa_calle)
    if cliente.empresa_numero:
        partes_dir_empresa.append(f"#{cliente.empresa_numero}")
    if cliente.empresa_colonia:
        partes_dir_empresa.append(f"Col. {cliente.empresa_colonia}")
    if cliente.empresa_cp:
        partes_dir_empresa.append(f"CP {cliente.empresa_cp}")
    direccion_empresa = ', '.join(partes_dir_empresa) if partes_dir_empresa else "[DIRECCIÓN DE LA EMPRESA]"

    # ─── Dirección cliente ────────────────────────────────────────────
    direccion_cliente = cliente.direccion_completa or "[DIRECCIÓN DEL ACTOR]"

    # ─── Periodo de pago ──────────────────────────────────────────────
    periodo_pago = 'mensuales'
    try:
        if hasattr(expediente, 'solicitud') and expediente.solicitud.periodo_pago:
            mapa = {'diario': 'diarios', 'semanal': 'semanales', 'quincenal': 'quincenales'}
            periodo_pago = mapa.get(expediente.solicitud.periodo_pago, 'mensuales')
    except Exception:
        pass

    # ─── Fechas ───────────────────────────────────────────────────────
    fecha_ingreso = _fecha_espanol(cliente.fecha_ingreso) if cliente.fecha_ingreso else "[FECHA DE INGRESO]"
    fecha_despido = _fecha_espanol(cliente.fecha_salida) if cliente.fecha_salida else "[FECHA DE DESPIDO]"
    fecha_tramite = _fecha_espanol(expediente.fecha_tramite) if expediente.fecha_tramite else "[FECHA DE TRÁMITE]"
    fecha_audiencia = _fecha_espanol(expediente.fecha_audiencia) if expediente.fecha_audiencia else "[FECHA DE AUDIENCIA]"

    # ─── Construir diccionario ────────────────────────────────────────
    marcadores = {
        # Datos del cliente (formato largo)
        # Nota: los campos sin fallback usan placeholders para que NUNCA llegue
        # None al reemplazo (str.replace() crashea con None → TypeError) y el
        # documento muestre qué dato falta en lugar de un espacio en blanco.
        'nombre_cliente': cliente.nombre or '[NOMBRE]',
        'curp_cliente': cliente.curp or '[CURP]',
        'rfc_cliente': cliente.rfc or '[RFC]',
        'telefono_cliente': cliente.telefono or '[TELÉFONO]',
        'email_cliente': cliente.email or '[EMAIL]',
        'direccion_cliente': direccion_cliente,
        'puesto_trabajador': cliente.puesto or '[PUESTO]',
        'salario_mensual': salario_mensual,
        'salario_diario': salario_diario,
        'periodo_pago': periodo_pago,
        'fecha_ingreso': fecha_ingreso,
        'fecha_despido': fecha_despido,
        'fecha': fecha_despido,
        'fecha_tramite': fecha_tramite,
        'fecha_audiencia': fecha_audiencia,
        'numero_expediente': expediente.numero,
        'folio_conciliacion': expediente.folio or '[FOLIO]',
        'monto_total': monto_total,
        'monto_reclamado': f"${expediente.monto_reclamado:,.2f}" if expediente.monto_reclamado else '[MONTO]',
        'monto_convenio': f"${expediente.monto_convenio:,.2f}" if expediente.monto_convenio else '[MONTO]',
        'asesor_asignado': asesor,
        'hoy': hoy_str,
        'mes_actual': mes_actual,
        'anio_actual': anio_actual,

        # Empresa / Demandado
        'nombre_empresa': cliente.empresa_razon_social or cliente.empresa or '[EMPRESA]',
        'razon_social': cliente.empresa_razon_social or cliente.empresa or '[EMPRESA]',
        'direccion_empresa': direccion_empresa,
        'empresa_actividad': cliente.empresa_actividad or '[ACTIVIDAD]',
        'empresa_telefono': cliente.empresa_telefono or '[TELÉFONO EMPRESA]',
        'empresa_rfc': cliente.empresa_rfc or cliente.rfc or '[RFC EMPRESA]',
        'nombre_representante': '[REPRESENTANTE LEGAL]',
        'cargo_representante': '[CARGO DEL REPRESENTANTE]',

        # Alias cortos (para compatibilidad con machotes importados)
        'salario': salario_mensual,
        'curp': cliente.curp or '[CURP]',
        'rfc': cliente.rfc or '[RFC]',
        'telefono': cliente.telefono or '[TELÉFONO]',
        'email': cliente.email or '[EMAIL]',
        'direccion': direccion_cliente,
        'puesto': cliente.puesto or '[PUESTO]',
        'empresa': cliente.empresa_razon_social or cliente.empresa or '[EMPRESA]',
        'asesor': asesor,

        # Prestaciones individuales
        'aguinaldo': aguinaldo_val,
        'vacaciones': vacaciones_val,
        'dias_vacaciones': dias_vacaciones,
        'prima_vacacional': prima_vacacional_val,
        'prima_antiguedad': prima_antiguedad_val,
        'tope_aplicado': tope_aplicado,
        'indemnizacion': indemnizacion_val,
        'dias_trabajados': dias_trabajados,

        # Tipo de despido
        'tipo_despido': expediente.get_tipo_despido_display() if expediente.tipo_despido else '[TIPO DE DESPIDO]',
    }

    return marcadores


# ─── Reemplazo de marcadores en HTML ──────────────────────────────────────

def reemplazar_marcadores(html: str, expediente: Expediente,
                           calculo: Dict[str, Any] | None = None) -> str:
    """
    Reemplaza todos los marcadores {{ variable }} en el HTML
    con los datos reales del expediente y cliente.

    Args:
        html: Contenido HTML con marcadores {{ nombre }}
        expediente: Instancia de Expediente
        calculo: Dict opcional de cálculo pre-computado

    Returns:
        str: HTML con todos los marcadores reemplazados
    """
    marcadores = get_marcadores(expediente, calculo)

    # Guarda defensiva: aunque un marcador llegue como None (cliente con datos
    # incompletos), se reemplaza por cadena vacía en vez de crashear con
    # TypeError (str.replace() no acepta None).
    for key, value in marcadores.items():
        valor = value if value is not None else ''
        html = html.replace('{{ ' + key + ' }}', valor)
        html = html.replace('{{' + key + '}}', valor)

    return html


# ─── Metadata de datos faltantes ───────────────────────────────────────────

def get_datos_faltantes(expediente: Expediente,
                         calculo: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    """
    Analiza qué datos del expediente/cliente están incompletos
    y retorna una lista con metadata de cada campo faltante.

    Cada item contiene:
        - key: nombre del marcador
        - label: nombre legible del campo
        - section: sección a la que pertenece
        - status: 'completo', 'incompleto', o 'pendiente'
        - value: valor actual (o None si falta)
        - edit_url: URL para editar este campo

    Args:
        expediente: Instancia de Expediente
        calculo: Dict opcional de cálculo pre-computado

    Returns:
        List[Dict]: Lista de campos con su estado
    """
    cliente = expediente.cliente
    campos = []

    # ─── Campos del cliente ───────────────────────────────────────────
    campos.extend([
        {
            'key': 'nombre_cliente',
            'label': 'Nombre completo del cliente',
            'section': 'Cliente',
            'status': 'completo' if cliente.nombre else 'incompleto',
            'value': cliente.nombre,
            'edit_url': f'/clientes/{cliente.pk}/editar/',
        },
        {
            'key': 'curp_cliente',
            'label': 'CURP',
            'section': 'Cliente',
            'status': 'completo' if len(cliente.curp or '') >= 15 else 'incompleto',
            'value': cliente.curp,
            'edit_url': f'/clientes/{cliente.pk}/editar/',
        },
        {
            'key': 'direccion_cliente',
            'label': 'Dirección del cliente',
            'section': 'Cliente',
            'status': 'completo' if cliente.direccion_completa else 'incompleto',
            'value': cliente.direccion_completa,
            'edit_url': f'/clientes/{cliente.pk}/editar/',
        },
        # ─── Empleo ───────────────────────────────────────────────────
        {
            'key': 'puesto_trabajador',
            'label': 'Puesto desempeñado',
            'section': 'Empleo',
            'status': 'completo' if cliente.puesto else 'incompleto',
            'value': cliente.puesto,
            'edit_url': f'/clientes/{cliente.pk}/editar/',
        },
        {
            'key': 'salario_mensual',
            'label': 'Salario mensual',
            'section': 'Empleo',
            'status': 'completo' if cliente.salario and cliente.salario > 0 else 'incompleto',
            'value': f"${cliente.salario:,.2f}" if cliente.salario else None,
            'edit_url': f'/clientes/{cliente.pk}/editar/',
        },
        {
            'key': 'fecha_ingreso',
            'label': 'Fecha de ingreso',
            'section': 'Empleo',
            'status': 'completo' if cliente.fecha_ingreso else 'incompleto',
            'value': cliente.fecha_ingreso,
            'edit_url': f'/clientes/{cliente.pk}/editar/',
        },
        {
            'key': 'fecha_salida',
            'label': 'Fecha de salida / despido',
            'section': 'Empleo',
            'status': 'completo' if cliente.fecha_salida else 'incompleto',
            'value': cliente.fecha_salida,
            'edit_url': f'/clientes/{cliente.pk}/editar/',
        },
        # ─── Empresa ──────────────────────────────────────────────────
        {
            'key': 'nombre_empresa',
            'label': 'Nombre / Razón social de la empresa',
            'section': 'Empresa',
            'status': 'completo' if (cliente.empresa_razon_social or cliente.empresa) else 'incompleto',
            'value': cliente.empresa_razon_social or cliente.empresa,
            'edit_url': f'/clientes/{cliente.pk}/editar/',
        },
        {
            'key': 'direccion_empresa',
            'label': 'Dirección de la empresa',
            'section': 'Empresa',
            'status': 'completo' if cliente.empresa_calle else 'incompleto',
            'value': None,
            'edit_url': f'/clientes/{cliente.pk}/editar/',
        },
        # ─── Expediente ───────────────────────────────────────────────
        {
            'key': 'folio_conciliacion',
            'label': 'Folio de conciliación',
            'section': 'Expediente',
            'status': 'completo' if expediente.folio else 'incompleto',
            'value': expediente.folio,
            'edit_url': f'/expedientes/{expediente.pk}/editar/',
        },
        {
            'key': 'monto_reclamado',
            'label': 'Monto reclamado',
            'section': 'Expediente',
            'status': 'completo' if expediente.monto_reclamado and expediente.monto_reclamado > 0 else 'incompleto',
            'value': f"${expediente.monto_reclamado:,.2f}" if expediente.monto_reclamado else None,
            'edit_url': f'/expedientes/{expediente.pk}/editar/',
        },
        {
            'key': 'tipo_despido',
            'label': 'Tipo de despido',
            'section': 'Expediente',
            'status': 'completo' if expediente.tipo_despido else 'incompleto',
            'value': expediente.get_tipo_despido_display() if expediente.tipo_despido else None,
            'edit_url': f'/expedientes/{expediente.pk}/editar/',
        },
    ])

    # Ordenar por sección para que {% regroup %} en templates funcione correctamente
    orden_secciones = {'Cliente': 0, 'Empleo': 1, 'Empresa': 2, 'Expediente': 3}
    campos.sort(key=lambda c: (orden_secciones.get(c['section'], 99), c['key']))
    return campos


# ─── Contadores de completitud ────────────────────────────────────────────

def get_completitud_stats(campos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calcula estadísticas de completitud a partir de la lista de campos.

    Returns:
        Dict con: total, completos, incompletos, porcentaje, por_seccion
    """
    total = len(campos)
    completos = sum(1 for c in campos if c['status'] == 'completo')
    incompletos = total - completos
    porcentaje = round((completos / total * 100)) if total > 0 else 0

    # Por sección
    secciones = {}
    for c in campos:
        sec = c['section']
        if sec not in secciones:
            secciones[sec] = {'total': 0, 'completos': 0}
        secciones[sec]['total'] += 1
        if c['status'] == 'completo':
            secciones[sec]['completos'] += 1

    return {
        'total': total,
        'completos': completos,
        'incompletos': incompletos,
        'porcentaje': porcentaje,
        'por_seccion': secciones,
    }
