"""
Reglas Legales Configurables para Cálculos Laborales Mexicanos
==============================================================

Tablas y constantes legales, agrupadas en un objeto `ReglasLegales` inmutable
para que la jurisprudencia cambie SIN tocar las fórmulas:

    ReglasLegales(...)            → objeto de reglas (inmutable)
    reglas.salario_minimo(zona)   → salario mínimo del área geográfica
    reglas.tope_prima_antiguedad(zona)  → arts. 485/486 LFT
    reglas.conceptos_para_tipo(tipo_despido) → qué procede según el art. 50/162

Vigencia: LFT reforma DOF 01-05-2026 (reducción gradual de la jornada) y
valores CONASAMI/INEGI 2026.  La reducción gradual exige tablas por año, no
una constante única (ver `JORNADA_MAXIMA_SEMANAL_ANIOS` y
`HORAS_EXTRA_AL_DOBLE_SEMANA_ANIOS`).

SIN DEPENDENCIAS DE DJANGO: este módulo es importable desde cualquier contexto.

Autor: Conciliacion Laboral Tijuana - Motor Jurídico Parametrizable
"""

from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════
# ZONAS SALARIALES (CONASAMI)
# ═══════════════════════════════════════════════════════════════════════════
#
# 'general'  → resto del país (incluye la CDMX)
# 'frontera' → Zona Libre de la Frontera Norte (Tijuana, Mexicali, Ciudad
#              Juárez, Reynosa, Matamoros, Nogales...).  Tijuana está en ZLFN:
#              el tope de los arts. 485/486 LFT se mide con el salario mínimo
#              de ESTA zona, no con el general ni con la UMA.

ZONA_GENERAL = 'general'
ZONA_FRONTERA = 'frontera'
ZONAS_SALARIALES = (ZONA_GENERAL, ZONA_FRONTERA)


# ═══════════════════════════════════════════════════════════════════════════
# TABLA DE VACACIONES (art. 76 LFT, reforma DOF 27-12-2022)
# ═══════════════════════════════════════════════════════════════════════════
#
# "Las personas trabajadoras que tengan más de un año de servicios disfrutarán
#  de un periodo anual de vacaciones pagadas, que en ningún caso podrá ser
#  inferior a doce días laborables, y que aumentará en dos días laborables,
#  hasta llegar a veinte, por cada año subsecuente de servicios. A partir del
#  sexto año, el periodo de vacaciones aumentará en dos días por cada cinco de
#  servicios."
#
#   1 año  → 12 días      6-10 años → 22 días
#   2 años → 14 días     11-15     → 24 días
#   3 años → 16 días     16-20     → 26 días
#   4 años → 18 días     21-25     → 28 días
#   5 años → 20 días     26-30     → 30 días

TABLA_VACACIONES: List[Tuple[int, int]] = [
    (1, 12),    # 1 año → 12 días
    (2, 14),    # 2 años → 14 días
    (3, 16),    # 3 años → 16 días
    (4, 18),    # 4 años → 18 días
    (5, 20),    # 5 años → 20 días
    (10, 22),   # 10 años → 22 días
    (15, 24),   # 15 años → 24 días
    (20, 26),   # 20 años → 26 días
    (25, 28),   # 25 años → 28 días
    (30, 30),   # 30 años → 30 días
]


