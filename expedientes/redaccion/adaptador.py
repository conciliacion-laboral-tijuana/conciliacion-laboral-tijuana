"""Adaptador: modelos Django → `datos` que consume el motor de redacción.

Este es el ÚNICO módulo del paquete que conoce Django.  Su trabajo es aplanar
`Cliente` + `Expediente` + `CalculoLaboral` al diccionario de claves que
esperan los capítulos, y aportar los valores derivados (salario diario,
integrado, periodo de horas extras, nombre comercial del patrón).

Se conserva el nombre de las claves del motor original (`demanda-auto`) para no
romper el redactado, y se agregan las claves propias del sistema local
(`despido_frase`, `despido_comunicado_por`, `modalidad_despido`, etc.), que son
más ricas que las del original.
"""

from decimal import Decimal


def _dec(valor):
    """Decimal seguro (None → 0)."""
    if valor is None:
        return Decimal('0')
    if isinstance(valor, Decimal):
        return valor
    return Decimal(str(valor))


def _texto(valor) -> str:
    return str(valor or '').strip()


def datos_de_expediente(expediente) -> dict:
    """Aplana un Expediente (con su Cliente) al dict del motor.

    Args:
        expediente: instancia de `expedientes.models.Expediente` con
                    `cliente` accesible.

    Returns:
        dict con todas las claves que consumen los capítulos.
    """
    cliente = expediente.cliente
    datos = {}

    # ─── Actor ────────────────────────────────────────────────────────────
    datos['actor_nombre'] = _texto(cliente.nombre).upper()
    datos['actor_sexo'] = 'F' if cliente.genero == 'femenino' else 'M'
    datos['actor_nacionalidad'] = _texto(getattr(cliente, 'nacionalidad', '')) or 'mexicana'
    datos['actor_ciudad'] = _texto(getattr(cliente, 'ciudad', '')) or 'Tijuana'
    datos['actor_estado'] = _texto(getattr(cliente, 'estado', '')) or 'Baja California'
    datos['actor_domicilio'] = _texto(cliente.direccion_completa).upper()
    datos['actor_curp'] = _texto(cliente.curp)
    datos['actor_rfc'] = _texto(cliente.rfc)
    datos['actor_telefono'] = _texto(cliente.telefono)
    datos['actor_email'] = _texto(cliente.email)
    datos['actor_fecha_nacimiento'] = cliente.fecha_nacimiento

    # ─── Representación legal ─────────────────────────────────────────────
    datos['apoderados'] = _apoderados(expediente)
    datos['autorizados'] = _autorizados(expediente)

    # ─── Demandada ────────────────────────────────────────────────────────
    razon_social = _texto(cliente.empresa_razon_social) or _texto(cliente.empresa)
    datos['demandada_razon_social'] = razon_social
    datos['demandada_nombre_comercial'] = _texto(cliente.empresa) or razon_social
    datos['demandada_domicilio'] = _domicilio_demandada(cliente)
    datos['demandada_rfc'] = _texto(cliente.empresa_rfc)
    datos['demandada_telefono'] = _texto(cliente.empresa_telefono)
    datos['demandada_tipo_persona'] = cliente.tipo_persona_citado or 'fisica'
    datos['demandada_representante'] = _texto(getattr(cliente, 'empresa_representante', ''))

    # ─── Datos laborales ──────────────────────────────────────────────────
    datos['puesto'] = _texto(cliente.puesto).upper()
    datos['actividades'] = _texto(getattr(cliente, 'actividades', ''))
    datos['tipo_contrato'] = _texto(getattr(cliente, 'tipo_contrato', '')) or 'indefinido'
    datos['tipo_contrato_texto'] = _tipo_contrato_texto(datos['tipo_contrato'])
    datos['lugar_trabajo'] = _texto(cliente.lugar_trabajo)
    datos['fecha_ingreso'] = cliente.fecha_ingreso
    datos['fecha_despido'] = cliente.fecha_salida

    # ─── Salario ──────────────────────────────────────────────────────────
    datos['salario'] = _dec(cliente.salario)
    datos['salario_tipo'] = cliente.get_periodo_pago_display().lower() if cliente.periodo_pago else 'mensual'
    datos['forma_pago'] = _texto(getattr(cliente, 'forma_pago', '')) or 'semanalmente'
    datos['dia_pago'] = _texto(getattr(cliente, 'dia_pago', ''))
    datos['otras_prestaciones_detalle'] = _texto(getattr(cliente, 'otras_prestaciones_detalle', ''))

    # ─── Jornada ──────────────────────────────────────────────────────────
    datos['jornada'] = cliente.get_jornada_display().lower() if cliente.jornada else 'diurna'
    datos['jornada_tipo'] = datos['jornada']
    datos['horas_semanales'] = cliente.horas_semanales
    datos['horario_entrada'] = _texto(getattr(cliente, 'horario_entrada', ''))
    datos['horario_salida'] = _texto(getattr(cliente, 'horario_salida', ''))
    datos['dias_trabajo'] = _texto(getattr(cliente, 'dias_trabajo', ''))
    datos['dia_descanso'] = _texto(getattr(cliente, 'dia_descanso', ''))

    # ─── IMSS ─────────────────────────────────────────────────────────────
    datos['imss_confirmado'] = bool(cliente.imss_confirmado)
    datos['tuvo_imss'] = bool(cliente.tuvo_imss) if cliente.imss_confirmado else None
    datos['imss_salario_inferior'] = bool(cliente.imss_salario_inferior)
    datos['imss_salario_diario'] = cliente.imss_salario_diario

    # ─── Despido (narrativa estructurada local) ───────────────────────────
    datos['modalidad_despido'] = _texto(cliente.modalidad_despido) or 'verbal'
    datos['hubo_documento_despido'] = bool(cliente.hubo_documento_despido)
    datos['despido_comunicado_por'] = _texto(cliente.despido_comunicado_por)
    datos['despido_lugar'] = _texto(cliente.despido_lugar)
    datos['despido_frase'] = _texto(cliente.despido_frase)
    datos['despido_documento_motivo'] = _texto(cliente.despido_documento_motivo)
    datos['despido_otra_modalidad'] = _texto(cliente.despido_otra_modalidad)
    datos['hora_despido'] = _texto(getattr(cliente, 'hora_despido', ''))
    datos['persona_despide_nombre'] = datos['despido_comunicado_por']
    datos['persona_despide_puesto'] = _texto(getattr(cliente, 'despido_persona_puesto', ''))
    datos['motivo_alegado'] = datos['despido_documento_motivo']
    datos['se_firmo_renuncia'] = bool(getattr(cliente, 'se_firmo_renuncia', False))
    datos['hubo_ofrecimiento'] = bool(getattr(cliente, 'hubo_ofrecimiento', False))
    datos['hubo_discriminacion'] = bool(getattr(cliente, 'hubo_discriminacion', False))
    datos['tipo_discriminacion'] = _texto(getattr(cliente, 'tipo_discriminacion', ''))
    datos['detalle_discriminacion'] = _texto(getattr(cliente, 'detalle_discriminacion', ''))
    datos['circunstancias_despido'] = _texto(cliente.circunstancias_despido)
    datos['testigos'] = _texto(cliente.testigos)
    datos['documentos_prueba'] = _texto(cliente.documentos_prueba)
    datos['tipo_despido'] = expediente.tipo_despido or 'injustificado'

    # ─── Expediente / conciliación ────────────────────────────────────────
    datos['folio'] = _texto(expediente.folio)
    datos['fecha_tramite'] = expediente.fecha_tramite
    datos['numero_expediente'] = _texto(expediente.numero)

    # ─── Acción preferida (art. 48 LFT) ───────────────────────────────────
    datos['accion_preferida'] = cliente.accion_preferida or 'indemnizacion'

    # ─── Prestaciones reclamadas ──────────────────────────────────────────
    # Por defecto se reclama lo que el tipo de despido permite; el asesor puede
    # apagarlo desde la hoja de prestaciones.
    datos.update(_banderas_prestaciones(cliente, expediente))

    # ─── Horas extras ─────────────────────────────────────────────────────
    datos.update(_horas_extras(cliente, expediente))

    # ─── Pruebas ──────────────────────────────────────────────────────────
    datos.update(_banderas_pruebas(cliente))

    # ─── Referencia al expediente ─────────────────────────────────────────
    # `prestaciones.renglones` reutiliza `demanda_generator._filas_prestaciones`,
    # que necesita el expediente para las filas de respaldo cuando el cálculo no
    # está disponible.  Se adjunta aquí para no duplicar esa lógica.
    datos['_expediente'] = expediente

    return datos


