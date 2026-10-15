"""Capítulo 5 — CAPÍTULO DE HECHOS.

Reproduce el orden y el estilo del estándar del despacho (págs. 6-9), usando la
narrativa ESTRUCTURADA que ya captura el sistema (`modalidad_despido`,
`hubo_documento_despido`, `despido_comunicado_por`, `despido_lugar`,
`despido_frase`, `despido_documento_motivo`, `circunstancias_despido`) en lugar
de un solo texto libre.

Además se conservan los dos hechos que el sistema ya generaba y que son
irrenunciables:

  * agotamiento de la instancia conciliatoria con su FOLIO (requisito de
    procedibilidad), y
  * la elección de acción del artículo 48 LFT (reinstalación vs. indemnización).

El redactado de la separación se apoya en el artículo 47 LFT: sin aviso escrito
de rescisión, la separación se presume injustificada.
"""

from ..demanda_generator import _fecha_espanol, _ordinal, _texto_como_lista


def _horas(valor) -> str:
    """Hora en 'HH:MM' tal como se captura, sin reformatear si ya viene así."""
    if not valor:
        return ''
    return str(valor)[:5]


def hechos(datos: dict, calculo: dict, condiciones: dict,
           tipo_despido: str = 'injustificado') -> list:
    """Lista de hechos (texto sin numerar; la numeración la pone el ensamblado).

    `tipo_despido` cambia el HECHO CENTRAL: no es lo mismo un despido
    injustificado que una rescisión imputable al patrón (art. 51 LFT), una
    renuncia voluntaria o una separación por causa justificada (art. 46 LFT).
    """
    lista = []

    empresa = (datos.get('demandada_razon_social')
               or datos.get('demandada_nombre_comercial') or '[EMPRESA DEMANDADA]')
    domicilio_empresa = datos.get('demandada_domicilio') or '[DOMICILIO DE LA DEMANDADA]'
    puesto = datos.get('puesto') or '[PUESTO DESEMPEÑADO]'
    f_ingreso = _fecha_espanol(datos.get('fecha_ingreso'))
    f_despido = _fecha_espanol(datos.get('fecha_despido'))
    ciudad = datos.get('actor_ciudad') or 'Tijuana'
    estado = datos.get('actor_estado') or 'Baja California'
    salario_tipo = datos.get('salario_tipo') or 'diario'

    # ─── 1. Contratación ──────────────────────────────────────────────────
    lista.append(
        f'Con fecha {f_ingreso}, fui contratado en esta ciudad de {ciudad}, '
        f'{estado}, por la moral aquí demandada "{empresa}", ubicada en '
        f'{domicilio_empresa}, para prestar mis servicios de manera personal y '
        f'subordinada, los cuales siempre brindé continua e ininterrumpidamente '
        f'a favor de estos, bajo quienes estuve supeditado a sus órdenes '
        f'diarias bajo un horario determinado, habiéndome fijado un salario '
        f'{salario_tipo} en contraprestación a mis servicios.'
    )

    # ─── 2. Entrevistas y documentación de ingreso al IMSS ────────────────
    ingreso_doc = (
        'Manifiesto que para efecto de ser admitido por los aquí demandados fui '
        'sujeto a entrevistas a efecto de considerarme apto y viable para el '
        'puesto a desempeñar, analizada la cual se me consideró viable para '
        'ejercer el puesto y las labores asignadas por los aquí demandados, '
        'quienes recabaron una serie de documentos personales que me fueron '
        'requeridos para ser dado de alta como su empleado ante el IMSS.'
    )
    if condiciones['incluir_imss']:
        ingreso_doc += (
            ' Bajo protesta de decir verdad, desconozco si dieron cabal '
            'cumplimiento a las aportaciones frente a las cuales están '
            'obligados ante las autoridades laborales y de seguridad social, '
            'en virtud de habérseme negado dicha información de manera personal.'
        )
    lista.append(ingreso_doc)

    # ─── 3. Firmas en blanco al ingreso (condicional, narrativa libre) ────
    circunstancias = str(datos.get('circunstancias_despido') or '').strip()
    if circunstancias:
        lista.append(circunstancias)

    # ─── 4. Impugnación anticipada de renuncia (condicional) ──────────────
    if condiciones['incluir_renuncia']:
        lista.append(
            'Manifiesto desde este momento, bajo protesta de decir verdad, que '
            'jamás ha sido mi voluntad renunciar a mi empleo, por lo que '
            'impugno de manera anticipada cualquier documento con el que la '
            'parte patronal pretenda acreditar una supuesta renuncia voluntaria '
            'o finiquito liberatorio.'
        )

    # ─── 5. Contrato y puesto ─────────────────────────────────────────────
    tipo_contrato = datos.get('tipo_contrato_texto') or 'por tiempo indefinido'
    puesto_txt = (
        f'La relación obrero-patronal antes mencionada inició mediante la '
        f'celebración de un contrato individual de trabajo por escrito '
        f'{tipo_contrato}, del cual no se me dio copia alguna a pesar de '
        f'haberlo requerido en más de una ocasión, donde se me asignó el puesto '
        f'de {puesto}.'
    )
    actividades = str(datos.get('actividades') or '').strip()
    if actividades:
        puesto_txt += f' En dicho puesto mis funciones comprendían: {actividades}'
    lista.append(puesto_txt)

    # ─── 6. Jornada ───────────────────────────────────────────────────────
    if condiciones['incluir_jornada']:
        entrada = _horas(datos.get('horario_entrada'))
        salida_h = _horas(datos.get('horario_salida'))
        dias = datos.get('dias_trabajo') or 'lunes a viernes'
        descanso = datos.get('dia_descanso') or 'sábado y domingo'
        jornada_tipo = datos.get('jornada') or 'diurna'
        horas_sem = datos.get('horas_semanales')
        if isinstance(dias, (list, tuple)):
            dias = ', '.join(str(d) for d in dias)
        if isinstance(descanso, (list, tuple)):
            descanso = ' y '.join(str(d) for d in descanso)

        jornada_txt = (
            f'La jornada de trabajo que se me fijó desde un principio y que '
            f'vine desempeñando consistió del día {dias}, en una jornada '
            f'{jornada_tipo} en la cual se me asignó el horario de las '
            f'{entrada} horas para culminar a las {salida_h} horas'
        )
        if horas_sem:
            jornada_txt += f' laborando así {horas_sem} horas semanales'
        jornada_txt += (
            f', teniendo los días {descanso} como descanso semanal.'
        )
        lista.append(jornada_txt)

    # ─── 7. Salario e integración (arts. 84 y 89 LFT) ─────────────────────
    if calculo.get('success'):
        sd = calculo.get('salario_diario') or 0
        sdi = calculo.get('salario_diario_integrado') or 0
        salario_txt = (
            f'El salario base diario que venía devengando en contraprestación a '
            f'los servicios laborales del suscrito era la cantidad de '
            f'${sd:,.2f} pesos, y el salario diario integrado era de '
            f'${sdi:,.2f} pesos'
        )
        componentes = calculo.get('salario_integrado_componentes') or {}
        detalle = ', '.join(
            f'{_nombre_componente(k)}: ${v:,.2f}' for k, v in componentes.items() if v
        )
        if detalle:
            salario_txt += f', integrado por {detalle}'
        forma_pago = datos.get('forma_pago') or 'semanalmente'
        salario_txt += (
            f', los cuales me eran cubiertos {forma_pago}. Reclamando así la '
            f'indemnización al salario diario integrado de ${sdi:,.2f} pesos, '
            f'es decir, en términos del artículo 84 de la Ley Federal del '
            f'Trabajo, en el cual se establece que deberá incluirse además '
            f'cualquiera otra cantidad o prestación que se entregue al '
            f'trabajador a cambio de su trabajo.'
        )
        lista.append(salario_txt)
    elif datos.get('salario'):
        lista.append(
            f'El salario que venía devengando en contraprestación a los '
            f'servicios laborales del suscrito era la cantidad de '
            f'${datos["salario"]:,.2f} pesos {salario_tipo}s.'
        )

    # ─── 8. IMSS (condicional) ────────────────────────────────────────────
    if condiciones['incluir_imss']:
        lista.append(
            'No se me dio de alta ante el IMSS con el salario real devengado, '
            'por lo que no se efectuaron las cotizaciones que la patronal debía '
            'cubrir en relación con este, tanto ante el Instituto Mexicano del '
            'Seguro Social como ante el Instituto del Fondo Nacional de la '
            'Vivienda para los Trabajadores.'
        )

    # ─── 9. Desempeño ─────────────────────────────────────────────────────
    lista.append(
        'Durante la totalidad de la relación de trabajo desarrollé, bajo '
        'protesta de decir verdad, mis actividades con estricta rectitud, '
        'conduciéndome en todo momento con probidad y honradez, de manera tal '
        'que jamás fui objeto de medida disciplinaria alguna por parte de los '
        'demandados; al contrario, tuve el reconocimiento por la manera en que '
        'siempre desempeñé mi trabajo.'
    )

    # ─── 10. Antigüedad ───────────────────────────────────────────────────
    if calculo.get('success'):
        anios = calculo.get('años_completos') or 0
        anios_txt = f'{anios} año' + ('' if anios == 1 else 's') + ' completos'
        lista.append(
            f'La relación laboral tuvo una duración de {anios_txt}, '
            f'transcurridos entre el {f_ingreso} y el {f_despido}.'
        )

    # ─── 11. La separación (hecho central, redactado estructurado) ────────
    lista.append(_texto_despido(datos, condiciones, tipo_despido))

    # ─── 12. Discriminación (condicional) ─────────────────────────────────
    if condiciones['incluir_discriminacion']:
        detalle_div = str(datos.get('detalle_discriminacion') or '').strip()
        lista.append(
            'Bajo protesta de decir verdad, los hoy demandados tuvieron hacia '
            'mi persona un trato hostil y ofensivo, siendo víctima además de '
            'actos discriminatorios por parte de mis jefes directos, por razón '
            f'de {datos.get("tipo_discriminacion") or "mi condición"}.'
            + (f' {detalle_div}' if detalle_div else '')
        )

    # ─── 13. Horas extras (condicional) ───────────────────────────────────
    if condiciones['incluir_horas_extras']:
        he = (calculo or {}).get('horas_extras') or {}
        if float(he.get('monto') or 0) > 0:
            lista.append(_texto_horas_extras(datos, calculo))

    # ─── 14. Instancia conciliatoria (requisito de procedibilidad) ────────
    folio = datos.get('folio')
    if folio:
        lista.append(
            f'El actor agotó la instancia conciliatoria ante el Centro de '
            f'Conciliación Laboral, según consta en el expediente número '
            f'{folio} de fecha {_fecha_espanol(datos.get("fecha_tramite"))}, sin '
            f'que se lograra acuerdo conciliatorio alguno, por lo que se expidió '
            f'la constancia de no conciliación correspondiente.'
        )
    else:
        lista.append(
            'El actor agotó la instancia conciliatoria ante el Centro de '
            'Conciliación Laboral, según consta en la constancia de no '
            'conciliación que se exhibe con la presente demanda, sin que se '
            'lograra acuerdo conciliatorio alguno.'
        )

    # ─── 15. Falta de pago ────────────────────────────────────────────────
    lista.append(
        'A la fecha de presentación de esta demanda, el demandado no ha '
        'cubierto el pago de las prestaciones laborales que se reclaman, a '
        'pesar de haber sido requerido para ello.'
    )

    # ─── 16. Elección de acción (art. 48 LFT) ─────────────────────────────
    accion = (calculo or {}).get('accion') or {}
    if accion.get('accion') == 'reinstalacion':
        lista.append(
            'En atención a lo dispuesto por el artículo 48 de la Ley Federal '
            'del Trabajo, el actor opta por la REINSTALACIÓN en el puesto que '
            'venía desempeñando, por lo que no se reclama la indemnización '
            'equivalente a tres meses de salario.'
        )

    # ─── 17. Testigos ─────────────────────────────────────────────────────
    testigos = _texto_como_lista(datos.get('testigos'))
    if testigos:
        lista.append(
            f'Los hechos anteriores podrán ser corroborados por las personas '
            f'que oportunamente se señalarán como testigos: {testigos}'
        )

    # ─── 18. Documento de terminación entregado ───────────────────────────
    if not condiciones['incluir_sin_aviso']:
        lista.append(
            'La parte demandada entregó al trabajador documentación relacionada '
            'con la terminación de la relación laboral, misma que será ofrecida '
            'como prueba en lo que resulte conducente.'
        )

    return lista


