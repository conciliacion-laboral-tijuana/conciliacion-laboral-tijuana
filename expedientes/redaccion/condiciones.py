"""Evaluación de condiciones: qué secciones, prestaciones y pruebas aparecen.

Traducido del `motor_redaccion/condiciones.py` de `demanda-auto`, adaptado a
los campos que el despacho SÍ captura (modelo `Cliente`/`Expediente`), y con
las banderas que el estándar de la demanda de referencia exige.

Regla de diseño: una condición sólo decide PRESENCIA de texto, nunca montos.
Los montos los fija el motor legal determinista (`core.laboral`).
"""


def _bool(datos: dict, clave: str, default: bool = False) -> bool:
    """Lee una bandera admitiendo True/False, '1'/'0', 'on', 'si'."""
    valor = datos.get(clave, default)
    if isinstance(valor, bool):
        return valor
    if valor is None:
        return default
    if isinstance(valor, (int, float)):
        return bool(valor)
    return str(valor).strip().lower() in ('1', 'true', 'on', 'si', 'sí', 'yes')


def _texto(datos: dict, clave: str) -> str:
    return str(datos.get(clave) or '').strip()


def evaluar_condiciones(datos: dict) -> dict:
    """Devuelve el dict de banderas que activan/desactivan cada bloque.

    Agrupadas en tres familias: secciones/hechos condicionales, prestaciones
    reclamadas y pruebas ofrecidas.
    """
    dias_devengados = datos.get('dias_salarios_devengados',
                                datos.get('dias_devengados', 0)) or 0
    try:
        dias_devengados = float(dias_devengados)
    except (TypeError, ValueError):
        dias_devengados = 0.0

    tuvo_imss = datos.get('tuvo_imss')
    imss_confirmado = _bool(datos, 'imss_confirmado', False)
    # Sólo se alega la omisión de alta cuando el asesor CONFIRMÓ que no hubo
    # IMSS: sin confirmar, afirmarlo sería inventar un hecho.
    incluir_imss = imss_confirmado and tuvo_imss is False

    hubo_horas_extras = _bool(datos, 'tuvo_horas_extras')
    reclama_horas_extras = _bool(datos, 'reclama_horas_extras', hubo_horas_extras)

    reclama_salarios_devengados = _bool(datos, 'reclama_salarios_devengados')

    return {
        # ─── Secciones y hechos condicionales ────────────────────────────
        'incluir_imss': incluir_imss,
        'incluir_renuncia': _bool(datos, 'se_firmo_renuncia'),
        'incluir_horas_extras': hubo_horas_extras and reclama_horas_extras,
        'incluir_salarios_devengados': (
            reclama_salarios_devengados and dias_devengados > 0
        ),
        'incluir_testigos': bool(_texto(datos, 'testigos')),
        'incluir_documentos': bool(_texto(datos, 'documentos_prueba')),
        'incluir_actividades': bool(_texto(datos, 'actividades')),
        'incluir_jornada': bool(
            _texto(datos, 'horario_entrada') or _texto(datos, 'horario_salida')
        ),
        'incluir_discriminacion': _bool(datos, 'hubo_discriminacion'),
        'incluir_ofrecimiento': _bool(datos, 'hubo_ofrecimiento'),
        'incluir_lugar_trabajo': bool(_texto(datos, 'lugar_trabajo')),
        # El aviso de rescisión ausente es el corazón del art. 47 LFT: se
        # alega cuando el asesor confirmó que NO se entregó documento.
        'incluir_sin_aviso': not _bool(datos, 'hubo_documento_despido', False),

        # ─── Prestaciones reclamadas ─────────────────────────────────────
        'reclama_indemnizacion': _bool(datos, 'reclama_indemnizacion', True),
        'reclama_prima_antiguedad': _bool(datos, 'reclama_prima_antiguedad', True),
        'reclama_vacaciones': _bool(datos, 'reclama_vacaciones', True),
        'reclama_prima_vacacional': _bool(datos, 'reclama_prima_vacacional', True),
        'reclama_aguinaldo': _bool(datos, 'reclama_aguinaldo', True),
        'reclama_horas_extras': reclama_horas_extras,
        'reclama_salarios_caidos': _bool(datos, 'reclama_salarios_caidos', True),
        'reclama_constancia': _bool(datos, 'reclama_constancia', True),
        'reclama_salarios_devengados': reclama_salarios_devengados,
        'reclama_otras_prestaciones': _bool(datos, 'reclama_otras_prestaciones'),
        # Comprobantes fiscales (IMSS/INFONAVIT/SAT) del estándar de referencia
        'reclama_comprobantes_fiscales': _bool(
            datos, 'reclama_comprobantes_fiscales', True
        ),

        # ─── Pruebas ofrecidas ───────────────────────────────────────────
        'prueba_confesional': _bool(datos, 'prueba_confesional', True),
        'prueba_confesional_propios': _bool(
            datos, 'prueba_confesional_propios',
            bool(_texto(datos, 'despido_comunicado_por')),
        ),
        'prueba_interrogatorio_libre': _bool(
            datos, 'prueba_interrogatorio_libre', True
        ),
        'prueba_testimonial': _bool(
            datos, 'prueba_testimonial', bool(_texto(datos, 'testigos'))
        ),
        'prueba_informes': _bool(datos, 'prueba_informes'),
        'prueba_inspeccion': _bool(datos, 'prueba_inspeccion', True),
        'prueba_documental': _bool(datos, 'prueba_documental', True),
        'prueba_presuncional': _bool(datos, 'prueba_presuncional', True),
        'prueba_instrumental': _bool(datos, 'prueba_instrumental', True),
    }
