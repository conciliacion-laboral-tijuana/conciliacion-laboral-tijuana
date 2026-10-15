"""Pruebas de los tres espacios de la pantalla de la demanda.

Fijan el contrato visible del rediseño:

  · datos      — actor (con domicilio), relación laboral, patrón y representación
  · estrategia — separación, IMSS y prestaciones
  · documento  — la demanda capítulo por capítulo, con los huecos enlazados

Lo que estas pruebas impiden que vuelva: un dato capturable en dos pantallas a
la vez, un campo que no se puede capturar desde ninguna (el domicilio del actor
sólo se podía editar desde «Editar cliente»), un semáforo que dice «Completo»
con la sección vacía y un documento que sale con `[DOMICILIO PARA
NOTIFICACIONES]` dentro.
"""

from datetime import date
from decimal import Decimal
import re

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Cliente, Expediente

ESPACIOS = ('datos', 'estrategia', 'documento')


class BaseEspacioDemanda(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('abogada_espacios')
        cls.user.profile.rol = 'abogada'          # rol con permiso de documentos
        cls.user.profile.save()

        cls.cliente = Cliente.objects.create(
            nombre='JUAN PÉREZ LÓPEZ', curp='PELJ890312HBCRRN08',
            salario=Decimal('12400.00'), periodo_pago='quincenal',
            fecha_ingreso=date(2019, 3, 4), fecha_salida=date(2026, 1, 28),
            puesto='Operador de montacargas',
            empresa='Transportes del Pacífico',
            empresa_razon_social='Transportes del Pacífico, S.A. de C.V.',
            empresa_calle='Blvd. Industrial', empresa_numero='1420',
            modalidad_despido='verbal',
            imss_confirmado=True, tuvo_imss=False,
        )
        cls.exp = Expediente.objects.create(
            cliente=cls.cliente, asesor=cls.user, tipo_despido='injustificado')

    def setUp(self):
        self.client.force_login(self.user)

    def _get(self, espacio=None, seccion=None):
        url = reverse('demanda_asistente', args=[self.exp.pk])
        parametros = []
        if espacio:
            parametros.append(f'espacio={espacio}')
        if seccion:
            parametros.append(f'seccion={seccion}')
        if parametros:
            url += '?' + '&'.join(parametros)
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.content.decode('utf-8')


class EspacioDatosTest(BaseEspacioDemanda):
    def test_el_espacio_de_datos_trae_sus_bloques_y_ninguno_mas(self):
        body = self._get('datos')

        for bloque in ('trabajador', 'laboral', 'empresa', 'representacion'):
            self.assertIn(f'id="sec-{bloque}"', body)
        # Las decisiones jurídicas NO se capturan aquí
        self.assertNotIn('id="sec-despido"', body)
        self.assertNotIn('id="sec-imss"', body)
        self.assertNotIn('name="modalidad_despido"', body)

    def test_el_domicilio_del_actor_se_captura_en_esta_pantalla(self):
        """Antes no se podía: el proemio salía con el marcador de hueco."""
        body = self._get('datos')

        for campo in ('direccion_calle', 'direccion_numero', 'direccion_colonia',
                      'direccion_cp'):
            self.assertIn(f'name="{campo}"', body)
        self.assertIn('grupo-domicilio-actor', body)

    def test_los_tres_espacios_se_anuncian_siempre(self):
        for espacio in ESPACIOS:
            body = self._get(espacio)
            for anunciado in ESPACIOS:
                self.assertIn(f'?espacio={anunciado}', body)
            self.assertIn('data-espacio=', body)

    def test_el_espacio_activo_depende_de_la_seccion_pedida(self):
        """`?seccion=` sigue funcionando como enlace directo al bloque."""
        body = self._get(seccion='representacion')
        self.assertIn('id="sec-representacion"', body)
        self.assertIn('apoderados-TOTAL_FORMS', body)

        body = self._get(seccion='despido')
        self.assertIn('id="sec-despido"', body)
        self.assertIn('id="sec-prestaciones"', body)


class EspacioEstrategiaTest(BaseEspacioDemanda):
    def test_el_espacio_de_estrategia_trae_las_decisiones(self):
        body = self._get('estrategia')

        for bloque in ('despido', 'imss', 'prestaciones'):
            self.assertIn(f'id="sec-{bloque}"', body)
        self.assertIn('name="tipo_despido"', body)
        self.assertIn('name="modalidad_despido"', body)
        self.assertIn('name="accion_preferida"', body)
        self.assertIn('name="imss_present"', body)
        # Los datos personales no se repiten aquí
        self.assertNotIn('id="sec-trabajador"', body)

    def test_la_hoja_de_prestaciones_vive_aqui_y_conserva_su_mecanica(self):
        body = self._get('estrategia')

        self.assertIn('name="hoja_calculos"', body)
        self.assertIn('name="revision_calculo"', body)
        self.assertIn('id="agregar-semana"', body)
        self.assertIn('id="calculo-final-resumen"', body)
        self.assertIn('value="calcular"', body)

    def test_la_confirmacion_del_imss_tiene_su_propio_bloque(self):
        """Estaba dentro de «Información laboral», que es un dato, no una decisión."""
        body = self._get('estrategia')

        self.assertIn('id="sec-imss"', body)
        self.assertIn('id="imss-detalles"', body)
        self.assertIn('Registro ante el IMSS', body)
        self.assertNotIn('id="sec-imss"', self._get('datos'))


class EspacioDocumentoTest(BaseEspacioDemanda):
    def test_el_documento_se_muestra_capitulo_por_capitulo(self):
        body = self._get('documento')

        for capitulo in ('proemio', 'demandados', 'prestaciones', 'jornada',
                         'hechos', 'pruebas', 'derecho', 'firma'):
            self.assertIn(f'id="cap-{capitulo}"', body)
        self.assertIn('CAPÍTULO DE HECHOS', body)

    def test_el_indice_marca_los_capitulos_fijos(self):
        body = self._get('documento')
        # El capítulo de derecho es plantilla del despacho: no se captura
        self.assertIn('Texto fijo del despacho', body)

    def test_los_datos_que_faltan_son_huecos_enlazados(self):
        """El marcador suelto del motor se convierte en un enlace al campo."""
        body = self._get('documento')

        self.assertIn('hueco-doc', body)
        self.assertNotIn('[DOMICILIO PARA NOTIFICACIONES]', body)
        self.assertIn('espacio=datos', body)
        self.assertIn('seccion=trabajador', body)
        self.assertIn('#grupo-domicilio-actor', body)

    def test_el_panel_de_coherencia_avisa_lo_que_el_escrito_afirmara(self):
        body = self._get('documento')

        self.assertIn('Coherencia del escrito', body)
        # Sin días de trabajo capturados, los hechos afirmarán «lunes a viernes»
        self.assertIn('lunes a viernes', body)
        # Sin lugar capturado, la separación se ubica en el domicilio del patrón
        self.assertIn('domicilio de la demandada', body)

    def test_el_semaforo_del_encabezado_refleja_lo_que_falta(self):
        """Sólo falta el domicilio del actor: el chip no puede exagerar ni ocultar."""
        body = re.sub(r'\s+', ' ', self._get('documento'))

        self.assertIn('Falta 1 requisito para poder presentar', body)
        self.assertNotIn('Sin datos pendientes', body)

    def test_el_semaforo_cuenta_las_decisiones_aparte_de_los_datos(self):
        self.exp.tipo_despido = ''
        self.exp.save(update_fields=['tipo_despido'])
        self.cliente.modalidad_despido = ''
        self.cliente.save(update_fields=['modalidad_despido'])

        body = re.sub(r'\s+', ' ', self._get('documento'))
        self.assertIn('son decisiones del abogado', body)

    def test_no_se_puede_descargar_mientras_falte_un_obligatorio(self):
        body = self._get('documento')

        # El enlace se deshabilita en el servidor (no sólo con CSS)
        self.assertIn('aria-disabled="true"', body)
        self.assertIn('Para poder presentarla falta', body)
        self.assertIn('Domicilio para notificaciones', body)

    def test_al_completar_el_domicilio_se_habilita_la_descarga(self):
        """El mismo estado alimenta el semáforo y el guard de la descarga."""
        self.cliente.direccion_calle = 'Av. Reforma'
        self.cliente.direccion_numero = '123'
        self.cliente.direccion_colonia = 'Centro'
        self.cliente.direccion_cp = '22000'
        self.cliente.save(update_fields=['direccion_calle', 'direccion_numero',
                                         'direccion_colonia', 'direccion_cp'])

        body = self._get('documento')

        self.assertNotIn('aria-disabled="true"', body)
        self.assertIn('Se puede presentar', body)
        self.assertNotIn('[DOMICILIO PARA NOTIFICACIONES]', body)


class AutoguardadoTest(BaseEspacioDemanda):
    """El contrato entre el autoguardado del navegador y el servidor."""

    def _url(self):
        return reverse('demanda_vista_previa', args=[self.exp.pk])

    def test_el_modo_compacto_guarda_y_devuelve_el_estado(self):
        """Los espacios de captura no necesitan el documento: sólo el estado."""
        respuesta = self.client.post(self._url(), {
            'compacto': '1', 'guardar_borrador': '1',
            'direccion_calle': 'Av. Reforma', 'direccion_numero': '123',
        })

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertTrue(datos['guardado'])
        self.assertNotIn('html', datos)
        self.assertIn('resumen', datos)
        self.assertIn('por_bloque', datos)

        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.direccion_calle, 'Av. Reforma')

    def test_sin_modo_compacto_sigue_devolviendo_el_documento(self):
        """El endpoint no cambió para quien no pide el modo compacto."""
        respuesta = self.client.post(self._url(), {'direccion_calle': 'Otra calle'})

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('html', respuesta.json())

    def test_el_autoguardado_de_datos_no_toca_las_prestaciones(self):
        """Guardar el actor no puede revalidar ni invalidar la hoja de prestaciones."""
        respuesta = self.client.post(self._url(), {
            'compacto': '1', 'guardar_borrador': '1',
            'nombre': 'OTRO NOMBRE', 'direccion_calle': 'Av. Reforma',
        })

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('prestaciones', respuesta.json().get('errores', {}))