def _texto_despido(datos: dict, condiciones: dict,
                   tipo_despido: str = 'injustificado') -> str:
    """Hecho central: cómo y dónde ocurrió la separación.

    Se arma con los campos estructurados del modelo, no con un texto libre, para
    que cada modalidad tenga su redactado jurídico.  El cierre cambia según la
    CAUSA de separación, porque de ella depende qué se reclama:

    - injustificado: separación sin causa → indemnización (arts. 47, 48 y 50).
    - justificado: el patrón acreditó causa → se reclaman sólo prestaciones
      devengadas y prima de antigüedad (art. 46 LFT excluye la indemnización).
    - voluntario: renuncia del trabajador → prestaciones proporcionales.
    - rescision: el patrón incurrió en causa grave → el actor rescinde
      (art. 51 LFT), con indemnización del art. 50.
    """
    fecha = _fecha_espanol(datos.get('fecha_despido'))
    hora = _horas(datos.get('hora_despido'))
    lugar = (str(datos.get('despido_lugar') or '').strip()
             or datos.get('demandada_domicilio')
             or 'el domicilio de la moral demandada')
    quien = str(datos.get('despido_comunicado_por') or '').strip()
    frase = str(datos.get('despido_frase') or '').strip()
    motivo_doc = str(datos.get('despido_documento_motivo') or '').strip()
    modalidad = str(datos.get('modalidad_despido') or 'verbal').strip()

    partes = [
        'Bajo los términos y condiciones laborales aplicables, el suscrito '
        'presté mis servicios bajo la subordinación de la empresa demandada, '
        'desempeñándome siempre a su entera complacencia. No obstante lo '
        f'anterior, el día {fecha}'
    ]
    if hora:
        partes.append(f', siendo aproximadamente las {hora} horas')
    partes.append(f', me encontraba laborando de manera habitual dentro de {lugar}. ')

    # Quién comunicó la separación
    if quien:
        partes.append(f'En ese momento, {quien} me notificó que ')
    else:
        partes.append('En ese momento, el personal de la demandada me notificó que ')

    if modalidad == 'acceso':
        partes.append('se me impedía el acceso al centro de trabajo')
    elif modalidad == 'escrito' and motivo_doc:
        partes.append(f'quedaba separado de mi puesto de trabajo por la causa que '
                      f'se consignó en el documento respectivo: {motivo_doc}')
    elif frase:
        partes.append(f'"{frase}"')
    else:
        partes.append('quedaba separado de mi puesto de trabajo')

    partes.append('. ')

    # El aviso de rescisión ausente es el núcleo del art. 47 LFT
    if condiciones['incluir_sin_aviso']:
        partes.append(
            'Lo anterior ocurrió sin que previamente se me hubiera informado de '
            'manera formal, clara y precisa causa o motivo alguno que justificara '
            'la terminación de la relación laboral, y sin que se me hiciera '
            'entrega del correspondiente aviso de rescisión en los términos del '
            'artículo 47 de la Ley Federal del Trabajo. '
        )
    else:
        partes.append(
            'Lo anterior ocurrió sin que se me acreditara la causa legal en que '
            'se pretende fundar la terminación de la relación laboral. '
        )

    partes.append(_cierre_separacion(tipo_despido, condiciones))
    return ''.join(partes)


