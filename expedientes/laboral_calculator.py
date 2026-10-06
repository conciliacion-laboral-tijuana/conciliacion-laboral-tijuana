"""
Puente entre modelos Django y el Motor Jurídico de Cálculos Laborales
=====================================================================

Conecta los datos de CalculoLaboral / Cliente con core/laboral/calculators.py
y core/laboral/rules.py.

Aquí es donde el expediente cobra vida jurídica:
  - El expediente aporta el periodo (fechas) y la zona salarial.
  - `LegalConfig` aporta las reglas (UMA, salary mínimo, topes, jornada).
  - `CalculoLaboral` aporta las capturas que no se pueden calcular (horas extra
    por tipo, días festivos, salary integrado declarado, etc.).

Autor: Conciliacion Laboral Tijuana
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.utils import timezone

from core.laboral import calculators
from core.laboral.calculators import CONCEPTOS_DISPONIBLES

CONCEPTOS_CALCULO = [c['key'] for c in CONCEPTOS_DISPONIBLES]


# ─── Reglas legales ──────────────────────────────────────────────────────

def reglas_activas() -> Any:
    """`ReglasLegales` derivadas de la LegalConfig activa.

    Si el despacho aún no ha configurado nada, se usan las reglas vigentes por
    defecto (LFT 2026 / CONASAMI 2026) sin tocar la base de datos.
    """
    from core.laboral.rules import ReglasLegales

    try:
        from .models import LegalConfig

        config = LegalConfig.get_active()
    except Exception:
        config = None

    if config is None:
        return ReglasLegales.por_defecto()
    return config.to_reglas()


def _conceptos_por_defecto() -> Dict[str, bool]:
    """Selección de conceptos por defecto del sistema.

    Usa los valores `incluir_por_defecto` de CONCEPTOS_DISPONIBLES
    (los 5 conceptos base activos; los adicionales desactivados),
    en lugar de incluir TODOS los conceptos automáticamente.
    Así la demanda/total coincide con lo que muestra la pantalla
    de Cálculo Laboral y con la suma de los renglones del documento.
    """
    return calculators.conceptos_base()


def conceptos_por_tipo_despido(tipo_despido: Optional[str], años_completos: int = 0,
                               base: Optional[Dict[str, bool]] = None) -> Dict[str, bool]:
    """Conceptos base + lo que la ley impone según la causa de separación.

    Delegado en `core.laboral.rules` (arts. 50 y 162 LFT) para que la pantalla,
    el recálculo y la demanda apliquen EXACTAMENTE la misma regla.
    """
    return calculators.conceptos_para_tipo(
        tipo_despido, años_completos,
        base=base if base is not None else _conceptos_por_defecto(),
    )


# ─── Cálculo ─────────────────────────────────────────────────────────────

def calcular_desde_expediente(
    expediente,
    conceptos_seleccionados: Optional[Dict[str, bool]] = None,
    datos_extra: Optional[Dict[str, Any]] = None,
    tipo_despido: Optional[str] = None,
    accion_preferida: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ejecuta el cálculo completo usando los datos del expediente y su cliente.

    Args:
        expediente: Instancia del modelo Expediente
        conceptos_seleccionados: Dict con booleanos para incluir/excluir conceptos.
            Si es None, se usan los conceptos base del sistema (los 5 por defecto
            de CONCEPTOS_DISPONIBLES) con las restricciones legales del tipo de
            separación, NO todos los conceptos.
        datos_extra: Dict con datos extra (días vencidos, horas extra, etc.)
        tipo_despido: Causa de separación. Si es None se toma la del expediente.
        accion_preferida: Elección del art. 48 LFT. Si es None se toma la del
            cliente ('indemnizacion' o 'reinstalacion').

    Returns:
        Dict con resultados de calcular_todo()
    """
    cliente = expediente.cliente

    fecha_ingreso = cliente.fecha_ingreso
    fecha_salida = cliente.fecha_salida
    salario = cliente.salario or Decimal('0')

    if not fecha_ingreso or not fecha_salida or salario <= 0:
        return calculators._resultado_vacio(
            "Completa los datos del cliente: fecha de ingreso, fecha de salida y salario"
        )

    # Periodo de pago
    periodo_pago = 'mensual'
    try:
        if hasattr(expediente, 'solicitud') and expediente.solicitud.periodo_pago:
            mapa = {'diario': 'diario', 'semanal': 'semanal', 'quincenal': 'quincenal'}
            periodo_pago = mapa.get(expediente.solicitud.periodo_pago, 'mensual')
    except Exception:
        pass

    tipo = tipo_despido or expediente.tipo_despido or 'injustificado'
    accion = accion_preferida or getattr(cliente, 'accion_preferida', None) or 'indemnizacion'

    if conceptos_seleccionados is None:
        años_completos = _años_completos(fecha_ingreso, fecha_salida)
        conceptos_seleccionados = conceptos_por_tipo_despido(tipo, años_completos)

    return calculators.calcular_todo(
        fecha_ingreso=fecha_ingreso,
        fecha_salida=fecha_salida,
        salario=salario,
        periodo_pago=periodo_pago,
        conceptos_seleccionados=conceptos_seleccionados,
        datos_extra=datos_extra,
        zona=cliente.zona_salarial or 'frontera',
        jornada=cliente.jornada or 'diurna',
        tipo_despido=tipo,
        accion_preferida=accion,
        reglas=reglas_activas(),
    )


