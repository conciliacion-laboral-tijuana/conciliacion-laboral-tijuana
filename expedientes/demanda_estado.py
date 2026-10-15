"""Estado de la demanda: qué le falta para poder presentarse.

Este módulo es la ÚNICA fuente de verdad de tres cosas que antes estaban
contradiciéndose entre sí:

1. **Huecos del documento.** Cada dato que el motor de redacción necesita y que
   hoy está vacío. El hueco sabe en qué capítulo impacta y qué campo de captura
   lo llena, así que la pantalla del documento puede señalar el hueco *en su
   lugar* y llevar de vuelta al campo.
2. **Decisiones del abogado.** Lo que no es un dato sino una elección jurídica
   (modalidad de la separación, acción del artículo 48, confirmación del IMSS,
   tipo de separación) y que no puede quedar en el valor por defecto.
3. **Coherencias.** Los contrastes entre lo capturado y lo que el documento va a
   afirmar. Incluye las *sustituciones silenciosas*: cuando un dato falta, el
   motor no deja un `[HUECO]` visible, escribe un texto genérico o el domicilio
   de la demandada. El documento se lee completo y afirma algo que nadie
   confirmó. Eso es lo que este módulo hace visible.

Los tres espacios de la pantalla (datos · estrategia · documento) y el conteo
del encabezado salen de aquí, para que el semáforo no pueda mentir.

Regla de diseño: este módulo NO redacta ni calcula. Sólo compara lo que el
motor (`expedientes.redaccion`) dice que consume contra lo que hay capturado.
"""

from .redaccion import datos_de_expediente, evaluar_condiciones

# ─── Los tres espacios de trabajo ────────────────────────────────────────────

ESPACIOS = (
    ('datos', 'Datos del caso',
     'Actor, relación laboral, patrón y representación. Nada jurídico.'),
    ('estrategia', 'Estrategia y prestaciones',
     'Cómo se separó, qué se reclama, con qué pruebas y con qué importes.'),
    ('documento', 'Documento',
     'La demanda capítulo por capítulo, con lo que falta señalado en su lugar.'),
)

# ─── Los siete capítulos del estándar del despacho ───────────────────────────

CAPITULOS = (
    ('proemio', 'Proemio', 'Actor, domicilio para notificaciones y representación.'),
    ('demandados', 'Demandados', 'Fuente de trabajo y moral demandada.'),
    ('prestaciones', 'Prestaciones', 'Importes del cálculo aprobado, en número y letra.'),
    ('jornada', 'Jornada y horas extras', 'Anexo con la tabla semanal.'),
    ('hechos', 'Hechos', 'Contratación, jornada, separación y hechos condicionales.'),
    ('pruebas', 'Pruebas', 'Confesional, documental, testimonial e inspección.'),
    ('derecho', 'Derecho', 'Fundamentos. Texto fijo del despacho: sólo se verifica.'),
    ('firma', 'Firma', 'El nombre del actor al calce, igual que en el proemio.'),
)

# Capítulos que no dependen de la captura caso por caso: son plantilla.
CAPITULOS_FIJOS = ('derecho',)


def capitulos_de(requisito):
    """Capítulos donde impacta un requisito.

    Un requisito declara `capitulo` (uno) o `capitulos` (varios). El nombre del
    actor, por ejemplo, aparece en el proemio, en las pruebas y otra vez en la
    firma, así que un dato faltante se señala en los tres.
    """
    varios = requisito.get('capitulos')
    if varios:
        return tuple(varios)
    unico = requisito.get('capitulo')
    return (unico,) if unico else ()


def espacio_de_bloque(bloque, por_defecto='datos'):
    """En qué espacio vive un bloque de captura (`?seccion=`)."""
    for requisito in REQUISITOS:
        if requisito['bloque'] == bloque:
            return requisito['espacio']
    return por_defecto


def _sin_condicion(datos, condiciones):
    return True


def _modalidad_verbal(datos, condiciones):
    """La hora del despido sólo se narra cuando la separación fue verbal."""
    return (datos.get('modalidad_despido') or 'verbal') == 'verbal'