def _cierre_separacion(tipo_despido: str, condiciones: dict) -> str:
    """Párrafo de cierre del hecho central, según la causa de separación."""
    cierres = {
        'injustificado': (
            'Por tal motivo, considero que la separación de mi empleo fue '
            'injustificada, toda vez que en ningún momento se me comunicó causa '
            'legal alguna para la terminación de la relación laboral. Por lo '
            'cual acudo ante este H. Tribunal a reclamar en la vía ordinaria la '
            'indemnización que conforme a derecho me corresponde.'
        ),
        'justificado': (
            'En atención a lo anterior, acudo ante este H. Tribunal a reclamar '
            'el pago de las prestaciones devengadas y la prima de antigüedad que '
            'conforme a derecho me corresponden, en términos del artículo 162 '
            'fracción III de la Ley Federal del Trabajo.'
        ),
        'voluntario': (
            'Por tal motivo, habiendo concluido la relación laboral, acudo ante '
            'este H. Tribunal a reclamar el pago de las prestaciones '
            'proporcionales que se generaron durante la vigencia de la relación '
            'de trabajo y que no me fueron cubiertas.'
        ),
        'rescision': (
            'Por tal motivo, me vi en la necesidad de dar por terminada la '
            'relación laboral de manera justificada, al actualizarse las causas '
            'graves de incumplimiento imputables al patrón previstas por el '
            'artículo 51 de la Ley Federal del Trabajo. Por lo cual acudo ante '
            'este H. Tribunal a reclamar la indemnización y las prestaciones que '
            'conforme a derecho me corresponden.'
        ),
        'otro': (
            'Por tal motivo, acudo ante este H. Tribunal a reclamar el pago de '
            'las prestaciones que conforme a derecho me corresponden con motivo '
            'de la terminación de la relación laboral.'
        ),
    }
    return cierres.get(tipo_despido, cierres['injustificado'])


