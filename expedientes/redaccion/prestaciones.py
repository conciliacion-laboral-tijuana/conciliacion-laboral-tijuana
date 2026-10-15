"""Capítulo 3 — CAPÍTULO DE PRESTACIONES.

Cada prestación se redacta como un numeral con su monto EN NÚMERO Y EN LETRA,
tal como exige el estándar del despacho (págs. 2-4):

    1. El pago de 3 meses de salario diario, siendo esto la cantidad de
       $51,859.08 pesos (Cincuenta y un mil ochocientos cincuenta y nueve
       pesos 08/100 Moneda Nacional) por concepto de Indemnización
       Constitucional mismos que me corresponde por el despido injustificado
       del que fui objeto.

Los MONTOS provienen siempre del cálculo determinista (`calculo_para_demanda`);
este módulo sólo los viste de texto.  El importe en letra se toma de
`demanda_generator.importe_en_letras` para no tener dos formateos distintos.
"""


def _importe(monto) -> str:
    """'$1,234.56 pesos (Mil doscientos treinta y cuatro pesos 56/100 M.N.)'."""
    from ..demanda_generator import importe_en_letras
    if monto is None:
        return '[MONTO]'
    return f'${monto:,.2f} pesos ({importe_en_letras(monto)})'


def _texto_otras_prestaciones(datos: dict) -> str:
    return str(datos.get('otras_prestaciones_detalle') or '').strip()


def renglones(datos: dict, calculo: dict, condiciones: dict) -> list:
    """Lista de textos, uno por prestación reclamada.

    El orden sigue el del estándar: indemnización, vacaciones vencidas, prima
    vacacional vencida, vacaciones proporcionales, prima vacacional
    proporcional, aguinaldo, salarios devengados, prima de antigüedad,
    constancia de servicios, comprobantes fiscales, horas extras.
    """
    from ..demanda_generator import _filas_prestaciones

    expediente = datos.get('_expediente')          # inyectado por el adaptador
    por_concepto = {}
    if expediente is not None:
        for concepto, fundamento, monto in _filas_prestaciones(calculo, expediente):
            por_concepto[concepto] = (monto, fundamento)
    elif not (calculo or {}).get('success'):
        # Sin cálculo y sin expediente no hay respaldo: se listan los conceptos
        # SIN monto, para que nunca aparezca una cifra inventada.
        for concepto in ('Indemnización Constitucional (3 meses)', 'Vacaciones',
                         'Prima Vacacional', 'Aguinaldo Proporcional',
                         'Prima de Antigüedad'):
            por_concepto[concepto] = (None, None)

    salida = []

    # ─── 1. Indemnización constitucional (arts. 48 y 50 LFT) ──────────────
    if condiciones['reclama_indemnizacion']:
        monto, _ = por_concepto.get('Indemnización Constitucional (3 meses)', (None, None))
        if monto:
            salida.append(
                f'El pago de 3 meses de salario diario, siendo esto la cantidad '
                f'de {_importe(monto)} por concepto de INDEMNIZACIÓN '
                f'CONSTITUCIONAL, misma que me corresponde por el despido '
                f'injustificado del que fui objeto.'
            )

    # ─── Indemnización de 20 días por año (art. 50 fr. II LFT) ────────────
    monto20, _ = por_concepto.get('Indemnización 20 días por año', (None, None))
    if monto20:
        salida.append(
            f'El pago de la cantidad de {_importe(monto20)} por concepto de '
            f'INDEMNIZACIÓN DE 20 DÍAS DE SALARIO POR CADA AÑO DE SERVICIOS '
            f'prestados, de conformidad con el artículo 50 fracción II de la '
            f'Ley Federal del Trabajo.'
        )

    # ─── Vacaciones (art. 76 LFT) ─────────────────────────────────────────
    if condiciones['reclama_vacaciones']:
        monto, fundamento = por_concepto.get('Vacaciones', (None, None))
        if monto:
            salida.append(
                f'El pago de la cantidad de {_importe(monto)} por concepto de '
                f'VACACIONES {_periodo_vacaciones(datos, calculo)}, cantidad '
                f'calculada de acuerdo con el artículo 76 de la Ley Federal del '
                f'Trabajo, mismas que no me fueron cubiertas en tiempo y forma '
                f'correspondientes al período laborado para los aquí demandados.'
            )

    # ─── Vacaciones de ciclos anteriores ──────────────────────────────────
    monto_venc, fund_venc = por_concepto.get(
        'Vacaciones de ciclos anteriores', (None, None)
    )
    if monto_venc:
        salida.append(
            f'El pago de la cantidad de {_importe(monto_venc)} por concepto de '
            f'VACACIONES VENCIDAS de ciclos anteriores no disfrutadas ni '
            f'pagadas, de conformidad con el artículo 79 de la Ley Federal del '
            f'Trabajo.'
        )

    # ─── Prima vacacional (art. 80 LFT) ───────────────────────────────────
    if condiciones['reclama_prima_vacacional']:
        monto, _ = por_concepto.get('Prima Vacacional', (None, None))
        if monto:
            pct = datos.get('prima_vacacional_porcentaje') or 25
            salida.append(
                f'El pago de la cantidad de {_importe(monto)} por concepto de '
                f'PRIMA VACACIONAL correspondiente al {pct:g}% sobre las '
                f'vacaciones que me corresponden, mismas que no me fueron '
                f'cubiertas en tiempo y forma correspondientes al período '
                f'laborado para los aquí demandados.'
            )

    # ─── Aguinaldo (art. 87 LFT) ──────────────────────────────────────────
    if condiciones['reclama_aguinaldo']:
        monto, _ = por_concepto.get('Aguinaldo Proporcional', (None, None))
        if monto:
            salida.append(
                f'El pago de la cantidad de {_importe(monto)} por concepto de '
                f'AGUINALDO PROPORCIONAL correspondiente al período laborado '
                f'durante el último año a la fecha de mi despido, mismos que no '
                f'me fueron cubiertos en tiempo y forma.'
            )

    # ─── Salarios devengados ──────────────────────────────────────────────
    if condiciones['incluir_salarios_devengados']:
        monto, _ = por_concepto.get('Salarios Devengados', (None, None))
        if monto:
            salida.append(
                f'El pago de la cantidad de {_importe(monto)} por concepto de '
                f'SALARIOS DEVENGADOS, mismos que no me fueron cubiertos en '
                f'tiempo y forma correspondientes al período laborado para los '
                f'aquí demandados.'
            )

    # ─── Prima de antigüedad (art. 162 LFT) ───────────────────────────────
    if condiciones['reclama_prima_antiguedad']:
        monto, fundamento = por_concepto.get('Prima de Antigüedad', (None, None))
        if monto:
            salida.append(
                f'El pago de la cantidad de {_importe(monto)} por concepto de '
                f'PRIMA DE ANTIGÜEDAD, de conformidad con el artículo 162 de la '
                f'Ley Federal del Trabajo, por el tiempo que duró la relación '
                f'laboral con los aquí demandados.'
            )

    # ─── Horas extras (arts. 66 y 68 LFT) ─────────────────────────────────
    if condiciones['incluir_horas_extras']:
        monto, _ = por_concepto.get('Horas Extras', (None, None))
        if monto:
            salida.append(
                f'El pago de la cantidad de {_importe(monto)} por concepto de '
                f'HORAS EXTRAS {_detalle_horas_extras(datos, calculo)}, mismas '
                f'que no me fueron cubiertas en tiempo y forma a pesar de '
                f'haberlas laborado.'
            )

    # ─── Otras prestaciones (capturadas por el asesor) ────────────────────
    otras = _texto_otras_prestaciones(datos)
    if otras:
        salida.append(
            f'El pago de las siguientes prestaciones: {otras}'
        )

    # ─── Constancia de servicios (art. 132 fr. VIII LFT) ──────────────────
    if condiciones['reclama_constancia']:
        salida.append(
            'La entrega de una CONSTANCIA DE SERVICIOS del tiempo laborado '
            'para los aquí demandados, en términos del artículo 132 fracción '
            'VIII de la Ley Federal del Trabajo.'
        )

    # ─── Comprobantes fiscales INFONAVIT / IMSS / SAT ─────────────────────
    if condiciones['reclama_comprobantes_fiscales']:
        periodo = _periodo_laboral(datos)
        for instituto in ('Instituto del Fondo Nacional de la Vivienda para los '
                          'Trabajadores',
                          'Instituto Mexicano del Seguro Social',
                          'Servicio de Administración Tributaria'):
            salida.append(
                f'La entrega de los comprobantes fiscales del cumplimiento de '
                f'los pagos efectuados a mi nombre por parte de la moral '
                f'demandada al {instituto}, correspondientes a los períodos '
                f'comprendidos {periodo}, y que obran en poder de la moral '
                f'demandada.'
            )

    return salida