def _modalidad_escrito(datos, condiciones):
    return (datos.get('modalidad_despido') or '') == 'escrito'


# ─── Requisitos ──────────────────────────────────────────────────────────────
#
# Campos de cada requisito:
#   clave        identificador estable (data-attributes y pruebas)
#   etiqueta     texto humano del hueco
#   dato         clave del dict del motor que se revisa (None si es una decisión)
#   crudo        atributo del Cliente que se revisa cuando el adaptador aplica un
#                valor por defecto y el `dato` nunca llega vacío
#   crudo_exp    atributo del Expediente, para el mismo caso
#   minimo       longitud mínima para considerar el dato completo
#   campos       campos del formulario que lo capturan (para el enlace)
#   ancla        fragmento al que se salta para capturarlo
#   espacio      datos | estrategia
#   bloque       id del bloque en pantalla (#sec-<bloque>)
#   capitulo     capítulo del documento donde impacta
#   marcador     texto literal que el motor escribe cuando falta (si lo escribe)
#   sustituto    texto genérico que el motor usa en su lugar (si lo usa)
#   obligatorio  lo exige la presentación del escrito
#   decision     es una elección del abogado, no un dato del cliente
#   condicion    callable(datos, condiciones) → sólo aplica en ciertos casos
#   ayuda        por qué importa, para el tooltip
#
# `accion_preferida` (art. 48 LFT) NO está aquí a propósito: el modelo la crea
# con `default='indemnizacion'`, así que nunca está «vacía». Se muestra en
# Estrategia con su advertencia (`advertencias_accion_cliente`) pero no puede
# contar como dato faltante sin inventar un estado que el sistema no guarda.

