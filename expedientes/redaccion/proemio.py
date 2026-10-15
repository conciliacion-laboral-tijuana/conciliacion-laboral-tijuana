"""Capítulo 1 — PROEMIO.

Estructura del estándar del despacho (pág. 1):

    PROEMIO.
    C. {actor}, con nacionalidad mexicana, mayor de edad, por mi propio
    derecho y señalando como domicilio para oír toda clase de notificaciones
    el ubicado en {domicilio}, y designando como mis apoderados legales a los
    CC., Lic. ... con número de cédula profesional ... respectivamente,
    expedidas por la Dirección General de Profesiones de la Secretaría de
    Educación Pública, a quienes les confiero las más amplias facultades de
    representación [...] autorizando para oír y recibir toda clase de
    notificaciones a las CC. ... personalidad que solicito les sea reconocida
    en los términos de los Artículos 692, frac. I, 693 y 696 de la Ley
    Federal del Trabajo.

    Que, con fundamento en lo establecido en los Artículos 123 Constitucional
    fracción XXII, 48, 50, 84 y demás relativos de la Ley Federal del Trabajo,
    y como lo acredito con el documento de CONSTANCIA DE NO CONCILIACIÓN,
    documental que se exhibe en la presente demanda.
"""

FACULTADES = (
    'a quienes les confiero las más amplias facultades de representación, '
    'para que se apersonen en mi nombre de manera conjunta o separada de '
    'manera indistinta a todas y cada una de las etapas del juicio, opongan '
    'excepciones dilatorias y perentorias, contra demanden, asistan a las '
    'audiencias de Ley, den por concluido el juicio mediante arreglo '
    'conciliatorio en cualquier estado que se guarde, contesten '
    'reconvenciones oponiendo las excepciones procedentes; ratifiquen, '
    'amplíen o desistan parcialmente del escrito de demanda; rindan toda '
    'clase de pruebas, reconozcan firmas y documentos; tachen de falsos los '
    'que se presenten; articulen y absuelvan posiciones; presenten testigos; '
    'repregunten y tachen a los testigos de la parte contraria; presenten '
    'peritos y objeten los de la contraria; recusen a los miembros del '
    'tribunal con causa o sin ella; reciban todo tipo de notificaciones; '
    'ejecuten embargos y me representen en las diligencias de embargo; pidan '
    'el remate de los bienes embargados; celebren convenios, reciban o '
    'consignen valores (cheques, vales, pagarés, transferencias electrónicas '
    'de dinero y efectivo) y para que reciban pagos en términos del artículo '
    '100 de la Ley Federal del Trabajo; den por pagado el laudo y se desistan '
    'del mismo; interpongan todo tipo de recursos procedentes y en su caso '
    'promuevan el Juicio de Amparo; hagan todo tipo de promociones que en su '
    'concepto me favorezcan; se desistan de cualquier tipo de juicio o '
    'recurso, autorizándolos expresamente para que se desistan de la Demanda '
    'y de la Acción, así como todas las facultades que de acuerdo con la Ley '
    'requieran cláusula especial'
)


def _lista_nombres(personas: list) -> str:
    """'A, B y C' — con coma final antes de 'y' como en el estándar."""
    nombres = [p.get('nombre', '').strip() for p in personas if p.get('nombre')]
    if not nombres:
        return ''
    if len(nombres) == 1:
        return nombres[0]
    return ', '.join(nombres[:-1]) + ' y ' + nombres[-1]


def _lista_cedulas(personas: list) -> str:
    """'7593879, 6223421 y 6860593' — cédulas en el mismo orden."""
    cedulas = [str(p.get('cedula', '')).strip() for p in personas]
    cedulas = [c for c in cedulas if c]
    if not cedulas:
        return ''
    if len(cedulas) == 1:
        return cedulas[0]
    return ', '.join(cedulas[:-1]) + ' y ' + cedulas[-1]


def proemio(datos: dict) -> str:
    """Texto del proemio."""
    actor = datos.get('actor_nombre', '')
    nacionalidad = datos.get('actor_nacionalidad') or 'mexicana'
    domicilio = datos.get('actor_domicilio') or '[DOMICILIO PARA NOTIFICACIONES]'

    partes = [
        f'C. {actor}, con nacionalidad {nacionalidad}, mayor de edad, por mi '
        f'propio derecho y señalando como domicilio para oír toda clase de '
        f'notificaciones el ubicado en {domicilio}'
    ]

    apoderados = datos.get('apoderados') or []
    if apoderados:
        nombres = _lista_nombres(apoderados)
        cedulas = _lista_cedulas(apoderados)
        fragmento = f' y designando como mis apoderados legales a los CC., Lic. {nombres}'
        if cedulas:
            fragmento += f' con número de cédula profesional {cedulas}'
            fragmento += (' respectivamente, expedidas por la Dirección General '
                          'de Profesiones de la Secretaría de Educación Pública,')
        fragmento += f' {FACULTADES}'
        partes.append(fragmento)

    autorizados = datos.get('autorizados') or []
    if autorizados:
        nombres_aut = _lista_nombres(autorizados)
        partes.append(
            f'y autorizando para oír y recibir toda clase de notificaciones a '
            f'las CC. {nombres_aut}, personalidad que solicito les sea '
            f'reconocida en los términos de los Artículos 692, frac. I, 693 y '
            f'696 de la Ley Federal del Trabajo'
        )

    texto = ', '.join(partes) + '. Ante este H. Tribunal, con el debido '
    texto += 'respeto, comparezco a exponer:'

    fundamento = (
        'Que, con fundamento en lo establecido en los Artículos 123 '
        'Constitucional fracción XXII, 48, 50, 84 y demás relativos de la Ley '
        'Federal del Trabajo'
    )
    if datos.get('folio'):
        fundamento += (
            ', y como lo acredito con el documento de CONSTANCIA DE NO '
            'CONCILIACIÓN, documental que se exhibe en la presente demanda'
        )
    else:
        fundamento += (
            ', y como lo acreditaré con la CONSTANCIA DE NO CONCILIACIÓN que '
            'se exhibe en la presente demanda'
        )
    fundamento += '.'

    return f'{texto}\n\n{fundamento}'
