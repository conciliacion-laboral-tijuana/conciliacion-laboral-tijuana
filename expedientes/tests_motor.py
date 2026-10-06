"""
Batería de pruebas del motor jurídico de cálculos (core/laboral)
================================================================

Casos que el despacho necesita poder reproducir y auditar:

  · Antigüedad: 3 meses, 11 meses, 1 año, 1 año 6 meses, 5 años, 10 años,
    y el caso límite de terminar exactamente en el aniversario.
  · Aguinaldo: proporcional al AÑO CALENDARIO, nunca a la antigüedad total.
  · Vacaciones: ciclos de aniversario, sin doble proporcionalidad, y el
    comportamiento con menos de un año según el criterio configurado.
  · Prima de antigüedad: piso y techo de los arts. 485/486 LFT por zona
    (frontera vs. resto del país).  Verificar que NO sea 2 × UMA.
  · Salario diario vs. salario diario integrado (arts. 84 y 89 LFT).
  · Horas extras: dobles (art. 66) y excedentes (art. 68), con los topes
    graduales 2026-2030 de la reforma del 1 de mayo de 2026.
  · Festivos (arts. 74-75) vs. descanso semanal (arts. 69 y 73).
  · Procedencia por tipo de despido (arts. 46, 50 y 162 LFT).

Uso:
    uv run python manage.py test expedientes.tests_motor --settings=config.settings_test
"""

from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from core.laboral import formulas as f
from core.laboral import rules as r
from core.laboral.calculators import calcular_todo, conceptos_base, conceptos_para_tipo
from core.laboral.periodo import construir_periodo


D = Decimal
SALARIO_MENSUAL = D('12000')      # $400.00 diarios
SD = D('400')                    # 12000 / 30


def _calcular(ingreso, salida, **kwargs):
    kwargs.setdefault('salario', SALARIO_MENSUAL)
    return calcular_todo(ingreso, salida, **kwargs)


def _q(valor):
    """Cuantiza a 2 decimales como hace el motor al devolver los montos."""
    return D(str(valor)).quantize(D('0.01'))


class ReglasLegalesTests(SimpleTestCase):
    """Valores y topes que deben venir de la ley, no de constantes del código."""

    def test_tope_prima_antiguedad_es_doble_de_salario_minimo_y_no_doble_uma(self):
        """Arts. 485/486 LFT: el tope es 2 × salario mínimo del ÁREA."""
        reglas = r.ReglasLegales.por_defecto()

        # Zona Libre de la Frontera Norte (Tijuana): 2 × $440.87
        self.assertEqual(D('440.87'), reglas.salario_minimo_frontera)
        self.assertEqual(D('881.74'), reglas.tope_prima_antiguedad('frontera'))

        # Resto del país: 2 × $315.04
        self.assertEqual(D('630.08'), reglas.tope_prima_antiguedad('general'))

        # NO debe ser 2 × UMA (ese era el error anterior)
        dos_uma = reglas.uma_diaria * 2
        self.assertEqual(D('234.62'), dos_uma)
        self.assertNotEqual(dos_uma, reglas.tope_prima_antiguedad('frontera'))

    def test_valores_2026_de_uma_y_salario_minimo(self):
        reglas = r.ReglasLegales.por_defecto()
        self.assertEqual(D('117.31'), reglas.uma_diaria)      # INEGI, desde 2026-02-01
        self.assertEqual(D('315.04'), reglas.salario_minimo)  # CONASAMI, desde 2026-01-01

    def test_topes_de_horas_extra_son_graduales_por_anio(self):
        """Transitorio Cuarto de la reforma DOF 01-05-2026."""
        reglas = r.ReglasLegales.por_defecto()
        esperados = {2026: 9, 2027: 9, 2028: 10, 2029: 11, 2030: 12}
        for anio, tope in esperados.items():
            self.assertEqual(tope, reglas.horas_extra_dobles_max_semana(anio), f'año {anio}')

    def test_jornada_ordinaria_maxima_sigue_siendo_48_en_2026(self):
        """La reducción a 40 h es gradual: en 2026 la jornada sigue en 48 h."""
        reglas = r.ReglasLegales.por_defecto()
        self.assertEqual(48, reglas.jornada_maxima_semanal(2026))
        self.assertEqual(46, reglas.jornada_maxima_semanal(2027))
        self.assertEqual(40, reglas.jornada_maxima_semanal(2030))
        # El texto del art. 59 ya dice 40 h, pero el transitorio Segundo retrasa
        # su aplicación hasta 2030.
        self.assertEqual(D('8'), reglas.jornada_diaria_horas('diurna'))
        self.assertEqual(D('7'), reglas.jornada_diaria_horas('nocturna'))
        self.assertEqual(D('7.5'), reglas.jornada_diaria_horas('mixta'))

    def test_tabla_de_vacaciones_por_antiguedad(self):
        """Art. 76 LFT (reforma DOF 27-12-2022)."""
        esperado = {0: 0, 1: 12, 2: 14, 3: 16, 4: 18, 5: 20,
                    6: 20, 9: 20, 10: 22, 11: 22, 15: 24, 20: 26}
        for años, dias in esperado.items():
            self.assertEqual(dias, r.obtener_dias_vacaciones(años), f'{años} años')

    def test_procedencia_por_tipo_despido(self):
        """Arts. 50 y 162 LFT: no todo concepto procede en todo caso."""
        reglas = r.ReglasLegales.por_defecto()

        injustificado = reglas.restricciones_por_tipo('injustificado')
        self.assertTrue(injustificado['incluir_indemnizacion'])
        self.assertTrue(injustificado['incluir_indemnizacion_20dias'])
        self.assertTrue(injustificado['incluir_prima_antiguedad'])

        # Despido justificado: el art. 46 excluye la responsabilidad del patrón
        justificado = reglas.restricciones_por_tipo('justificado')
        self.assertFalse(justificado['incluir_indemnizacion'])
        self.assertFalse(justificado['incluir_indemnizacion_20dias'])
        self.assertTrue(justificado['incluir_prima_antiguedad'])

        # Renuncia voluntaria: prima de antigüedad sólo con 15 años o más
        voluntaria_5 = reglas.restricciones_por_tipo('voluntario', 5)
        voluntaria_20 = reglas.restricciones_por_tipo('voluntario', 20)
        self.assertFalse(voluntaria_5['incluir_prima_antiguedad'])
        self.assertTrue(voluntaria_20['incluir_prima_antiguedad'])
        self.assertFalse(voluntaria_20['incluir_indemnizacion'])

    def test_restricciones_no_encienden_conceptos_apagados(self):
        """La ley no debe encender conceptos que el despacho dejó fuera."""
        base = conceptos_base()
        self.assertFalse(base['incluir_indemnizacion_20dias'])

        conceptos = conceptos_para_tipo('injustificado', 5, base=base)
        self.assertTrue(conceptos['incluir_indemnizacion_20dias'])
        # Los que no dependen de la causa de separación siguen apagados
        self.assertFalse(conceptos['incluir_horas_extras'])
        self.assertFalse(conceptos['incluir_dias_festivos'])
        self.assertFalse(conceptos['incluir_descanso_semanal'])