_REQUISITOS_CRUDOS = (
    # ══════════════════ Espacio: datos · actor ══════════════════
    {
        'clave': 'actor_nombre', 'etiqueta': 'Nombre completo del actor',
        'dato': 'actor_nombre', 'campos': ('nombre',), 'ancla': 'id_nombre',
        # Aparece tres veces en el escrito: carátula/proemio, pruebas y firma.
        'capitulos': ('proemio', 'pruebas', 'firma'),
        'espacio': 'datos', 'bloque': 'trabajador',
        'marcador': '[ACTOR]', 'obligatorio': True,
        'ayuda': 'Va en el proemio, en los hechos y en la firma.',
    },
    {
        'clave': 'actor_curp', 'etiqueta': 'CURP', 'dato': 'actor_curp', 'minimo': 15,
        'campos': ('curp',), 'ancla': 'id_curp',
        'espacio': 'datos', 'bloque': 'trabajador', 'capitulo': 'proemio',
        'obligatorio': True,
        'ayuda': 'Identifica al actor en el proemio.',
    },
    {
        'clave': 'actor_domicilio', 'etiqueta': 'Domicilio para notificaciones',
        'dato': 'actor_domicilio',
        'campos': ('direccion_calle', 'direccion_numero', 'direccion_colonia', 'direccion_cp'),
        'ancla': 'grupo-domicilio-actor',
        'espacio': 'datos', 'bloque': 'trabajador', 'capitulo': 'proemio',
        'marcador': '[DOMICILIO PARA NOTIFICACIONES]', 'obligatorio': True,
        'ayuda': 'Es el domicilio donde el Tribunal notificará al actor.',
    },
    {
        'clave': 'actor_ciudad', 'etiqueta': 'Ciudad de contratación',
        'dato': 'actor_ciudad', 'crudo': 'ciudad', 'campos': ('ciudad',), 'ancla': 'id_ciudad',
        'espacio': 'datos', 'bloque': 'trabajador', 'capitulo': 'hechos',
        'sustituto': 'Tijuana',
        'ayuda': 'El hecho 1 afirma dónde fue contratado.',
    },
    {
        'clave': 'actor_nacionalidad', 'etiqueta': 'Nacionalidad',
        'dato': 'actor_nacionalidad', 'crudo': 'nacionalidad',
        'campos': ('nacionalidad',), 'ancla': 'id_nacionalidad',
        'espacio': 'datos', 'bloque': 'trabajador', 'capitulo': 'proemio',
        'sustituto': 'mexicana',
    },

    # ══════════════════ Espacio: datos · relación laboral ══════════════════
    {
        'clave': 'puesto', 'etiqueta': 'Puesto desempeñado', 'dato': 'puesto',
        'campos': ('puesto',), 'ancla': 'id_puesto',
        'espacio': 'datos', 'bloque': 'laboral', 'capitulo': 'hechos',
        'marcador': '[PUESTO DESEMPEÑADO]', 'obligatorio': True,
    },
    {
        'clave': 'salario', 'etiqueta': 'Salario mensual', 'dato': 'salario',
        'campos': ('salario',), 'ancla': 'id_salario',
        'espacio': 'datos', 'bloque': 'laboral', 'capitulo': 'prestaciones',
        'obligatorio': True,
        'ayuda': 'Sin salario no hay cálculo: es la base de todas las prestaciones.',
    },
    {
        'clave': 'fecha_ingreso', 'etiqueta': 'Fecha de ingreso', 'dato': 'fecha_ingreso',
        'campos': ('fecha_ingreso',), 'ancla': 'id_fecha_ingreso',
        'espacio': 'datos', 'bloque': 'laboral', 'capitulo': 'hechos',
        'marcador': '[FECHA]', 'obligatorio': True,
    },
    {
        'clave': 'fecha_salida', 'etiqueta': 'Fecha de separación', 'dato': 'fecha_despido',
        'campos': ('fecha_salida',), 'ancla': 'id_fecha_salida',
        'espacio': 'datos', 'bloque': 'laboral', 'capitulo': 'hechos',
        'marcador': '[FECHA]', 'obligatorio': True,
    },
    {
        'clave': 'actividades', 'etiqueta': 'Actividades desempeñadas', 'dato': 'actividades',
        'campos': ('actividades',), 'ancla': 'id_actividades',
        'espacio': 'datos', 'bloque': 'laboral', 'capitulo': 'hechos',
        'ayuda': 'Sin actividades, el hecho del contrato no describe las funciones.',
    },
    {
        'clave': 'dias_trabajo', 'etiqueta': 'Días de trabajo y descanso',
        'dato': 'dias_trabajo', 'campos': ('dias_trabajo', 'dia_descanso'),
        'ancla': 'id_dias_trabajo',
        'espacio': 'datos', 'bloque': 'laboral', 'capitulo': 'hechos',
        'sustituto': 'lunes a viernes y descanso sábado y domingo',
        'ayuda': 'Si falta, los hechos AFIRMAN «lunes a viernes» sin que nadie lo '
                 'haya confirmado.',
    },
    {
        'clave': 'horario', 'etiqueta': 'Horario de entrada y salida',
        'dato': 'horario_entrada', 'campos': ('horario_entrada', 'horario_salida'),
        'ancla': 'id_horario_entrada',
        'espacio': 'datos', 'bloque': 'laboral', 'capitulo': 'hechos',
        'ayuda': 'Define el hecho de la jornada y el anexo de horas extras.',
    },

    # ══════════════════ Espacio: datos · patrón ══════════════════
    {
        'clave': 'empresa', 'etiqueta': 'Nombre del patrón', 'dato': 'demandada_nombre_comercial',
        'campos': ('empresa',), 'ancla': 'id_empresa',
        'espacio': 'datos', 'bloque': 'empresa', 'capitulo': 'hechos',
        'marcador': '[EMPRESA DEMANDADA]', 'obligatorio': True,
    },
    {
        'clave': 'empresa_razon_social', 'etiqueta': 'Razón social del patrón',
        'dato': 'demandada_razon_social', 'campos': ('empresa_razon_social',),
        'ancla': 'id_empresa_razon_social',
        'espacio': 'datos', 'bloque': 'empresa', 'capitulo': 'demandados',
        'marcador': '[MORAL DEMANDADA]', 'obligatorio': True,
        'ayuda': 'Es la persona moral a la que se demanda.',
    },
    {
        'clave': 'empresa_domicilio', 'etiqueta': 'Domicilio del patrón',
        # Se revisa el campo crudo: `demandada_domicilio` NUNCA llega vacío
        # porque el adaptador siempre agrega «TIJUANA, BAJA CALIFORNIA».
        'crudo': 'empresa_calle',
        'campos': ('empresa_calle', 'empresa_numero', 'empresa_colonia', 'empresa_cp'),
        'ancla': 'grupo-domicilio-empresa',
        'espacio': 'datos', 'bloque': 'empresa', 'capitulo': 'demandados',
        'obligatorio': True,
        'sustituto': 'TIJUANA, BAJA CALIFORNIA',
        'ayuda': 'Sin calle, el escrito ubica al patrón sólo en «Tijuana, Baja '
                 'California».',
    },

    # ══════════════════ Espacio: datos · representación ══════════════════
    {
        'clave': 'apoderados', 'etiqueta': 'Apoderados que firman (con cédula)',
        'dato': 'apoderados', 'campos': (), 'ancla': 'sec-representacion',
        'espacio': 'datos', 'bloque': 'representacion', 'capitulo': 'proemio',
        # NO es obligatorio: el proemio omite el fragmento cuando no hay
        # apoderados, y una demanda puede presentarse por propio derecho.
        'obligatorio': False,
        'ayuda': 'El proemio los lista con su número de cédula profesional. Sin ellos, '
                 'el actor comparece por su propio derecho.',
    },

    # ══════════════════ Espacio: estrategia · separación ══════════════════
    {
        'clave': 'tipo_despido', 'etiqueta': 'Tipo de separación',
        'crudo_exp': 'tipo_despido', 'campos': (), 'ancla': 'grupo-tipo-despido',
        'espacio': 'estrategia', 'bloque': 'despido', 'capitulo': 'hechos',
        'obligatorio': True, 'decision': True,
        'ayuda': 'Define la carátula, los hechos y qué prestaciones proceden.',
    },
    {
        'clave': 'modalidad_despido', 'etiqueta': 'Modalidad de la separación',
        'dato': 'modalidad_despido', 'crudo': 'modalidad_despido',
        'campos': ('modalidad_despido',), 'ancla': 'grupo-modalidad',
        'espacio': 'estrategia', 'bloque': 'despido', 'capitulo': 'hechos',
        'sustituto': 'despido verbal', 'obligatorio': True, 'decision': True,
        'ayuda': 'Cambia el redactado del hecho central y el alegato del art. 47 LFT.',
    },
    {
        'clave': 'hora_despido', 'etiqueta': 'Hora de la separación',
        'dato': 'hora_despido', 'campos': ('hora_despido',), 'ancla': 'id_hora_despido',
        'espacio': 'estrategia', 'bloque': 'despido', 'capitulo': 'hechos',
        'condicion': _modalidad_verbal,
        'ayuda': 'Si falta, el hecho narra la fecha pero omite la hora.',
    },
    {
        'clave': 'despido_lugar', 'etiqueta': 'Lugar donde ocurrió la separación',
        'dato': 'despido_lugar', 'campos': ('despido_lugar',), 'ancla': 'id_despido_lugar',
        'espacio': 'estrategia', 'bloque': 'despido', 'capitulo': 'hechos',
        'sustituto': 'el domicilio de la demandada',
        'ayuda': 'Si falta, los hechos dicen que ocurrió en el domicilio de la '
                 'demandada.',
    },
    {
        'clave': 'despido_comunicado_por', 'etiqueta': 'Quién comunicó la separación',
        'dato': 'despido_comunicado_por', 'campos': ('despido_comunicado_por',),
        'ancla': 'id_despido_comunicado_por',
        'espacio': 'estrategia', 'bloque': 'despido', 'capitulo': 'hechos',
        'sustituto': '«el personal de la demandada»',
        'ayuda': 'Si falta, los hechos atribuyen el aviso a un genérico y se pierde '
                 'la prueba confesional a su cargo.',
    },
    {
        'clave': 'despido_frase', 'etiqueta': 'Qué le dijeron al separarlo',
        'dato': 'despido_frase', 'campos': ('despido_frase',), 'ancla': 'id_despido_frase',
        'espacio': 'estrategia', 'bloque': 'despido', 'capitulo': 'hechos',
        'sustituto': '«quedaba separado de mi puesto de trabajo»',
        'ayuda': 'La frase textual es el hecho más difícil de rebatir.',
    },
    {
        'clave': 'despido_documento_motivo', 'etiqueta': 'Causa que consigna el documento',
        'dato': 'despido_documento_motivo', 'campos': ('despido_documento_motivo',),
        'ancla': 'id_despido_documento_motivo',
        'espacio': 'estrategia', 'bloque': 'despido', 'capitulo': 'hechos',
        'condicion': _modalidad_escrito,
        'ayuda': 'Si se entregó aviso escrito, hay que transcribir la causa que alega.',
    },
    {
        'clave': 'imss_confirmado', 'etiqueta': 'Confirmar el registro ante el IMSS',
        'dato': 'imss_confirmado', 'campos': ('imss_confirmado',),
        'ancla': 'grupo-imss',
        'espacio': 'estrategia', 'bloque': 'imss', 'capitulo': 'hechos',
        'obligatorio': True, 'decision': True,
        'ayuda': 'Sin confirmar no se alega nada del IMSS: afirmarlo sería inventar '
                 'un hecho.',
    },

    # ══════════════════ Espacio: estrategia · prestaciones ══════════════════
    {
        'clave': 'calculo_aprobado', 'etiqueta': 'Importes calculados y aprobados',
        'campos': (), 'ancla': 'sec-prestaciones',
        'espacio': 'estrategia', 'bloque': 'prestaciones', 'capitulo': 'prestaciones',
        'marcador': '[MONTO]', 'obligatorio': True,
        'ayuda': 'La demanda no inventa montos: si el cálculo no está aprobado, los '
                 'numerales salen sin cifra.',
    },
)