def _domicilio_demandada(cliente) -> str:
    """Domicilio del patrón en una línea, como lo pide el proemio/inspección."""
    partes = []
    if cliente.empresa_calle:
        calle = cliente.empresa_calle
        if cliente.empresa_numero:
            calle += f' NO. {cliente.empresa_numero}'
        partes.append(calle)
    if cliente.empresa_colonia:
        partes.append(cliente.empresa_colonia)
    partes.append('TIJUANA, BAJA CALIFORNIA')
    if cliente.empresa_cp:
        partes.append(f'C.P. {cliente.empresa_cp}')
    return ', '.join(p.upper() for p in partes if p)


def _tipo_contrato_texto(valor: str) -> str:
    """'indefinido' → 'por tiempo indefinido' (redactado del hecho 5)."""
    mapa = {
        'indefinido': 'por tiempo indefinido',
        'determinado': 'por tiempo determinado',
        'obra': 'por obra o tiempo determinado',
        'temporal': 'por tiempo determinado',
        'capacitacion': 'por tiempo determinado para capacitación inicial',
    }
    return mapa.get(valor, 'por tiempo indefinido')


def _apoderados(expediente) -> list:
    """Apoderados legales del expediente (si el modelo extendido existe)."""
    relacionados = getattr(expediente, 'apoderados', None)
    if relacionados is None:
        return []
    return [
        {'nombre': _texto(a.nombre), 'cedula': _texto(getattr(a, 'cedula_profesional', ''))}
        for a in relacionados.all()
    ]


