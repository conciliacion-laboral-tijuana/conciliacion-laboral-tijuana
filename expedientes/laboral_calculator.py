"""
Puente entre modelos Django y el Motor Jurídico de Cálculos Laborales
=====================================================================

Conecta los datos de CalculoLaboral / Cliente con core/laboral/calculators.py
y core/laboral/rules.py.

Autor: Conciliacion Laboral Tijuana
"""

from decimal import Decimal
from datetime import date
from typing import Dict, Any, Optional

from django.utils import timezone

from core.laboral import calculators, rules
from core.laboral.calculators import CONCEPTOS_DISPONIBLES


def _conceptos_por_defecto() -> Dict[str, bool]:
    """Selección de conceptos por defecto del sistema.

    Usa los valores `incluir_por_defecto` de CONCEPTOS_DISPONIBLES
    (los 5 conceptos base activos; los adicionales desactivados),
    en lugar de incluir TODOS los conceptos automáticamente.
    Así la demanda/total coincide con lo que muestra la pantalla
    de Cálculo Laboral y con la suma de los renglones del documento.
    """
    return {
        f'incluir_{c["key"]}': c.get('incluir_por_defecto', True)
        for c in CONCEPTOS_DISPONIBLES
    }


def calcular_desde_expediente(
    expediente,
    conceptos_seleccionados: Optional[Dict[str, bool]] = None,
    datos_extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Ejecuta el cálculo completo usando los datos del expediente y su cliente.

    Args:
        expediente: Instancia del modelo Expediente
        conceptos_seleccionados: Dict con booleanos para incluir/excluir conceptos.
            Si es None, usa los conceptos base del sistema (los 5 por defecto
            de CONCEPTOS_DISPONIBLES), NO todos los conceptos.
        datos_extra: Dict con datos extra (días vencidos, horas extra, etc.)

    Returns:
        Dict con resultados de calcular_todo()
    """
    cliente = expediente.cliente

    # Obtener datos base
    fecha_ingreso = cliente.fecha_ingreso
    fecha_salida = cliente.fecha_salida
    salario = cliente.salario or Decimal('0')

    # Conceptos por defecto del sistema (los 5 base) si no se indica otra selección
    if conceptos_seleccionados is None:
        conceptos_seleccionados = _conceptos_por_defecto()

    # Intentar obtener periodo de pago desde la solicitud de conciliación
    periodo_pago = 'mensual'
    try:
        if hasattr(expediente, 'solicitud') and expediente.solicitud.periodo_pago:
            mapa = {'diario': 'diario', 'semanal': 'semanal', 'quincenal': 'quincenal'}
            periodo_pago = mapa.get(expediente.solicitud.periodo_pago, 'mensual')
    except Exception:
        pass

    if not fecha_ingreso or not fecha_salida or salario <= 0:
        return calculators._resultado_vacio(
            "Completa los datos del cliente: fecha de ingreso, fecha de salida y salario"
        )

    return calculators.calcular_todo(
        fecha_ingreso=fecha_ingreso,
        fecha_salida=fecha_salida,
        salario=salario,
        periodo_pago=periodo_pago,
        conceptos_seleccionados=conceptos_seleccionados,
        datos_extra=datos_extra,
    )


def _aplicar_conceptos_excluidos(calculo_laboral, expediente=None) -> bool:
    """
    Fuerza desmarcados los conceptos que no proceden según el tipo de despido
    (renuncia voluntaria → sin indemnización constitucional ni prima de
    antigüedad), para que la pantalla de cálculo coincida con la demanda.

    Usa la misma regla del generador de demandas (_conceptos_para_demanda).
    Retorna True si algún concepto cambió de estado. NO guarda (el llamador
    hace save()).
    """
    if expediente is None:
        expediente = calculo_laboral.expediente
    # Import diferido para evitar import circular (demanda_generator importa
    # de este módulo a nivel de módulo).
    from .demanda_generator import _conceptos_para_demanda
    cambios = False
    for campo, incluir in _conceptos_para_demanda(
            expediente.tipo_despido or 'injustificado').items():
        if not incluir and getattr(calculo_laboral, campo, True):
            setattr(calculo_laboral, campo, False)
            cambios = True
    return cambios


def recalcular_calculo(calculo_laboral) -> None:
    """
    Recalcula y actualiza los campos de una instancia de CalculoLaboral.
    Respeta los conceptos seleccionados y datos extra guardados en la instancia.
    No guarda (el llamador debe hacer save()).

    Args:
        calculo_laboral: Instancia de CalculoLaboral
    """
    expediente = calculo_laboral.expediente

    # Leer selección de conceptos desde la instancia
    conceptos = {}
    for key in ['incluir_aguinaldo', 'incluir_vacaciones', 'incluir_prima_vacacional',
                 'incluir_prima_antiguedad', 'incluir_indemnizacion',
                 'incluir_indemnizacion_20dias', 'incluir_vacaciones_vencidas',
                 'incluir_horas_extras', 'incluir_salarios_devengados', 'incluir_dias_festivos']:
        conceptos[key] = getattr(calculo_laboral, key, True)

    datos_extra = {
        'dias_vacaciones_vencidos': calculo_laboral.dias_vacaciones_vencidos or 0,
        'horas_extra_cantidad': float(calculo_laboral.horas_extra_cantidad or 0),
        'salarios_devengados': float(calculo_laboral.salarios_devengados or 0),
        'dias_festivos_cantidad': calculo_laboral.dias_festivos_cantidad or 0,
        'dias_vacaciones_override': calculo_laboral.dias_vacaciones_override,
    }

    resultado = calcular_desde_expediente(
        expediente,
        conceptos_seleccionados=conceptos,
        datos_extra=datos_extra,
    )

    if not resultado['success']:
        return

    # Actualizar campos base
    calculo_laboral.salario_mensual = expediente.cliente.salario or Decimal('0')
    calculo_laboral.salario_diario = resultado['salario_diario']
    calculo_laboral.fecha_ingreso = expediente.cliente.fecha_ingreso
    calculo_laboral.fecha_salida = expediente.cliente.fecha_salida
    calculo_laboral.dias_trabajados = resultado['dias_trabajados']
    calculo_laboral.años_trabajados = resultado['años_trabajados']

    # Actualizar resultados existentes
    calculo_laboral.aguinaldo = resultado['aguinaldo']['monto']
    calculo_laboral.vacaciones = resultado['vacaciones']['monto']
    calculo_laboral.dias_vacaciones = resultado['vacaciones']['dias_segun_antiguedad']
    calculo_laboral.prima_vacacional = resultado['prima_vacacional']['monto']
    calculo_laboral.prima_antiguedad = resultado['prima_antiguedad']['monto']
    calculo_laboral.tope_salarial_aplicado = resultado['prima_antiguedad']['tope_aplicado']
    calculo_laboral.indemnizacion = resultado['indemnizacion']['monto']

    # Actualizar nuevos resultados
    calculo_laboral.indemnizacion_20dias = resultado['indemnizacion_20dias']['monto']
    calculo_laboral.vacaciones_vencidas = resultado['vacaciones_vencidas']['monto']
    # No sobrescribir datos de input si ya están guardados
    if not calculo_laboral.pk or resultado['vacaciones_vencidas']['dias'] > 0:
        calculo_laboral.dias_vacaciones_vencidos = resultado['vacaciones_vencidas']['dias']
    calculo_laboral.horas_extras = resultado['horas_extras']['monto']
    if not calculo_laboral.pk or resultado['horas_extras']['cantidad'] > 0:
        calculo_laboral.horas_extra_cantidad = resultado['horas_extras']['cantidad']
    calculo_laboral.salarios_devengados = resultado['salarios_devengados']['monto']
    calculo_laboral.dias_festivos = resultado['dias_festivos']['monto']
    if not calculo_laboral.pk or resultado['dias_festivos']['dias'] > 0:
        calculo_laboral.dias_festivos_cantidad = resultado['dias_festivos']['dias']

    calculo_laboral.total = resultado['total']
    calculo_laboral.recalculado_en = timezone.now()
