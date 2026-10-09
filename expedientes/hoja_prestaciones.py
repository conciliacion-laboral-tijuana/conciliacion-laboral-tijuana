"""Captura por periodos y cálculo revisable. Los borradores no aprueban importes."""
import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import asdict

from django import forms
from django.core.exceptions import ValidationError
from django.forms import formset_factory

from core.laboral.calculators import CONCEPTOS_DISPONIBLES
from core.laboral.periodo import construir_periodo
from .laboral_calculator import calcular_desde_expediente, reglas_activas, datos_extra_de, conceptos_por_tipo_despido
from .models import HojaPrestaciones, CalculoLaboral

D = Decimal
CERO = D('0')
CENTAVO = D('.01')
DIAS = ('lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo')


def dinero(valor):
    return D(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def empaquetar(value):
    if isinstance(value, Decimal):
        return {'decimal': str(value)}
    if isinstance(value, date):
        return {'fecha': value.isoformat()}
    if isinstance(value, dict):
        return {k: empaquetar(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [empaquetar(v) for v in value]
    return value


def desempaquetar(value):
    if isinstance(value, dict):
        if set(value) == {'fecha'}:
            return date.fromisoformat(value['fecha'])
        if set(value) == {'decimal'}:
            return D(value['decimal'])
        return {k: desempaquetar(v) for k, v in value.items()}
    if isinstance(value, list):
        return [desempaquetar(v) for v in value]
    return value


def huella(expediente, datos):
    cliente = expediente.cliente
    inputs = {name: getattr(cliente, name) for name in
              ('salario', 'fecha_ingreso', 'fecha_salida', 'jornada', 'zona_salarial', 'accion_preferida')}
    legacy = CalculoLaboral.objects.filter(expediente=expediente).first()
    config = {
        'motor': 1, 'cliente': inputs, 'tipo': expediente.tipo_despido or 'injustificado',
        'datos': datos, 'reglas': asdict(reglas_activas()),
        'extras_calculadora': datos_extra_de(legacy) if legacy else None,
        'conceptos_calculadora': {c['key']: getattr(legacy, 'incluir_' + c['key'])
                                  for c in CONCEPTOS_DISPONIBLES} if legacy else None,
    }
    return hashlib.sha256(json.dumps(empaquetar(config), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def hoja_de(expediente):
    return HojaPrestaciones.objects.filter(expediente=expediente).first()


def resultado_vigente(expediente, hoja=None, aprobado=False):
    hoja = hoja or hoja_de(expediente)
    if not hoja or not hoja.resultado or hoja.huella != huella(expediente, hoja.datos):
        return None
    if aprobado and not hoja.aprobado_en:
        return None
    return desempaquetar(hoja.resultado)


class CapturaForm(forms.Form):
    salario_integrado = forms.DecimalField(label='Salario diario integrado confirmado ($)', min_value=D('.01'), max_digits=12, decimal_places=2, required=False, widget=forms.NumberInput(attrs={'class': 'input', 'step': '.01'}))
    salarios_devengados = forms.DecimalField(label='Salarios devengados no cubiertos ($), después de descontar pagos', min_value=0, max_digits=12, decimal_places=2, initial=0, widget=forms.NumberInput(attrs={'class': 'input', 'step': '.01'}))

    extras_estado = forms.ChoiceField(label='Horas extras pendientes', choices=[('', 'Pendiente de confirmar'), ('no', 'No hay horas extras pendientes'), ('si', 'Sí, detallar por semana')], widget=forms.Select(attrs={'class': 'input'}))
    datos_confirmados = forms.BooleanField(label='Confirmé los periodos, salarios, pagos y reglas aplicables; los datos no son estimaciones.', required=False)
    aguinaldo_pagado = forms.DecimalField(label='Aguinaldo del año de salida ya pagado ($)', min_value=0, max_digits=12, decimal_places=2, initial=0, widget=forms.NumberInput(attrs={'class': 'input', 'step': '.01'}))
    dias_aguinaldo = forms.DecimalField(label='Días anuales de aguinaldo aplicables', min_value=1, max_value=366, max_digits=6, decimal_places=2, initial=15, widget=forms.NumberInput(attrs={'class': 'input', 'step': '.01'}))
    prima_porcentaje = forms.DecimalField(label='Prima vacacional aplicable (%)', min_value=0, max_value=1000, max_digits=7, decimal_places=2, initial=25, widget=forms.NumberInput(attrs={'class': 'input', 'step': '.01'}))


class SemanaForm(forms.Form):
    semana = forms.DateField(label='Lunes de la semana', widget=forms.DateInput(attrs={'class': 'input', 'type': 'date'}))
    salario_diario = forms.DecimalField(label='Salario diario de esa semana ($)', min_value=D('.01'), max_digits=12, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'input', 'step': '.01'}))
    jornada = forms.ChoiceField(choices=[('diurna', 'Diurna'), ('nocturna', 'Nocturna'), ('mixta', 'Mixta')], widget=forms.Select(attrs={'class': 'input'}))
    limite_dobles = forms.DecimalField(label='Umbral semanal para horas al doble', min_value=0, max_value=168, max_digits=5, decimal_places=2, initial=9, widget=forms.NumberInput(attrs={'class': 'input', 'step': '.01'}))
    pagado = forms.DecimalField(label='Horas extras ya pagadas en esta semana ($)', min_value=0, max_digits=12, decimal_places=2, initial=0, widget=forms.NumberInput(attrs={'class': 'input', 'step': '.01'}))
    for dia in DIAS:
        locals()['salario_' + dia] = forms.DecimalField(label='Base diaria del ' + dia + ' ($), si cambió', min_value=D('.01'), max_digits=12, decimal_places=2, required=False, widget=forms.NumberInput(attrs={'class': 'input', 'step': '.01'}))
        locals()[dia] = forms.DecimalField(label=dia.capitalize(), min_value=0, max_value=24, max_digits=5, decimal_places=2, initial=0, widget=forms.NumberInput(attrs={'class': 'input', 'step': '.01'}))
    del dia

    def clean_semana(self):
        value = self.cleaned_data['semana']
        if value.weekday() != 0:
            raise ValidationError('Selecciona el lunes que inicia la semana; esto evita contabilizarla dos veces.')
        return value


class VacacionesForm(forms.Form):
    anio = forms.IntegerField(label='Año de servicio', min_value=1, widget=forms.NumberInput(attrs={'class': 'input', 'readonly': True}))
    dias_derecho = forms.DecimalField(label='Días anuales de derecho aplicables', min_value=1, max_value=366, max_digits=7, decimal_places=3, widget=forms.NumberInput(attrs={'class': 'input', 'step': '.001'}))
    disfrutados = forms.DecimalField(label='Días disfrutados o compensados', min_value=0, max_digits=9, decimal_places=4, initial=0, widget=forms.NumberInput(attrs={'class': 'input', 'step': '.0001'}))
    salario_diario = forms.DecimalField(label='Base diaria aplicable para pago ($)', min_value=D('.01'), max_digits=12, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'input', 'step': '.01'}))
    pagado = forms.DecimalField(label='Pago adicional ya recibido de vacaciones ($)', min_value=0, max_digits=12, decimal_places=2, initial=0, widget=forms.NumberInput(attrs={'class': 'input', 'step': '.01'}))
    prima_pagada = forms.DecimalField(label='Prima vacacional ya recibida ($)', min_value=0, max_digits=12, decimal_places=2, initial=0, widget=forms.NumberInput(attrs={'class': 'input', 'step': '.01'}))
    incluir = forms.BooleanField(label='Reclamar el saldo de este periodo', required=False, initial=True)
    confirmado = forms.BooleanField(label='Revisé los días, la base salarial, los pagos y la procedencia de este periodo', required=False)


Semanas = formset_factory(SemanaForm, extra=0, can_delete=True, max_num=520, validate_max=True, absolute_max=520)
Vacaciones = formset_factory(VacacionesForm, extra=0, max_num=80, validate_max=True, absolute_max=80)


def ciclos_para(cliente):
    periodo = construir_periodo(cliente.fecha_ingreso, cliente.fecha_salida, reglas_activas())
    return periodo.ciclos_vacaciones if periodo else []


def formularios(expediente, post=None):
    hoja = hoja_de(expediente)
    datos = desempaquetar(hoja.datos) if hoja else {}
    cliente = expediente.cliente
    sd = dinero((cliente.salario or CERO) / 30)
    ciclos = ciclos_para(cliente)
    fechas = [str(cliente.fecha_ingreso), str(cliente.fecha_salida)]
    vacaciones = (datos.get('vacaciones') if datos.get('fechas') == fechas else None) or [
        {'anio': c.numero, 'dias_derecho': dias_sugeridos(c), 'salario_diario': sd,
         'disfrutados': 0, 'pagado': 0, 'prima_pagada': 0, 'incluir': True} for c in ciclos]
    config = datos.get('config', {'dias_aguinaldo': reglas_activas().aguinaldo_dias,
                                'prima_porcentaje': reglas_activas().prima_vacacional_porcentaje * 100})
    semanas_formset = Semanas(post, prefix='semanas', initial=datos.get('semanas', []))
    vacaciones_formset = Vacaciones(post, prefix='vacaciones', initial=vacaciones)
    # Un guardado automático puede persistir una fila nueva mientras el navegador
    # conserva INITIAL_FORMS=0. Esa fila sigue siendo real aunque no haya cambiado.
    if post is not None:
        for formset in (semanas_formset, vacaciones_formset):
            for row in formset.forms:
                row.empty_permitted = False
    return {
        'captura_prestaciones': CapturaForm(post, prefix='prestaciones', initial=config),
        'semanas_formset': semanas_formset,
        'vacaciones_formset': vacaciones_formset,
        'ciclos_vacaciones': ciclos,
        'periodos_fechas': '|'.join(fechas),
        'hoja': hoja,
    }


def validar_formularios(expediente, forms_context, final=False):
    config, semanas, vacaciones = (forms_context[key] for key in
                                  ('captura_prestaciones', 'semanas_formset', 'vacaciones_formset'))
    hoja = forms_context.get('hoja')
    fechas = [str(expediente.cliente.fecha_ingreso), str(expediente.cliente.fecha_salida)]
    if (hoja and hoja.datos.get('fechas') and hoja.datos.get('fechas') != fechas
            and config.data.get('periodos_fechas') != '|'.join(fechas)):
        config.is_valid()
        config.add_error(None, 'Las fechas cambiaron. Recarga la hoja para revisar los nuevos periodos de vacaciones.')
        return None
    valid = all([config.is_valid(), semanas.is_valid(), vacaciones.is_valid()])
    if not valid:
        return None
    if final and not config.cleaned_data.get('salario_integrado'):
        config.add_error('salario_integrado', 'Captura el salario diario integrado revisado para las indemnizaciones.')
        return None
    if final and not config.cleaned_data['datos_confirmados']:
        config.add_error('datos_confirmados', 'Confirma los datos y las reglas aplicables antes de calcular.')
        return None
    if config.cleaned_data['prima_porcentaje'] < 25:
        config.add_error('prima_porcentaje', 'Revisa el porcentaje: no puede ser inferior al mínimo de 25%.')
        return None
    if config.cleaned_data['dias_aguinaldo'] < 15:
        config.add_error('dias_aguinaldo', 'Revisa los días: no pueden ser inferiores al mínimo de 15.')
        return None
    semana_rows = [dict(f.cleaned_data) for f in semanas if f.cleaned_data and not f.cleaned_data.get('DELETE')]
    for row in semana_rows:
        row.pop('DELETE', None)
    if config.cleaned_data['extras_estado'] == 'no' and semana_rows:
        config.add_error('extras_estado', 'Elimina las semanas o selecciona que sí hay horas extras.')
        return None
    if config.cleaned_data['extras_estado'] == 'si' and not semana_rows:
        config.add_error('extras_estado', 'Agrega las semanas que tienen horas extras pendientes.')
        return None
    if len({r['semana'] for r in semana_rows}) != len(semana_rows):
        config.add_error(None, 'Hay semanas duplicadas; reúne todas las horas de una semana en una sola fila.')
        return None
    cliente = expediente.cliente
    for row in semana_rows:
        for i, dia in enumerate(DIAS):
            fecha = row['semana'] + timedelta(days=i)
            if row[dia] and (not cliente.fecha_ingreso or not cliente.fecha_salida
                             or not cliente.fecha_ingreso <= fecha <= cliente.fecha_salida):
                config.add_error(None, 'Hay horas extras fuera de las fechas de la relación laboral.')
                return None
    vac_rows = [dict(f.cleaned_data) for f in vacaciones if f.cleaned_data]
    expected = {c.numero for c in ciclos_para(cliente)}
    if {r['anio'] for r in vac_rows} != expected or len(vac_rows) != len(expected):
        config.add_error(None, 'Las fechas cambiaron o falta un aniversario. Guarda los datos y revisa todos los periodos de vacaciones.')
        return None
    if final and not expected:
        config.add_error(None, 'Completa fechas válidas para construir los periodos de vacaciones.')
        return None
    if final and any(not row.get('confirmado') for row in vac_rows):
        config.add_error(None, 'Revisa y confirma cada periodo de vacaciones; no se presume que todos estén pendientes.')
        return None
    return empaquetar({'fechas': [str(cliente.fecha_ingreso), str(cliente.fecha_salida)], 'config': config.cleaned_data, 'semanas': semana_rows, 'vacaciones': vac_rows})


def calcular_hoja(expediente, stored):
    datos = desempaquetar(stored)
    config = datos['config']
    cliente = expediente.cliente
    if not config['datos_confirmados'] or not config['extras_estado'] or not config.get('salario_integrado'):
        raise ValidationError('Confirma los datos y si hay horas extras pendientes.')
    if not cliente.imss_confirmado:
        raise ValidationError('Confirma si el trabajador tuvo IMSS.')
    if not cliente.salario or not cliente.fecha_ingreso or not cliente.fecha_salida:
        raise ValidationError('Completa salario y fechas antes de calcular.')
    if cliente.fecha_salida < cliente.fecha_ingreso:
        raise ValidationError('La fecha de salida no puede ser anterior al ingreso.')
    if config['salario_integrado'] < cliente.salario / 30:
        raise ValidationError('El salario diario integrado no puede ser menor que la base diaria. Revisa los componentes salariales.')
    if any(not row.get('confirmado') for row in datos['vacaciones']):
        raise ValidationError('Confirma todos los periodos de vacaciones.')
    legacy = CalculoLaboral.objects.filter(expediente=expediente).first()
    conceptos = {f'incluir_{c["key"]}': getattr(legacy, f'incluir_{c["key"]}') for c in CONCEPTOS_DISPONIBLES} if legacy else None
    extra = datos_extra_de(legacy) if legacy else {}
    # Estos conceptos tienen captura propia: no se suman los antiguos totales.
    extra.update(salario_integrado=config['salario_integrado'], salarios_devengados=config['salarios_devengados'], dias_vacaciones_override=0, dias_vacaciones_vencidos=0,
                 horas_extra_normales=0, horas_extra_excedentes=0, horas_extra_cantidad=0)
    if conceptos is not None:
        conceptos['incluir_salarios_devengados'] = config['salarios_devengados'] > 0
    else:
        conceptos = conceptos_por_tipo_despido(expediente.tipo_despido or 'injustificado', construir_periodo(cliente.fecha_ingreso, cliente.fecha_salida).años_completos)
        conceptos['incluir_salarios_devengados'] = config['salarios_devengados'] > 0
    result = calcular_desde_expediente(expediente, conceptos_seleccionados=conceptos, datos_extra=extra)
    if not result['success']:
        raise ValidationError(result['error'])
    audit = []
    sd = result['salario_diario']
    periodo = construir_periodo(cliente.fecha_ingreso, cliente.fecha_salida, reglas_activas())
    aguinaldo_bruto = dinero(sd * config['dias_aguinaldo'] * D(periodo.dias_anio_actual) / periodo.dias_anio_total)
    if conceptos and not conceptos['incluir_aguinaldo']:
        aguinaldo_bruto = CERO
    if config['aguinaldo_pagado'] > aguinaldo_bruto:
        raise ValidationError('El aguinaldo ya pagado supera el importe calculado. Revisa el periodo y el pago.')
    result['aguinaldo']['monto'] = aguinaldo_bruto - config['aguinaldo_pagado']
    result['aguinaldo']['dias_ley'] = config['dias_aguinaldo']
    audit.append({'concepto': 'Aguinaldo', 'periodo': f'{max(cliente.fecha_ingreso, date(cliente.fecha_salida.year, 1, 1))} a {cliente.fecha_salida}',
                  'formula': f'{sd} × {config["dias_aguinaldo"]} × {periodo.dias_anio_actual}/{periodo.dias_anio_total}',
                  'bruto': aguinaldo_bruto, 'pagado': config['aguinaldo_pagado'], 'pendiente': result['aguinaldo']['monto']})
    dobles = triples = monto_horas = pagado_horas = CERO
    for row in datos['semanas']:
        cantidad = sum((row[dia] for dia in DIAS), CERO)
        doble = min(cantidad, row['limite_dobles'])
        triple = cantidad - doble
        jornada = reglas_activas().jornada_diaria_horas(row['jornada'])
        disponible = row['limite_dobles']
        bruto_sin_redondear = CERO
        detalle_dias = []
        for dia in DIAS:
            horas = row[dia]
            al_doble = min(horas, disponible)
            al_triple = horas - al_doble
            disponible -= al_doble
            base = row.get('salario_' + dia) or row['salario_diario']
            bruto_sin_redondear += (base / jornada) * (al_doble * 2 + al_triple * 3)
            if horas:
                detalle_dias.append(f'{dia}: ({base}/{jornada}) × ({al_doble} h × 2 + {al_triple} h × 3)')
        bruto = dinero(bruto_sin_redondear)
        if row['pagado'] > bruto:
            raise ValidationError(f'El pago de horas extras de la semana {row["semana"]} supera su importe calculado.')
        dobles += doble
        triples += triple
        monto_horas += bruto - row['pagado']
        pagado_horas += row['pagado']
        audit.append({'concepto': 'Horas extras', 'periodo': f'{row["semana"]} a {row["semana"] + timedelta(days=6)}',
                      'formula': '; '.join(detalle_dias) + f'; umbral semanal {row["limite_dobles"]} h',
                      'bruto': bruto, 'pagado': row['pagado'], 'pendiente': bruto - row['pagado']})
    result['horas_extras'].update(cantidad=dobles + triples, dobles=dobles, triples=triples, monto=monto_horas,
                                por_semana=True, pagado=pagado_horas)
    rows_by_year = {r['anio']: r for r in datos['vacaciones']}
    vac_total = prima_total = dias_pendientes = CERO
    for ciclo in periodo.ciclos_vacaciones:
        row = rows_by_year.get(ciclo.numero)
        if row is None:
            raise ValidationError('Falta capturar un periodo de vacaciones.')
        derecho = row['dias_derecho'] if ciclo.completo else row['dias_derecho'] * ciclo.fraccion
        if row['disfrutados'] > derecho:
            raise ValidationError(f'Los días disfrutados del año de servicio {ciclo.numero} superan el derecho calculado.')
        # La prima también corresponde a vacaciones ya disfrutadas, si no se pagó.
        pendiente_dias = derecho - row['disfrutados']
        bruto = dinero(pendiente_dias * row['salario_diario'])
        prima_bruto = dinero(derecho * row['salario_diario'] * config['prima_porcentaje'] / 100)
        if row['pagado'] > bruto or row['prima_pagada'] > prima_bruto:
            raise ValidationError(f'Los pagos del año de servicio {ciclo.numero} superan el importe calculado; revisa su captura.')
        vac = bruto - row['pagado'] if row['incluir'] else CERO
        prima = prima_bruto - row['prima_pagada'] if row['incluir'] else CERO
        vac_total += vac
        prima_total += prima
        if row['incluir']:
            dias_pendientes += pendiente_dias
        periodo_fin = ciclo.fin - timedelta(days=1) if ciclo.completo else cliente.fecha_salida
        etiqueta = f'{ciclo.inicio} a {periodo_fin} · año {ciclo.numero}'
        audit.append({'concepto': 'Vacaciones' + ('' if ciclo.completo else ' proporcionales'), 'periodo': etiqueta,
                      'formula': f'({derecho:.4f} días de derecho − {row["disfrutados"]} disfrutados) × {row["salario_diario"]}; ' + ('incluido' if row['incluir'] else 'excluido por el abogado'),
                      'bruto': bruto, 'pagado': row['pagado'], 'pendiente': vac})
        audit.append({'concepto': 'Prima vacacional', 'periodo': etiqueta,
                      'formula': f'{derecho:.4f} días de derecho × {row["salario_diario"]} × {config["prima_porcentaje"]}%',
                      'bruto': prima_bruto, 'pagado': row['prima_pagada'], 'pendiente': prima})
    result['vacaciones'].update(monto=vac_total, dias_segun_antiguedad=dias_pendientes,
                               dias_causadas_anteriores=0, dias_proporcionales=dias_pendientes,
                               monto_causadas=CERO, monto_proporcionales=vac_total, por_periodos=True)
    result['vacaciones_vencidas'].update(monto=CERO, dias=0)
    result['prima_vacacional'].update(monto=prima_total, porcentaje=config['prima_porcentaje'])
    for concept in CONCEPTOS_DISPONIBLES:
        key = concept['key']
        if key not in ('aguinaldo', 'vacaciones', 'prima_vacacional', 'vacaciones_vencidas', 'horas_extras'):
            audit.append({'concepto': concept['label'], 'periodo': f'{cliente.fecha_ingreso} a {cliente.fecha_salida}',
                          'formula': formula_concepto(key, result),
                          'bruto': result[key]['monto'], 'pagado': CERO, 'pendiente': result[key]['monto']})
    result['total'] = sum((result[c['key']]['monto'] for c in CONCEPTOS_DISPONIBLES), CERO)
    result['hoja_desglose'] = audit
    return result


def formula_concepto(key, result):
    dato = result[key]
    if key == 'indemnizacion':
        return f'{dato["dias"]} días × salario diario integrado {dato["base"]}'
    if key == 'indemnizacion_20dias':
        return f'{dato["dias_por_año"]} días × {dato["años_servicio"]} años × salario diario integrado {dato["base"]}'
    if key == 'prima_antiguedad':
        return f'{dato["dias_por_año"]} días × {dato["años_servicio"]} años × base diaria {dato["salario_base"]}; piso {dato["piso_diario"]}, tope {dato["tope_diario"]}'
    if key in ('dias_festivos', 'descanso_semanal'):
        return f'{dato["dias"]} días × {dato["multiplicador"]} × salario diario {result["salario_diario"]}'
    if key == 'salarios_devengados':
        return 'Saldo declarado y confirmado de salarios devengados no cubiertos'
    return 'Concepto no incluido'


def dias_sugeridos(ciclo):
    # El derecho de un ciclo completo nació en su aniversario. Los periodos
    # anteriores a 2023 usan la tabla previa a vacaciones dignas; el abogado
    # confirma la aplicación temporal y cualquier mejora contractual.
    if ciclo.completo and ciclo.fin < date(2023, 1, 1):
        return 6 + 2 * (ciclo.numero - 1) if ciclo.numero <= 4 else 14 + 2 * ((ciclo.numero - 5) // 5)
    return ciclo.dias_correspondientes