def _autorizados(expediente) -> list:
    """Personas autorizadas para oír y recibir notificaciones."""
    relacionados = getattr(expediente, 'autorizados', None)
    if relacionados is None:
        return []
    return [{'nombre': _texto(a.nombre)} for a in relacionados.all()]


def _banderas_prestaciones(cliente, expediente) -> dict:
    """Qué prestaciones se reclama, según el tipo de separación.

    Se delega en la MISMA regla que usa el motor legal
    (`_conceptos_para_demanda` → arts. 50 y 162 LFT) para que las banderas y los
    MONTOS no puedan discrepar.  En particular:

    - El art. 50 LFT (indemnización) no procede en renuncia voluntaria.
    - La prima de antigüedad del art. 162 fr. III sólo se paga en renuncia
      voluntaria a partir de 15 años de servicios, así que no se puede afirmar
      sin contar la antigüedad.
    """
    from ..demanda_generator import _años_completos_de, _conceptos_para_demanda

    tipo = expediente.tipo_despido or 'injustificado'
    conceptos = _conceptos_para_demanda(tipo, _años_completos_de(cliente))

    return {
        'reclama_indemnizacion': conceptos.get('incluir_indemnizacion', True),
        'reclama_prima_antiguedad': conceptos.get('incluir_prima_antiguedad', True),
        'reclama_salarios_caidos': conceptos.get('incluir_indemnizacion', True),
        'reclama_vacaciones': True,
        'reclama_prima_vacacional': True,
        'reclama_aguinaldo': True,
        'reclama_constancia': True,
        'reclama_salarios_devengados': False,
        'reclama_otras_prestaciones': bool(_texto(
            getattr(cliente, 'otras_prestaciones_detalle', '')
        )),
        'reclama_comprobantes_fiscales': True,
    }


