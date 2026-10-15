"""Capítulo 6 — PRUEBAS.

El capítulo más extenso del estándar (págs. 9-14, cuatro de las catorce
páginas).  Es casi todo plantilla: la estructura se repite y sólo cambian los
nombres de los demandados, el actor y el periodo laboral.

Orden del estándar del despacho:

    1. CONFESIONAL POR POSICIONES (moral)             arts. 788, 789 LFT
    2. CONFESIONAL POR POSICIONES (fuente de trabajo) arts. 788, 789 LFT
    3. INTERROGATORIO LIBRE
    4. INSPECCIÓN OCULAR — recibos/talones/nómina (moral)   arts. 804, 828, 784-VIII
    5. INSPECCIÓN OCULAR — recibos/talones/nómina (fuente)  arts. 804, 828, 784-VIII
    6. INSPECCIÓN OCULAR — controles de asistencia (moral)  arts. 804, 828, 784-VIII
    7. INSPECCIÓN OCULAR — controles de asistencia (fuente) arts. 804, 828, 784-VIII
    8. DOCUMENTAL PRIVADA — contratos individuales de trabajo
    9. PRESUNCIONAL LEGAL Y HUMANA
   10. INSTRUMENTAL PÚBLICA DE ACTUACIONES

Las inspecciones se ofrecen POR CADA DEMANDADO (moral y fuente de trabajo):
es lo que hace el estándar y evita que la prueba se tenga por no ofrecida
respecto de uno de los codemandados.
"""

# Los tres objetos que persigue la inspección ocular de documentos de nómina
OBJETO_NOMINA = [
    'Que el hoy actor percibía de la hoy demandada el salario plasmado en el '
    'numeral de hechos respectivo de la presente demanda.',
    'Que entre el hoy actor y la demandada existió una relación laboral de '
    'carácter obrero-patronal.',
    'Que el hoy actor desempeñó sus labores para los aquí demandados laborando '
    'horas extras en términos de lo plasmado en la presente demanda.',
]

OBJETO_ASISTENCIA = [
    'Que el hoy actor laboró la jornada plasmada en la presente demanda durante '
    'el periodo objeto de la inspección solicitada.',
    'Que el hoy actor desempeñó sus labores para los aquí demandados laborando '
    'horas extras en términos de lo plasmado en la presente demanda.',
    'Que el hoy actor registró su asistencia diariamente en los horarios '
    'plasmados en el presente escrito de demanda durante todo el tiempo que '
    'duró la relación de trabajo, tanto al momento de presentarse a trabajar '
    'como a la hora de salida, registro que se encuentra en poder de la empresa '
    'demandada.',
    'Que el hoy actor le debía sujeción y subordinación a la demandada en '
    'términos de lo manifestado en el capítulo de hechos de la presente demanda.',
    'Que entre el hoy actor y la demandada existió una relación laboral de '
    'carácter obrero-patronal.',
]


def _documentos(datos: dict) -> list:
    """Documentos que el estándar pide inspeccionar, en orden."""
    return ['RECIBOS DE PAGO, TALONES DE RAYA y CONTROLES DE NÓMINA',
            'CONTROLES DE ASISTENCIA']


def _referencia_patron(datos: dict) -> str:
    """Nombre comercial con la fórmula de la fuente de trabajo."""
    nombre = (datos.get('demandada_nombre_comercial')
              or datos.get('demandada_razon_social') or '').strip()
    if nombre:
        return (f'QUIEN RESULTE RESPONSABLE DE LA FUENTE DE TRABAJO QUE EXPLOTA '
                f'EL NOMBRE COMERCIAL DE "{nombre}"')
    return 'QUIEN RESULTE RESPONSABLE DE LA FUENTE DE TRABAJO'