def advertencias_accion(cliente) -> List[str]:
    """Avisos para el asesor sobre la acción preferida (arts. 48 y 49 LFT).

    Devuelve textos vacíos si la elección es coherente con el caso, para que la
    pantalla pueda avisar antes de generar la demanda.
    """
    from core.laboral.rules import ReglasLegales

    accion = getattr(cliente, 'accion_preferida', 'indemnizacion')
    if accion != 'reinstalacion':
        return []

    if not (cliente.fecha_ingreso and cliente.fecha_salida):
        return ['Se pidió la REINSTALACIÓN: completa las fechas para verificar si '
                'procede conforme al art. 49 fr. I LFT.']

    años = _años_completos(cliente.fecha_ingreso, cliente.fecha_salida)
    tipo = getattr(cliente, 'tipo_despido', '') or 'injustificado'
    resolucion = ReglasLegales.por_defecto().accion_posible(accion, años, tipo)

    return [] if resolucion['procede'] else [resolucion['motivo']]


def _años_completos(fecha_ingreso, fecha_salida) -> int:
    from core.laboral.periodo import construir_periodo

    periodo = construir_periodo(fecha_ingreso, fecha_salida)
    return periodo.años_completos if periodo else 0


def _aplicar_conceptos_excluidos(calculo_laboral, expediente=None) -> bool:
    """
    Fuerza desmarcados los conceptos que no proceden según el tipo de despido
    (art. 50 y art. 162 LFT), para que la pantalla de cálculo coincida con la
    demanda.

    Usa la misma regla del generador de demandas (`_conceptos_para_demanda`).
    Retorna True si algún concepto cambió de estado. NO guarda (el llamador
    hace save()).
    """
    if expediente is None:
        expediente = calculo_laboral.expediente
    # Import diferido para evitar import circular (demanda_generator importa
    # de este módulo a nivel de módulo).
    from .demanda_generator import _conceptos_para_demanda

    cliente = expediente.cliente
    años_completos = _años_completos(cliente.fecha_ingreso, cliente.fecha_salida)
    cambios = False
    for campo, incluir in _conceptos_para_demanda(
            expediente.tipo_despido or 'injustificado',
            años_completos=años_completos).items():
        if not incluir and getattr(calculo_laboral, campo, True):
            setattr(calculo_laboral, campo, False)
            cambios = True
    return cambios


# ─── Recálculo y persistencia ───────────────────────────────────────────

