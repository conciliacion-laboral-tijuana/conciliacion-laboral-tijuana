# -*- coding: utf-8 -*-
"""Pruebas de la captura de datos por voz.

Dos capas:

1. **Interpretación** (`expedientes.captura_voz`): lo que el asesor dicta se
   convierte en fecha, dinero, hora o modalidad sin adivinar. Si no se entiende,
   se avisa y el campo queda vacío.
2. **Pantalla y guardado**: la vista pregunta el guion, guarda por la MISMA
   validación del acordeón y no toca el tipo de separación ni las prestaciones.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .captura_voz import (
    interpretar, parse_dinero, parse_fecha, parse_hora, parse_modalidad,
    pasos_con_valores,
)
from .models import Cliente, Expediente


class FechasTest(SimpleTestCase):
    def test_fecha_con_mes_en_palabras(self):
        self.assertEqual(parse_fecha('3 de mayo de 2022'), date(2022, 5, 3))

    def test_fecha_con_mes_y_anio_dictados_en_palabras(self):
        self.assertEqual(
            parse_fecha('tres de mayo de dos mil veintidós'), date(2022, 5, 3))

    def test_fecha_numerica(self):
        self.assertEqual(parse_fecha('03/05/2022'), date(2022, 5, 3))
        self.assertEqual(parse_fecha('3-5-22'), date(2022, 5, 3))

    def test_fecha_iso(self):
        self.assertEqual(parse_fecha('2022-05-03'), date(2022, 5, 3))

    def test_fecha_invalida_o_sin_anio_no_se_adivina(self):
        self.assertIsNone(parse_fecha('mañana'))
        self.assertIsNone(parse_fecha('3 de mayo'))
        self.assertIsNone(parse_fecha('31 de febrero de 2022'))


class DineroTest(SimpleTestCase):
    def test_cifras_con_y_sin_separadores(self):
        self.assertEqual(parse_dinero('$2,400.00'), Decimal('2400.00'))
        self.assertEqual(parse_dinero('2400'), Decimal('2400.00'))
        self.assertEqual(parse_dinero('12 400'), Decimal('12400.00'))

    def test_punto_como_separador_de_miles(self):
        """En México «12.400» son doce mil cuatrocientos, no 12.4."""
        self.assertEqual(parse_dinero('12.400 pesos'), Decimal('12400.00'))
        self.assertEqual(parse_dinero('1.234.567'), Decimal('1234567.00'))
        self.assertEqual(parse_dinero('12.5'), Decimal('12.50'))

    def test_cantidades_dictadas_en_palabras(self):
        self.assertEqual(parse_dinero('dos mil cuatrocientos'), Decimal('2400.00'))
        self.assertEqual(parse_dinero('doce mil'), Decimal('12000.00'))
        self.assertEqual(parse_dinero('mil quinientos pesos'), Decimal('1500.00'))

    def test_digitos_con_mil(self):
        self.assertEqual(parse_dinero('2 mil'), Decimal('2000.00'))
        self.assertEqual(parse_dinero('12 mil 400 pesos'), Decimal('12400.00'))

    def test_no_entiende_o_no_es_positivo(self):
        self.assertIsNone(parse_dinero('mucho'))
        self.assertIsNone(parse_dinero('0'))


class HoraTest(SimpleTestCase):
    def test_hora_24_horas(self):
        self.assertEqual(parse_hora('14:45'), '14:45')

    def test_hora_con_am_pm(self):
        self.assertEqual(parse_hora('2:45 pm'), '14:45')
        self.assertEqual(parse_hora('9:30 am'), '09:30')

    def test_hora_dictada_con_y(self):
        self.assertEqual(parse_hora('2 y 45'), '02:45')
        self.assertEqual(parse_hora('2 y 45 de la tarde'), '14:45')

    def test_hora_invalida(self):
        self.assertIsNone(parse_hora('mediodía'))
        self.assertIsNone(parse_hora('25:99'))


class ModalidadTest(SimpleTestCase):
    def test_verbal(self):
        self.assertEqual(parse_modalidad('fue despido verbal'), 'verbal')

    def test_documento(self):
        self.assertEqual(parse_modalidad('me dieron un papel'), 'escrito')

    def test_negada_la_entrada(self):
        self.assertEqual(parse_modalidad('no me dejaron entrar'), 'acceso')

    def test_otra(self):
        self.assertEqual(parse_modalidad('fue otra cosa'), 'otro')

    def test_no_entendida(self):
        self.assertIsNone(parse_modalidad('no sé'))


class InterpretarTest(SimpleTestCase):
    def test_fecha_devuelve_iso_y_etiqueta(self):
        datos = interpretar('fecha_ingreso', '3 de mayo de 2022')
        self.assertEqual(datos['valor'], '2022-05-03')
        self.assertEqual(datos['etiqueta'], '3 de mayo de 2022')
        self.assertEqual(datos['error'], '')

    def test_curp_se_normaliza(self):
        datos = interpretar('curp', 'gupg 850315 hbcrrs08')
        self.assertEqual(datos['valor'], 'GUPG850315HBCRRS08')
        self.assertEqual(datos['aviso'], '')

    def test_curp_corta_avisa(self):
        datos = interpretar('curp', 'GUPG850315')
        self.assertTrue(datos['aviso'])

    def test_salario_devuelve_numero_y_etiqueta(self):
        datos = interpretar('salario', 'doce mil cuatrocientos')
        self.assertEqual(datos['valor'], '12400.00')
        self.assertIn('$12,400.00', datos['etiqueta'])

    def test_si_no_entiende_avisa_y_no_inventa(self):
        datos = interpretar('fecha_salida', 'el mes pasado')
        self.assertEqual(datos['valor'], '')
        self.assertTrue(datos['error'])

    def test_campo_desconocido(self):
        self.assertTrue(interpretar('prestaciones', 'todo')['error'])


class PasosConValoresTest(SimpleTestCase):
    def test_marca_lo_ya_capturado(self):
        cliente = Cliente(
            nombre='JUAN PÉREZ', salario=Decimal('2000.00'),
            fecha_ingreso=date(2022, 5, 3), modalidad_despido='verbal')
        pasos = {p['campo']: p for p in pasos_con_valores(cliente)}

        self.assertTrue(pasos['nombre']['capturado'])
        self.assertTrue(pasos['fecha_ingreso']['capturado'])
        self.assertEqual(pasos['fecha_ingreso']['etiqueta'], '3 de mayo de 2022')
        self.assertEqual(pasos['salario']['etiqueta'], '$2,000.00 mensual')
        self.assertEqual(pasos['modalidad_despido']['etiqueta'],
                         'Despido verbal (sin documento)')
        self.assertFalse(pasos['puesto']['capturado'])
        self.assertEqual(len(pasos['modalidad_despido']['opciones']), 4)


class BaseCapturaVozTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('abogada_voz')
        cls.user.profile.rol = 'abogada'
        cls.user.profile.puede_generar_documentos = True
        cls.user.profile.save()

        cls.ajeno = User.objects.create_user('asesor_voz_ajeno')
        cls.ajeno.profile.rol = 'asesor'
        cls.ajeno.profile.puede_generar_documentos = True
        cls.ajeno.profile.save()

        cls.sin_permiso = User.objects.create_user('asesor_voz_sin_permiso')
        cls.sin_permiso.profile.rol = 'asesor'
        cls.sin_permiso.profile.puede_generar_documentos = False
        cls.sin_permiso.profile.save()

        cls.cliente = Cliente.objects.create(
            nombre='GUSTAVO GUTIERREZ PEREZ', curp='GUPG850315HBCRRS08')
        cls.exp = Expediente.objects.create(
            cliente=cls.cliente, asesor=cls.user, tipo_despido='injustificado')

    def setUp(self):
        self.client.force_login(self.user)

    def _url(self):
        return reverse('captura_voz', args=[self.exp.pk])

    def _interpretar(self, campo, texto):
        return self.client.post(
            reverse('captura_voz_interpretar', args=[self.exp.pk]),
            data={'campo': campo, 'texto': texto},
            content_type='application/json',
        )


class PermisosCapturaVozTest(BaseCapturaVozTest):
    def test_exige_sesion(self):
        self.client.logout()
        respuesta = self.client.get(self._url())
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/accounts/login/', respuesta['Location'])

    def test_sin_permiso_de_documentos_redirige(self):
        self.client.force_login(self.sin_permiso)
        respuesta = self.client.get(self._url())
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/dashboard/asesor/', respuesta['Location'])

    def test_no_abre_expediente_de_otro(self):
        self.client.force_login(self.ajeno)
        respuesta = self.client.get(self._url())
        self.assertEqual(respuesta.status_code, 404)


class PantallaCapturaVozTest(BaseCapturaVozTest):
    def test_muestra_el_guion_y_lo_capturado(self):
        respuesta = self.client.get(self._url())
        cuerpo = respuesta.content.decode('utf-8')

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('id="voz-pasos"', cuerpo)
        self.assertIn('nombre completo del trabajador', cuerpo)
        self.assertIn('Captura por voz', cuerpo)
        self.assertIn('GUPG850315HBCRRS08', cuerpo)


class GuardadoCapturaVozTest(BaseCapturaVozTest):
    def test_guarda_lo_valido_y_devuelve_el_destino(self):
        respuesta = self.client.post(self._url(), {
            'accion': 'guardar',
            'nombre': 'JUAN PÉREZ LÓPEZ',
            'curp': 'PELJ890312HBCRRN08',
            'salario': '12400.00',
            'fecha_ingreso': '2022-05-03',
            'fecha_salida': '2026-01-28',
            'puesto': 'Operador de montacargas',
            'modalidad_despido': 'verbal',
        })

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertTrue(datos['guardado'])
        self.assertIn('espacio=datos', datos['redirect'])

        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.nombre, 'JUAN PÉREZ LÓPEZ')
        self.assertEqual(self.cliente.salario, Decimal('12400.00'))
        self.assertEqual(self.cliente.fecha_ingreso, date(2022, 5, 3))
        self.assertEqual(self.cliente.modalidad_despido, 'verbal')

    def test_no_cambia_el_tipo_de_separacion(self):
        self.exp.tipo_despido = 'voluntario'
        self.exp.save(update_fields=['tipo_despido'])

        self.client.post(self._url(), {
            'accion': 'guardar', 'nombre': 'OTRO NOMBRE',
        })

        self.exp.refresh_from_db()
        self.assertEqual(self.exp.tipo_despido, 'voluntario')

    def test_no_borra_lo_que_no_se_captura(self):
        """Omitir un dato no puede vaciar lo que ya estaba en el expediente."""
        self.cliente.empresa = 'ACME'
        self.cliente.puesto = 'SOLDADOR'
        self.cliente.save(update_fields=['empresa', 'puesto'])

        self.client.post(self._url(), {
            'accion': 'guardar', 'nombre': 'NOMBRE NUEVO',
        })

        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.nombre, 'NOMBRE NUEVO')
        self.assertEqual(self.cliente.empresa, 'ACME')
        self.assertEqual(self.cliente.puesto, 'SOLDADOR')

    def test_fecha_invalida_no_se_guarda_y_se_avisa(self):
        respuesta = self.client.post(self._url(), {
            'accion': 'guardar',
            'nombre': 'NOMBRE VÁLIDO',
            'fecha_ingreso': '2022-13-45',
        })

        self.assertEqual(respuesta.status_code, 400)
        errores = respuesta.json()['errores']
        self.assertIn('fecha_ingreso', errores)

        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.nombre, 'NOMBRE VÁLIDO')  # lo válido sí se guarda
        self.assertIsNone(self.cliente.fecha_ingreso)

    def test_interpretar_desde_el_navegador(self):
        respuesta = self._interpretar('fecha_salida', '3 de mayo de 2022')

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()['valor'], '2022-05-03')
        self.assertEqual(respuesta.json()['etiqueta'], '3 de mayo de 2022')

    def test_interpretar_exige_permiso(self):
        self.client.force_login(self.sin_permiso)
        respuesta = self._interpretar('salario', 'dos mil')
        self.assertEqual(respuesta.status_code, 403)