class PeriodoLaboralTests(SimpleTestCase):
    """El modelo temporal: antigüedad exacta, ciclos y año calendario."""

    def test_antiguedad_usa_aniversarios_y_no_dias_entre_365(self):
        p = construir_periodo(date(2021, 9, 15), date(2026, 9, 15))
        self.assertEqual(5, p.años_completos)
        self.assertEqual(D('5.0000'), p.años_servicio_decimal)
        self.assertEqual(date(2026, 9, 15), p.aniversario_vigente)
        self.assertEqual(date(2027, 9, 15), p.proximo_aniversario)

        # Un día después ya es 5 años + fracción
        p2 = construir_periodo(date(2021, 9, 15), date(2026, 9, 16))
        self.assertEqual(5, p2.años_completos)
        self.assertEqual(D('5.0027'), p2.años_servicio_decimal)

    def test_bisiesto_no_rompe_la_antiguedad(self):
        """2024 es bisiesto: 731 días siguen siendo 2 años, no 2.0027 años."""
        p = construir_periodo(date(2020, 2, 2), date(2022, 2, 2))
        self.assertEqual(2, p.años_completos)
        self.assertEqual(D('2.0000'), p.años_servicio_decimal)

        p2 = construir_periodo(date(2021, 2, 2), date(2023, 2, 2))
        self.assertEqual(2, p2.años_completos)

    def test_ingreso_29_de_febrero(self):
        p = construir_periodo(date(2024, 2, 29), date(2026, 2, 28))
        self.assertEqual(2, p.años_completos)
        self.assertEqual(date(2026, 2, 28), p.aniversario_vigente)

    def test_dias_del_anio_calendario_para_aguinaldo(self):
        p = construir_periodo(date(2021, 9, 15), date(2026, 9, 15))
        self.assertEqual(2026, p.anio_aguinaldo)
        # 1 ene 2026 → 15 sep 2026 inclusive = 258 días, de 365
        self.assertEqual(258, p.dias_anio_actual)
        self.assertEqual(365, p.dias_anio_total)

    def test_dias_del_ano_bisiesto_para_aguinaldo(self):
        p = construir_periodo(date(2024, 1, 1), date(2024, 3, 31))
        self.assertEqual(366, p.dias_anio_total)
        self.assertEqual(91, p.dias_anio_actual)

    def test_ciclos_de_vacaciones_uno_por_anio_de_servicio(self):
        p = construir_periodo(date(2021, 9, 15), date(2026, 9, 15))
        numeros = [c.numero for c in p.ciclos_vacaciones]
        self.assertEqual([1, 2, 3, 4, 5, 6], numeros)
        # Los cinco primeros están cumplidos; el sexto apenas comienza
        completos = [c.completo for c in p.ciclos_vacaciones]
        self.assertEqual([True] * 5 + [False], completos)
        # Derecho del último año cumplido
        self.assertEqual(20, p.ciclos_vacaciones[-2].dias_correspondientes)

    def test_salida_anterior_al_ingreso_devuelve_none(self):
        self.assertIsNone(construir_periodo(date(2026, 1, 1), date(2025, 1, 1)))

    def test_mismo_dia_ingreso_y_salida(self):
        p = construir_periodo(date(2026, 5, 1), date(2026, 5, 1))
        self.assertEqual(1, p.dias_relacion)
        self.assertEqual(0, p.años_completos)