def obtener_dias_vacaciones(años_completos: int,
                            tabla: Optional[List[Tuple[int, int]]] = None) -> int:
    """
    Días de vacaciones que corresponden a un número de años completos (art. 76 LFT).

    El derecho NACIENDO al cumplir un año de servicios: con menos de un año
    completo la función devuelve 0 y quien decide si hay derecho proporcional
    es `ReglasLegales.vacaciones_antes_de_un_ano` (criterio jurisprudencial
   discussible, por eso es parámetro y no constante).

    Args:
        años_completos: Años completos de servicios.
        tabla: Tabla alternativa. Si es None usa TABLA_VACACIONES.

    Returns:
        Días de vacaciones correspondientes (0 si < 1 año).
    """
    if tabla is None:
        tabla = TABLA_VACACIONES

    años_completos = int(años_completos)
    if años_completos < 1:
        return 0

    for años, dias in reversed(tabla):
        if años_completos >= años:
            return dias

    # Por encima del último escalón de la tabla: +2 días cada 5 años
    ultimos_anos, ultimos_dias = tabla[-1]
    adicional = ((años_completos - ultimos_anos) // 5) * 2
    return ultimos_dias + adicional


# ═══════════════════════════════════════════════════════════════════════════
# JORNADA Y HORAS EXTRA (LFT reforma DOF 01-05-2026, transitorios Segundo y Cuarto)
# ═══════════════════════════════════════════════════════════════════════════
#
# Art. 59 (texto reformado): "La duración máxima de la jornada ordinaria de
# trabajo será de cuarenta horas semanales", pero el transitorio Segundo lo hace
# gradual: en 2026 la jornada ordinaria SIGUE SIENDO 48 horas.  La reducción a
# 40 horas llega hasta 2030.
#
# Transitorio Cuarto (horas al doble del art. 66):
#     2026 → 9      2027 → 9      2028 → 10    2029 → 11    2030 → 12
#
# Art. 66 (reformado): el tiempo extraordinario "no excederá de doce horas en
# una semana, las cuales podrán distribuirse en hasta cuatro horas diarias, en
# un máximo de cuatro días en ese periodo".
#
# Art. 68 (reformado): lo que exceda el art. 66 "no podrá ser mayor de cuatro
# horas a la semana y obliga a la persona empleadora a pagar un doscientos por
# ciento más del salario que corresponda a las horas de la jornada ordinaria"
# (pago al triple de la hora ordinaria).  Además, ordinaria + extraordinaria
# nunca puede exceder 12 horas diarias.

JORNADA_MAXIMA_SEMANAL_ANIOS: Dict[int, int] = {
    2026: 48,
    2027: 46,
    2028: 44,
    2029: 42,
    2030: 40,
}
HORAS_EXTRA_AL_DOBLE_SEMANA_ANIOS: Dict[int, int] = {
    2026: 9,
    2027: 9,
    2028: 10,
    2029: 11,
    2030: 12,
}
HORAS_EXTRA_AL_TRIPLE_SEMANA_MAX = 4   # art. 68 LFT
HORAS_EXTRA_AL_DOBLE_DIAS_MAX = 4       # art. 66 LFT (máx. días con tiempo extraordinario)
HORAS_EXTRA_DIARIAS_MAX = 4            # art. 66 LFT (máx. 4 h/día al doble)
JORNADA_DIARIA_MAX_HORAS = 12          # art. 68 LFT (ordinaria + extraordinaria)

# Art. 61 LFT: duración máxima de la jornada diaria por tipo de jornada.
JORNADA_DIARIA_HORAS: Dict[str, Decimal] = {
    'diurna': Decimal('8'),
    'nocturna': Decimal('7'),
    'mixta': Decimal('7.5'),
}
JORNADA_DIARIA_HORAS_DEFECTO = Decimal('8')


# ═══════════════════════════════════════════════════════════════════════════
# TIPOS DE DESPIDIO Y QUÉ PRESTACIÓN PROCEDE
# ═══════════════════════════════════════════════════════════════════════════
#
# Art. 50 LFT (indemnizaciones por terminación) y art. 162 LFT (prima de
# antigüedad).  Antes estas dos prestaciones se trataban como automáticas; sólo
# la renuncia voluntaria las excluía.
#
#   injustificado → 90 días (art. 50 fr. III) + 20 días/año (art. 50 fr. II)
#                    + prima de antigüedad (art. 162 fr. III)
#   justificado   → sin indemnización art. 50 (art. 46: "sin incurrir en
#                    responsabilidad"), pero SÍ prima de antigüedad
#                    (art. 162 fr. III: "se pagará a los que se separen por
#                    causa justificada")
#   rescisión     → el trabajador se separa por causa imputable al patrón
#                    (art. 51/52) → indemnizaciones del art. 50 + prima
#   voluntario    → sin art. 50; prima de antigüedad sólo con 15 años o más
#                    (art. 162 fr. III)
#
# Las prestaciones ordinarias no dependen del tipo de separación:
# aguinaldo, vacaciones, prima vacacional y horas extras se deben en todos los
# casos (arts. 87, 76, 80, 66-68).

CONCEPTO_INDEMNIZACION = 'indemnizacion'
CONCEPTO_INDEMNIZACION_20 = 'indemnizacion_20dias'
CONCEPTO_PRIMA_ANTIGUEDAD = 'prima_antiguedad'

_TODAS_LAS_PRESTACIONES = frozenset({
    'aguinaldo', 'vacaciones', 'prima_vacacional',
    CONCEPTO_PRIMA_ANTIGUEDAD, CONCEPTO_INDEMNIZACION, CONCEPTO_INDEMNIZACION_20,
    'vacaciones_vencidas', 'horas_extras', 'salarios_devengados',
    'dias_festivos', 'descanso_semanal',
})

# Prestaciones que dependen de la causa de separación.
POR_TIPO_DESPIDIO: Dict[str, Tuple[bool, bool, bool]] = {
    #  tipo              (90 días, 20 días/año, prima antigüedad)
    'injustificado':     (True,  True,  True),
    'justificado':       (False, False, True),
    'rescision':         (True,  True,  True),
    'voluntario':        (False, False, 'quince_anos'),
    'otro':              (True,  True,  True),
}

# La renuncia voluntaria con menos de 15 años no tiene prima de antigüedad.
INDICADOR_PRIMA_ANTIGUEDAD_POR_ANTIGUEDAD = 'quince_anos'


# ═══════════════════════════════════════════════════════════════════════════
# ACCIÓN PREFERIDA ANTE UN DESPIDO (arts. 48 y 49 LFT)
# ═══════════════════════════════════════════════════════════════════════════
#
# El art. 48 LFT da al trabajador una ELECCIÓN entre la reinstalación en el
# puesto que desempeñaba y la indemnización de tres meses de salario.  No son
# dos prestaciones acumulables: son acciones excluyentes.  La reinstalación
# desaparece en los supuestos del art. 49 LFT, y el patrón puede depositarla
# ante el Tribunal para obtener la exclusión de la obligación de reinstalar.
#
# Supuestos del art. 49 LFT en los que NO hay reinstalación:
#   I.    antigüedad menor a un año
#   II.   contacto directo y permanente con el patrón, a criterio del Tribunal
#   III.  trabajadores de confianza
#   IV.   trabajo del hogar
#   V.    trabajadores eventuales
#   VI.   personas trabajadoras en plataformas digitales
# (El art. 49 se reformó con la LFT de 2024 para integrar el trabajo del hogar y
#  las plataformas digitales; el resto de las fracciones no ha cambiado.)

ACCION_INDEMNIZACION = 'indemnizacion'
ACCION_REINSTALACION = 'reinstalacion'
ACCIONES = (ACCION_INDEMNIZACION, ACCION_REINSTALACION)

# Antigüedad mínima (en años completos) para que haya reinstalación: art. 49
# fr. I LFT.
ANTIGUEDAD_MINIMA_REINSTALACION_ANIOS = 1


# ═══════════════════════════════════════════════════════════════════════════
# OBJETO DE REGLAS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ReglasLegales:
    """Conjunto inmutable de reglas legales aplicables a un cálculo.

    Todos los montos van en PESOS DIARIOS salvo indicación contraria.
    """

    # ─── UMA y salario mínimo (CONASAMI / INEGI) ──────────────────────
    uma_diaria: Decimal = Decimal('117.31')                    # INEGI, vigente desde 2026-02-01
    salario_minimo: Decimal = Decimal('315.04')                 # zona general, desde 2026-01-01
    salario_minimo_frontera: Decimal = Decimal('440.87')        # Zona Libre de la Frontera Norte

    # ─── Prestaciones ────────────────────────────────────────────────
    aguinaldo_dias: int = 15                                   # art. 87 LFT (mínimo legal)
    prima_vacacional_porcentaje: Decimal = Decimal('0.25')     # art. 80 LFT (mínimo 25%)
    prima_antiguedad_dias_por_ano: int = 12                    # art. 162 fr. I LFT
    prima_antiguedad_anios_voluntaria: int = 15                # art. 162 fr. III LFT
    vacaciones_antes_de_un_ano: str = 'proporcional'           # ver nota en la clase

    # ─── Indemnizaciones (art. 50 LFT) ───────────────────────────────
    indemnizacion_dias: int = 90                               # fr. III: 3 meses
    indemnizacion_20dias_dias_por_ano: int = 20                # fr. II: 20 días por año
    indemnizacion_20dias_incluye_fraccion: bool = True         # años con fracción

    # ─── Tope de la prima de antigüedad (arts. 485/486 LFT) ─────────
    # NO es 2 × UMA: es 2 × salario mínimo del ÁREA GEOGRÁFICA donde se
    # prestó el trabajo.  Piso (art. 485) y techo (art. 486).
    tope_prima_antiguedad_multiplo: int = 2
    tope_prima_antiguedad_piso: bool = True                    # nunca menos del salario mínimo

    # ─── Días de descanso (arts. 69-75 LFT) ─────────────────────────
    descanso_semanal_dias_cada: int = 6                        # art. 69: 1 descanso / 6 trabajados
    descanso_semanal_multiplicador: Decimal = Decimal('2')     # art. 73: salario doble por el servicio
    festivo_multiplicador: Decimal = Decimal('3')               # art. 74 + 75: doble + día íntegro
    prima_descanso_semanal_dias_por_ano: int = 0                # 0 = la prima de 20 días/año es contractual (CCT)

    # ─── Salario integrado (art. 84 LFT) ────────────────────────────
    # Mode 'explicit'   → suma los conceptos declarados (todo 0 = igual al diario)
    # Modo 'porcentaje' → diario × (1 + pct/100)
    salario_integrado_modo: str = 'explicit'                    # 'explicit' | 'porcentaje'
    salario_integrado_porcentaje: Decimal = Decimal('0')

    # ─── Antigüedad ──────────────────────────────────────────────────
    # Base del cálculo: días reales del ciclo (respeta años bisiestos), no
    # dividir entre 365.  Ver core/laboral/periodo.py.
    antiguedad_base: str = 'ciclo_calendar'                     # 'ciclo_calendar' | '365'

    tabla_vacaciones: List[Tuple[int, int]] = field(default_factory=lambda: list(TABLA_VACACIONES))

    # ─── Constructores ───────────────────────────────────────────────

    @classmethod
    def por_defecto(cls) -> 'ReglasLegales':
        """Reglas vigentes por defecto (LFT 2026, valores 2026)."""
        return cls()

    @classmethod
    def desde_legal_config(cls, config, **extra) -> 'ReglasLegales':
        """Construye las reglas desde una fila de `expedientes.models.LegalConfig`.

        Acepta cualquier objeto con esos atributos (permite probarlo con un
        stub sin tocar la base de datos).  Los parámetros no presentes en el
        modelo se toman del valor por defecto o de `extra`.
        """
        base = cls.por_defecto()
        datos = {
            'uma_diaria': _dec(getattr(config, 'uma_diaria', None), base.uma_diaria),
            'salario_minimo': _dec(getattr(config, 'salario_minimo', None), base.salario_minimo),
            'salario_minimo_frontera': _dec(
                getattr(config, 'salario_minimo_frontera', None), base.salario_minimo_frontera),
            'aguinaldo_dias': int(getattr(config, 'aguinaldo_dias', None) or base.aguinaldo_dias),
            'prima_vacacional_porcentaje': (
                _dec(getattr(config, 'prima_vacacional_porcentaje', None),
                     base.prima_vacacional_porcentaje * 100) / 100),
            'prima_antiguedad_dias_por_ano': int(
                getattr(config, 'prima_antiguedad_dias_por_ano', None)
                or base.prima_antiguedad_dias_por_ano),
            'indemnizacion_dias': int(
                getattr(config, 'indemnizacion_dias', None) or base.indemnizacion_dias),
            'tope_prima_antiguedad_multiplo': int(
                getattr(config, 'tope_prima_multiplo', None) or base.tope_prima_antiguedad_multiplo),
        }
        # El tipo de tope guardado en el admin ("uma"/"salario_minimo"/"frontera")
        # solo elegía QUÉ cifra usar; el factor es siempre el salario mínimo del
        # área (arts. 485/486).  Se conserva la zona por defecto "frontera" si
        # así se guardó, pero la zona se resuelve por expediente (Tijuana).
        for clave, valor in extra.items():
            if clave in base.__dataclass_fields__:
                datos[clave] = valor
        return cls(**datos)

    def con(self, **cambios) -> 'ReglasLegales':
        """Copia con los campos indicados modificados (inmutable)."""
        return replace(self, **cambios)

    # ─── Salarios mínimos y topes ────────────────────────────────────

    def salario_minimo_de(self, zona: str = ZONA_GENERAL) -> Decimal:
        """Salario mínimo diario del área geográfica (CONASAMI)."""
        if zona == ZONA_FRONTERA:
            return self.salario_minimo_frontera
        return self.salario_minimo

    def tope_prima_antiguedad(self, zona: str = ZONA_GENERAL) -> Decimal:
        """Salario máximo para la prima de antigüedad (arts. 485/486 LFT).

        Es 2 × salario mínimo del ÁREA donde se prestó el trabajo, NO 2 × UMA:
        con la Zona Libre de la Frontera Norte el tope de 2026 es
        $881.74 diarios, frente a $630.08 en la zona general y $234.62 si
        (incorrectamente) se usara 2 × UMA.
        """
        return (self.salario_minimo_de(zona) * Decimal(self.tope_prima_antiguedad_multiplo))

    def piso_salario_indemnizaciones(self, zona: str = ZONA_GENERAL) -> Decimal:
        """Piso de la base de cálculo: nunca menos del salario mínimo (art. 485)."""
        return self.salario_minimo_de(zona) if self.tope_prima_antiguedad_piso else Decimal('0')

    # ─── Jornada y horas extra ───────────────────────────────────────

    def jornada_diaria_horas(self, jornada: str = 'diurna') -> Decimal:
        """Horas de la jornada diaria según el tipo de jornada (art. 61 LFT)."""
        return JORNADA_DIARIA_HORAS.get((jornada or '').lower(), JORNADA_DIARIA_HORAS_DEFECTO)

    def jornada_maxima_semanal(self, anio: int) -> int:
        """Jornada ordinaria máxima semanal vigente en el año (transitorio Segundo)."""
        return _vigente_por_anio(JORNADA_MAXIMA_SEMANAL_ANIOS, anio, 48)

    def horas_extra_dobles_max_semana(self, anio: int) -> int:
        """Horas al doble máximas por semana (art. 66 + transitorio Cuarto)."""
        return _vigente_por_anio(HORAS_EXTRA_AL_DOBLE_SEMANA_ANIOS, anio, 9)

    # ─── Vacaciones ───────────────────────────────────────────────────

    def dias_vacaciones(self, años_completos: int) -> int:
        """Días de vacaciones por años completos (art. 76 LFT)."""
        return obtener_dias_vacaciones(años_completos, self.tabla_vacaciones)

    # ─── Procedencia por tipo de separación ───────────────────────────

    def accion_posible(self, accion: Optional[str], años_completos: int,
                       tipo_despido: Optional[str] = None) -> Dict[str, Any]:
        """Resuelve la acción preferida del art. 48 LFT (elegir reinstalación o
        indemnización) y explica por qué procede o no.

        La reinstalación NO procede cuando:
          - se pide para una relación menor a un año (art. 49 fr. I LFT);
          - el tipo de separación no genera responsabilidad del patrón
            (despido justificado o renuncia voluntaria: art. 46 LFT).

        Args:
            accion: 'reinstalacion' o 'indemnizacion'.
            años_completos: Años completos de servicio del trabajador.
            tipo_despido: Causa de separación, si se conoce.

        Returns:
            dict con 'accion', 'procede', 'indemnizacion_incluida' y 'motivo'.
        """
        if accion not in ACCIONES:
            accion = ACCION_INDEMNIZACION

        resultado = {
            'accion': accion,
            'procede': False,
            'indemnizacion_incluida': True,
            'motivo': '',
        }

        if accion != ACCION_REINSTALACION:
            resultado['motivo'] = 'Se reclama la indemnización de tres meses de salario.'
            return resultado

        if años_completos < ANTIGUEDAD_MINIMA_REINSTALACION_ANIOS:
            resultado['motivo'] = (
                f'No procede la reinstalación: la antigüedad es menor a un año '
                f'({años_completos} año(s) completos), supuesto del art. 49 fr. I LFT. '
                f'Procede la indemnización del art. 50 LFT.'
            )
            return resultado

        if tipo_despido in ('justificado', 'voluntario'):
            resultado['motivo'] = (
                'No procede la reinstalación en una separación justificada o por '
                'renuncia voluntaria: el art. 46 LFT excluye la responsabilidad '
                'del patrón. Procede la indemnización del art. 50 LFT.'
            )
            return resultado

        resultado.update({
            'procede': True,
            'indemnizacion_incluida': False,
            'motivo': (
                f'El actor opta por la reinstalación en el puesto que desempeñaba '
                f'(art. 48 LFT), por lo que NO se incluye la indemnización de tres '
                f'meses de salario. Con antigüedad de {años_completos} año(s) '
                f'completos no aplica el supuesto de excepción del art. 49 fr. I LFT.'
            ),
        })
        return resultado

    def restricciones_por_tipo(self, tipo_despido: Optional[str],
                               años_completos: int = 0) -> Dict[str, bool]:
        """Sólo las restricciones que dependen de la causa de separación.

        Devuelve las claves `incluir_*` de los conceptos que la ley condiciona
        (art. 50 y art. 162 LFT), para poder sobreescribirlas sobre cualquier
        selección base sin encender los conceptos que el despacho dejó apagados.
        """
        if not tipo_despido:
            return {}

        ind90, ind20, pa = POR_TIPO_DESPIDIO.get(
            tipo_despido, POR_TIPO_DESPIDIO['injustificado'])

        if pa == INDICADOR_PRIMA_ANTIGUEDAD_POR_ANTIGUEDAD:
            pa = años_completos >= self.prima_antiguedad_anios_voluntaria

        return {
            f'incluir_{CONCEPTO_INDEMNIZACION}': bool(ind90),
            f'incluir_{CONCEPTO_INDEMNIZACION_20}': bool(ind20),
            f'incluir_{CONCEPTO_PRIMA_ANTIGUEDAD}': bool(pa),
        }

    def conceptos_para_tipo(self, tipo_despido: Optional[str],
                            años_completos: int = 0) -> Dict[str, bool]:
        """Conceptos que proceden según la causa de separación.

        Devuelve el mapa completo `incluir_<concepto>` para que pueda usarse
        tal cual como `conceptos_seleccionados` de `calcular_todo()`.
        """
        resultado = {f'incluir_{c}': True for c in _TODAS_LAS_PRESTACIONES}
        if not tipo_despido:
            return resultado

        ind90, ind20, pa = POR_TIPO_DESPIDIO.get(
            tipo_despido, POR_TIPO_DESPIDIO['injustificado'])

        if pa == INDICADOR_PRIMA_ANTIGUEDAD_POR_ANTIGUEDAD:
            pa = años_completos >= self.prima_antiguedad_anios_voluntaria

        resultado[f'incluir_{CONCEPTO_INDEMNIZACION}'] = bool(ind90)
        resultado[f'incluir_{CONCEPTO_INDEMNIZACION_20}'] = bool(ind20)
        resultado[f'incluir_{CONCEPTO_PRIMA_ANTIGUEDAD}'] = bool(pa)
        return resultado


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _dec(valor, defecto) -> Decimal:
    """Convierte a Decimal; si viene vacío devuelve el defecto."""
    if valor is None or valor == '':
        return defecto
    return Decimal(str(valor))


def _vigente_por_anio(tabla: Dict[int, int], anio: int, defecto: int) -> int:
    """Valor de una tabla gradual por año.

    Años anteriores al primer escalón usan el primer valor conocido; años
    posteriores al último escalón mantienen el valor final (la reducción
    gradual ya no requiere más cambios normativos, pero queda parametrizable).
    """
    if not tabla:
        return defecto
    if anio in tabla:
        return tabla[anio]
    if anio < min(tabla):
        return tabla[min(tabla)]
    return tabla[max(tabla)]