def datos_extra_de(calculo_laboral) -> Dict[str, Any]:
    """Captures del modelo → `datos_extra` de calcular_todo()."""
    return {
        # Salario integrado (arts. 84 y 89 LFT)
        'salario_integrado_cuota': calculo_laboral.salario_integrado_cuota_diaria or 0,
        'salario_integrado_gratificaciones': calculo_laboral.salario_integrado_gratificaciones or 0,
        'salario_integrado_ayudas': calculo_laboral.salario_integrado_ayudas or 0,
        'salario_integrado_pct': calculo_laboral.salario_integrado_porcentaje or 0,
        # Vacaciones
        'dias_vacaciones_vencidos': calculo_laboral.dias_vacaciones_vencidos or 0,
        'dias_vacaciones_override': calculo_laboral.dias_vacaciones_override,
        # Horas extras (arts. 66 y 68 LFT)
        'horas_extra_normales': _cero_si_vacio(calculo_laboral.horas_extra_normales),
        'horas_extra_excedentes': _cero_si_vacio(calculo_laboral.horas_extra_excedentes),
        'horas_extra_cantidad': float(calculo_laboral.horas_extra_cantidad or 0),
        # Montos declarados
        'salarios_devengados': float(calculo_laboral.salarios_devengados or 0),
        'dias_festivos_cantidad': calculo_laboral.dias_festivos_cantidad or 0,
        'dias_descanso_semanal_cantidad': calculo_laboral.dias_descanso_semanal_cantidad or 0,
    }


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
    conceptos = {
        f'incluir_{key}': getattr(calculo_laboral, f'incluir_{key}', True)
        for key in CONCEPTOS_CALCULO
    }

    resultado = calcular_desde_expediente(
        expediente,
        conceptos_seleccionados=conceptos,
        datos_extra=datos_extra_de(calculo_laboral),
    )

    if not resultado['success']:
        return

    cliente = expediente.cliente

    # Actualizar campos base
    calculo_laboral.salario_mensual = cliente.salario or Decimal('0')
    calculo_laboral.salario_diario = resultado['salario_diario']
    calculo_laboral.salario_diario_integrado = resultado['salario_diario_integrado']
    calculo_laboral.zona_salarial = resultado.get('zona') or calculo_laboral.zona_salarial
    calculo_laboral.fecha_ingreso = cliente.fecha_ingreso
    calculo_laboral.fecha_salida = cliente.fecha_salida
    calculo_laboral.dias_trabajados = resultado['dias_trabajados']
    calculo_laboral.años_trabajados = resultado['años_trabajados']

    # Actualizar resultados existentes
    calculo_laboral.aguinaldo = resultado['aguinaldo']['monto']
    calculo_laboral.vacaciones = resultado['vacaciones']['monto']
    calculo_laboral.dias_vacaciones = _int(resultado['vacaciones']['dias_segun_antiguedad'])
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
    if not calculo_laboral.pk or resultado['horas_extras']['dobles'] > 0:
        calculo_laboral.horas_extra_normales = resultado['horas_extras']['dobles']
    if not calculo_laboral.pk or resultado['horas_extras']['triples'] > 0:
        calculo_laboral.horas_extra_excedentes = resultado['horas_extras']['triples']
    calculo_laboral.salarios_devengados = resultado['salarios_devengados']['monto']
    calculo_laboral.dias_festivos = resultado['dias_festivos']['monto']
    if not calculo_laboral.pk or resultado['dias_festivos']['dias'] > 0:
        calculo_laboral.dias_festivos_cantidad = resultado['dias_festivos']['dias']
    calculo_laboral.descanso_semanal = resultado['descanso_semanal']['monto']
    if not calculo_laboral.pk or resultado['descanso_semanal']['dias'] > 0:
        calculo_laboral.dias_descanso_semanal_cantidad = resultado['descanso_semanal']['dias']

    calculo_laboral.total = resultado['total']
    calculo_laboral.recalculado_en = timezone.now()


def _cero_si_vacio(valor):
    """None → 0 para que el motor sepa que no hay desglose capturado."""
    return 0 if valor is None else valor


def _int(valor) -> int:
    try:
        return int(Decimal(str(valor)))
    except Exception:
        return 0