class AguinaldoTests(SimpleTestCase):
    """Art. 87 LFT: la parte proporcional es del AÑO en curso, no de la antigüedad."""

    def test_aguinaldo_proporcional_al_anio_calendario(self):
        r5 = _calcular(date(2021, 9, 15), date(2026, 9, 15), tipo_despido='injustificado')
        # 258 días de 365 × 15 días × $400
        self.assertEqual(_q(D('258') / D('365') * 15 * SD), r5['aguinaldo']['monto'])
        self.assertEqual(2026, r5['aguinaldo']['anio'])
        self.assertEqual(258, r5['aguinaldo']['dias_trabajados'])
        self.assertEqual(365, r5['aguinaldo']['dias_del_anio'])

    def test_aguinaldo_no_depende_de_los_anos_de_antiguedad(self):
        """El mismo periodo de 2026 da el mismo aguinaldo con 1 año o con 10."""
        r1 = _calcular(date(2025, 1, 1), date(2026, 9, 15))
        r10 = _calcular(date(2016, 1, 1), date(2026, 9, 15))
        self.assertEqual(r1['aguinaldo']['monto'], r10['aguinaldo']['monto'])

    def test_aguinaldo_un_solo_dia_trabajado(self):
        r = _calcular(date(2026, 9, 15), date(2026, 9, 15))
        self.assertEqual(_q(15 * SD / D('365')), r['aguinaldo']['monto'])

    def test_aguinaldo_del_anio_bisiesto_usa_366(self):
        r = _calcular(date(2024, 1, 1), date(2024, 3, 31))
        self.assertEqual(91, r['aguinaldo']['dias_trabajados'])
        self.assertEqual(366, r['aguinaldo']['dias_del_anio'])
        self.assertEqual(_q(91 / D('366') * 15 * SD), r['aguinaldo']['monto'])