def _normalizar(requisitos):
    """Completa las claves opcionales: todo requisito tiene la misma forma.

    Sin esto, cada consumidor tendría que recordar qué claves son opcionales
    (`r['obligatorio']` reventaba con KeyError en los que no la declaraban).
    """
    base = {
        'dato': None, 'crudo': None, 'crudo_exp': None, 'minimo': None,
        'campos': (), 'capitulo': None, 'capitulos': (), 'marcador': None,
        'sustituto': '', 'obligatorio': False, 'decision': False,
        'condicion': _sin_condicion, 'ayuda': '',
    }
    normalizados = []
    for requisito in requisitos:
        completo = dict(base)
        completo.update(requisito)
        normalizados.append(completo)
    return tuple(normalizados)


REQUISITOS = _normalizar(_REQUISITOS_CRUDOS)


# ─── Evaluación ──────────────────────────────────────────────────────────────

def _presente(requisito, datos, cliente, expediente, calculo_listo):
    """¿El requisito está satisfecho con lo que hay capturado?

    Se revisa primero el campo crudo cuando el adaptador aplica un valor por
    defecto (`modalidad_despido` siempre llega como 'verbal', `actor_ciudad`
    como 'Tijuana'): si no, el hueco nunca aparecería aunque el abogado no haya
    elegido nada.
    """
    if requisito['clave'] == 'calculo_aprobado':
        return bool(calculo_listo)
    if requisito.get('crudo'):
        return bool(getattr(cliente, requisito['crudo'], None))
    if requisito.get('crudo_exp'):
        return bool(getattr(expediente, requisito['crudo_exp'], None))
    if requisito.get('dato') is not None:
        valor = datos.get(requisito['dato'])
        minimo = requisito.get('minimo')
        if minimo is not None:
            return len(str(valor or '')) >= minimo
        # bool() sirve para texto, fechas, listas y Decimal (Decimal('0') es falso).
        return bool(valor)
    return True


