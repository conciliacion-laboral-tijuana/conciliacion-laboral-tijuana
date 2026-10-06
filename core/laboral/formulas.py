"""
Fórmulas Matemáticas Puras para Cálculos Laborales Mexicanos
============================================================

Este módulo NO tiene dependencias de Django.
Contiene SOLO lógica matemática: recibe números, devuelve números.
Las reglas legales (días de vacaciones, topes, UMA, jornada) se las pasa quien
llama, en un objeto `ReglasLegales`.

REGLA DE DISEÑO: cada fórmula recibe el PERIODO que su artículo exige, no un
`dias_trabajados` genérico.  Ver core/laboral/periodo.py.

Autor: Conciliacion Laboral Tijuana - Motor Jurídico Parametrizable
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Tuple


# ─── Utilidades ────────────────────────────────────────────────────────────

def _decimal(valor, digitos=2) -> Decimal:
    """Convierte a Decimal con redondeo medio hacia arriba."""
    return Decimal(str(valor)).quantize(Decimal(f'0.{"0" * digitos}'), rounding=ROUND_HALF_UP)


def _d(valor) -> Decimal:
    """Decimal sin cuantizar (para ratios y productos intermedios)."""
    return Decimal(str(valor))


def _pos(*valores) -> bool:
    """True si algún valor es > 0."""
    return any(_d(v) > 0 for v in valores)


def dias_entre(fecha_inicio: date, fecha_fin: date) -> int:
    """Días calendario entre dos fechas (diferencia, extremo final exclusive)."""
    return (fecha_fin - fecha_inicio).days


def años_completos(fecha_inicio: date, fecha_fin: date) -> Decimal:
    """Años de servicio exactos (aniversarios cumplidos), con fracción decimal.

    NO usa `dias / 365`: los años bisiestos alteran el resultado y en un
    cálculo jurídico la antigüedad se mide por aniversarios.  Se mantiene el
    nombre histórico por compatibilidad; la fuente de verdad es
    `core.laboral.periodo.construir_periodo`.
    """
    from .periodo import construir_periodo

    periodo = construir_periodo(fecha_inicio, fecha_fin)
    if periodo is None:
        return Decimal('0')
    return periodo.años_servicio_decimal


# ─── Salario ───────────────────────────────────────────────────────────────

def salario_diario(salario, periodo: str = 'mensual') -> Decimal:
    """
    Salario diario según el periodo de pago (art. 89 LFT, último párrafo).

    Args:
        salario: Monto del salario en el periodo
        periodo: 'mensual' (÷30), 'quincenal' (÷15), 'semanal' (÷7), 'diario' (×1)

    Returns:
        Salario diario calculado
    """
    divisores = {
        'mensual': Decimal('30'),
        'quincenal': Decimal('15'),
        'semanal': Decimal('7'),
        'diario': Decimal('1'),
    }
    divisor = divisores.get(periodo, Decimal('30'))
    return _decimal(_d(salario) / divisor)


def salario_integrado(
    salario_diario_valor: Decimal,
    conceptos: Optional[Dict[str, Decimal]] = None,
    modo: str = 'explicit',
    porcentaje: Decimal = Decimal('0'),
) -> Decimal:
    """
    Salario diario integrado (art. 84 y 89 LFT).

    Base de las indemnizaciones: cuota diaria y la parte proporcional de las
    prestaciones del art. 84.  NO integran el aguinaldo, las vacaciones, la
    prima vacacional, la prima de antigüedad ni las horas extras: cada una se
    calcula sobre el salario ordinario y se paga aparte.

    Args:
        salario_diario_valor: Salario diario ordinario (cuota diaria incluida).
        conceptos: Dict {'cuota_diaria': x, 'gratificaciones': y, 'ayudas': z,
            'comisiones': w, 'prestaciones_especie': v, ...}
        modo: 'explicit' (suma los conceptos declarados; ceros = igual al
            diario) o 'porcentaje' (diario × (1 + porcentaje/100)).
        porcentaje: Porcentaje adicional de prestaciones integradas, sólo para
            el modo 'porcentaje'.

    Returns:
        Salario diario integrado, nunca menor al salario diario ordinario.
    """
    base = _d(salario_diario_valor)
    if base <= 0:
        return Decimal('0')

    if modo == 'porcentaje':
        return _decimal(base * (Decimal('1') + _d(porcentaje) / Decimal('100')))

    adicional = Decimal('0')
    for valor in (conceptos or {}).values():
        adicional += _d(valor)

    integrado = base + adicional
    return _decimal(integrado if integrado > base else base)


# ─── 1. Aguinaldo Proporcional (art. 87 LFT) ──────────────────────────────

def aguinaldo_proporcional(
    dias_anio_actual: int,
    dias_anio_total: int,
    salario_diario_valor: Decimal,
    dias_aguinaldo: int = 15
) -> Decimal:
    """
    Aguinaldo proporcional = (días trabajados DEL AÑO EN CURSO / días del año)
                             × días de aguinaldo × salario diario

    El art. 87 LFT obliga a pagar "la parte proporcional del mismo, conforme al
    tiempo que hubieren trabajado".  Ese tiempo es el del AÑO CALENDARIO en
    curso, no toda la antigüedad: un trabajador con 5 años despedido el 15 de
    septiembre de 2026 trabajó 258 días de 2026, no 5 años.

    Args:
        dias_anio_actual: Días trabajados dentro del año calendario de terminación.
        dias_anio_total: Días del año (365 o 366 si el año es bisiesto).
        salario_diario_valor: Salario diario ordinario.
        dias_aguinaldo: Días de aguinaldo (mínimo legal 15).

    Returns:
        Aguinaldo proporcional calculado
    """
    if not _pos(dias_anio_actual, salario_diario_valor):
        return Decimal('0')
    if _d(dias_anio_total) <= 0:
        return Decimal('0')

    return _decimal(
        (_d(dias_anio_actual) / _d(dias_anio_total))
        * _d(dias_aguinaldo)
        * _d(salario_diario_valor)
    )


# ─── 2. Vacaciones (art. 76, 79, 81 LFT) ─────────────────────────────────

def vacaciones_proporcionales(
    dias_correspondientes,
    fraccion_ciclo: Decimal,
    salario_diario_valor: Decimal
) -> Decimal:
    """
    Vacaciones proporcionales = días que corresponden por antigüedad × fracción
                                del ciclo de aniversario × salario diario

    La proporcionalidad se aplica UNA sola vez.  El error anterior era calcular
    `int(dias/365*12)` y después volver a multiplicar por `dias/365`, dejando
    los días al cuadrado.

    Args:
        dias_correspondientes: Días de vacaciones del año de servicio (tabla
            art. 76), ya sea entero o proporcional al primer año.
        fraccion_ciclo: Fracción cumplida del ciclo de aniversario (0-1).
        salario_diario_valor: Salario diario.

    Returns:
        Monto de vacaciones proporcionales del ciclo en curso
    """
    if not _pos(dias_correspondientes, fraccion_ciclo, salario_diario_valor):
        return Decimal('0')

    fraccion = _d(fraccion_ciclo)
    if fraccion > 1:
        fraccion = Decimal('1')

    return _decimal(_d(dias_correspondientes) * fraccion * _d(salario_diario_valor))


def dias_vacaciones_totales(
    dias_causados_pendientes,
    dias_proporcionales
) -> Decimal:
    """Suma de días de vacaciones a pagar (causados + proporcionales)."""
    return _d(dias_causados_pendientes) + _d(dias_proporcionales)


def vacaciones_vencidas(dias_vencidos, salario_diario_valor: Decimal) -> Decimal:
    """
    Vacaciones de ciclos anteriores ya cumplidos y no disfrutados ni pagados.

    Args:
        dias_vencidos: Días de vacaciones adeudados de ciclos anteriores.
        salario_diario_valor: Salario diario.

    Returns:
        Monto de vacaciones pendientes de ciclos anteriores
    """
    if not _pos(dias_vencidos, salario_diario_valor):
        return Decimal('0')
    return _decimal(_d(dias_vencidos) * _d(salario_diario_valor))


def dias_descanso_semanal_teoricos(dias_trabajados: int, dias_cada: int = 6) -> int:
    """
    Días de descanso semanal que genera el periodo laborado (art. 69 LFT).

    "Por cada seis días de trabajo se deberá otorgar, por lo menos, un día de
    descanso con goce de salario íntegro."  Es informativo: normalmente ya se
    pagaron en nómina, así que el motor no las cobra salvo que el asesor las
    declare como no disfrutadas.
    """
    if _d(dias_trabajados) <= 0 or _d(dias_cada) <= 0:
        return 0
    return int(_d(dias_trabajados) // _d(dias_cada))


# ─── 3. Prima Vacacional (art. 80 LFT) ────────────────────────────────────

def prima_vacacional(
    vacaciones_monto: Decimal,
    porcentaje_prima: Decimal = Decimal('0.25')
) -> Decimal:
    """
    Prima vacacional = 25% de los salarios del periodo de vacaciones.

    Args:
        vacaciones_monto: Monto de vacaciones pagadas (causadas + proporcionales).
        porcentaje_prima: Porcentaje de prima vacacional (mínimo legal 0.25).

    Returns:
        Prima vacacional calculada
    """
    if not _pos(vacaciones_monto):
        return Decimal('0')
    return _decimal(_d(vacaciones_monto) * _d(porcentaje_prima))


# ─── 4. Prima de Antigüedad (art. 162, 485, 486 LFT) ──────────────────────

def salario_base_con_tope(
    salario_diario_valor: Decimal,
    tope: Optional[Decimal] = None,
    piso: Optional[Decimal] = None,
) -> Tuple[Decimal, bool]:
    """
    Salario base para la prima de antigüedad (arts. 485/486 LFT).

    Piso: nunca menor al salario mínimo (art. 485).
    Techo: si el salario excede el doble del salario mínimo del área
    geográfica, se toma ese doble como salario máximo (art. 486).

    Returns:
        (salario_base, tope_aplicado)
    """
    base = _d(salario_diario_valor)
    if base <= 0:
        return Decimal('0'), False

    if piso is not None and _d(piso) > 0 and base < _d(piso):
        base = _d(piso)

    if tope is not None and _d(tope) > 0 and _d(salario_diario_valor) > _d(tope):
        return _decimal(_d(tope)), True

    return _decimal(base), False


def prima_antiguedad(
    años_trabajados,
    salario_diario_valor: Decimal,
    dias_por_año: int = 12,
    salario_tope: Optional[Decimal] = None,
    salario_piso: Optional[Decimal] = None,
) -> Decimal:
    """
    Prima de antigüedad = 12 días de salario × años de servicio × salario base.

    El salary base lo fijan los arts. 485 y 486 LFT: el salario mínimo del área
    geográfica donde se prestó el trabajo como piso y su doble como techo.
    NO es 2 × UMA (Tijuana: 2 × $440.87 = $881.74, no 2 × $117.31 = $234.62).

    Args:
        años_trabajados: Años de servicio, con fracción.
        salario_diario_valor: Salario diario.
        dias_por_año: Días por año (12, art. 162 fr. I).
        salario_tope: Tope diario (doble del salario mínimo del área).
        salario_piso: Piso diario (salario mínimo del área).

    Returns:
        Prima de antigüedad calculada
    """
    if not _pos(años_trabajados):
        return Decimal('0')

    base, _ = salario_base_con_tope(salario_diario_valor, salario_tope, salario_piso)
    if base <= 0:
        return Decimal('0')

    return _decimal(_d(dias_por_año) * _d(años_trabajados) * base)


# ─── 5. Indemnización Constitucional (art. 50 fr. III LFT) ─────────────────

def indemnizacion_constitucional(salario_diario_valor: Decimal, dias: int = 90) -> Decimal:
    """
    Indemnización constitucional = 3 meses de salario integrado (90 días).

    La base es el SALARIO INTEGRADO (art. 89 LFT): cuota diaria y parte
    proporcional de las prestaciones del art. 84.

    Args:
        salario_diario_valor: Salario diario integrado.
        dias: Días de indemnización (90 = 3 meses).

    Returns:
        Monto de la indemnización de 3 meses
    """
    if not _pos(salario_diario_valor, dias):
        return Decimal('0')
    return _decimal(_d(dias) * _d(salario_diario_valor))


# ─── 6. Indemnización 20 días por año (art. 50 fr. II LFT) ─────────────────

def indemnizacion_20dias_por_ano(
    años_trabajados,
    salario_diario_valor: Decimal,
    dias_por_año: int = 20,
    con_fraccion: bool = True,
    salario_tope: Optional[Decimal] = None
) -> Decimal:
    """
    Indemnización = 20 días de salario integrado por cada año de servicios.

    Procede como indemnización POR TERMINACIÓN de la relación (arts. 49 y 50
    LFT): despido sin justa causa, despido justificado en los supuestos del
    art. 49 o rescisión del trabajador (arts. 51/52).  NO procede en la renuncia
    voluntaria: por eso `ReglasLegales.conceptos_para_tipo()` decide, en vez de
    tratarla como prestación automática.

    Args:
        años_trabajados: Años de servicio.
        salario_diario_valor: Salario diario integrado (art. 89).
        dias_por_año: Días por año (20, art. 50 fr. II).
        con_fraccion: Si la fracción de año se paga proporcionalmente.
        salario_tope: Tope a aplicar, si el despacho lo requiere.

    Returns:
        Monto de la indemnización de 20 días por año
    """
    if not _pos(años_trabajados):
        return Decimal('0')

    años = _d(años_trabajados)
    if not con_fraccion:
        años = Decimal(int(años))

    base = _d(salario_diario_valor)
    if base <= 0:
        return Decimal('0')
    if salario_tope is not None and _d(salario_tope) > 0:
        base = min(base, _d(salario_tope))

    return _decimal(_d(dias_por_año) * años * base)


# ─── 7. Horas extras (arts. 61, 66, 68 LFT) ───────────────────────────────

def valor_hora(salario_diario_valor: Decimal, horas_jornada) -> Decimal:
    """
    Valor de la hora ordinaria según la jornada diaria (art. 61 LFT).

    diurna 8 h · nocturna 7 h · mixta 7.5 h.  NO usar siempre 8.
    """
    if not _pos(salario_diario_valor, horas_jornada):
        return Decimal('0')
    return _decimal(_d(salario_diario_valor) / _d(horas_jornada))


def distribuir_horas_extra(
    horas_totales,
    semanas,
    maximo_dobles_semana: int,
    maximo_triples_semana: int
) -> Tuple[Decimal, Decimal]:
    """
    Reparte un total de horas extra en dobles (art. 66) y triples (art. 68).

    Una cantidad total NO contiene información jurídica suficiente: el límite de
    horas al doble es semanal y depende del año (transitorio Cuarto de la
    reforma del 01-05-2026: 9 h en 2026 y 2027, 10 en 2028, 11 en 2029, 12 en
    2030) y lo que excede ese límite se paga al triple, con un máximo de 4 h
    semanales (art. 68).  Por eso el total se reparte contra esos topes y se
    devuelven ambos importes por separado.

    Args:
        horas_totales: Total de horas extra declaradas.
        semanas: Semanas trabajadas del periodo.
        maximo_dobles_semana: Tope semanal de horas al doble del año.
        maximo_triples_semana: Tope semanal de horas al triple (art. 68).

    Returns:
        (horas_dobles, horas_triples)
    """
    total = _d(horas_totales)
    if total <= 0 or _d(semanas) <= 0:
        return Decimal('0'), Decimal('0')

    tope_dobles = _d(maximo_dobles_semana) * _d(semanas)
    tope_triples = _d(maximo_triples_semana) * _d(semanas)

    dobles = min(total, tope_dobles)
    triples = min(total - dobles, tope_triples)
    if triples < 0:
        triples = Decimal('0')

    return _cuantiza_horas(dobles), _cuantiza_horas(triples)


def horas_extras(
    horas_dobles,
    horas_triples,
    salario_diario_valor: Decimal,
    horas_jornada=Decimal('8')
) -> Decimal:
    """
    Monto de horas extra: dobles al 200% y excedentes al 300% de la hora ordinaria.

    Art. 66 LFT (100% adicional) y art. 68 LFT (200% adicional).  Se elimina el
    factor promedio de 2.5 que antes se aplicaba a un total indiscriminado: cada
    hora se paga según su categoría jurídica.

    Args:
        horas_dobles: Horas al doble (art. 66).
        horas_triples: Horas excedentes al triple (art. 68).
        salario_diario_valor: Salario diario ordinario.
        horas_jornada: Horas de la jornada diaria (art. 61).

    Returns:
        Monto total de horas extra
    """
    if not _pos(salario_diario_valor):
        return Decimal('0')

    vh = valor_hora(salario_diario_valor, horas_jornada)
    if vh <= 0:
        return Decimal('0')

    monto = (_d(horas_dobles) * vh * Decimal('2')) + (_d(horas_triples) * vh * Decimal('3'))
    return _decimal(monto)


# ─── 8. Días festivos y de descanso semanal (arts. 69, 73-75 LFT) ─────────

def dias_festivos(
    cantidad_dias,
    salario_diario_valor: Decimal,
    multiplicador: Decimal = Decimal('3')
) -> Decimal:
    """
    Días de descanso obligatorio laborados (arts. 74 y 75 LFT).

    El patrón paga "independientemente del salario que le corresponda por el
    descanso obligatorio, un salario doble por el servicio prestado" (art. 75):
    doble por el servicio + el día íntegro = 3 × salario diario.

    Args:
        cantidad_dias: Días festivos laborados no pagados.
        salario_diario_valor: Salario diario.
        multiplicador: 3 por defecto (art. 74 + 75).

    Returns:
        Monto de días festivos
    """
    if not _pos(cantidad_dias, salario_diario_valor):
        return Decimal('0')
    return _decimal(_d(cantidad_dias) * _d(salario_diario_valor) * _d(multiplicador))


def descanso_semanal(
    cantidad_dias,
    salario_diario_valor: Decimal,
    multiplicador: Decimal = Decimal('2')
) -> Decimal:
    """
    Días de descanso semanal trabajados (arts. 69 y 73 LFT).

    Art. 69: por cada 6 días de trabajo, 1 día de descanso con goce de salario
    íntegro.  Art. 73: si se trabaja en el descanso, el patrón paga "un salario
    doble por el servicio prestado", además del salario íntegro del descanso
    (3 × en la práctica si el descanso no se cubrió; por eso el multiplicador
    es parámetro y no constante).

    Args:
        cantidad_dias: Días de descanso semanal laborados.
        salario_diario_valor: Salario diario.
        multiplicador: 2 (art. 73) o 3 si además se adeuda el día íntegro.

    Returns:
        Monto del descanso semanal trabajado
    """
    if not _pos(cantidad_dias, salario_diario_valor):
        return Decimal('0')
    return _decimal(_d(cantidad_dias) * _d(salario_diario_valor) * _d(multiplicador))


# ─── 9. Total general ─────────────────────────────────────────────────────

def total_prestaciones(*montos) -> Decimal:
    """Suma todas las prestaciones calculadas."""
    suma = sum((_d(m) for m in montos), Decimal('0'))
    return _decimal(suma)


def _cuantiza_horas(valor) -> Decimal:
    """Cuantiza horas a 2 decimales (media hora es la unidad práctica)."""
    return _d(valor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)