class VacacionesTests(SimpleTestCase):
    """Arts. 76, 79 y 81 LFT: ciclos de aniversario, no años × días."""

    def test_vacaciones_de_anios_cumplidos_mas_proporcionales(self):
        """A los 5 años exactos: 20 días del último año cumplido."""
        r = _calcular(date(2021, 9, 15), date(2026, 9, 15))
        v = r['vacaciones']
        self.assertEqual(20, v['dias_causadas_anteriores'])
        self.assertEqual(0, v['dias_proporcionales'])
        self.assertEqual(20, v['dias_segun_antiguedad'])
        self.assertEqual(20 * SD, v['monto'])

    def test_proporcional_usa_el_ciclo_vigente_no_los_anos_totales(self):
        """1 año 6 meses: 14 días del año 2 × fracción del ciclo, NO 1.5 × 16."""
        r = _calcular(date(2025, 3, 1), date(2026, 9, 1))
        v = r['vacaciones']
        # Años cumplidos: 1 (el segundo aniversario es el 01-03-2027)
        self.assertEqual(1, r['años_completos'])
        self.assertEqual(14, v['dias_tabla_ley'])            # año de servicio 2
        self.assertEqual(12, v['dias_causadas_anteriores'])  # año de servicio 1
        # 184 días cumplidos de 365 = 0.5041 → 7.06 días
        self.assertAlmostEqual(D('7.06'), v['dias_proporcionales'], places=2)
        self.assertAlmostEqual(D('19.06'), v['dias_segun_antiguedad'], places=2)

    def test_no_hay_doble_proporcionalidad(self):
        """Regresión: el motor anterior multiplicaba la proporción dos veces."""
        r = _calcular(date(2025, 1, 1), date(2026, 6, 30))
        v = r['vacaciones']
        fraccion = r['periodo_laboral']['fraccion_ciclo_vigente']
        esperado = D(v['dias_tabla_ley']) * fraccion
        self.assertAlmostEqual(esperado, v['dias_proporcionales'], places=2)
        # Con la proporcionalidad doble el resultado sería fraccion², mucho menor
        self.assertGreater(v['dias_proporcionales'], D(v['dias_tabla_ley']) * fraccion ** 2)

    def test_menos_de_un_anio_criterio_proporcional(self):
        """Criterio parametrizado: 12 × tiempo/año (no doblemente proporcional)."""
        r = _calcular(date(2026, 1, 1), date(2026, 6, 30))
        v = r['vacaciones']
        fraccion = D('180') / D('365')
        self.assertEqual(0, r['años_completos'])
        self.assertEqual(12, v['dias_tabla_ley'])
        self.assertAlmostEqual(12 * fraccion, v['dias_proporcionales'], places=2)

    def test_menos_de_un_anio_criterio_mayoritario_sin_vacaciones(self):
        """Criterio 'ninguna': el art. 76 LFT exige más de un año de servicios."""
        reglas = r.ReglasLegales.por_defecto().con(vacaciones_antes_de_un_ano='ninguna')
        res = _calcular(date(2026, 1, 1), date(2026, 6, 30), reglas=reglas)
        self.assertEqual(0, res['vacaciones']['monto'])
        self.assertEqual(0, res['prima_vacacional']['monto'])

    def test_diez_anos_tabla_de_vacaciones(self):
        r = _calcular(date(2016, 9, 15), date(2026, 9, 15))
        self.assertEqual(10, r['años_completos'])
        # El último año cumplido es el 10 → 22 días
        self.assertEqual(22, r['vacaciones']['dias_causadas_anteriores'])

    def test_override_manual_reemplaza_el_calculo(self):
        r = _calcular(date(2021, 9, 15), date(2026, 9, 15),
                      datos_extra={'dias_vacaciones_override': 6})
        v = r['vacaciones']
        self.assertTrue(v['override_aplicado'])
        self.assertEqual(6, v['dias_segun_antiguedad'])
        self.assertEqual(6 * SD, v['monto'])

    def test_vacaciones_de_ciclos_anteriores_se_suman_aparte(self):
        r = _calcular(date(2016, 9, 15), date(2026, 9, 15),
                      conceptos_seleccionados=dict(conceptos_base(),
                                                    incluir_vacaciones_vencidas=True),
                      datos_extra={'dias_vacaciones_vencidos': 20})
        self.assertEqual(20, r['vacaciones_vencidas']['dias'])
        self.assertEqual(20 * SD, r['vacaciones_vencidas']['monto'])
        # Y NO se repite dentro de `vacaciones`
        self.assertEqual(22, r['vacaciones']['dias_segun_antiguedad'])

    def test_prima_vacacional_es_25_por_ciento_del_total(self):
        r = _calcular(date(2021, 9, 15), date(2026, 9, 15))
        self.assertEqual(D('0.25'), D(str(r['prima_vacacional']['porcentaje'])) / D('100'))
        self.assertEqual(r['vacaciones']['monto'] * D('0.25'),
                         r['prima_vacacional']['monto'])