def _huecos(requisitos, datos, condiciones, cliente, expediente, calculo_listo):
    pendientes = []
    for requisito in requisitos:
        condicion = requisito.get('condicion', _sin_condicion)
        if not condicion(datos, condiciones):
            continue
        if _presente(requisito, datos, cliente, expediente, calculo_listo):
            continue
        pendientes.append(requisito)
    return pendientes


def _por_bloque(pendientes):
    """{bloque: {'total', 'faltantes', 'obligatorios', 'opcionales', 'decisiones', 'espacio'}}

    Se separa lo obligatorio de lo que sólo precisa el relato: un bloque no
    puede gritar «falta» por un dato opcional, pero tampoco puede ocultarlo.
    """
    bloques = {}
    for requisito in pendientes:
        entrada = bloques.setdefault(
            requisito['bloque'],
            {'total': 0, 'faltantes': [], 'obligatorios': 0, 'opcionales': 0,
             'decisiones': 0, 'espacio': requisito['espacio'],
             'faltantes_obligatorios': [], 'faltantes_opcionales': []},
        )
        entrada['total'] += 1
        entrada['faltantes'].append(requisito['etiqueta'])
        if requisito.get('obligatorio'):
            entrada['obligatorios'] += 1
            entrada['faltantes_obligatorios'].append(requisito['etiqueta'])
        else:
            entrada['opcionales'] += 1
            entrada['faltantes_opcionales'].append(requisito['etiqueta'])
        if requisito.get('decision'):
            entrada['decisiones'] += 1
    return bloques