def _texto_horas_extras(datos: dict, calculo: dict) -> str:
    """Hecho de horas extras, alimentado por el patrón capturado y el cálculo."""
    he = (calculo or {}).get('horas_extras') or {}
    dias = datos.get('horas_extras_dias') or datos.get('dias_trabajo') or []
    if isinstance(dias, (list, tuple)) and dias:
        nombre_dias = ', '.join(str(d) for d in dias)
    else:
        nombre_dias = 'los días laborables'

    horas_dia = datos.get('horas_extras_dia')
    total_horas = he.get('total_horas') or 0
    tipo = he.get('tipo') or 'dobles'
    etiqueta = {'dobles': 'horas extras dobles',
                'triples': 'horas extras triples'}.get(
        tipo, 'horas extras dobles y triples conforme a ley')

    desde = datos.get('horas_extras_periodo_inicio') or datos.get('fecha_ingreso')
    hasta = datos.get('horas_extras_periodo_fin') or datos.get('fecha_despido')

    texto = (
        f'El suscrito laboró horas extras durante el periodo comprendido del '
        f'{_fecha_espanol(desde)} al {_fecha_espanol(hasta)}, '
    )
    if horas_dia:
        texto += f'consistentes en {float(horas_dia):g} horas extras diarias de {nombre_dias}. '
    if total_horas:
        texto += f'En total, el suscrito laboró {_horas_legibles(total_horas)} de {etiqueta}, '
    else:
        texto += f'consistentes en {etiqueta}, '
    texto += ('mismas que no fueron cubiertas en tiempo y forma a pesar de '
              'haberlas reclamado en más de una ocasión. Las horas '
              'extraordinarias reclamadas corresponden exclusivamente a las '
              'semanas y días detallados en el desglose de prestaciones; no se '
              'presume un horario extraordinario constante durante toda la '
              'relación laboral.')
    return texto


def _horas_legibles(total_horas) -> str:
    """7.6 → '7 horas y 36 minutos'."""
    try:
        total = float(total_horas)
    except (TypeError, ValueError):
        return str(total_horas)
    horas = int(total)
    minutos = round((total - horas) * 60)
    if minutos == 60:
        horas += 1
        minutos = 0
    partes = []
    if horas:
        partes.append(f'{horas} hora' + ('' if horas == 1 else 's'))
    if minutos:
        partes.append(f'{minutos} minuto' + ('' if minutos == 1 else 's'))
    if not partes:
        return '0 horas'
    return ' y '.join(partes)


def _nombre_componente(clave: str) -> str:
    """Nombre legible de un componente del salario integrado (art. 84 LFT)."""
    from ..demanda_generator import _nombre_componente as original
    return original(clave)
