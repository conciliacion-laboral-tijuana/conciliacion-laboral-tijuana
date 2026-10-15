"""Capítulo 2 — DEMANDADOS.

El estándar del despacho demanda SIEMPRE a dos sujetos (pág. 2):

    I.-  A QUIEN RESULTE RESPONSABLE DE LA FUENTE DE TRABAJO QUE EXPLOTA EL
         NOMBRE COMERCIAL DE "{nombre comercial}" ubicada en: {domicilio},
         misma que puede ser notificada y emplazada a juicio en el mismo
         domicilio antes mencionado.

    II.- A la MORAL "{razón social}", ubicada en {domicilio}, misma que puede
         ser notificada y emplazada a juicio en el mismo domicilio antes
         mencionado.

El primer numeral cubre al patrón real (persona física o moral sin
personalidad jurídica reconocida); el segundo a la persona moral.  Ambos se
requieren para que la condena alcance a quien realmente explota la fuente de
trabajo y para pedir la solidaridad cuando aplique.
"""


def _domicilio_demandado(datos: dict) -> str:
    return datos.get('demandada_domicilio') or '[DOMICILIO DE LA DEMANDADA]'


def demandados(datos: dict) -> list:
    """Lista de numerales del capítulo de demandados."""
    razon_social = (datos.get('demandada_razon_social')
                    or datos.get('demandada_nombre_comercial') or '').strip()
    nombre_comercial = (datos.get('demandada_nombre_comercial')
                        or razon_social).strip()
    domicilio = _domicilio_demandado(datos)

    cierre = ('misma que puede ser notificada y emplazada a juicio en el mismo '
              'domicilio antes mencionado.')

    numerales = []

    if nombre_comercial:
        numerales.append(
            f'A QUIEN RESULTE RESPONSABLE DE LA FUENTE DE TRABAJO QUE EXPLOTA '
            f'EL NOMBRE COMERCIAL DE "{nombre_comercial}" ubicada en: '
            f'{domicilio}, {cierre}'
        )

    if razon_social:
        numerales.append(
            f'A la MORAL "{razon_social}", ubicada en {domicilio}, {cierre}'
        )

    return numerales


def introduccion(tipo_despido: str = 'injustificado') -> str:
    """Párrafo que introduce las prestaciones reclamadas."""
    narrativas = {
        'injustificado': (
            'Demandando en virtud del despido injustificado del que fui objeto '
            'cuando estaba en cumplimiento de la relación obrero-patronal, sin '
            'comunicarme los motivos específicos de su decisión, despido que me '
            'otorga pleno derecho de reclamar el pago y cumplimiento de las '
            'siguientes prestaciones que me reconoce la Ley Federal del Trabajo:'
        ),
        'rescision': (
            'Demandando en virtud de la rescisión de la relación laboral '
            'imputable al patrón, por las causas graves de incumplimiento que '
            'se narran en el capítulo de hechos, lo que me otorga pleno derecho '
            'de reclamar el pago y cumplimiento de las siguientes prestaciones '
            'que me reconoce la Ley Federal del Trabajo:'
        ),
        'voluntario': (
            'Demandando en virtud de la terminación de la relación laboral, '
            'reclamando el pago de las prestaciones proporcionales que me '
            'reconoce la Ley Federal del Trabajo:'
        ),
        'justificado': (
            'Demandando en virtud de la terminación de la relación laboral, '
            'reclamando el pago y cumplimiento de las siguientes prestaciones '
            'que me reconoce la Ley Federal del Trabajo:'
        ),
        'otro': (
            'Demandando en virtud de la terminación de la relación laboral, '
            'reclamando el pago y cumplimiento de las siguientes prestaciones '
            'que me reconoce la Ley Federal del Trabajo:'
        ),
    }
    return narrativas.get(tipo_despido, narrativas['injustificado'])