def _por_capitulo(pendientes):
    """{capitulo: {'total', 'faltantes', 'obligatorios', 'opcionales', ...}}

    Igual que en los bloques, se separa lo obligatorio de lo que sólo precisa
    el relato: el capítulo no puede marcar «falta» por un dato opcional.
    """
    capitulos_pend = {}
    for requisito in pendientes:
        for clave in capitulos_de(requisito):
            entrada = capitulos_pend.setdefault(clave, {
                'total': 0, 'faltantes': [], 'obligatorios': 0, 'opcionales': 0,
                'faltantes_obligatorios': [], 'faltantes_opcionales': []})
            entrada['total'] += 1
            entrada['faltantes'].append(requisito['etiqueta'])
            if requisito.get('obligatorio'):
                entrada['obligatorios'] += 1
                entrada['faltantes_obligatorios'].append(requisito['etiqueta'])
            else:
                entrada['opcionales'] += 1
                entrada['faltantes_opcionales'].append(requisito['etiqueta'])
    return capitulos_pend


def estado(expediente, calculo_listo=False, datos=None):
    """Estado completo de la demanda de un expediente.

    Args:
        expediente: Expediente con `cliente` accesible.
        calculo_listo: el cálculo está vigente y aprobado (lo decide la vista,
            que es quien conoce la hoja de prestaciones).
        datos: dict del motor; si no se pasa, se arma con el adaptador.

    Returns:
        dict con huecos, decisiones, coherencias, estado por bloque y por
        capítulo, y el resumen que alimenta el encabezado.
    """
    cliente = expediente.cliente
    if datos is None:
        datos = datos_de_expediente(expediente)
    condiciones = evaluar_condiciones(datos)

    pendientes = _huecos(REQUISITOS, datos, condiciones, cliente, expediente, calculo_listo)
    huecos = [r for r in pendientes if not r.get('decision')]
    decisiones = [r for r in pendientes if r.get('decision')]
    obligatorios = [r for r in pendientes if r.get('obligatorio')]

    por_capitulo = _por_capitulo(pendientes)
    capitulos_estado = {}
    for clave, titulo, descripcion in CAPITULOS:
        info = por_capitulo.get(clave, {
            'total': 0, 'faltantes': [], 'obligatorios': 0, 'opcionales': 0,
            'faltantes_obligatorios': [], 'faltantes_opcionales': []})
        capitulos_estado[clave] = {
            'clave': clave, 'titulo': titulo, 'descripcion': descripcion,
            'faltantes': info['faltantes_obligatorios'],
            'faltantes_opcionales': info['faltantes_opcionales'],
            'total_faltantes': info['obligatorios'],
            'total_opcionales': info['opcionales'],
            'fijo': clave in CAPITULOS_FIJOS,
            'completo': info['obligatorios'] == 0,
        }

    return {
        'huecos': huecos,
        'decisiones': decisiones,
        'pendientes': pendientes,
        'por_bloque': _por_bloque(pendientes),
        'capitulos': capitulos_estado,
        'coherencias': coherencias(datos, condiciones, cliente,
                                   calculo_listo=calculo_listo),
        'resumen': {
            'huecos': len(huecos),
            'decisiones': len(decisiones),
            'pendientes': len(pendientes),
            'obligatorios': len(obligatorios),
            'opcionales': len(pendientes) - len(obligatorios),
            # «listo» = se puede presentar; «completo» = además no queda nada
            # por precisar en el relato.
            'listo': not obligatorios,
            'completo': not pendientes,
        },
    }