class PrimaAntiguedadTests(SimpleTestCase):
    """Art. 162 con el piso y techo de los arts. 485 y 486 LFT."""

    def test_salario_en_rango_usa_el_salario_real(self):
        """$600 diarios está entre el mínimo y su doble: prima sobre $600."""
        r = _calcular(date(2021, 9, 15), date(2026, 9, 15),
                      salario=D('18000'), zona='frontera')
        pa = r['prima_antiguedad']
        self.assertEqual(D('600'), pa['salario_base'])
        self.assertFalse(pa['tope_aplicado'])
        self.assertEqual(12 * 5 * D('600'), pa['monto'])

    def test_salario_bajo_el_salario_minimo_usa_el_piso_del_articulo_485(self):
        """$400 diarios < $440.87 de la ZLFN: la base se eleva al mínimo."""
        r = _calcular(date(2021, 9, 15), date(2026, 9, 15),
                      salario=D('12000'), zona='frontera')
        pa = r['prima_antiguedad']
        self.assertEqual(D('400'), r['salario_diario'])
        self.assertEqual(D('440.87'), pa['salario_base'])
        self.assertFalse(pa['tope_aplicado'])   # no es tope, es piso
        self.assertEqual(12 * 5 * D('440.87'), pa['monto'])

    def test_salario_sobre_el_tope_se_topea_a_doble_salario_minimo(self):
        """$900 diarios > $881.74 (ZLFN): la prima usa $881.74, no $900."""
        r = _calcular(date(2016, 9, 15), date(2026, 9, 15),
                      salario=D('27000'), zona='frontera')
        pa = r['prima_antiguedad']
        self.assertEqual(D('900'), r['salario_diario'])
        self.assertEqual(D('881.74'), pa['tope_diario'])
        self.assertEqual(D('881.74'), pa['salario_base'])
        self.assertTrue(pa['tope_aplicado'])
        self.assertEqual(12 * 10 * D('881.74'), pa['monto'])

    def test_zona_general_tiene_un_tope_menor_que_la_frontera(self):
        kwargs = dict(fecha_ingreso=date(2016, 9, 15), fecha_salida=date(2026, 9, 15),
                      salario=D('27000'))
        general = calcular_todo(**kwargs, zona='general')
        frontera = calcular_todo(**kwargs, zona='frontera')

        self.assertEqual(D('630.08'), general['prima_antiguedad']['tope_diario'])
        self.assertEqual(D('881.74'), frontera['prima_antiguedad']['tope_diario'])
        self.assertGreater(frontera['prima_antiguedad']['monto'],
                           general['prima_antiguedad']['monto'])

    def test_salario_minor_al_salario_minimo_usa_el_piso(self):
        """Art. 485 LFT: la base nunca puede ser menor al salario mínimo."""
        r = _calcular(date(2021, 9, 15), date(2026, 9, 15),
                      salario=D('6000'), zona='frontera')  # $200 diarios
        pa = r['prima_antiguedad']
        self.assertEqual(D('200'), r['salario_diario'])
        self.assertEqual(D('440.87'), pa['salario_base'])
        self.assertEqual(12 * 5 * D('440.87'), pa['monto'])

    def test_prima_antiguedad_usa_años_con_fraccion(self):
        r = _calcular(date(2021, 1, 1), date(2026, 7, 1), salario=D('18000'))
        pa = r['prima_antiguedad']
        self.assertEqual(5, r['años_completos'])
        # 181 días cumplidos del ciclo 2026-01-01 → 2027-01-01 (365) = 0.4959
        self.assertEqual(D('5.4959'), pa['años_servicio'])
        self.assertEqual(12 * D('5.4959') * D('600'), pa['monto'])


class SalarioIntegradoTests(SimpleTestCase):
    """Arts. 84 y 89 LFT: las indemnizaciones van sobre el salario integrado."""

    def test_sin_prestaciones_declaradas_integrado_igual_a_diario(self):
        r = _calcular(date(2021, 9, 15), date(2026, 9, 15))
        self.assertEqual(r['salario_diario'], r['salario_diario_integrado'])

    def test_indemnizaciones_usan_el_salario_integrado(self):
        r = _calcular(date(2021, 9, 15), date(2026, 9, 15),
                      tipo_despido='injustificado',
                      datos_extra={'salario_integrado_cuota': D('73.33'),
                                   'salario_integrado_ayudas': D('50')})
        sdi = D('523.33')
        self.assertEqual(sdi, r['salario_diario_integrado'])
        self.assertEqual(90 * sdi, r['indemnizacion']['monto'])
        self.assertEqual(20 * 5 * sdi, r['indemnizacion_20dias']['monto'])
        # Pero el aguinaldo y las vacaciones van sobre el salario ordinario
        self.assertEqual(_q(258 / D('365') * 15 * SD), r['aguinaldo']['monto'])

    def test_integrado_por_porcentaje(self):
        reglas = r.ReglasLegales.por_defecto().con(
            salario_integrado_modo='porcentaje', salario_integrado_porcentaje=D('25'))
        res = _calcular(date(2021, 9, 15), date(2026, 9, 15), reglas=reglas)
        self.assertEqual(D('500'), res['salario_diario_integrado'])  # 400 × 1.25
        self.assertEqual(90 * D('500'), res['indemnizacion']['monto'])

    def test_integrado_nunca_menor_al_diario(self):
        r = _calcular(date(2021, 9, 15), date(2026, 9, 15),
                      datos_extra={'salario_integrado': D('100')})
        self.assertEqual(SD, r['salario_diario_integrado'])