def pruebas(datos: dict, condiciones: dict) -> list:
    """Lista de pruebas; cada elemento es un dict con titulo/texto/objeto."""
    from ..demanda_generator import _fecha_espanol

    actor = datos.get('actor_nombre') or '[ACTOR]'
    razon_social = (datos.get('demandada_razon_social') or '[MORAL DEMANDADA]').strip()
    fuente = _referencia_patron(datos)
    domicilio = datos.get('demandada_domicilio') or '[DOMICILIO DE LA DEMANDADA]'
    desde = _fecha_espanol(datos.get('fecha_ingreso')).upper()
    hasta = _fecha_espanol(datos.get('fecha_despido')).upper()

    salida = []

    apercibimiento = (
        'con el apercibimiento de tenerlo confeso de todas y cada una de las '
        'posiciones que se lleguen a articular al momento del desahogo de esta '
        'probanza para el caso de que no comparezca sin causa justificada el '
        'día y hora que se señale exprofeso para su desahogo, debiendo '
        'notificársele en el domicilio procesal señalado en autos o por '
        'conducto de su apoderado legal, apercibido que en caso de '
        'incomparecencia se utilizarán en su contra los medios de apremio que '
        'establece la ley.'
    )
    fundamento_confesional = (
        'El apercibimiento que solicitamos tiene su apoyo en los artículos 788, '
        '789 y demás relativos de la Ley Federal del Trabajo. Esta prueba se '
        'ofrece para acreditar todos y cada uno de los hechos de la demanda, en '
        'especial las condiciones de trabajo y el despido del que fue objeto el '
        'hoy actor por conducto de la parte demandada; por lo que la presente '
        'probanza se relaciona con todos y cada uno de los hechos del escrito '
        'inicial de demanda y se ofrece para probar los hechos de la parte '
        'actora del presente juicio.'
    )

    # ─── 1. Confesional a cargo de la moral ───────────────────────────────
    if condiciones['prueba_confesional']:
        salida.append({
            'titulo': 'LA CONFESIONAL POR POSICIONES',
            'texto': (
                f'a cargo de la moral demandada "{razon_social}", ubicada en '
                f'{domicilio}, por conducto de su representante o apoderado '
                f'legal designado en autos del expediente en que se actúa, '
                f'{apercibimiento}'
            ),
            'objeto': fundamento_confesional,
        })

    # ─── 2. Confesional a cargo de la fuente de trabajo ───────────────────
    if condiciones['prueba_confesional']:
        salida.append({
            'titulo': 'LA CONFESIONAL POR POSICIONES',
            'texto': (
                f'a cargo de la demandada {fuente}, quien deberá comparecer de '
                f'forma personal o por conducto de su apoderado o representante '
                f'legal designado en autos del expediente en que se actúa, '
                f'{apercibimiento}'
            ),
            'objeto': fundamento_confesional,
        })

    # ─── 2b. Confesional para hechos propios (quien despidió) ─────────────
    if condiciones['prueba_confesional_propios']:
        quien = str(datos.get('despido_comunicado_por') or '').strip()
        salida.append({
            'titulo': 'LA CONFESIONAL PARA HECHOS PROPIOS',
            'texto': (
                f'a cargo de {quien}, quien deberá comparecer a absolver '
                f'posiciones de manera personal, {apercibimiento}'
            ),
            'objeto': ('Esta probanza se ofrece para acreditar los hechos '
                       'relativos al despido del que fue objeto el hoy actor.'),
        })

    # ─── 3. Interrogatorio libre ──────────────────────────────────────────
    if condiciones['prueba_interrogatorio_libre']:
        salida.append({
            'titulo': 'INTERROGATORIO LIBRE',
            'texto': (
                'A desahogar durante el desahogo de la prueba confesional como '
                'un complemento de la misma y no como una prueba autónoma, de '
                'acuerdo con los criterios jurisprudenciales sustentados por la '
                'Suprema Corte de Justicia de la Nación, mediante las preguntas '
                'abiertas que tendrán relación directa con la litis fijada '
                'dentro del presente procedimiento, a fin de llegar a la verdad '
                'de los hechos plasmados en el escrito inicial de demanda y que '
                'no deberá evadir, so pena de declararse confesa de las '
                'preguntas que evada o de aquellas que pretenda remitir a su '
                'escrito de contestación.'
            ),
            'objeto': ('Esta probanza es para demostrar en su totalidad los '
                       'contenidos de los hechos de la presente demanda.'),
        })

    # ─── 4-7. Inspecciones oculares, una por cada demandado y documento ───
    if condiciones['prueba_inspeccion']:
        documentos_nomina, documentos_asistencia = _documentos(datos)
        for demandado in (f'la moral demandada "{razon_social}"', f'la demandada {fuente}'):
            salida.append({
                'titulo': 'LA INSPECCIÓN OCULAR',
                'texto': (
                    f'consistente en los {documentos_nomina} de los empleados de '
                    f'{demandado}, particularmente en lo referente al empleado '
                    f'{actor}, del periodo del {desde} al {hasta}, mismos '
                    f'documentos que en forma física o digital tiene la '
                    f'obligación de conservar y exhibir en juicio la parte '
                    f'patronal según lo señalado en el artículo 804 de la Ley '
                    f'Federal del Trabajo vigente. Solicitando se le requiera '
                    f'para que los presente en este H. Tribunal y sea en este '
                    f'recinto donde se lleve a cabo dicha inspección, en '
                    f'términos del artículo 828 de la Ley Federal del Trabajo, '
                    f'y en el supuesto de que le sea imposible presentarlos, sea '
                    f'el personal de esta Autoridad quien se dirija al domicilio '
                    f'de la fuente de trabajo ubicada en {domicilio}. Lo '
                    f'anterior en términos del artículo 784 fracción VIII de la '
                    f'Ley Federal del Trabajo.'
                ),
                'objeto': OBJETO_NOMINA,
            })
            salida.append({
                'titulo': 'LA INSPECCIÓN OCULAR',
                'texto': (
                    f'consistente en los {documentos_asistencia} de los '
                    f'empleados de {demandado}, particularmente en lo referente '
                    f'al empleado {actor}, del periodo del {desde} al {hasta}, '
                    f'mismos documentos que en forma física o digital tiene la '
                    f'obligación de conservar y exhibir en juicio la parte '
                    f'patronal según lo señalado en el artículo 804 de la Ley '
                    f'Federal del Trabajo vigente. Solicitando se le requiera '
                    f'para que los presente en este H. Tribunal y sea en este '
                    f'recinto donde se lleve a cabo dicha inspección, en '
                    f'términos del artículo 828 de la Ley Federal del Trabajo, '
                    f'y en el supuesto de que le sea imposible presentarlos, sea '
                    f'el personal de esta Autoridad quien se dirija al domicilio '
                    f'de la fuente de trabajo ubicada en {domicilio}, lugar '
                    f'donde el suscrito actor fue contratado y donde se '
                    f'encuentra el registro de su expediente laboral y registros '
                    f'de entrada, salida y días laborados. Lo anterior en '
                    f'términos del artículo 784 fracción VIII de la Ley Federal '
                    f'del Trabajo.'
                ),
                'objeto': OBJETO_ASISTENCIA,
            })

    # ─── 8. Documental privada (contratos individuales) ───────────────────
    if condiciones['prueba_documental']:
        salida.append({
            'titulo': 'LA DOCUMENTAL PRIVADA',
            'texto': (
                f'consistente en los CONTRATOS INDIVIDUALES DE TRABAJO '
                f'celebrados entre la moral demandada "{razon_social}" y el '
                f'empleado {actor}, documento que obra en poder de la parte '
                f'demandada, por lo que se solicita a este H. Tribunal Laboral '
                f'requiera a la parte demandada para que lo exhiba en original '
                f'durante el desahogo de la presente prueba.'
            ),
            'objeto': [
                'La existencia de la relación obrero-patronal entre el actor y '
                'la parte demandada.',
                'La fecha de ingreso del actor a laborar para la parte demandada.',
                'El puesto o categoría para el cual fue contratado el actor.',
                'El salario pactado por la prestación de los servicios '
                'personales y subordinados del actor.',
                'La jornada y horario de trabajo pactados entre las partes.',
                'Los días de trabajo y días de descanso pactados.',
                'Las demás condiciones y términos bajo los cuales se desarrolló '
                'la relación laboral entre el actor y la parte demandada.',
            ],
        })

    # ─── 8b. Documental con los documentos del cliente ────────────────────
    documentos_cliente = str(datos.get('documentos_prueba') or '').strip()
    if documentos_cliente:
        salida.append({
            'titulo': 'LA DOCUMENTAL',
            'texto': (
                f'consistente en los documentos que se acompañan y que obran en '
                f'poder del suscrito, los cuales se describen a continuación: '
                f'{documentos_cliente}'
            ),
            'objeto': ('acreditar las condiciones de trabajo y las '
                       'circunstancias del despido narradas en el capítulo de '
                       'hechos.'),
        })

    # ─── 9. Presuncional legal y humana ───────────────────────────────────
    if condiciones['prueba_presuncional']:
        salida.append({
            'titulo': 'LA PRESUNCIONAL LEGAL Y HUMANA',
            'texto': (
                'en todo aquello que producto de la tramitación del presente '
                'juicio beneficie a los intereses del actor, para probar '
                'aquellos hechos que no son susceptibles de demostrarse de '
                'manera directa. Este medio de prueba se ofrece adminiculado '
                'con las demás pruebas del presente capítulo para demostrar la '
                'totalidad del contenido de los hechos del presente escrito de '
                'demanda.'
            ),
            'objeto': 'acreditar la totalidad de los hechos de la demanda.',
        })

    # ─── 10. Instrumental pública de actuaciones ──────────────────────────
    if condiciones['prueba_instrumental']:
        salida.append({
            'titulo': 'LA INSTRUMENTAL PÚBLICA DE ACTUACIONES',
            'texto': (
                'consistente en todo lo actuado en el presente juicio, y que '
                'beneficie a los intereses del actor. Este medio de prueba se '
                'ofrece adminiculado con las demás pruebas del presente '
                'capítulo para demostrar la totalidad del contenido de los '
                'hechos del presente escrito de demanda.'
            ),
            'objeto': 'acreditar la totalidad de los hechos de la demanda.',
        })

    return salida
