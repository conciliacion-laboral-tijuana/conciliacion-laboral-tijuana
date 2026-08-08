"""
Calculadoras / Orquestadores para Cálculos Laborales
=====================================================

Combina:
  - Datos del expediente (fechas, salario, periodo de pago)
  - Reglas legales (tabla vacaciones, UMA, topes)
  - Fórmulas puras (formulas.py)

Devuelve diccionarios listos para mostrar en la UI o guardar en CalculoLaboral.

Autor: Conciliacion Laboral Tijuana - Motor Jurídico Parametrizable
"""

from decimal import Decimal
from datetime import date
from typing import Optional, Dict, Any, List, Callable

from . import formulas as f
from . import rules as r


# ─── Estructura de conceptos ────────────────────────────────────────────

CONCEPTOS_DISPONIBLES = [
    {
        'key': 'aguinaldo',
        'label': 'Aguinaldo Proporcional',
        'icono': '🎄',
        'articulo': 'Art. 87 LFT',
        'tipo': 'auto',
        'incluir_por_defecto': True,
    },
    {
        'key': 'vacaciones',
        'label': 'Vacaciones Proporcionales',
        'icono': '🏖️',
        'articulo': 'Art. 76 LFT',
        'tipo': 'auto',
        'incluir_por_defecto': True,
    },
    {
        'key': 'prima_vacacional',
        'label': 'Prima Vacacional',
        'icono': '✈️',
        'articulo': 'Art. 80 LFT',
        'tipo': 'auto',
        'incluir_por_defecto': True,
    },
    {
        'key': 'prima_antiguedad',
        'label': 'Prima de Antigüedad',
        'icono': '📜',
        'articulo': 'Art. 162 LFT',
        'tipo': 'auto',
        'incluir_por_defecto': True,
    },
    {
        'key': 'indemnizacion',
        'label': 'Indemnización Constitucional (90 días)',
        'icono': '⚖️',
        'articulo': 'Art. 50 LFT',
        'tipo': 'auto',
        'incluir_por_defecto': True,
    },
    {
        'key': 'indemnizacion_20dias',
        'label': 'Indemnización 20 días por año',
        'icono': '📆',
        'articulo': 'Art. 50 Frac. II LFT',
        'tipo': 'auto',
        'incluir_por_defecto': False,
    },
    {
        'key': 'vacaciones_vencidas',
        'label': 'Vacaciones Vencidas',
        'icono': '🗓️',
        'articulo': 'Art. 76 LFT',
        'tipo': 'semi_auto',
        'campo_input': 'dias_vacaciones_vencidos',
        'incluir_por_defecto': False,
    },
    {
        'key': 'horas_extras',
        'label': 'Horas Extras',
        'icono': '⏰',
        'articulo': 'Art. 66-68 LFT',
        'tipo': 'semi_auto',
        'campo_input': 'horas_extra_cantidad',
        'incluir_por_defecto': False,
    },
    {
        'key': 'salarios_devengados',
        'label': 'Salarios Devengados',
        'icono': '💰',
        'articulo': 'Art. 48 LFT',
        'tipo': 'manual',
        'campo_input': 'salarios_devengados',
        'incluir_por_defecto': False,
    },
    {
        'key': 'dias_festivos',
        'label': 'Días Festivos',
        'icono': '🎉',
        'articulo': 'Art. 75 LFT',
        'tipo': 'semi_auto',
        'campo_input': 'dias_festivos_cantidad',
        'incluir_por_defecto': False,
    },
]