def _periodo_laboral(datos: dict) -> str:
    """'del día 1 de abril de 2022 al 30 de abril de 2026'."""
    from ..demanda_generator import _fecha_espanol
    desde = datos.get('fecha_ingreso')
    hasta = datos.get('fecha_despido')
    if desde and hasta:
        return (f'del día {_fecha_espanol(desde)} al {_fecha_espanol(hasta)}')
    return 'del período laborado'


def _periodo_vacaciones(datos: dict, calculo: dict) -> str:
    """'Vencidas Correspondientes del periodo comprendido del ... al ...'."""
    from ..demanda_generator import _fecha_espanol
    desde = datos.get('fecha_ingreso')
    hasta = datos.get('fecha_despido')
    if desde and hasta:
        return (f'correspondientes al periodo comprendido del '
                f'{_fecha_espanol(desde)} al {_fecha_espanol(hasta)}')
    return 'correspondientes al período laborado'


def _detalle_horas_extras(datos: dict, calculo: dict) -> str:
    """'“Dobles” (a razón de N horas extras por semana) laboradas, del periodo ...'."""
    from ..demanda_generator import _fecha_espanol
    he = (calculo or {}).get('horas_extras') or {}
    tipo = he.get('tipo') or 'dobles'
    etiqueta = {'dobles': '“Dobles”', 'triples': '“Triples”'}.get(tipo, '“Dobles y Triples”')
    horas_dia = datos.get('horas_extras_dia')
    razon = f' (a razón de {horas_dia:g} horas extras por semana)' if horas_dia else ''
    desde = datos.get('horas_extras_periodo_inicio') or datos.get('fecha_ingreso')
    hasta = datos.get('horas_extras_periodo_fin') or datos.get('fecha_despido')
    periodo = ''
    if desde and hasta:
        periodo = (f', del periodo comprendido del {_fecha_espanol(desde)} al '
                   f'{_fecha_espanol(hasta)}')
    total_horas = he.get('total_horas')
    horas_txt = ''
    if total_horas:
        horas_txt = f' de {_horas_legibles(total_horas)}'
    return f'{etiqueta}{razon} laboradas{periodo}{horas_txt}'


def _horas_legibles(total_horas) -> str:
    """7.6 → '7 horas y 36 minutos' (como el estándar del despacho)."""
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
    if len(partes) == 1:
        return partes[0]
    return ' y '.join(partes)