def _horas_extras(cliente, expediente) -> dict:
    """Bandas y patrón de horas extras.

    El patrón de horas extras no está en `Cliente`; se toma de la hoja de
    prestaciones (que sí tiene el desglose semanal) si existe.
    """
    banderas = {
        'tuvo_horas_extras': False,
        'reclama_horas_extras': False,
        'horas_extras_dia': None,
        'horas_extras_dias': [],
        'horas_extras_periodo_inicio': None,
        'horas_extras_periodo_fin': None,
    }
    hoja = getattr(expediente, 'hoja_prestaciones', None)
    if hoja is None:
        return banderas

    datos_hoja = hoja.datos or {}
    config = datos_hoja.get('config') or {}
    semanas = datos_hoja.get('semanas') or []
    if not semanas:
        return banderas

    # Los días con horas extras capturados en la primera semana sirven de patrón
    dias_semana = []
    primera = semanas[0]
    for dia in ('lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'):
        if primera.get(dia):
            dias_semana.append(dia)

    banderas.update({
        'tuvo_horas_extras': True,
        'reclama_horas_extras': bool(config.get('reclama_horas_extras', True)),
        'horas_extras_dia': _suma_horas_semana(primera),
        'horas_extras_dias': dias_semana,
        'horas_extras_periodo_inicio': primera.get('semana'),
        'horas_extras_periodo_fin': max(
            (s.get('semana') for s in semanas if s.get('semana')), default=None
        ),
    })
    return banderas


def _suma_horas_semana(semana: dict):
    """Horas extra de la semana (suma de los días capturados)."""
    total = Decimal('0')
    for dia in ('lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'):
        valor = semana.get(dia)
        if valor:
            total += _dec(valor)
    return total or None


def _banderas_pruebas(cliente) -> dict:
    """Pruebas ofrecidas: valores por defecto del estándar del despacho."""
    return {
        'prueba_confesional': True,
        'prueba_confesional_propios': bool(_texto(cliente.despido_comunicado_por)),
        'prueba_interrogatorio_libre': True,
        'prueba_testimonial': bool(_texto(cliente.testigos)),
        'prueba_informes': False,
        'prueba_inspeccion': True,
        'prueba_documental': True,
        'prueba_presuncional': True,
        'prueba_instrumental': True,
    }


def datos_desde_post(expediente, post) -> dict:
    """Sobreescribe los datos del expediente con lo capturado en el formulario.

    Permite que el editor de capítulos previsualice cambios ANTES de guardarlos,
    sin escribir en la base de datos.
    """
    datos = datos_de_expediente(expediente)
    if not post:
        return datos

    directos = {
        'hora_despido': 'hora_despido',
        'despido_persona_puesto': 'persona_despide_puesto',
        'se_firmo_renuncia': 'se_firmo_renuncia',
        'actividades': 'actividades',
        'tipo_contrato': 'tipo_contrato',
        'horario_entrada': 'horario_entrada',
        'horario_salida': 'horario_salida',
        'dia_descanso': 'dia_descanso',
        'dias_trabajo': 'dias_trabajo',
        'nacionalidad': 'actor_nacionalidad',
        'ciudad': 'actor_ciudad',
        'estado': 'actor_estado',
    }
    for campo_post, clave in directos.items():
        if campo_post in post:
            datos[clave] = _texto(post.get(campo_post))

    # Banderas de pruebas (los checkbox no viajan cuando están desmarcados)
    for bandera in ('prueba_confesional', 'prueba_confesional_propios',
                    'prueba_interrogatorio_libre', 'prueba_testimonial',
                    'prueba_informes', 'prueba_inspeccion', 'prueba_documental',
                    'prueba_presuncional', 'prueba_instrumental'):
        if any(k.startswith(bandera) for k in post.keys()):
            datos[bandera] = post.get(bandera) in ('on', 'true', '1', 'si', 'sí', True)

    return datos
