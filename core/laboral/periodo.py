"""
Modelo Temporal de la Relación Laboral
======================================

Descompone la relación laboral en los PERIODOS que cada prestación necesita.
El error clásico del motor era usar `dias_trabajados` (días de toda la
relación) para todo; cada prestación exige un periodo distinto:

    Aguinaldo   → días trabajados del AÑO CALENDARIO en curso (art. 87)
    Vacaciones  → ciclo de aniversario (art. 76/81) + ciclos cumplidos
    Prima antig.→ años de servicio completos (art. 162)
    20 días/año → años de servicio con fracción (art. 50 fr. II)
    Horas extras → semanas trabajadas (art. 66/68)

`PeriodoLaboral` es la única fuente de fechas y conteos: `formulas.py` sólo
recibe números y `calculators.py` ya no adivina periodos.

SIN DEPENDENCIAS DE DJANGO.

Autor: Conciliacion Laboral Tijuana - Motor Jurídico Parametrizable
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional

from . import rules as r


# ═══════════════════════════════════════════════════════════════════════════
# Ciclo de vacaciones (art. 76 y 81 LFT)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CicloVacaciones:
    """Un ciclo anual de vacaciones basado en el ANIVERSARIO de ingreso.

    El derecho nace al cumplir un año de servicios (art. 76) y debe
    concederse dentro de los seis meses siguientes (art. 81).  El ciclo `k`
    va del aniversario k-1 al aniversario k; su duración en días es la real
    (365 o 366 si el ciclo contiene el 29 de febrero).
    """

    numero: int                       # año de servicio (1 = primer año)
    inicio: date                      # aniversario previo (o fecha de ingreso)
    fin: date                         # aniversario de este ciclo (inclusive)
    dias_ciclo: int                   # duración real del ciclo en días
    dias_trabajados: int              # días efectivamente trabajados en el ciclo
    dias_correspondientes: int        # días de vacaciones del año (tabla art. 76)
    fraccion: Decimal                 # fracción del ciclo cumplida (0-1)
    dias_proporcionales: Decimal      # días de vacaciones proporcionales
    completo: bool                    # ¿se cumplió el año de servicios?

    @property
    def dias_causados_no_disfrutados(self) -> int:
        """Días causados por el art. 76 que, sin haberlos disfrutado, quedan
        pendientes de pago si la relación termina dentro de este ciclo."""
        if not self.completo:
            return 0
        return self.dias_correspondientes


# ═══════════════════════════════════════════════════════════════════════════
# Periodo laboral
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PeriodoLaboral:
    """Descomposición temporal completa de la relación laboral."""

    fecha_ingreso: date
    fecha_salida: date

    # ─── antigüedad ───────────────────────────────────────────────────
    dias_relacion: int              # días naturales inclusivos (ambos extremos)
    años_completos: int             # aniversarios cumplidos (exacto, bisiesto-aware)
    aniversario_vigente: date        # último aniversario cumplido
    proximo_aniversario: date        # aniversario que cierra el ciclo en curso
    dias_ciclo_vigente: int         # días reales del ciclo en curso
    dias_cumplidos_ciclo_vigente: int   # días cumplidos del ciclo (0 = en el aniversario)
    fraccion_ciclo_vigente: Decimal  # fracción del ciclo cumplida (0-1)

    # ─── años de servicio para indemnizaciones ────────────────────────
    años_servicio_decimal: Decimal   # años_completos + fracción del ciclo

    # ─── año calendario (aguinaldo, art. 87) ──────────────────────────
    anio_aguinaldo: int
    dias_anio_actual: int           # días trabajados dentro del año calendario
    dias_anio_total: int            # 365 o 366

    # ─── vacaciones ───────────────────────────────────────────────────
    ciclos_vacaciones: List[CicloVacaciones]
    ciclo_vacaciones_vigente: Optional[CicloVacaciones]

    # ───helpers ───────────────────────────────────────────────────────

    @property
    def dias_anio_anterior(self) -> int:
        """Días trabajados en el año calendario anterior al de terminación."""
        return _dias_en_anio(self.fecha_ingreso, self.fecha_salida,
                              self.fecha_salida.year - 1)


def construir_periodo(
    fecha_ingreso: date,
    fecha_salida: date,
    reglas: Optional[r.ReglasLegales] = None,
) -> Optional[PeriodoLaboral]:
    """Construye el `PeriodoLaboral` de la relación.

    Args:
        fecha_ingreso: Inicio de la relación laboral.
        fecha_salida: Terminación de la relación laboral.
        reglas: Reglas legales (para la tabla de vacaciones). Por defecto las
            vigentes.

    Returns:
        PeriodoLaboral, o None si las fechas no forman una relación válida.
    """
    if not fecha_ingreso or not fecha_salida or fecha_salida < fecha_ingreso:
        return None

    if reglas is None:
        reglas = r.ReglasLegales.por_defecto()

    # ─── días inclusivos ──────────────────────────────────────────────
    dias_relacion = (fecha_salida - fecha_ingreso).days + 1

    # ─── aniversarios (exactos,.sin dividir entre 365) ───────────────
    años_completos = _años_completos(fecha_ingreso, fecha_salida)
    aniversario_vigente = _aniversario(fecha_ingreso, años_completos)
    proximo_aniversario = _aniversario(fecha_ingreso, años_completos + 1)
    dias_ciclo_vigente = (proximo_aniversario - aniversario_vigente).days
    # Días cumplidos del ciclo: 0 si la relación termina exactamente en el
    # aniversario (entonces `años_servicio_decimal` es un entero exacto y no
    # 5.0027), y `dias_ciclo_vigente` si termina un día antes del siguiente.
    dias_cumplidos = (fecha_salida - aniversario_vigente).days
    fraccion_ciclo = (Decimal(dias_cumplidos) / Decimal(dias_ciclo_vigente)
                      if dias_ciclo_vigente > 0 else Decimal('1'))

    # ─── años de servicio para el art. 50 fr. II ──────────────────────
    años_servicio = Decimal(años_completos) + _cuantizar(fraccion_ciclo)

    # ─── año calendario para el aguinaldo (art. 87) ────────────────────
    anio = fecha_salida.year
    dias_anio = _dias_en_anio(fecha_ingreso, fecha_salida, anio)
    dias_anio_total = 366 if _es_bisiesto(anio) else 365

    # ─── ciclos de vacaciones ─────────────────────────────────────────
    ciclos = _ciclos_vacaciones(fecha_ingreso, fecha_salida, años_completos,
                                 dias_cumplidos, fraccion_ciclo, reglas)
    ciclo_vigente = ciclos[-1] if ciclos else None

    return PeriodoLaboral(
        fecha_ingreso=fecha_ingreso,
        fecha_salida=fecha_salida,
        dias_relacion=dias_relacion,
        años_completos=años_completos,
        aniversario_vigente=aniversario_vigente,
        proximo_aniversario=proximo_aniversario,
        dias_ciclo_vigente=dias_ciclo_vigente,
        dias_cumplidos_ciclo_vigente=dias_cumplidos,
        fraccion_ciclo_vigente=fraccion_ciclo,
        años_servicio_decimal=años_servicio,
        anio_aguinaldo=anio,
        dias_anio_actual=dias_anio,
        dias_anio_total=dias_anio_total,
        ciclos_vacaciones=ciclos,
        ciclo_vacaciones_vigente=ciclo_vigente,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Helpers de calendario
# ═══════════════════════════════════════════════════════════════════════════

def _es_bisiesto(anio: int) -> bool:
    return anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0)


def _dias_del_anio(anio: int) -> int:
    return 366 if _es_bisiesto(anio) else 365


def _aniversario(fecha_ingreso: date, años: int) -> date:
    """Aniversario número `años` de la fecha de ingreso.

    Usa `replace` con clamping: el 29 de febrero se cumple el 28 de febrero en
    años no bisiestos (misma convención que el ciclo-legal Scanner de nómina).
    """
    try:
        return fecha_ingreso.replace(year=fecha_ingreso.year + años)
    except ValueError:
        return fecha_ingreso.replace(year=fecha_ingreso.year + años, day=28)


def _años_completos(fecha_ingreso: date, fecha_salida: date) -> int:
    """Años completos de servicio, exactos (no `dias / 365`)."""
    if fecha_salida < fecha_ingreso:
        return 0
    años = fecha_salida.year - fecha_ingreso.year
    if fecha_salida < _aniversario(fecha_ingreso, años):
        años -= 1
    return max(0, años)


def _dias_en_anio(fecha_ingreso: date, fecha_salida: date, anio: int) -> int:
    """Días trabajados dentro de un año calendario (inclusivos)."""
    inicio = max(fecha_ingreso, date(anio, 1, 1))
    fin = min(fecha_salida, date(anio, 12, 31))
    if fin < inicio:
        return 0
    return (fin - inicio).days + 1


def _ciclos_vacaciones(
    fecha_ingreso: date,
    fecha_salida: date,
    años_completos: int,
    dias_cumplidos: int,
    fraccion_ciclo: Decimal,
    reglas: r.ReglasLegales,
) -> List[CicloVacaciones]:
    """Genera un ciclo por cada año de servicio, marcando el vigente.

    El último elemento es SIEMPRE el ciclo en curso (incompleto si la relación
    termina antes de cumplir otro aniversario).  Los ciclos previos se
    conservan para que el asesor vea cuántos días ya se causaron.
    """
    ciclos: List[CicloVacaciones] = []
    total = años_completos + 1

    for numero in range(1, total + 1):
        inicio = fecha_ingreso if numero == 1 else _aniversario(fecha_ingreso, numero - 1)
        fin = _aniversario(fecha_ingreso, numero)
        if fin > fecha_salida:
            fin = fecha_salida

        dias_ciclo = (fin - inicio).days + 1
        completo = numero <= años_completos

        if numero < total:
            # ciclo ya cumplido: los días trabajados son todos los del ciclo
            dias_trabajados = dias_ciclo
            fraccion = Decimal('1')
        else:
            dias_trabajados = min(dias_cumplidos + 1, dias_ciclo)
            fraccion = fraccion_ciclo

        dias_correspondientes = reglas.dias_vacaciones(numero)
        # El proporcional usa los días del AÑO de servicio al que corresponde
        # el ciclo.  Para el primer año (<1 año) la tabla devuelve 0 y el
        # criterio lo decide `ReglasLegales.vacaciones_antes_de_un_ano`.
        if numero == 1:
            dias_correspondientes = _dias_vacaciones_primer_anio(reglas)

        dias_prop = _cuantizar(Decimal(dias_correspondientes) * fraccion)

        ciclos.append(CicloVacaciones(
            numero=numero,
            inicio=inicio,
            fin=fin,
            dias_ciclo=dias_ciclo,
            dias_trabajados=dias_trabajados,
            dias_correspondientes=dias_correspondientes,
            fraccion=fraccion,
            dias_proporcionales=dias_prop,
            completo=completo,
        ))

    return ciclos


def _dias_vacaciones_primer_anio(reglas: r.ReglasLegales) -> int:
    """Días de vacaciones aplicables al primer año (relación < 1 año).

    El art. 76 LFT exige "más de un año de servicios", así que el criterio
    mayoritario NO genera vacaciones antes del primer aniversario.  El criterio
    proporcional (12 × tiempo/año) también se aplica en la práctica — por eso
    es un parámetro de `ReglasLegales` ('ninguna' | 'proporcional') y no una
    constante del motor.
    """
    if reglas.vacaciones_antes_de_un_ano == 'ninguna':
        return 0
    return r.obtener_dias_vacaciones(1, reglas.tabla_vacaciones)


def _cuantizar(valor: Decimal, decimales: int = 4) -> Decimal:
    """Cuantiza a N decimales con redondeo medio hacia arriba."""
    from decimal import ROUND_HALF_UP
    return valor.quantize(Decimal('1.' + '0' * decimales), rounding=ROUND_HALF_UP)