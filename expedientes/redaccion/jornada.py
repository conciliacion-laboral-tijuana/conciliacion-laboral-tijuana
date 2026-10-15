"""Capítulo 4 — ANEXO: JORNADA SEMANAL Y HORAS EXTRAS.

El estándar del despacho inserta, después del capítulo de prestaciones, un
cuadro de dos páginas con la jornada semana por semana (págs. 4-5):

    JORNADA SEMANAL | JORNADA ORDINARIA | JORNADA EXTRA | HORAS EXTRAS
    22/09/25 - 26/09/25 | 07:00 hrs - 17:00 hrs | 07:00 del lunes a las 15:00
    del viernes (48 horas) | A partir de las 15:00 del viernes hasta las 17:00
    del mismo día. | 2 horas dobles

El respaldo de datos ya existe: `hoja_prestaciones.calcular_hoja` produce
`detalle_semanas` con inicio, fin y el desglose por día.  Aquí sólo se le da la
forma de la tabla del estándar.
"""


def _fmt_corta(fecha) -> str:
    return fecha.strftime('%d/%m/%y') if fecha else ''


def _duracion(valor) -> str:
    """2.0 → '2 horas'; 1.5 → '1 hora y 30 minutos'."""
    from decimal import Decimal, ROUND_HALF_UP
    try:
        minutos = int((Decimal(str(valor)) * 60).quantize(Decimal('1'),
                                                          rounding=ROUND_HALF_UP))
    except Exception:
        return str(valor)
    horas = minutos // 60
    resto = minutos % 60
    partes = []
    if horas:
        partes.append(f'{horas} hora' + ('' if horas == 1 else 's'))
    if resto:
        partes.append(f'{resto} minuto' + ('' if resto == 1 else 's'))
    return ' y '.join(partes) or '0 horas'


def filas_jornada(datos: dict, calculo: dict) -> list:
    """Renglones (jornada_semanal, ordinaria, extra, horas) del cuadro.

    Se arma desde `calculo['horas_extras']['semanas']` (el desglose que ya
    produjo la hoja de prestaciones).  Si el expediente no trae horas extras
    detalladas, devuelve lista vacía y el capítulo no se emite.
    """
    semanas = (calculo or {}).get('horas_extras', {}).get('semanas') or []
    if not semanas:
        return []

    entrada = str(datos.get('horario_entrada') or '')[:5]
    salida = str(datos.get('horario_salida') or '')[:5]
    horas_sem = datos.get('horas_semanales')
    dias = datos.get('dias_trabajo')
    if isinstance(dias, (list, tuple)) and dias:
        dias_txt = ', '.join(str(d) for d in dias)
    else:
        dias_txt = 'lunes a viernes'

    filas = []
    for semana in semanas:
        # Jornada ordinaria: "07:00 hrs - 17:00 hrs"
        ordinaria_rango = ''
        if entrada and salida:
            ordinaria_rango = f'{entrada} hrs - {salida} hrs'

        # A partir del detalle diario, reconstruir la jornada ordinaria y la extra
        partes_ordinaria, partes_extra = [], []
        for dia in semana.get('dias', []):
            fecha = _fmt_corta(dia.get('fecha'))
            dia_entrada = str(dia.get('entrada') or '')[:5]
            dia_ordinaria = str(dia.get('ordinaria') or '')[:5]
            dia_salida = str(dia.get('salida') or '')[:5]
            if dia_entrada and dia_ordinaria:
                partes_ordinaria.append(f'{fecha}: {dia_entrada} a {dia_ordinaria}')
            if dia_ordinaria and dia_salida:
                partes_extra.append(
                    f'{fecha}: {dia_ordinaria} a {dia_salida} '
                    f'({_duracion(dia.get("horas"))})'
                )
            elif dia.get('horas'):
                partes_extra.append(f'{fecha}: {_duracion(dia.get("horas"))}')

        if not partes_ordinaria and entrada and salida:
            descripcion_ordinaria = (
                f'{entrada} hrs del {dias_txt} '
                + (f'({horas_sem:g} horas)' if horas_sem else '')
            )
        else:
            descripcion_ordinaria = '; '.join(partes_ordinaria) or 'Horario no capturado'

        descripcion_extra = '; '.join(partes_extra) or 'Horario no capturado'

        dobles = semana.get('dobles') or 0
        triples = semana.get('triples') or 0
        if dobles and triples:
            horas_txt = (f'{_duracion(dobles)} dobles y '
                         f'{_duracion(triples)} triples')
        elif triples:
            horas_txt = f'{_duracion(triples)} triples'
        else:
            horas_txt = f'{_duracion(dobles)} dobles'

        filas.append({
            'jornada_semanal': (f'{_fmt_corta(semana.get("inicio"))} - '
                                f'{_fmt_corta(semana.get("fin"))}'),
            'jornada_ordinaria': ordinaria_rango or descripcion_ordinaria,
            'jornada_extra': descripcion_extra,
            'horas': horas_txt,
        })

    return filas


def resumen(datos: dict, calculo: dict) -> str:
    """Párrafo de entrada del anexo (resumen del reclamo de horas extras)."""
    from ..demanda_generator import _importe_demanda
    horas = (calculo or {}).get('horas_extras') or {}
    monto = horas.get('monto') or 0
    dobles = horas.get('dobles') or 0
    triples = horas.get('triples') or 0
    if not monto:
        return ''
    partes = [f'Se reclama el saldo de {_importe_demanda(monto)} por horas extraordinarias']
    if dobles:
        partes.append(f'({_duracion(dobles)} al doble')
    if triples:
        partes.append(('y ' if dobles else '(') + f'{_duracion(triples)} al triple')
    if dobles or triples:
        partes.append(')')
    return ' '.join(partes) + ', conforme al siguiente desglose semanal.'


ENCABEZADOS = ['JORNADA SEMANAL', 'JORNADA ORDINARIA', 'JORNADA EXTRA', 'HORAS EXTRAS']