def bloqueos(expediente, calculo_listo=False, datos=None):
    """Etiquetas de lo que impide PRESENTAR el escrito (sólo lo obligatorio).

    Es la lista que usa el guard de la descarga. Redactar un borrador no se
    bloquea: lo que se bloquea es el documento que se lleva al Tribunal.
    """
    info = estado(expediente, calculo_listo=calculo_listo, datos=datos)
    return [r['etiqueta'] for r in info['pendientes'] if r['obligatorio']]


# ─── Coherencias (lo que el documento afirmará) ──────────────────────────────
def coherencias(datos, condiciones, cliente, calculo_listo=False):
    """Contrastes entre lo capturado y lo que el documento va a decir.

    Cada entrada: {'nivel': 'bien' | 'ojo' | 'info', 'texto': str}.
    """
    avisos = []

    # 1. Sustituciones silenciosas: el documento se lee completo y afirma algo
    #    que nadie confirmó. Es el riesgo más caro, así que va primero.
    if not str(datos.get('dias_trabajo') or '').strip():
        avisos.append({
            'nivel': 'ojo',
            'texto': 'Los hechos afirmarán «de lunes a viernes» y descanso '
                     '«sábado y domingo» porque no se capturaron los días de '
                     'trabajo. Corrígelo si la jornada era otra.',
        })
    if not str(datos.get('despido_lugar') or '').strip() and datos.get('demandada_domicilio'):
        avisos.append({
            'nivel': 'ojo',
            'texto': 'Los hechos dirán que la separación ocurrió en el domicilio de '
                     'la demandada, porque no se capturó el lugar.',
        })
    if not str(datos.get('despido_comunicado_por') or '').strip():
        avisos.append({
            'nivel': 'ojo',
            'texto': 'Los hechos atribuirán el aviso a «el personal de la demandada». '
                     'Con el nombre se sostiene la prueba confesional a su cargo.',
        })
    if not str(getattr(cliente, 'empresa_calle', '') or '').strip():
        avisos.append({
            'nivel': 'ojo',
            'texto': 'El capítulo de demandados ubicará al patrón en «TIJUANA, BAJA '
                     'CALIFORNIA» porque no se capturó la calle. Si el centro de '
                     'trabajo está en otro municipio, el emplazamiento se dirige mal.',
        })
    if (datos.get('modalidad_despido') or 'verbal') == 'verbal' \
            and not str(datos.get('hora_despido') or '').strip():
        avisos.append({
            'nivel': 'info',
            'texto': 'El hecho de la separación narrará la fecha sin la hora.',
        })

    # 2. El aviso escrito del artículo 47 LFT.
    if condiciones.get('incluir_sin_aviso'):
        avisos.append({
            'nivel': 'bien',
            'texto': 'Se alegará el artículo 47 LFT: no hubo aviso escrito de '
                     'rescisión.',
        })
    else:
        avisos.append({
            'nivel': 'info',
            'texto': 'Se registró aviso escrito de terminación, así que NO se alegará '
                     'la presunción del artículo 47 LFT.',
        })
        if not str(datos.get('despido_documento_motivo') or '').strip():
            avisos.append({
                'nivel': 'ojo',
                'texto': 'Hay aviso escrito pero no se transcribe la causa que '
                         'consigna el documento.',
            })

    # 3. El IMSS: sólo se alega cuando el abogado confirmó y no hubo alta.
    if not datos.get('imss_confirmado'):
        avisos.append({
            'nivel': 'ojo',
            'texto': 'Sin confirmar el registro ante el IMSS no se alegará nada al '
                     'respecto (ni a favor ni en contra).',
        })
    elif condiciones.get('incluir_imss'):
        avisos.append({
            'nivel': 'bien',
            'texto': 'Se agregará el hecho de la omisión de alta ante el IMSS.',
        })

    # 4. La acción del artículo 48 contra la antigüedad.
    accion = datos.get('accion_preferida') or 'indemnizacion'
    anios = _antiguedad_anios(datos)
    if accion == 'reinstalacion' and anios is not None and anios < 1:
        avisos.append({
            'nivel': 'ojo',
            'texto': 'Se pidió reinstalación con menos de un año de antigüedad: no '
                     'procede (art. 49 fracción I LFT).',
        })
    elif accion == 'reinstalacion':
        avisos.append({
            'nivel': 'info',
            'texto': 'Se pidió reinstalación, así que no se reclama la indemnización '
                     'constitucional.',
        })

    # 5. Renuncia voluntaria y prima de antigüedad (art. 162 fr. III).
    if datos.get('tipo_despido') == 'voluntario' and anios is not None and anios < 15:
        avisos.append({
            'nivel': 'info',
            'texto': 'En renuncia voluntaria la prima de antigüedad exige 15 años de '
                     'servicios: con esta antigüedad no se reclama.',
        })

    # 6. La firma: el nombre del actor es el que aparece arriba y abajo.
    if datos.get('actor_nombre'):
        avisos.append({
            'nivel': 'bien',
            'texto': 'El nombre del actor se usa en la carátula, en el proemio y en la '
                     'firma: no puede quedar el de una demanda anterior.',
        })

    # 7. Pruebas: la testimonial depende de que haya testigos capturados.
    if not condiciones.get('incluir_testigos'):
        avisos.append({
            'nivel': 'info',
            'texto': 'Sin testigos capturados no se ofrece la prueba testimonial.',
        })
    if not condiciones.get('incluir_documentos'):
        avisos.append({
            'nivel': 'info',
            'texto': 'Sin documentos enlistados la prueba documental se ofrece en '
                     'blanco.',
        })

    # 8. Los importes.
    if calculo_listo:
        avisos.append({
            'nivel': 'bien',
            'texto': 'Los importes del capítulo de prestaciones salen del cálculo '
                     'aprobado, no se escriben a mano.',
        })
    else:
        avisos.append({
            'nivel': 'ojo',
            'texto': 'Sin cálculo aprobado los numerales de prestaciones saldrán sin '
                     'cifra.',
        })

    return avisos


