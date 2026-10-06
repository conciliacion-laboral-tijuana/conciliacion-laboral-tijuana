"""
Calculadoras / Orquestadores para Cálculos Laborales
=====================================================

Combina:
  - El periodo laboral descompuesto (core/laboral/periodo.py)
  - Las reglas legales (core/laboral/rules.py)
  - Fórmulas puras (core/laboral/formulas.py)
  - Los datos del expediente (fechas, salario, jornada, zona)

Devuelve diccionarios listos para mostrar en la UI o guardar en CalculoLaboral.

ARQUITECTURA: `calcular_todo()` mantiene su interfaz (mismos argumentos y mismas
claves de salida), pero ya NO adivina periodos a partir de dos fechas: primero
construye el `PeriodoLaboral` y cada fórmula recibe el periodo que su artículo
exige.

Autor: Conciliacion Laboral Tijuana - Motor Jurídico Parametrizable
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from . import formulas as f
from . import rules as r
from .periodo import construir_periodo


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
        'label': 'Vacaciones (causadas + proporcionales)',
        'icono': '🏖️',
        'articulo': 'Art. 76 y 81 LFT',
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
        'articulo': 'Art. 50 fr. III LFT',
        'tipo': 'auto',
        'incluir_por_defecto': True,
    },
    {
        'key': 'indemnizacion_20dias',
        'label': 'Indemnización 20 días por año',
        'icono': '📆',
        'articulo': 'Art. 50 fr. II LFT',
        'tipo': 'auto',
        'incluir_por_defecto': False,
    },
    {
        'key': 'vacaciones_vencidas',
        'label': 'Vacaciones de ciclos anteriores no disfrutadas',
        'icono': '🗓️',
        'articulo': 'Art. 79 y 81 LFT',
        'tipo': 'semi_auto',
        'campo_input': 'dias_vacaciones_vencidos',
        'incluir_por_defecto': False,
    },
    {
        'key': 'horas_extras',
        'label': 'Horas Extras (dobles y excedentes)',
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
        'label': 'Días Festivos laborados',
        'icono': '🎉',
        'articulo': 'Art. 74-75 LFT',
        'tipo': 'semi_auto',
        'campo_input': 'dias_festivos_cantidad',
        'incluir_por_defecto': False,
    },
    {
        'key': 'descanso_semanal',
        'label': 'Días de Descanso Semanal laborados',
        'icono': '🛏️',
        'articulo': 'Art. 69 y 73 LFT',
        'tipo': 'semi_auto',
        'campo_input': 'dias_descanso_semanal_cantidad',
        'incluir_por_defecto': False,
    },
]

# Conceptos que dependen de la causa de separación (arts. 50 y 162 LFT).
CONCEPTOS_INDEMPENDIZATORIOS = ('indemnizacion', 'indemnizacion_20dias', 'prima_antiguedad')


def conceptos_base() -> Dict[str, bool]:
    """Selección de conceptos por defecto del sistema (CONCEPTOS_DISPONIBLES).

    Son los 5 conceptos base; el resto arranca apagado aunque `calcular_todo()`
    los daría por incluidos si no se pasan explícitamente.  Sin esto, marcar
    `tipo_despido` encendería también conceptos que el despacho dejó vacíos.
    """
    return {
        f'incluir_{c["key"]}': c.get('incluir_por_defecto', True)
        for c in CONCEPTOS_DISPONIBLES
    }


def conceptos_para_tipo(tipo_despido: Optional[str], años_completos: int = 0,
                        base: Optional[Dict[str, bool]] = None,
                        reglas: Optional[r.ReglasLegales] = None) -> Dict[str, bool]:
    """Conceptos base + las restricciones legales por causa de separación.

    Los arts. 50 y 162 LFT sólo apagan o encienden los conceptos
    indemnizatorios; el resto de la selección del despacho se respeta.
    """
    if reglas is None:
        reglas = r.ReglasLegales.por_defecto()
    conceptos = dict(conceptos_base() if base is None else base)
    conceptos.update(reglas.restricciones_por_tipo(tipo_despido, años_completos))
    return conceptos


def calcular_todo(
    fecha_ingreso: date,
    fecha_salida: date,
    salario: Decimal,
    periodo_pago: str = 'mensual',
    umas: Optional[Dict[str, Decimal]] = None,
    conceptos_seleccionados: Optional[Dict[str, bool]] = None,
    datos_extra: Optional[Dict[str, Any]] = None,
    zona: str = r.ZONA_FRONTERA,
    jornada: str = 'diurna',
    tipo_despido: Optional[str] = None,
    accion_preferida: Optional[str] = None,
    reglas: Optional[r.ReglasLegales] = None,
) -> Dict[str, Any]:
    """
    Calcula las prestaciones laborales.

    Args:
        fecha_ingreso: Fecha de inicio de la relación laboral
        fecha_salida: Fecha de término / despido
        salario: Salario base (en el periodo indicado)
        periodo_pago: 'mensual', 'quincenal', 'semanal', 'diario'
        umas: Deprecated. Los valores legales se pasan por `reglas`.
        conceptos_seleccionados: Dict con booleanos `incluir_<concepto>`.
            Ej: {'incluir_aguinaldo': True, 'incluir_vacaciones': False}
        datos_extra: Datos no calculables automáticamente. Claves aceptadas:
            'salario_integrado'          → monto diario integrado (art. 84)
            'salario_integrado_pct'      → % de prestaciones integradas
            'salario_integrado_cuota'    → cuota diaria
            'salario_integrado_gratificaciones'
            'salario_integrado_ayudas'
            'salario_integrado_comisiones'
            'dias_vacaciones_vencidos'   → días de ciclos anteriores adeudados
            'dias_vacaciones_override'   → días totales a pagar (manual)
            'horas_extra_normales'       → horas al doble (art. 66)
            'horas_extra_excedentes'     → horas excedentes al triple (art. 68)
            'horas_extra_cantidad'       → total, se reparte con los topes
            'horas_extra_semanas'        → semanas para ese reparto
            'salarios_devengados'        → monto manual
            'dias_festivos_cantidad'     → días festivos laborados
            'dias_descanso_semanal_cantidad' → días de descanso semanal laborados
        zona: 'general' o 'frontera' (Zona Libre de la Frontera Norte).
        jornada: 'diurna', 'nocturna' o 'mixta' (art. 61 LFT).
        tipo_despido: 'injustificado', 'justificado', 'voluntario', 'rescision',
            'otro'. Si se indica y el llamador no pasó conceptos explícitos, se
            aplican las reglas de procedencia de los arts. 50 y 162 LFT.
        accion_preferida: Elección del trabajador conforme al art. 48 LFT:
            'indemnizacion' (3 meses de salario) o 'reinstalacion'.  Si
            procede la reinstalación, la indemnización de 3 meses se excluye del
            total; si no procede (art. 49 LFT o art. 46 LFT), el motor lo explica
            y mantiene la indemnización.
        reglas: ReglasLegales. Si es None, las vigentes por defecto.

    Returns:
        Dict con todos los cálculos
    """
# ─── 0. Reglas y datos base ───────────────────────────────────────
    if reglas is None:
        reglas = r.ReglasLegales.por_defecto()

    if datos_extra is None:
        datos_extra = {}

    sd = f.salario_diario(salario, periodo_pago)
    if sd <= 0:
        return _resultado_vacio("Salario no especificado")

    # ─── 1. Periodo laboral descompuesto ─────────────────────────────
    periodo = construir_periodo(fecha_ingreso, fecha_salida, reglas)
    if periodo is None:
        return _resultado_vacio("Fechas inválidas: la salida no puede ser anterior al ingreso")

    # La procedencia por tipo de separations necesita los años cumplidos
    # (art. 162: la renuncia voluntaria sólo genera prima a los 15 años).
    if conceptos_seleccionados is None:
        conceptos_seleccionados = conceptos_para_tipo(
            tipo_despido, periodo.años_completos, base=conceptos_base(), reglas=reglas)

    anio = fecha_salida.year
    horas_jornada = reglas.jornada_diaria_horas(jornada)

    def _incluye(key: str) -> bool:
        return conceptos_seleccionados.get(f'incluir_{key}', True)

    # ─── 2. Salario diario y salary integrado (arts. 84 y 89) ────────
    sdi = _salario_integrado(sd, datos_extra, reglas)

    # ─── 3. Aguinaldo proporcional del AÑO CALENDARIO (art. 87) ───────
    if _incluye('aguinaldo'):
        aguinaldo = f.aguinaldo_proporcional(
            periodo.dias_anio_actual,
            periodo.dias_anio_total,
            sd,
            reglas.aguinaldo_dias,
        )
    else:
        aguinaldo = Decimal('0')

    # ─── 4. Vacaciones: ciclos cumplidos + ciclo en curso (arts. 76-81) ─
    #
    # El derecho nace al cumplir cada año de servicios (art. 76) y debe
    # concederse dentro de los seis meses siguientes (art. 81).  Al terminar la
    # relación hay dos-components distintos y ambos se pagan:
    #
    #   a) CICLOS CUMPLIDOS: el derecho del último año completado, que a la
    #      fecha de terminación todavía no se ha cuchillo disfrutar.  Sin esto,
    #      quien se va justo en su aniversario no tendría vacaciones.
    #   b) CICLO EN CURSO: proporcional al tiempo cumplido del año en curso
    #      (no "años × 16 días", que es lo que hacía el motor anterior).
    #
    # Los ciclos ANTERIORES al último (más de un año adeudado) son el concepto
    # manual `vacaciones_vencidas`, que se suma aparte para no duplicar.
    ciclo = periodo.ciclo_vacaciones_vigente
    dias_vac_ciclo = int(ciclo.dias_correspondientes) if ciclo else 0
    dias_vac_proporcionales = ciclo.dias_proporcionales if ciclo else Decimal('0')
    fraccion_vac = ciclo.fraccion if ciclo else Decimal('0')

    ultimo_ciclo_completo = _ultimo_ciclo_completo(periodo)
    dias_causadas_calculados = (ultimo_ciclo_completo.dias_correspondientes
                                if ultimo_ciclo_completo else 0)
    ciclo_anterior = _ciclo_anterior(periodo)
    dias_causadas_extra_sugeridos = ciclo_anterior.dias_correspondientes if ciclo_anterior else 0

    # Override manual de días totales a pagar (el asesor conoce lo adeudado)
    override = _datos_int(datos_extra, 'dias_vacaciones_override', None)
    override_aplicado = override is not None

    if override_aplicado:
        dias_vac_causadas = 0
        dias_vac_proporcionales = Decimal(override)
        monto_causadas = Decimal('0')
        monto_proporcionales = f.vacaciones_proporcionales(override, Decimal('1'), sd)
        dias_vac_total = override
        dias_vac_ciclo = override
    elif not _incluye('vacaciones'):
        # Desmarcar "Vacaciones" apaga tanto los días causados como los
        # proporcionales: son la misma prestación (arts. 76 y 81 LFT).
        dias_vac_causadas = 0
        dias_vac_proporcionales = Decimal('0')
        monto_causadas = Decimal('0')
        monto_proporcionales = Decimal('0')
        dias_vac_total = 0
    else:
        # (a) ciclos cumplidos no disfrutados
        dias_vac_causadas = dias_causadas_calculados
        monto_causadas = f.vacaciones_vencidas(dias_vac_causadas, sd)
        # (b) proporcional del ciclo en curso
        monto_proporcionales = f.vacaciones_proporcionales(
            dias_vac_ciclo, fraccion_vac, sd
        )
        dias_vac_total = dias_vac_causadas + _redondea_dias(dias_vac_proporcionales)

    vac_monto = f.total_prestaciones(monto_causadas, monto_proporcionales)

    # Ciclos ANTERIORES al último, declarados por el asesor (concepto aparte)
    dias_vac_extra = _datos_int(datos_extra, 'dias_vacaciones_vencidos', 0) or 0
    if not _incluye('vacaciones_vencidas') or override_aplicado:
        dias_vac_extra = 0
    vac_extra = f.vacaciones_vencidas(dias_vac_extra, sd)

    # ─── 5. Prima vacacional (art. 80) ────────────────────────────────
    if _incluye('prima_vacacional'):
        prima_vac = f.prima_vacacional(vac_monto, reglas.prima_vacacional_porcentaje)
    else:
        prima_vac = Decimal('0')

    # ─── 6. Prima de antigüedad (arts. 162, 485, 486) ─────────────────
    # Base propia: salario diario con piso/techo del salary mínimo del ÁREA
    # (NO UMA).  Años de servicio completos con fracción.
    tope_antiguedad = reglas.tope_prima_antiguedad(zona)
    piso_antiguedad = reglas.piso_salario_indemnizaciones(zona)
    base_antiguedad, tope_aplicado = f.salario_base_con_tope(sdi, tope_antiguedad, piso_antiguedad)
    if _incluye('prima_antiguedad'):
        prima_ant = f.prima_antiguedad(
            periodo.años_servicio_decimal,
            sdi,
            reglas.prima_antiguedad_dias_por_ano,
            tope_antiguedad,
            piso_antiguedad,
        )
    else:
        prima_ant = Decimal('0')
        tope_aplicado = False

    # ─── 7. Indemnización constitucional (art. 50 fr. III) ────────────
    #
    # El art. 48 LFT da al trabajador una ELECCIÓN entre la reinstalación y la
    # indemnización de 3 meses: no son acumulables.  Si la acción elegida es la
    # reinstalación y procede, los 90 días salen del total.
    accion = reglas.accion_posible(
        accion_preferida, periodo.años_completos, tipo_despido)
    if _incluye('indemnizacion') and accion['indemnizacion_incluida']:
        indemnizacion = f.indemnizacion_constitucional(sdi, reglas.indemnizacion_dias)
    else:
        indemnizacion = Decimal('0')

    # ─── 8. Indemnización 20 días por año (art. 50 fr. II) ───────────
    if _incluye('indemnizacion_20dias'):
        años_indem = (periodo.años_servicio_decimal
                      if reglas.indemnizacion_20dias_incluye_fraccion
                      else Decimal(periodo.años_completos))
        indemnizacion_20 = f.indemnizacion_20dias_por_ano(
            años_indem,
            sdi,
            reglas.indemnizacion_20dias_dias_por_ano,
            reglas.indemnizacion_20dias_incluye_fraccion,
        )
    else:
        indemnizacion_20 = Decimal('0')

    # ─── 9. Horas extras (arts. 61, 66, 68) ───────────────────────────
    extras = _horas_extras(datos_extra, periodo, reglas, anio, sd, horas_jornada)
    if _incluye('horas_extras'):
        hrs_dobles, hrs_triples = extras['dobles'], extras['triples']
        hrsextra = f.horas_extras(hrs_dobles, hrs_triples, sd, horas_jornada)
    else:
        hrs_dobles, hrs_triples = Decimal('0'), Decimal('0')
        hrsextra = Decimal('0')

    # ─── 10. Salarios devengados (art. 48) ────────────────────────────
    if _incluye('salarios_devengados'):
        sal_dev = _datos_dec(datos_extra, 'salarios_devengados', Decimal('0'))
    else:
        sal_dev = Decimal('0')

    # ─── 11. Días festivos laborados (arts. 74 y 75) ─────────────────
    if _incluye('dias_festivos'):
        dias_fest = _datos_int(datos_extra, 'dias_festivos_cantidad', 0) or 0
        festivos = f.dias_festivos(dias_fest, sd, reglas.festivo_multiplicador)
    else:
        dias_fest = 0
        festivos = Decimal('0')

    # ─── 12. Días de descanso semanal laborados (arts. 69 y 73) ──────
    if _incluye('descanso_semanal'):
        dias_desc = _datos_int(datos_extra, 'dias_descanso_semanal_cantidad', 0) or 0
        descanso = f.descanso_semanal(dias_desc, sd, reglas.descanso_semanal_multiplicador)
    else:
        dias_desc = 0
        descanso = Decimal('0')

    # ─── Total ────────────────────────────────────────────────────────
    total = f.total_prestaciones(
        aguinaldo, vac_monto, vac_extra, prima_vac, prima_ant,
        indemnizacion, indemnizacion_20,
        hrsextra, sal_dev, festivos, descanso,
    )

    # El desglose que espera la interfaz: `vacaciones_vencidas` son ciclos
    # ANTERIORES al último año cumplido, así que se suman aparte y no se
    # duplican dentro de `vacaciones`.
    return {
        'success': True,
        # ── salaries ──
        'salario_diario': sd,
        'salario_diario_integrado': sdi,
        'salario_integrado_componentes': _componentes_salario_integrado(datos_extra),
        'periodo_pago': periodo_pago,
        'jornada': jornada,
        'zona': zona,

        # ── periodo laboral (descomposición temporal) ──
        'dias_trabajados': periodo.dias_relacion,
        'periodo_laboral': _periodo_dict(periodo),

        # Antigüedad: `años_trabajados` conserva el nombre histórico.
        'años_trabajados': periodo.años_servicio_decimal,
        'años_completos': periodo.años_completos,

        # ── conceptos ──
        'aguinaldo': {
            'dias_ley': reglas.aguinaldo_dias,
            'anio': periodo.anio_aguinaldo,
            'dias_trabajados': periodo.dias_anio_actual,
            'dias_del_anio': periodo.dias_anio_total,
            'fraccion_anio': _fraccion(periodo.dias_anio_actual, periodo.dias_anio_total),
            'monto': aguinaldo,
        },
        'vacaciones': {
            'dias_segun_antiguedad': dias_vac_total,
            'dias_tabla_ley': dias_vac_ciclo,
            'dias_anio_servicio': periodo.años_completos + 1,
            'dias_causadas_anteriores': dias_vac_causadas,
            'dias_causadas_calculadas': dias_causadas_calculados,
            'dias_ciclos_extra_sugeridos': dias_causadas_extra_sugeridos,
            'dias_proporcionales': _redondea_dias(dias_vac_proporcionales),
            'fraccion_ciclo': _fraccion(fraccion_vac, 1),
            'override_aplicado': override_aplicado,
            'monto_causadas': monto_causadas,
            'monto_proporcionales': monto_proporcionales,
            'monto': vac_monto,
        },
        'prima_vacacional': {
            'porcentaje': float(reglas.prima_vacacional_porcentaje * 100),
            'base': vac_monto,
            'monto': prima_vac,
        },
        'prima_antiguedad': {
            'dias_por_año': reglas.prima_antiguedad_dias_por_ano,
            'tope_diario': tope_antiguedad,
            'tope_tipo': 'salario_minimo_zona',
            'piso_diario': piso_antiguedad,
            'salario_base': base_antiguedad,
            'tope_aplicado': tope_aplicado,
            'años_servicio': periodo.años_servicio_decimal,
            'monto': prima_ant,
        },
        'indemnizacion': {
            'dias': reglas.indemnizacion_dias,
            'base': sdi,
            'monto': indemnizacion,
        },
        'accion': accion,
        'indemnizacion_20dias': {
            'dias_por_año': reglas.indemnizacion_20dias_dias_por_ano,
            'años_servicio': (periodo.años_servicio_decimal
                              if reglas.indemnizacion_20dias_incluye_fraccion
                              else Decimal(periodo.años_completos)),
            'base': sdi,
            'monto': indemnizacion_20,
        },
        'vacaciones_vencidas': {
            'dias': dias_vac_extra,
            'dias_sugeridos': dias_causadas_extra_sugeridos,
            'monto': vac_extra,
        },
        'horas_extras': {
            'cantidad': hrs_dobles + hrs_triples,
            'dobles': hrs_dobles,
            'triples': hrs_triples,
            'valor_hora': f.valor_hora(sd, horas_jornada),
            'horas_jornada': horas_jornada,
            'jornada_maxima_semanal': reglas.jornada_maxima_semanal(anio),
            'maximo_dobles_semana': reglas.horas_extra_dobles_max_semana(anio),
            'monto': hrsextra,
        },
        'salarios_devengados': {'monto': sal_dev},
        'dias_festivos': {
            'dias': dias_fest,
            'multiplicador': reglas.festivo_multiplicador,
            'monto': festivos,
        },
        'descanso_semanal': {
            'dias': dias_desc,
            'multiplicador': reglas.descanso_semanal_multiplicador,
            'dias_teoricos': f.dias_descanso_semanal_teoricos(
                periodo.dias_relacion, reglas.descanso_semanal_dias_cada),
            'monto': descanso,
        },
        'total': total,
        'detalles': {
            'fecha_ingreso': fecha_ingreso.isoformat(),
            'fecha_salida': fecha_salida.isoformat(),
            'salario_mensual': str(salario),
            'uma_diaria': reglas.uma_diaria,
            'salario_minimo_zona': reglas.salario_minimo_de(zona),
            'anio_normativo': anio,
            'tipo_despido': tipo_despido,
        },
    }


def _salario_integrado(sd: Decimal, datos_extra: Dict[str, Any],
                       reglas: r.ReglasLegales) -> Decimal:
    """Salario diario integrado para las indemnizaciones (arts. 84 y 89)."""
    monto = _datos_dec(datos_extra, 'salario_integrado', None)
    if monto is not None and monto > 0:
        # El asesor declaró el integrado completo: se respeta su piso.
        return max(sd, monto)

    componentes = _componentes_salario_integrado(datos_extra)
    pct = _datos_dec(datos_extra, 'salario_integrado_pct', None)
    if pct is None:
        pct = reglas.salario_integrado_porcentaje

    return f.salario_integrado(sd, componentes, reglas.salario_integrado_modo, pct)


def _componentes_salario_integrado(datos_extra: Dict[str, Any]) -> Dict[str, Decimal]:
    """Conceptos del art. 84 LFT declarados para el salario integrado."""
    return {
        'cuota_diaria': _datos_dec(datos_extra, 'salario_integrado_cuota', Decimal('0')),
        'gratificaciones': _datos_dec(datos_extra, 'salario_integrado_gratificaciones', Decimal('0')),
        'ayudas': _datos_dec(datos_extra, 'salario_integrado_ayudas', Decimal('0')),
        'comisiones': _datos_dec(datos_extra, 'salario_integrado_comisiones', Decimal('0')),
        'prestaciones_especie': _datos_dec(datos_extra, 'salario_integrado_especie', Decimal('0')),
    }


def _horas_extras(datos_extra: Dict[str, Any], periodo, reglas: r.ReglasLegales,
                  anio: int, sd: Decimal, horas_jornada) -> Dict[str, Decimal]:
    """Reparte las horas extra en dobles (art. 66) y excedentes (art. 68).

    Se acepta la captura estructurada (`horas_extra_normales` /
    `horas_extra_excedentes`) que es la forma correcta, y también el total
    histórico (`horas_extra_cantidad`), que se reparte contra los topes
    semanales del año en vez de aplicar un factor promedio de 2.5.
    """
    dobles = _datos_dec(datos_extra, 'horas_extra_normales', None)
    triples = _datos_dec(datos_extra, 'horas_extra_excedentes', None)

    if dobles is not None or triples is not None:
        return {'dobles': max(dobles or Decimal('0'), Decimal('0')),
                'triples': max(triples or Decimal('0'), Decimal('0'))}

    total = _datos_dec(datos_extra, 'horas_extra_cantidad', Decimal('0'))
    if total <= 0:
        return {'dobles': Decimal('0'), 'triples': Decimal('0')}

    semanas = _datos_dec(datos_extra, 'horas_extra_semanas', None)
    if semanas is None or semanas <= 0:
        # Sin semanas declaradas se asume el periodo completo de la relación.
        semanas = Decimal(periodo.dias_relacion) / Decimal('7')

    return dict(zip(('dobles', 'triples'), f.distribuir_horas_extra(
        total,
        semanas,
        reglas.horas_extra_dobles_max_semana(anio),
        r.HORAS_EXTRA_AL_TRIPLE_SEMANA_MAX,
    )))


def _ultimo_ciclo_completo(periodo):
    """Último ciclo de vacaciones ya cumplido (art. 76: derecho ya naciente)."""
    for ciclo in reversed(periodo.ciclos_vacaciones):
        if ciclo.completo:
            return ciclo
    return None


def _ciclo_anterior(periodo):
    """Ciclo cumplido previo al último (base del input manual de vacaciones)."""
    cumplidos = [c for c in periodo.ciclos_vacaciones if c.completo]
    return cumplidos[-2] if len(cumplidos) >= 2 else None


def _periodo_dict(periodo) -> Dict[str, Any]:
    """Descomposición temporal serializable (para UI y documentos)."""
    return {
        'fecha_ingreso': periodo.fecha_ingreso.isoformat(),
        'fecha_salida': periodo.fecha_salida.isoformat(),
        'dias_relacion': periodo.dias_relacion,
        'años_completos': periodo.años_completos,
        'años_servicio': periodo.años_servicio_decimal,
        'aniversario_vigente': periodo.aniversario_vigente.isoformat(),
        'proximo_aniversario': periodo.proximo_aniversario.isoformat(),
        'dias_ciclo_vigente': periodo.dias_ciclo_vigente,
        'dias_cumplidos_ciclo_vigente': periodo.dias_cumplidos_ciclo_vigente,
        'fraccion_ciclo_vigente': periodo.fraccion_ciclo_vigente,
        'anio_aguinaldo': periodo.anio_aguinaldo,
        'dias_anio_actual': periodo.dias_anio_actual,
        'dias_anio_total': periodo.dias_anio_total,
        'ciclos': [
            {
                'numero': c.numero,
                'inicio': c.inicio.isoformat(),
                'fin': c.fin.isoformat(),
                'dias_correspondientes': c.dias_correspondientes,
                'dias_trabajados': c.dias_trabajados,
                'dias_proporcionales': c.dias_proporcionales,
                'completo': c.completo,
            }
            for c in periodo.ciclos_vacaciones
        ],
    }


def simular(
    salario: Decimal,
    fecha_ingreso: date,
    fecha_salida: date,
    periodo_pago: str = 'mensual',
    zona: str = r.ZONA_FRONTERA,
    jornada: str = 'diurna',
    tipo_despido: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Simulación rápida para el asesor.
    Calcula los conceptos automáticos y muestra el desglose completo.
    """
    resultado = calcular_todo(
        fecha_ingreso, fecha_salida, salario, periodo_pago,
        zona=zona, jornada=jornada, tipo_despido=tipo_despido,
    )
    if not resultado['success']:
        return resultado

    return {
        'success': True,
        'salario_diario': resultado['salario_diario'],
        'salario_diario_integrado': resultado['salario_diario_integrado'],
        'dias_trabajados': resultado['dias_trabajados'],
        'años_trabajados': resultado['años_trabajados'],
        'total': resultado['total'],
        'desglose': {
            'aguinaldo': resultado['aguinaldo']['monto'],
            'vacaciones': resultado['vacaciones']['monto'],
            'vacaciones_vencidas': resultado['vacaciones_vencidas']['monto'],
            'prima_vacacional': resultado['prima_vacacional']['monto'],
            'prima_antiguedad': resultado['prima_antiguedad']['monto'],
            'indemnizacion': resultado['indemnizacion']['monto'],
            'indemnizacion_20dias': resultado['indemnizacion_20dias']['monto'],
            'horas_extras': resultado['horas_extras']['monto'],
            'salarios_devengados': resultado['salarios_devengados']['monto'],
            'dias_festivos': resultado['dias_festivos']['monto'],
            'descanso_semanal': resultado['descanso_semanal']['monto'],
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _datos_dec(datos: Dict[str, Any], clave: str, defecto):
    valor = datos.get(clave)
    if valor is None or valor == '':
        return defecto
    return Decimal(str(valor))


def _datos_int(datos: Dict[str, Any], clave: str, defecto):
    valor = datos.get(clave)
    if valor is None or valor == '':
        return defecto
    return int(Decimal(str(valor)))


def _redondea_dias(valor) -> Decimal:
    """Días con 2 decimales (medio día es la unidad práctica del finiquito)."""
    from decimal import ROUND_HALF_UP
    return Decimal(str(valor)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _fraccion(numerador, denominador) -> Decimal:
    """Fracción 0-1 cuantizada a 4 decimales."""
    from decimal import ROUND_HALF_UP
    den = Decimal(str(denominador))
    if den <= 0:
        return Decimal('0')
    return (Decimal(str(numerador)) / den).quantize(
        Decimal('0.0001'), rounding=ROUND_HALF_UP)


def _resultado_vacio(razon: str = "") -> Dict[str, Any]:
    """Retorna un dict de error con la misma forma que un cálculo exitoso."""
    return {
        'success': False,
        'error': razon,
        'salario_diario': Decimal('0'),
        'salario_diario_integrado': Decimal('0'),
        'salario_integrado_componentes': {},
        'dias_trabajados': 0,
        'periodo_laboral': {},
        'años_trabajados': Decimal('0'),
        'años_completos': 0,
        'aguinaldo': {'dias_ley': 15, 'monto': Decimal('0')},
'vacaciones': {'dias_segun_antiguedad': 0, 'dias_tabla_ley': 0,
                       'dias_causadas_anteriores': 0, 'dias_causadas_calculadas': 0,
                       'dias_ciclos_extra_sugeridos': 0,
                       'dias_proporcionales': Decimal('0'), 'override_aplicado': False,
                       'monto_causadas': Decimal('0'), 'monto_proporcionales': Decimal('0'),
                       'monto': Decimal('0')},
        'prima_vacacional': {'porcentaje': 25, 'monto': Decimal('0')},
        'prima_antiguedad': {'dias_por_año': 12, 'tope_diario': Decimal('0'),
                             'piso_diario': Decimal('0'), 'salario_base': Decimal('0'),
                             'tope_aplicado': False, 'años_servicio': Decimal('0'),
                             'monto': Decimal('0')},
        'indemnizacion': {'dias': 90, 'monto': Decimal('0')},
        'accion': {'accion': 'indemnizacion', 'procede': False,
                    'indemnizacion_incluida': True, 'motivo': ''},
        'indemnizacion_20dias': {'dias_por_año': 20, 'años_servicio': Decimal('0'),
                                 'monto': Decimal('0')},
        'vacaciones_vencidas': {'dias': 0, 'dias_sugeridos': 0, 'monto': Decimal('0')},
        'horas_extras': {'cantidad': Decimal('0'), 'dobles': Decimal('0'),
                         'triples': Decimal('0'), 'monto': Decimal('0')},
        'salarios_devengados': {'monto': Decimal('0')},
        'dias_festivos': {'dias': 0, 'monto': Decimal('0')},
        'descanso_semanal': {'dias': 0, 'dias_teoricos': 0, 'monto': Decimal('0')},
        'total': Decimal('0'),
        'detalles': {},
    }