class HorasExtrasTests(SimpleTestCase):
    """Arts. 61, 66 y 68 LFT: nada de factor promedio de 2.5."""

    def test_horas_dobles_se_pagan_al_doble(self):
        r = _calcular(date(2025, 1, 1), date(2026, 6, 30),
                      conceptos_seleccionados=dict(conceptos_base(), incluir_horas_extras=True),
                      datos_extra={'horas_extra_normales': D('10'),
                                   'horas_extra_excedentes': D('0')})
        h = r['horas_extras']
        self.assertEqual(D('50'), h['valor_hora'])          # 400 / 8 h
        self.assertEqual(10 * D('50') * 2, h['monto'])
        self.assertEqual(D('10'), h['dobles'])
        self.assertEqual(D('0'), h['triples'])

    def test_horas_excedentes_se_pagan_al_triple(self):
        r = _calcular(date(2025, 1, 1), date(2026, 6, 30),
                      conceptos_seleccionados=dict(conceptos_base(), incluir_horas_extras=True),
                      datos_extra={'horas_extra_normales': D('8'),
                                   'horas_extra_excedentes': D('3')})
        h = r['horas_extras']
        self.assertEqual(8 * D('50') * 2 + 3 * D('50') * 3, h['monto'])

    def test_el_total_se_reparte_contra_el_tope_semanal_del_ano(self):
        """Con total y semanas, el motor reparte dobles/triples, no 2.5×."""
        r = _calcular(date(2025, 1, 1), date(2026, 1, 1),
                      conceptos_seleccionados=dict(conceptos_base(), incluir_horas_extras=True),
                      datos_extra={'horas_extra_cantidad': D('100'),
                                   'horas_extra_semanas': D('10')})
        h = r['horas_extras']
        # 2026 permite 9 h/semana al doble → 90 dobles en 10 semanas
        self.assertEqual(D('90'), h['dobles'])
        # El resto (10 h) entra en las 4 h/semana al triple del art. 68
        self.assertEqual(D('10'), h['triples'])
        self.assertEqual(9, h['maximo_dobles_semana'])
        # El factor promedio 2.5 habría dado 12,500 en vez de 10,500
        self.assertEqual(D('10500'), h['monto'])

    def test_tope_de_triples_es_cuatro_horas_por_semana(self):
        dobles, triples = f.distribuir_horas_extra(D('200'), D('10'), 9, 4)
        self.assertEqual(D('90'), dobles)
        self.assertEqual(D('40'), triples)

    def test_tope_de_dobles_cambia_en_2030(self):
        dobles_2026, _ = f.distribuir_horas_extra(D('120'), D('10'), 9, 4)
        dobles_2030, _ = f.distribuir_horas_extra(D('120'), D('10'), 12, 4)
        self.assertEqual(D('90'), dobles_2026)
        self.assertEqual(D('120'), dobles_2030)

    def test_valor_hora_segun_jornada(self):
        """Art. 61 LFT: la jornada nocturna dura 7 h, no 8."""
        diurna = f.valor_hora(SD, D('8'))
        nocturna = f.valor_hora(SD, D('7'))
        mixta = f.valor_hora(SD, D('7.5'))
        self.assertEqual(D('50.00'), diurna)
        self.assertEqual(D('57.14'), nocturna)
        self.assertEqual(D('53.33'), mixta)

    def test_horas_extras_usan_la_jornada_del_cliente(self):
        r = _calcular(date(2025, 1, 1), date(2026, 6, 30), jornada='nocturna',
                      conceptos_seleccionados=dict(conceptos_base(), incluir_horas_extras=True),
                      datos_extra={'horas_extra_normales': D('7')})
        self.assertEqual(D('57.14'), r['horas_extras']['valor_hora'])
        self.assertEqual(7 * D('57.14') * 2, r['horas_extras']['monto'])


class DescansoYFestivosTests(SimpleTestCase):
    """Arts. 69, 73, 74 y 75 LFT: son conceptos distintos."""

    def test_festivos_se_pagan_al_triplo(self):
        """Arts. 74 y 75: doble por el servicio + el día íntegro."""
        r = _calcular(date(2025, 1, 1), date(2026, 6, 30),
                      conceptos_seleccionados=dict(conceptos_base(), incluir_dias_festivos=True),
                      datos_extra={'dias_festivos_cantidad': 3})
        self.assertEqual(3 * SD * 3, r['dias_festivos']['monto'])

    def test_descanso_semanal_es_concepto_distinto_a_festivos(self):
        """Art. 73: salario doble por el servicio prestado en el descanso."""
        r = _calcular(date(2025, 1, 1), date(2026, 6, 30),
                      conceptos_seleccionados=dict(conceptos_base(),
                                                   incluir_descanso_semanal=True),
                      datos_extra={'dias_descanso_semanal_cantidad': 4})
        self.assertEqual(4 * SD * 2, r['descanso_semanal']['monto'])
        # Los festivos siguen en cero: no se mezclan
        self.assertEqual(D('0'), r['dias_festivos']['monto'])

    def test_dias_de_descanso_teoricos_de_un_dia_por_seis(self):
        """Art. 69 LFT: 1 día de descanso íntegro por cada 6 trabajados."""
        self.assertEqual(60, f.dias_descanso_semanal_teoricos(365, 6))
        self.assertEqual(0, f.dias_descanso_semanal_teoricos(5, 6))