def _antiguedad_anios(datos):
    """Años completos entre ingreso y separación (None si falta alguna fecha)."""
    ingreso = datos.get('fecha_ingreso')
    salida = datos.get('fecha_despido')
    if not ingreso or not salida:
        return None
    anios = salida.year - ingreso.year
    if (salida.month, salida.day) < (ingreso.month, ingreso.day):
        anios -= 1
    return anios


# ─── Marcado del documento ───────────────────────────────────────────────────

def marcador_agrupado(pendientes):
    """{marcador: [requisitos]} para los huecos que el motor escribe literal."""
    grupos = {}
    for requisito in pendientes:
        marcador = requisito.get('marcador')
        if marcador:
            grupos.setdefault(marcador, []).append(requisito)
    return grupos


def marcar_html(html, pendientes, url_de):
    """Sustituye los marcadores del documento por enlaces al campo que falta.

    `url_de(requisito)` la aporta la vista: este módulo no conoce URLs.

    Cuando un mismo marcador corresponde a varios requisitos (dos fechas
    comparten `[FECHA]`) se usa una etiqueta conjunta, para no prometer que un
    solo clic resuelve los dos.
    """
    for marcador, requisitos in marcador_agrupado(pendientes).items():
        if marcador not in html:
            continue
        if len(requisitos) == 1:
            etiqueta = requisitos[0]['etiqueta']
        else:
            etiqueta = ' o '.join(r['etiqueta'] for r in requisitos)
        enlace = (
            f'<a class="hueco-doc" href="{url_de(requisitos[0])}"'
            f' title="Falta: {etiqueta}">+ {etiqueta}</a>'
        )
        html = html.replace(marcador, enlace)
    return html
