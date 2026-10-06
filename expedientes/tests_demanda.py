"""
Tests de la narrativa del despido y de la accion preferida (art. 48 LFT)
=====================================================================

Cubre lo que se integro del generador de demanda "acordeon":

  * Narrativa de HECHOS segun la modalidad de la separacion
    (verbal / documento / acceso / otra), con el efecto del art. 47 LFT.
  * Una sola fuente de narrativa: DOCX y HTML dicen lo mismo.
  * Reinstalacion como accion EXCLUYENTE de la indemnizacion de 3 meses
    (art. 48 LFT) y sus limites (art. 49 fr. I y art. 46 LFT).
  * La antiguedad de los HECHOS la calcula el motor, no `dias / 365`.

Uso:
    uv run python manage.py test expedientes.tests_demanda --settings=config.settings_test
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from accounts.models import UserProfile
from django.contrib.auth.models import User

from expedientes.demanda_generator import (_puntos_petitorios, construir_hechos,
                                           generar_demanda_html, generar_demanda_word)
from expedientes.laboral_calculator import (advertencias_accion,
                                             calcular_desde_expediente)
from expedientes.models import CalculoLaboral, Cliente, Expediente


class BaseDemanda(TestCase):
    """Cliente y expediente con datos completos para redactar la demanda."""

    @classmethod
    def setUpTestData(cls):
        cls.asesor = User.objects.create_user(
            username='abogada_demanda_test', password='x',
            first_name='Abogada', last_name='Demanda',
        )
        if not hasattr(cls.asesor, 'profile'):
            UserProfile.objects.create(user=cls.asesor, rol='asesor')

    def _cliente(self, **kwargs):
        # El CURP es único en la BD: se genera uno por cliente creado.
        BaseDemanda._contador = getattr(BaseDemanda, '_contador', 0) + 1
        curp = 'NARR{:04d}01HDFRNT09'.format(BaseDemanda._contador)[:18]

        datos = dict(
            nombre='Cliente Narrativa',
            curp=curp,
            puesto='Operador de produccion',
            empresa='Empresa Narrativa SA de CV',
            empresa_razon_social='Empresa Narrativa SA de CV',
            salario=Decimal('18000.00'),
            periodo_pago='mensual',
            horas_semanales=48,
            jornada='diurna',
            zona_salarial='frontera',
            fecha_ingreso=date(2021, 9, 15),
            fecha_salida=date(2026, 9, 15),
        )
        datos.update(kwargs)
        return Cliente.objects.create(**datos)

    def _expediente(self, cliente, tipo='injustificado'):
        return Expediente.objects.create(
            cliente=cliente,
            asesor=self.asesor,
            estado='demanda',
            tipo_despido=tipo,
            notas='Caso para probar la narrativa de la demanda.',
        )

    def _hechos_de(self, tipo='injustificado', **kwargs_cliente):
        cliente = self._cliente(**kwargs_cliente)
        expediente = self._expediente(cliente, tipo)
        return construir_hechos(expediente, calcular_desde_expediente(expediente), tipo)


class NarrativaModalidadTests(BaseDemanda):
    """Cada modalidad de separacion genera su propio redactado."""

    def test_despido_verbal_aclara_la_falta_de_aviso_escrito(self):
        texto = '\n'.join(self._hechos_de(
            modalidad_despido='verbal',
            despido_comunicado_por='el ING. RAMON PEREZ',
            despido_lugar='la planta de Otay',
            despido_frase='ya no se necesita que venga',
        ))

        self.assertIn('despido verbal', texto)
        self.assertIn('sin que se le entregara documento alguno', texto)
        self.assertIn('RAMON PEREZ', texto)
        self.assertIn('planta de Otay', texto)
        # La frase textual se cita entre comillas
        self.assertIn('"ya no se necesita que venga"', texto)
        # Consecuencia juridica del art. 47 LFT
        self.assertIn('artículo 47', texto)
        self.assertIn('injustificada', texto)

    def test_despido_por_documento_cita_el_motivo_consignado(self):
        texto = '\n'.join(self._hechos_de(
            modalidad_despido='escrito',
            hubo_documento_despido=True,
            despido_documento_motivo='baja por cambio de puesto',
        ))

        self.assertIn('recibió un documento', texto)
        self.assertIn('baja por cambio de puesto', texto)

    def test_despido_por_documento_sin_motivo_lo_admite(self):
        texto = '\n'.join(self._hechos_de(modalidad_despido='escrito'))
        self.assertIn('no consigna causa alguna', texto)

    def test_negada_la_entrada_al_centro_de_trabajo(self):
        texto = '\n'.join(self._hechos_de(
            modalidad_despido='acceso',
            despido_comunicado_por='el guardia de acceso',
        ))

        self.assertIn('se le impidió el acceso', texto)
        self.assertIn('guardia de acceso', texto)
        self.assertIn('equivale a la separación', texto)

    def test_otra_modalidad_usa_la_explicacion_del_asesor(self):
        texto = '\n'.join(self._hechos_de(
            modalidad_despido='otro',
            despido_otra_modalidad='Le dieron el gafete y no lo dejaron salir',
        ))
        self.assertIn('Le dieron el gafete', texto)

    def test_sin_modalidad_se_usa_la_narrativa_del_tipo_de_despido(self):
        texto = '\n'.join(self._hechos_de(modalidad_despido=''))
        self.assertIn('terminada la relación laboral de manera injustificada', texto)

    def test_hechos_van_numerados_y_en_orden(self):
        hechos = self._hechos_de(modalidad_despido='verbal')
        self.assertTrue(hechos[0].startswith('PRIMERO.-'))
        self.assertTrue(hechos[1].startswith('SEGUNDO.-'))
        for hecho in hechos:
            self.assertRegex(hecho, r'^[A-ZÁÉÍÓÚÑ0-9 ]+\.- ')

    def test_documento_de_separacion_se_menciona_solo_si_lo_hubo(self):
        con = '\n'.join(self._hechos_de(modalidad_despido='escrito',
                                         hubo_documento_despido=True))
        sin = '\n'.join(self._hechos_de(modalidad_despido='escrito',
                                         hubo_documento_despido=False))
        self.assertIn('entregó al trabajador documentación', con)
        self.assertNotIn('entregó al trabajador documentación', sin)


class NarrativaDatosTests(BaseDemanda):
    """Salario, antiguedad, testigos y centro de trabajo en los HECHOS."""

    def test_hechos_asientan_salario_diario_e_integrado(self):
        texto = '\n'.join(self._hechos_de())
        self.assertIn('salario diario de $600.00', texto)
        self.assertIn('salario diario integrado', texto)

    def test_hechos_muestran_la_antiguedad_exacta(self):
        texto = '\n'.join(self._hechos_de())
        # 5 años exactos al 15/09/2026, contados por aniversarios
        self.assertIn('5 años completos', texto)
        # No debe usar la aproximacion `dias // 365`
        self.assertNotIn('1827 días', texto)

    def test_jornada_y_centro_de_trabajo_en_los_hechos(self):
        texto = '\n'.join(self._hechos_de(lugar_trabajo='Planta Otay km 12'))
        self.assertIn('Planta Otay km 12', texto)
        self.assertIn('régimen diurna', texto)

    def test_testigos_solo_aparecen_si_capturaron(self):
        con = '\n'.join(self._hechos_de(testigos='MARIA LOPEZ\nJUAN PEREZ'))
        sin = '\n'.join(self._hechos_de(testigos=''))
        self.assertIn('MARIA LOPEZ', con)
        self.assertIn('testigos', con)
        self.assertNotIn('como testigos', sin)

def test_circunstancias_de_texto_libre_se_suman_al_final(self):
        texto = '\n'.join(self._hechos_de(
            modalidad_despido='verbal',
            circunstancias_despidio='Le ofrecieron liquidar solo el mes',
        ))
        self.assertIn('Le ofrecieron liquidar solo el mes', texto)
        self.assertIn('adicionalmente lo siguiente', texto)


class AccionPreferidaTests(TestCase):
    """Art. 48 LFT: la reinstalacion y la indemnizacion son excluyentes."""

    def _caso(self, accion, ingreso, salida, tipo='injustificado'):
        nombre_user = f'abogada_{accion}_{ingreso.year}_{salida.day}'
        asesor, _ = User.objects.get_or_create(
            username=nombre_user,
            defaults={'password': 'x'})
        if not hasattr(asesor, 'profile'):
            UserProfile.objects.create(user=asesor, rol='asesor')

        sufijo = f'{ingreso.year}{salida.month:02d}{len(accion)}'
        cliente = Cliente.objects.create(
            nombre=f'Cliente {accion}',
            curp=f'ACCI{sufijo[:10]}HDFRNT01',
            puesto='Operador',
            empresa='Empresa Accion SA',
            empresa_razon_social='Empresa Accion SA',
            salario=Decimal('18000.00'),
            fecha_ingreso=ingreso,
            fecha_salida=salida,
            accion_preferida=accion,
        )
        expediente = Expediente.objects.create(
            cliente=cliente, asesor=asesor, estado='demanda', tipo_despido=tipo)
        return cliente, expediente

    def test_reinstalacion_excluye_la_indemnizacion_de_tres_meses(self):
        _, expediente = self._caso('reinstalacion', date(2018, 1, 1), date(2026, 1, 1))
        resultado = calcular_desde_expediente(expediente)

        self.assertEqual('reinstalacion', resultado['accion']['accion'])
        self.assertTrue(resultado['accion']['procede'])
        self.assertEqual(Decimal('0'), resultado['indemnizacion']['monto'])
        # El resto de las prestaciones siguen intactas
        self.assertGreater(resultado['prima_antiguedad']['monto'], 0)

    def test_reinstalacion_no_procede_con_menos_de_un_ano(self):
        """Art. 49 fr. I LFT: antigüedad menor a un año."""
        _, expediente = self._caso('reinstalacion', date(2026, 3, 1), date(2026, 9, 1))
        resultado = calcular_desde_expediente(expediente)

        self.assertFalse(resultado['accion']['procede'])
        self.assertIn('art. 49 fr. I LFT', resultado['accion']['motivo'])
        # Se mantiene la indemnización de 3 meses
        self.assertGreater(resultado['indemnizacion']['monto'], 0)

    def test_reinstalacion_no_procede_en_renuncia_voluntaria(self):
        """Art. 46 LFT: la rescisión justificada no genera responsabilidad."""
        _, expediente = self._caso('reinstalacion', date(2018, 1, 1), date(2026, 1, 1),
                                   tipo='voluntario')
        resultado = calcular_desde_expediente(expediente)

        self.assertFalse(resultado['accion']['procede'])
        self.assertIn('art. 46 LFT', resultado['accion']['motivo'])
        self.assertEqual(Decimal('0'), resultado['indemnizacion']['monto'])

    def test_indemnizacion_es_el_default(self):
        _, expediente = self._caso('indemnizacion', date(2018, 1, 1), date(2026, 1, 1))
        resultado = calcular_desde_expediente(expediente)

        self.assertEqual('indemnizacion', resultado['accion']['accion'])
        self.assertGreater(resultado['indemnizacion']['monto'], 0)

    def test_advertencia_al_asesor_cuando_no_procede(self):
        cliente, _ = self._caso('reinstalacion', date(2026, 3, 1), date(2026, 9, 1))
        avisos = advertencias_accion(cliente)
        self.assertEqual(1, len(avisos))
        self.assertIn('art. 49', avisos[0])

    def test_sin_advertencia_cuando_procede(self):
        cliente, _ = self._caso('reinstalacion', date(2018, 1, 1), date(2026, 1, 1))
        self.assertEqual([], advertencias_accion(cliente))

    def test_sin_advertencia_si_se_reclama_indemnizacion(self):
        cliente, _ = self._caso('indemnizacion', date(2026, 3, 1), date(2026, 9, 1))
        self.assertEqual([], advertencias_accion(cliente))


class PetitoriosTests(TestCase):
    """Los petitorios se adaptan a la accion elegida."""

    @classmethod
    def setUpTestData(cls):
        cls.asesor = User.objects.create_user(username='abogada_pet_test', password='x')
        if not hasattr(cls.asesor, 'profile'):
            UserProfile.objects.create(user=cls.asesor, rol='asesor')

    def _caso(self, accion, ingreso=date(2018, 1, 1), salida=date(2026, 1, 1)):
        cliente = Cliente.objects.create(
            nombre=f'Cliente Pet {accion}',
            curp=f'PETI{accion[:3].upper()}01HDFRNT09',
            puesto='Operador',
            empresa='Empresa Pet SA',
            empresa_razon_social='Empresa Pet SA',
            salario=Decimal('18000.00'),
            fecha_ingreso=ingreso,
            fecha_salida=salida,
            accion_preferida=accion,
            modalidad_despido='verbal',
        )
        expediente = Expediente.objects.create(
            cliente=cliente, asesor=self.asesor, estado='demanda',
            tipo_despido='injustificado')
        return expediente, calcular_desde_expediente(expediente)

    def test_petitorios_con_indemnizacion_piden_el_pago(self):
        expediente, calculo = self._caso('indemnizacion')
        petitorios = _puntos_petitorios(calculo, expediente)
        texto = '\n'.join(petitorios)

        self.assertIn('al pago de', texto)
        self.assertNotIn('REINSTALACIÓN', texto)

    def test_petitorios_con_reinstalacion_la_piden_expresamente(self):
        expediente, calculo = self._caso('reinstalacion')
        petitorios = _puntos_petitorios(calculo, expediente)
        texto = '\n'.join(petitorios)

        self.assertIn('REINSTALACIÓN', texto)
        self.assertIn('puesto que venía desempeñando', texto)
        self.assertIn('salarios caídos', texto)

    def test_reinstalacion_no_reclama_los_tres_meses(self):
        """El SEGUNDO petitorio pide la reinstalación, no la indemnización."""
        expediente, calculo = self._caso('reinstalacion')
        segundo = [p for p in _puntos_petitorios(calculo, expediente)
                   if p.startswith('SEGUNDO')][0]

        self.assertIn('REINSTALACIÓN', segundo)
        self.assertNotIn('tres meses', segundo)


class GeneradoresCoherentesTests(TestCase):
    """El DOCX y el HTML deben decir lo mismo (una sola narrativa)."""

    @classmethod
    def setUpTestData(cls):
        cls.asesor = User.objects.create_user(username='abogada_coherencia', password='x')
        if not hasattr(cls.asesor, 'profile'):
            UserProfile.objects.create(user=cls.asesor, rol='asesor')

        cls.cliente = Cliente.objects.create(
            nombre='Cliente Coherencia',
            curp='COHE010101HDFRNT09',
            puesto='Operador de planta',
            empresa='Empresa Coherencia SA',
            empresa_razon_social='Empresa Coherencia SA',
            salario=Decimal('18000.00'),
            fecha_ingreso=date(2018, 1, 1),
            fecha_salida=date(2026, 1, 1),
            modalidad_despido='verbal',
            despido_comunicado_por='la JEFA DE PRODUCCION',
            despido_lugar='la nave 3',
            despido_frase='ya se fue',
            testigos='TESTIGO UNICO',
            accion_preferida='reinstalacion',
        )
        cls.expediente = Expediente.objects.create(
            cliente=cls.cliente, asesor=cls.asesor, estado='demanda',
            tipo_despido='injustificado')

    def test_html_incluye_los_hechos_de_la_modalidad(self):
        html = generar_demanda_html(self.expediente)
        self.assertIn('JEFA DE PRODUCCION', html)
        self.assertIn('TESTIGO UNICO', html)

    def test_docx_se_genera_con_la_accion_elegida(self):
        doc = generar_demanda_word(self.expediente)
        texto = '\n'.join(p.text for p in doc.paragraphs)
        self.assertIn('REINSTALACIÓN', texto)
        self.assertIn('PRIMERO.-', texto)

    def test_la_demanda_usa_el_calculo_guardado(self):
        """La demanda toma el total del CalculoLaboral, no recalcula otro."""
        from expedientes.laboral_calculator import recalcular_calculo

        calculo_guardado = CalculoLaboral.objects.create(
            expediente=self.expediente,
            incluir_indemnizacion=True,
            incluir_prima_antiguedad=True,
        )
        recalcular_calculo(calculo_guardado)
        esperado = f'${calculo_guardado.total:,.2f}'

        self.assertIn(esperado, generar_demanda_html(self.expediente))