class ProcedenciaPorTipoDespidoTests(SimpleTestCase):
    """Qué conceptos se claimant en cada caso (arts. 46, 50 y 162 LFT)."""

    def test_despido_injustificado_reclama_todo(self):
        r = _calcular(date(2021, 9, 15), date(2026, 9, 15), tipo_despido='injustificado')
        self.assertGreater(r['indemnizacion']['monto'], 0)
        self.assertGreater(r['indemnizacion_20dias']['monto'], 0)
        self.assertGreater(r['prima_antiguedad']['monto'], 0)

    def test_despido_justificado_no_reclama_indemnizacion_pero_si_prima(self):
        r = _calcular(date(2021, 9, 15), date(2026, 9, 15), tipo_despido='justificado')
        self.assertEqual(D('0'), r['indemnizacion']['monto'])
        self.assertEqual(D('0'), r['indemnizacion_20dias']['monto'])
        self.assertGreater(r['prima_antiguedad']['monto'], 0)
        # Las prestaciones ordinarias sí se deben
        self.assertGreater(r['aguinaldo']['monto'], 0)
        self.assertGreater(r['vacaciones']['monto'], 0)

    def test_renuncia_voluntaria_sin_indemnizacion(self):
        r = _calcular(date(2021, 9, 15), date(2026, 9, 15), tipo_despido='voluntario')
        self.assertEqual(D('0'), r['indemnizacion']['monto'])
        self.assertEqual(D('0'), r['indemnizacion_20dias']['monto'])
        self.assertEqual(D('0'), r['prima_antiguedad']['monto'])

    def test_renuncia_voluntaria_con_15_anos_cobra_prima_de_antiguedad(self):
        r = _calcular(date(2011, 9, 15), date(2026, 9, 15), tipo_despido='voluntario')
        self.assertGreater(r['prima_antiguedad']['monto'], 0)

    def test_rescision_reclama_indemnizacion_completa(self):
        r = _calcular(date(2021, 9, 15), date(2026, 9, 15), tipo_despido='rescision')
        self.assertGreater(r['indemnizacion']['monto'], 0)
        self.assertGreater(r['indemnizacion_20dias']['monto'], 0)


class CasosDeAntiguedadTests(SimpleTestCase):
    """Batería por antigüedad: 3 meses, 11 meses, 1 año, 1a6m, 5 y 10 años."""

    CASOS = [
        # (nombre, ingreso, salida, años_completos esperados)
        ('3 meses', date(2026, 4, 1), date(2026, 6, 30), 0),
        ('11 meses', date(2025, 10, 1), date(2026, 9, 1), 0),
        ('1 año', date(2025, 9, 15), date(2026, 9, 15), 1),
        ('1 año 6 meses', date(2025, 3, 1), date(2026, 9, 1), 1),
        ('5 años', date(2021, 9, 15), date(2026, 9, 15), 5),
        ('10 años', date(2016, 9, 15), date(2026, 9, 15), 10),
    ]

    def test_antiguedad_por_caso(self):
        for nombre, ingreso, salida, años in self.CASOS:
            with self.subTest(caso=nombre):
                r = _calcular(ingreso, salida, tipo_despido='injustificado')
                self.assertEqual(años, r['años_completos'], nombre)
                self.assertTrue(r['success'], nombre)
                self.assertGreater(r['total'], 0, nombre)

    def test_vacaciones_crecen_con_la_antiguedad(self):
        for nombre, ingreso, salida, _ in self.CASOS:
            with self.subTest(caso=nombre):
                r = _calcular(ingreso, salida)
                self.assertGreater(r['vacaciones']['monto'], 0, nombre)

    def test_aguinaldo_no_crece_con_la_antiguedad(self):
        """Todos los casos terminan en 2026: el aguinaldo sólo depende del año."""
        montos = set()
        for nombre, ingreso, salida, _ in self.CASOS:
            with self.subTest(caso=nombre):
                r = _calcular(ingreso, salida)
                montos.add((r['aguinaldo']['dias_trabajados'], r['aguinaldo']['monto']))
        # Sólo difieren por los días trabajados dentro de 2026, no por la antigüedad
        self.assertTrue(len(montos) > 1)
        for dias, monto in montos:
            self.assertEqual(_q(dias / D('365') * 15 * SD), monto)