def calcular_todo(
    fecha_ingreso: date,
    fecha_salida: date,
    salario: Decimal,
    periodo_pago: str = 'mensual',
    umas: Optional[Dict[str, Decimal]] = None,
    conceptos_seleccionados: Optional[Dict[str, bool]] = None,
    datos_extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Calcula las prestaciones laborales.

    Args:
        fecha_ingreso: Fecha de inicio de la relación laboral
        fecha_salida: Fecha de término / despido
        salario: Salario base (en el periodo indicado)
        periodo_pago: 'mensual', 'quincenal', 'semanal', 'diario'
        umas: Diccionario opcional con valores de UMA, salario_minimo, etc.
        conceptos_seleccionados: Dict con booleanos para cada concepto.
            ej: {'incluir_aguinaldo': True, 'incluir_vacaciones': False, ...}
        datos_extra: Dict con datos extra para conceptos semi-automáticos.
            ej: {'dias_vacaciones_vencidos': 14, 'horas_extra_cantidad': 20, 'dias_festivos_cantidad': 3}

    Returns:
        Dict con todos los cálculos
    """
    # ─── Preparar datos base ───────────────────────────────────────────
    sd = f.salario_diario(salario, periodo_pago)
    dias = f.dias_entre(fecha_ingreso, fecha_salida)
    años = f.años_completos(fecha_ingreso, fecha_salida)
    años_enteros = int(años)

    if dias <= 0 or sd <= 0:
        return _resultado_vacio("Fechas inválidas o salario no especificado")

    # Conceptos por defecto: todos activos
    if conceptos_seleccionados is None:
        conceptos_seleccionados = {}
    if datos_extra is None:
        datos_extra = {}

    tope = r.ReglasPorDefecto.obtener_tope_salarial()
    aguinaldo_dias = r.ReglasPorDefecto.AGUINALDO_DIAS

    def _incluye(key):
        return conceptos_seleccionados.get(f'incluir_{key}', True)

    # ─── 1. Aguinaldo Proporcional ─────────────────────────────────────
    if _incluye('aguinaldo'):
        aguinaldo = f.aguinaldo_proporcional(dias, sd, aguinaldo_dias)
    else:
        aguinaldo = Decimal('0')

    # ─── 2. Vacaciones Proporcionales ──────────────────────────────────
    dias_vacaciones = r.obtener_dias_vacaciones(años_enteros)
    if años_enteros < 1:
        dias_vacaciones_proporcional = max(0, int(dias / 365 * 12))
        dias_vacaciones_calculados = dias_vacaciones_proporcional
        vac_monto = f.vacaciones_proporcionales(dias, dias_vacaciones_proporcional, sd)
    else:
        dias_vacaciones_calculados = dias_vacaciones
        vac_monto = f.vacaciones_proporcionales(dias, dias_vacaciones, sd)

    # Override manual: el caso no siempre corresponde al total por antigüedad
    # (ej. ya se pagaron o disfrutaron algunos años de vacaciones).
    vacaciones_override_aplicado = False
    dias_vacaciones_override = datos_extra.get('dias_vacaciones_override')
    if dias_vacaciones_override not in (None, ''):
        dias_vacaciones_calculados = int(dias_vacaciones_override)
        vac_monto = f.vacaciones_vencidas(dias_vacaciones_calculados, sd)
        vacaciones_override_aplicado = True

    if not _incluye('vacaciones'):
        vac_monto = Decimal('0')

    # ─── 3. Prima Vacacional ───────────────────────────────────────────
    if _incluye('prima_vacacional'):
        prima_vac = f.prima_vacacional(vac_monto, r.ReglasPorDefecto.PRIMA_VACACIONAL_PORCENTAJE)
    else:
        prima_vac = Decimal('0')

    # ─── 4. Prima de Antigüedad ────────────────────────────────────────
    tope_aplicado = sd > tope
    if _incluye('prima_antiguedad'):
        prima_ant = f.prima_antiguedad(años, sd, r.ReglasPorDefecto.PRIMA_ANTIGUEDAD_DIAS_POR_ANO, tope)
    else:
        prima_ant = Decimal('0')
        tope_aplicado = False

    # ─── 5. Indemnización Constitucional (90 días) ─────────────────────
    if _incluye('indemnizacion'):
        indemnizacion = f.indemnizacion_constitucional(sd)
    else:
        indemnizacion = Decimal('0')

    # ─── 6. Indemnización 20 días por año ──────────────────────────────
    if _incluye('indemnizacion_20dias'):
        indemnizacion_20 = f.indemnizacion_20dias_por_ano(años, sd, tope)
    else:
        indemnizacion_20 = Decimal('0')

    # ─── 7. Vacaciones Vencidas ────────────────────────────────────────
    if _incluye('vacaciones_vencidas'):
        dias_vv = int(datos_extra.get('dias_vacaciones_vencidos', 0))
        vac_vencidas = f.vacaciones_vencidas(dias_vv, sd)
    else:
        dias_vv = 0
        vac_vencidas = Decimal('0')

    # ─── 8. Horas Extras ───────────────────────────────────────────────
    if _incluye('horas_extras'):
        hrs_extra = Decimal(str(datos_extra.get('horas_extra_cantidad', 0)))
        hrsextra = f.horas_extras(hrs_extra, sd)
    else:
        hrs_extra = Decimal('0')
        hrsextra = Decimal('0')

    # ─── 9. Salarios Devengados ────────────────────────────────────────
    if _incluye('salarios_devengados'):
        sal_dev = Decimal(str(datos_extra.get('salarios_devengados', 0)))
    else:
        sal_dev = Decimal('0')

    # ─── 10. Días Festivos ─────────────────────────────────────────────
    if _incluye('dias_festivos'):
        dias_fest = int(datos_extra.get('dias_festivos_cantidad', 0))
        festivos = f.dias_festivos(dias_fest, sd)
    else:
        dias_fest = 0
        festivos = Decimal('0')

    # ─── Total ───────────────────────────────────────────────────────
    total = f.total_prestaciones(
        aguinaldo, vac_monto, prima_vac, prima_ant,
        indemnizacion, indemnizacion_20, vac_vencidas,
        hrsextra, sal_dev, festivos
    )

    return {
        'success': True,
        'salario_diario': sd,
        'dias_trabajados': dias,
        'años_trabajados': años,
        'años_enteros': años_enteros,
        'periodo_pago': periodo_pago,
        'aguinaldo': {'dias_ley': aguinaldo_dias, 'monto': aguinaldo},
        'vacaciones': {
            'dias_segun_antiguedad': dias_vacaciones_calculados,
            'dias_tabla_ley': dias_vacaciones,
            'override_aplicado': vacaciones_override_aplicado,
            'monto': vac_monto,
        },
        'prima_vacacional': {'porcentaje': float(r.ReglasPorDefecto.PRIMA_VACACIONAL_PORCENTAJE * 100), 'monto': prima_vac},
        'prima_antiguedad': {
            'dias_por_año': r.ReglasPorDefecto.PRIMA_ANTIGUEDAD_DIAS_POR_ANO,
            'tope_diario': tope,
            'tope_aplicado': tope_aplicado,
            'monto': prima_ant,
        },
        'indemnizacion': {'dias': r.ReglasPorDefecto.INDEMNIZACION_DIAS, 'monto': indemnizacion},
        'indemnizacion_20dias': {'monto': indemnizacion_20},
        'vacaciones_vencidas': {'dias': dias_vv, 'monto': vac_vencidas},
        'horas_extras': {'cantidad': hrs_extra, 'monto': hrsextra},
        'salarios_devengados': {'monto': sal_dev},
        'dias_festivos': {'dias': dias_fest, 'monto': festivos},
        'total': total,
        'detalles': {
            'fecha_ingreso': fecha_ingreso.isoformat(),
            'fecha_salida': fecha_salida.isoformat(),
            'salario_mensual': salario,
            'uma_diaria': r.ReglasPorDefecto.UMA_DIARIA,
        },
    }


def simular(
    salario: Decimal,
    fecha_ingreso: date,
    fecha_salida: date,
    periodo_pago: str = 'mensual',
) -> Dict[str, Any]:
    """
    Simulación rápida para el asesor.
    Calcula todos los conceptos automáticos y muestra el desglose completo.
    """
    resultado = calcular_todo(fecha_ingreso, fecha_salida, salario, periodo_pago)
    if not resultado['success']:
        return resultado

    return {
        'success': True,
        'salario_diario': resultado['salario_diario'],
        'dias_trabajados': resultado['dias_trabajados'],
        'años_trabajados': resultado['años_trabajados'],
        'total': resultado['total'],
        'desglose': {
            'aguinaldo': resultado['aguinaldo']['monto'],
            'vacaciones': resultado['vacaciones']['monto'],
            'prima_vacacional': resultado['prima_vacacional']['monto'],
            'prima_antiguedad': resultado['prima_antiguedad']['monto'],
            'indemnizacion': resultado['indemnizacion']['monto'],
            'indemnizacion_20dias': resultado['indemnizacion_20dias']['monto'],
            'vacaciones_vencidas': resultado['vacaciones_vencidas']['monto'],
            'horas_extras': resultado['horas_extras']['monto'],
            'salarios_devengados': resultado['salarios_devengados']['monto'],
            'dias_festivos': resultado['dias_festivos']['monto'],
        },
    }


def _resultado_vacio(razon: str = "") -> Dict[str, Any]:
    """Retorna un dict de error."""
    return {
        'success': False,
        'error': razon,
        'salario_diario': Decimal('0'),
        'dias_trabajados': 0,
        'años_trabajados': Decimal('0'),
        'aguinaldo': {'dias_ley': 15, 'monto': Decimal('0')},
        'vacaciones': {'dias_segun_antiguedad': 0, 'dias_tabla_ley': 0, 'override_aplicado': False, 'monto': Decimal('0')},
        'prima_vacacional': {'porcentaje': 25, 'monto': Decimal('0')},
        'prima_antiguedad': {'dias_por_año': 12, 'tope_diario': Decimal('0'), 'tope_aplicado': False, 'monto': Decimal('0')},
        'indemnizacion': {'dias': 90, 'monto': Decimal('0')},
        'indemnizacion_20dias': {'monto': Decimal('0')},
        'vacaciones_vencidas': {'dias': 0, 'monto': Decimal('0')},
        'horas_extras': {'cantidad': Decimal('0'), 'monto': Decimal('0')},
        'salarios_devengados': {'monto': Decimal('0')},
        'dias_festivos': {'dias': 0, 'monto': Decimal('0')},
        'total': Decimal('0'),
        'detalles': {},
    }
