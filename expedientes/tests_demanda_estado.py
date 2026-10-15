"""Pruebas del estado de la demanda (`expedientes.demanda_estado`).

Lo que se fija aquí es el contrato del que dependen los tres espacios de la
pantalla: qué cuenta como hueco, qué como decisión, qué coherencias se avisan y
cómo se marca el documento. El defecto que estas pruebas impiden que vuelva es
el semáforo que decía «COMPLETA» con la sección vacía.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from .demanda_estado import (
    CAPITULOS, REQUISITOS, capitulos_de, espacio_de_bloque, estado,
    marcador_agrupado, marcar_html,
)
from .models import ApoderadoLegal, Cliente, Expediente


def _cliente_completo(**extra):
    """Un cliente con TODO lo que la demanda necesita (caso presentable)."""
    datos = dict(
        nombre='JUAN PÉREZ LÓPEZ', curp='PELJ890312HBCRRN08',
        nacionalidad='mexicana', ciudad='Tijuana', estado='Baja California',
        direccion_calle='Av. Reforma', direccion_numero='123',
        direccion_colonia='Centro', direccion_cp='22000',
        puesto='Operador de montacargas',
        actividades='Manejo de montacargas y carga de tráiler.',
        salario=Decimal('12400.00'), periodo_pago='quincenal',
        fecha_ingreso=date(2019, 3, 4), fecha_salida=date(2026, 1, 28),
        dias_trabajo='lunes a viernes', dia_descanso='sábado y domingo',
        horario_entrada='08:00', horario_salida='18:00',
        empresa='Transportes del Pacífico',
        empresa_razon_social='Transportes del Pacífico, S.A. de C.V.',
        empresa_calle='Blvd. Industrial', empresa_numero='1420',
        empresa_colonia='Nueva Tijuana', empresa_cp='22435',
        modalidad_despido='verbal', accion_preferida='indemnizacion',
        hora_despido='14:45', despido_lugar='Andén 3, nave B',
        despido_comunicado_por='Ricardo Beltrán',
        despido_frase='Ya no lo necesitamos, el lunes ya no te presentes.',
        imss_confirmado=True, tuvo_imss=False,
    )
    datos.update(extra)
    return Cliente.objects.create(**datos)


class EstadoBaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('abogada_estado')
        cls.user.profile.rol = 'abogada'
        cls.user.profile.puede_generar_documentos = True
        cls.user.profile.save()

    def _expediente(self, cliente=None, **extra):
        """Expediente de prueba. Por defecto con un cliente SIN ningún dato."""
        return Expediente.objects.create(
            cliente=cliente or Cliente.objects.create(nombre=''),
            asesor=self.user, **extra)


class HuecosTest(EstadoBaseTest):
    """Un caso vacío declara todo lo que falta; uno completo no declara nada."""

    def test_caso_vacio_declara_los_huecos_obligatorios(self):
        expediente = self._expediente()
        info = estado(expediente, calculo_listo=False)
        claves = {h['clave'] for h in info['huecos']}

        for esperada in ('actor_nombre', 'actor_curp', 'actor_domicilio', 'puesto',
                         'salario', 'fecha_ingreso', 'fecha_salida', 'empresa',
                         'empresa_razon_social', 'empresa_domicilio', 'apoderados'):
            self.assertIn(esperada, claves, f'{esperada} debe ser un hueco')

        self.assertFalse(info['resumen']['listo'])
        self.assertGreater(info['resumen']['obligatorios'], 0)

    def test_caso_completo_no_deja_huecos(self):
        cliente = _cliente_completo()
        expediente = self._expediente(cliente=cliente, tipo_despido='injustificado')
        ApoderadoLegal.objects.create(
            expediente=expediente, nombre='María Fernanda Ruiz Soto',
            cedula_profesional='12345678', orden=1)

        info = estado(expediente, calculo_listo=True)

        self.assertEqual([h['etiqueta'] for h in info['pendientes']], [])
        self.assertTrue(info['resumen']['listo'])
        self.assertTrue(all(c['completo'] for c in info['capitulos'].values()))

    def test_el_domicilio_del_actor_es_un_hueco_y_el_motor_lo_marca(self):
        """El acordeón nunca capturaba la dirección: el proemio salía con [DOMICILIO]."""
        expediente = self._expediente()
        info = estado(expediente)
        hueco = next(h for h in info['huecos'] if h['clave'] == 'actor_domicilio')

        self.assertEqual(hueco['marcador'], '[DOMICILIO PARA NOTIFICACIONES]')
        self.assertIn('direccion_calle', hueco['campos'])
        self.assertEqual(hueco['ancla'], 'grupo-domicilio-actor')

    def test_la_curp_corta_cuenta_como_hueco(self):
        cliente = _cliente_completo(curp='PELJ890312')
        expediente = self._expediente(cliente=cliente)
        claves = {h['clave'] for h in estado(expediente, calculo_listo=True)['huecos']}
        self.assertIn('actor_curp', claves)

    def test_las_decisiones_se_separan_de_los_datos(self):
        """Elegir modalidad, tipo de separación e IMSS no es capturar un dato."""
        expediente = self._expediente()
        info = estado(expediente)
        decisiones = {d['clave'] for d in info['decisiones']}

        self.assertEqual(decisiones, {'tipo_despido', 'modalidad_despido',
                                      'imss_confirmado'})
        self.assertNotIn('actor_nombre', decisiones)
        self.assertNotIn('salario', decisiones)

    def test_la_accion_del_48_no_cuenta_como_faltante(self):
        """El modelo la crea con default: no puede «faltar» algo que siempre tiene valor."""
        self.assertNotIn('accion_preferida', {r['clave'] for r in REQUISITOS})

    def test_el_calculo_pendiente_es_un_hueco_obligatorio(self):
        cliente = _cliente_completo()
        expediente = self._expediente(cliente=cliente)
        ApoderadoLegal.objects.create(
            expediente=expediente, nombre='Quien firma', cedula_profesional='1', orden=1)

        pendiente = estado(expediente, calculo_listo=False)
        claves = {h['clave'] for h in pendiente['pendientes']}
        self.assertIn('calculo_aprobado', claves)

        aprobado = estado(expediente, calculo_listo=True)
        self.assertNotIn('calculo_aprobado',
                         {h['clave'] for h in aprobado['pendientes']})


class SemaforoTest(EstadoBaseTest):
    """El semáforo por bloque no puede decir «completa» con campos vacíos."""

    def test_bloque_con_un_solo_campo_no_esta_completo(self):
        """El defecto original: `completa=cliente.nombre` pintaba verde la sección."""
        cliente = Cliente.objects.create(nombre='SOLO NOMBRE')
        expediente = self._expediente(cliente=cliente)
        info = estado(expediente)

        trabajador = info['por_bloque']['trabajador']
        self.assertGreater(trabajador['total'], 1)
        self.assertIn('CURP', trabajador['faltantes'])

    def test_representacion_vacia_no_esta_completa(self):
        """El defecto original: `total_form_count` es siempre ≥ 1 → verde."""
        expediente = self._expediente()
        self.assertFalse(expediente.apoderados.exists())
        info = estado(expediente)
        self.assertIn('representacion', info['por_bloque'])

    def test_los_bloques_de_los_huecos_existen_en_alguna_pantalla(self):
        bloques = {r['bloque'] for r in REQUISITOS}
        self.assertTrue(
            {'trabajador', 'laboral', 'empresa', 'representacion'} <= bloques)
        self.assertTrue({'despido', 'imss', 'prestaciones'} <= bloques)

    def test_cada_requisito_declara_capitulo_valido(self):
        validos = {clave for clave, _, _ in CAPITULOS}
        for requisito in REQUISITOS:
            for clave in capitulos_de(requisito):
                self.assertIn(clave, validos, requisito['clave'])
            self.assertIn(requisito['espacio'], ('datos', 'estrategia'), requisito['clave'])

    def test_el_nombre_del_actor_impacta_proemio_pruebas_y_firma(self):
        """Es el dato que más veces aparece: no puede vigilarse en un solo capítulo."""
        requisito = next(r for r in REQUISITOS if r['clave'] == 'actor_nombre')
        self.assertEqual(capitulos_de(requisito), ('proemio', 'pruebas', 'firma'))

    def test_cada_bloque_sabe_en_que_espacio_vive(self):
        """Los enlaces de hueco llevan al espacio correcto, no siempre al primero."""
        self.assertEqual(espacio_de_bloque('trabajador'), 'datos')
        self.assertEqual(espacio_de_bloque('empresa'), 'datos')
        self.assertEqual(espacio_de_bloque('despido'), 'estrategia')
        self.assertEqual(espacio_de_bloque('prestaciones'), 'estrategia')
        self.assertEqual(espacio_de_bloque('revision', 'documento'), 'documento')


class CoherenciasTest(EstadoBaseTest):
    """Las sustituciones silenciosas del motor tienen que avisarse."""

    def _avisos(self, cliente, calculo_listo=True):
        expediente = self._expediente(cliente=cliente)
        info = estado(expediente, calculo_listo=calculo_listo)
        return [(c['nivel'], c['texto']) for c in info['coherencias']]

    def test_avisa_que_los_hechos_afirmaran_la_jornada_por_defecto(self):
        avisos = self._avisos(_cliente_completo(dias_trabajo=''))
        self.assertTrue(
            any(nivel == 'ojo' and 'lunes a viernes' in texto for nivel, texto in avisos),
            avisos)

    def test_avisa_que_la_separacion_se_ubica_en_el_domicilio_del_patron(self):
        avisos = self._avisos(_cliente_completo(despido_lugar=''))
        self.assertTrue(
            any('domicilio de la demandada' in texto for _, texto in avisos), avisos)

    def test_avisa_que_el_aviso_se_atribuye_a_un_generico(self):
        avisos = self._avisos(_cliente_completo(despido_comunicado_por=''))
        self.assertTrue(
            any('personal de la demandada' in texto for _, texto in avisos), avisos)

    def test_avisa_cuando_no_se_alegara_el_articulo_47(self):
        avisos = self._avisos(_cliente_completo(hubo_documento_despido=True))
        self.assertTrue(
            any('no se alegará la presunción del artículo 47' in texto.lower()
                for _, texto in avisos), avisos)

    def test_avisa_que_el_domicilio_del_patron_queda_en_la_ciudad(self):
        """El motor agrega «TIJUANA, BAJA CALIFORNIA» aunque no haya calle."""
        avisos = self._avisos(_cliente_completo(empresa_calle=''))
        self.assertTrue(
            any('TIJUANA, BAJA CALIFORNIA' in texto for _, texto in avisos), avisos)

    def test_el_domicilio_del_patron_es_hueco_sin_calle(self):
        expediente = self._expediente(cliente=_cliente_completo(empresa_calle=''))
        claves = {h['clave'] for h in estado(expediente, calculo_listo=True)['huecos']}
        self.assertIn('empresa_domicilio', claves)

    def test_avisa_cuando_hay_aviso_escrito_sin_causa_transcrita(self):
        avisos = self._avisos(_cliente_completo(
            modalidad_despido='escrito', hubo_documento_despido=True,
            despido_documento_motivo=''))
        self.assertTrue(
            any('no se transcribe la causa' in texto for _, texto in avisos), avisos)

    def test_avisa_que_sin_confirmar_el_imss_no_se_alega_nada(self):
        avisos = self._avisos(_cliente_completo(imss_confirmado=False))
        self.assertTrue(
            any('Sin confirmar el registro ante el IMSS' in texto
                for _, texto in avisos), avisos)

    def test_confirma_el_hecho_de_la_omision_de_alta(self):
        avisos = self._avisos(_cliente_completo(imss_confirmado=True, tuvo_imss=False))
        self.assertTrue(
            any(nivel == 'bien' and 'omisión de alta' in texto for nivel, texto in avisos),
            avisos)

    def test_avisa_la_reinstalacion_sin_antiguedad_suficiente(self):
        avisos = self._avisos(_cliente_completo(
            accion_preferida='reinstalacion',
            fecha_ingreso=date(2025, 6, 1), fecha_salida=date(2026, 1, 28)))
        self.assertTrue(
            any('no procede (art. 49 fracción I LFT)' in texto for _, texto in avisos),
            avisos)

    def test_avisa_que_la_prima_de_antiguedad_no_se_reclama_en_renuncia_corta(self):
        expediente = self._expediente(cliente=_cliente_completo(
            fecha_ingreso=date(2020, 1, 1), fecha_salida=date(2026, 1, 1)))
        expediente.tipo_despido = 'voluntario'
        expediente.save(update_fields=['tipo_despido'])
        info = estado(expediente, calculo_listo=True)
        self.assertTrue(any('exige 15 años' in c['texto'] for c in info['coherencias']))

    def test_avisa_cuando_los_importes_saldran_sin_cifra(self):
        avisos = self._avisos(_cliente_completo(), calculo_listo=False)
        self.assertTrue(
            any(nivel == 'ojo' and 'sin cifra' in texto for nivel, texto in avisos),
            avisos)


class MarcadoDelDocumentoTest(EstadoBaseTest):
    """Los marcadores del motor se vuelven enlaces al campo que falta."""

    def setUp(self):
        self.expediente = self._expediente()
        self.info = estado(self.expediente)
        self.urls = []

    def _url_de(self, requisito):
        url = (f"/expedientes/{self.expediente.pk}/demanda/asistente/"
               f"?espacio={requisito['espacio']}&seccion={requisito['bloque']}"
               f"#id_{requisito['clave']}")
        self.urls.append((requisito['clave'], url))
        return url

    def test_sustituye_el_marcador_del_proemio_por_un_enlace(self):
        html = '<p>señalando como domicilio [DOMICILIO PARA NOTIFICACIONES], y</p>'
        marcado = marcar_html(html, self.info['pendientes'], self._url_de)

        self.assertNotIn('[DOMICILIO PARA NOTIFICACIONES]', marcado)
        self.assertIn('hueco-doc', marcado)
        self.assertIn('+ Domicilio para notificaciones', marcado)
        self.assertIn('seccion=trabajador', marcado)

    def test_no_toca_marcadores_de_datos_que_si_estan(self):
        html = '<p>[PUESTO DESEMPEÑADO]</p>'
        cliente = _cliente_completo()          # el puesto SÍ está capturado
        expediente = self._expediente(cliente=cliente, tipo_despido='injustificado')
        info = estado(expediente, calculo_listo=True)
        marcado = marcar_html(html, info['pendientes'], self._url_de)
        self.assertIn('[PUESTO DESEMPEÑADO]', marcado)

    def test_las_dos_fechas_comparten_marcador_y_se_agrupan(self):
        """`[FECHA]` sirve para ingreso y separación: no puede prometer una sola."""
        grupos = marcador_agrupado(self.info['pendientes'])
        self.assertEqual(len(grupos['[FECHA]']), 2)

        marcado = marcar_html('<p>el día [FECHA] y el [FECHA]</p>',
                              self.info['pendientes'], self._url_de)
        self.assertNotIn('[FECHA]', marcado)
        self.assertIn('Fecha de ingreso o Fecha de separación', marcado)

    def test_el_marcador_de_importes_lleva_a_prestaciones(self):
        marcado = marcar_html('<p>la cantidad de [MONTO] pesos</p>',
                              self.info['pendientes'], self._url_de)
        self.assertIn('seccion=prestaciones', marcado)
        self.assertIn('+ Importes calculados y aprobados', marcado)