class IntegridadDelTotalTests(SimpleTestCase):
    """El total siempre debe ser la suma exacta de los renglones."""

    def test_total_es_la_suma_de_todos_los_conceptos(self):
        r = _calcular(date(2016, 9, 15), date(2026, 9, 15), zona='frontera',
                      tipo_despido='injustificado',
                      conceptos_seleccionados=dict(conceptos_base(),
                                                   incluir_horas_extras=True,
                                                   incluir_dias_festivos=True,
                                                   incluir_descanso_semanal=True,
                                                   incluir_vacaciones_vencidas=True,
                                                   incluir_salarios_devengados=True),
                      datos_extra={'horas_extra_normales': D('20'),
                                   'horas_extra_excedentes': D('5'),
                                   'dias_festivos_cantidad': 2,
                                   'dias_descanso_semanal_cantidad': 3,
                                   'dias_vacaciones_vencidos': 20,
                                   'salarios_devengados': D('5000'),
                                   'salario_integrado_cuota': D('73.33')})
        suma = (r['aguinaldo']['monto'] + r['vacaciones']['monto']
                + r['vacaciones_vencidas']['monto'] + r['prima_vacacional']['monto']
                + r['prima_antiguedad']['monto'] + r['indemnizacion']['monto']
                + r['indemnizacion_20dias']['monto'] + r['horas_extras']['monto']
                + r['salarios_devengados']['monto'] + r['dias_festivos']['monto']
                + r['descanso_semanal']['monto'])
        self.assertEqual(suma, r['total'])

    def test_conceptos_excluidos_valen_cero(self):
        seleccion = conceptos_base()
        seleccion['incluir_aguinaldo'] = False
        seleccion['incluir_vacaciones'] = False
        seleccion['incluir_prima_vacacional'] = False
        seleccion['incluir_prima_antiguedad'] = False
        seleccion['incluir_indemnizacion'] = False
        r = _calcular(date(2016, 9, 15), date(2026, 9, 15),
                      conceptos_seleccionados=seleccion)
        self.assertEqual(D('0'), r['total'])

    def test_fechas_invalidas(self):
        r = calcular_todo(date(2026, 1, 1), date(2025, 1, 1), D('12000'))
        self.assertFalse(r['success'])
        self.assertTrue(r['error'])
        self.assertEqual(D('0'), r['total'])

    def test_salario_cero(self):
        r = calcular_todo(date(2026, 1, 1), date(2026, 6, 1), D('0'))
        self.assertFalse(r['success'])


class FormulasPurasTests(SimpleTestCase):
    """Las fórmulas no dependen del expediente, sólo de números."""

    def test_salario_diario_por_periodo(self):
        self.assertEqual(D('400.00'), f.salario_diario(D('12000'), 'mensual'))
        self.assertEqual(D('133.33'), f.salario_diario(D('2000'), 'quincenal'))
        self.assertEqual(D('285.71'), f.salario_diario(D('2000'), 'semanal'))
        self.assertEqual(D('2000'), f.salario_diario(D('2000'), 'diario'))

    def test_anos_completos_usa_aniversarios(self):
        self.assertEqual(D('2.0000'), f.años_completos(date(2020, 2, 2), date(2022, 2, 2)))
        self.assertEqual(D('1.0000'), f.años_completos(date(2025, 9, 15), date(2026, 9, 15)))
        self.assertEqual(D('0'), f.años_completos(date(2026, 1, 1), date(2025, 1, 1)))

    def test_salario_base_con_tope_aplica_piso_y_techo(self):
        base, topado = f.salario_base_con_tope(D('900'), D('881.74'), D('440.87'))
        self.assertEqual(D('881.74'), base)
        self.assertTrue(topado)

        base, topado = f.salario_base_con_tope(D('200'), D('881.74'), D('440.87'))
        self.assertEqual(D('440.87'), base)
        self.assertFalse(topado)

        base, topado = f.salario_base_con_tope(D('500'), D('881.74'), D('440.87'))
        self.assertEqual(D('500'), base)
        self.assertFalse(topado)

    def test_prima_antiguedad_con_tope(self):
        # 12 días × 10 años × $881.74 (doble del salario mínimo de la ZLFN)
        self.assertEqual(D('105808.80'),
                         f.prima_antiguedad(D('10'), D('900'), 12, D('881.74'), D('440.87')))

    def test_indemnizacion_20_dias_sin_fraccion(self):
        # 20 días × 5 años × $200
        self.assertEqual(D('20000'), f.indemnizacion_20dias_por_ano(D('5'), D('200')))
        # Sin fracción se trunca a años enteros: 5, no 5.5
        self.assertEqual(D('20000'),
                         f.indemnizacion_20dias_por_ano(D('5.5'), D('200'), con_fraccion=False))
        # Con fracción sí se paga la parte proporcional del año
        self.assertEqual(D('22000'), f.indemnizacion_20dias_por_ano(D('5.5'), D('200')))

    def test_salario_integrado_explicito(self):
        componentes = {'cuota_diaria': D('73.33'), 'ayudas': D('50')}
        self.assertEqual(D('523.33'),
                         f.salario_integrado(D('400'), componentes))
        # Sin conceptos declarados iguala al diario
        self.assertEqual(D('400'), f.salario_integrado(D('400'), {}))