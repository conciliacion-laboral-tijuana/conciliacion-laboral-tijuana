# -*- coding: utf-8 -*-
"""Pruebas del apartado de JURISPRUDENCIA de la demanda.

Fijan el contrato de la función que pidió el despacho:

· La biblioteca de tesis se captura una vez y se reutiliza por expediente.
· La selección es explícita, ordenada y con un argumento por tesis.
· El apartado se imprime DESPUÉS del capítulo de derecho y sólo si hay tesis.
· No bloquea la descarga: una demanda puede presentarse sólo con los artículos.
"""

import io
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from docx import Document

from .demanda_estado import bloqueos, estado
from .models import (Cliente, Expediente, Jurisprudencia, TesisEnDemanda)
from .redaccion import capitulos, generar_texto_completo
from .tests_redaccion_capitulos import _calculo, _datos_con_expediente

TESIS = {
    'rubro': 'PRIMA DE ANTIGÜEDAD. DEBE PAGARSE CONFORME AL ÚLTIMO SALARIO.',
    'texto': 'El artículo 162, fracción III, de la Ley Federal del Trabajo '
             'ordena pagar la prima de antigüedad conforme al último salario.',
    'tipo': 'Jurisprudencia',
    'tema_display': 'Prima de antigüedad',
    'organo': 'Segunda Sala de la Suprema Corte de Justicia de la Nación',
    'epoca': 'Undécima Época',
    'clave_tesis': '2a./J. 12/2020',
    'registro_digital': '2020123',
    'fuente': 'Semanario Judicial de la Federación',
    'argumento': 'Se invoca porque la demandada fijó un salario distinto al real.',
}


class MotorJurisprudenciaTest(TestCase):
    """El motor imprime lo seleccionado y NADA cuando no hay selección."""

    def test_sin_tesis_no_aparece_el_apartado(self):
        datos = _datos_con_expediente()
        cap = capitulos(datos, _calculo(), 'injustificado')

        self.assertEqual(cap['jurisprudencia']['tesis'], [])
        self.assertNotIn('JURISPRUDENCIA', generar_texto_completo(
            datos, _calculo(), 'injustificado'))

    def test_con_tesis_se_transcriben_rubro_texto_argumento_y_cita(self):
        datos = _datos_con_expediente(jurisprudencia=[TESIS])
        cap = capitulos(datos, _calculo(), 'injustificado')

        self.assertEqual(len(cap['jurisprudencia']['tesis']), 1)
        texto = generar_texto_completo(datos, _calculo(), 'injustificado')

        self.assertIn('JURISPRUDENCIA:', texto)
        self.assertIn('criterio jurisprudencial:', texto)
        self.assertIn('Se invoca porque la demandada', texto)
        self.assertIn('“PRIMA DE ANTIGÜEDAD.', texto)
        self.assertIn('ordena pagar la prima de antigüedad', texto)
        self.assertIn('Registro digital: 2020123', texto)
        self.assertIn('2a./J. 12/2020', texto)

    def test_el_apartado_va_despues_del_capitulo_de_derecho(self):
        datos = _datos_con_expediente(jurisprudencia=[TESIS])
        texto = generar_texto_completo(datos, _calculo(), 'injustificado')

        self.assertGreater(texto.find('JURISPRUDENCIA:'),
                           texto.find('CAPÍTULO DE DERECHO:'))

    def test_varias_tesis_conservan_el_orden_y_el_plural(self):
        segunda = dict(TESIS, rubro='HORAS EXTRA. SU PAGO ES OBLIGATORIO.',
                       registro_digital='2020999', clave_tesis='2a./J. 99/2020')
        datos = _datos_con_expediente(jurisprudencia=[TESIS, segunda])
        texto = generar_texto_completo(datos, _calculo(), 'injustificado')

        self.assertIn('criterios jurisprudenciales:', texto)
        self.assertLess(texto.find('PRIMA DE ANTIGÜEDAD.'),
                        texto.find('HORAS EXTRA.'))

    def test_no_se_imprime_una_tesis_sin_rubro(self):
        datos = _datos_con_expediente(jurisprudencia=[{'texto': 'sin rubro'}])
        cap = capitulos(datos, _calculo(), 'injustificado')
        self.assertEqual(cap['jurisprudencia']['tesis'], [])


class BaseJurisprudenciaTest(TestCase):
    """Un caso presentable, como el que ya usa la descarga por capítulos."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('abogada_tesis')
        cls.user.profile.rol = 'abogada'
        cls.user.profile.puede_generar_documentos = True
        cls.user.profile.save()

        cls.cliente = Cliente.objects.create(
            nombre='GUSTAVO GUTIERREZ PEREZ', curp='GUPG850315HBCRRS08',
            salario=Decimal('2000.00'), fecha_ingreso=date(2022, 4, 1),
            fecha_salida=date(2026, 4, 30), imss_confirmado=True,
            tuvo_imss=False, puesto='SOLDADOR ARMADO', empresa='JEIMEX',
            empresa_razon_social='JEIMEX, S.A. DE C.V.',
            empresa_calle='Boulevard Héroes de la Independencia',
            empresa_numero='10351',
            direccion_calle='Calle Segunda', direccion_numero='2200',
            direccion_colonia='Zona Centro', direccion_cp='22000',
            modalidad_despido='verbal',
        )
        cls.exp = Expediente.objects.create(
            cliente=cls.cliente, asesor=cls.user, tipo_despido='injustificado')
        cls.tesis = Jurisprudencia.objects.create(
            tipo='jurisprudencia', tema='prima_antiguedad',
            rubro=TESIS['rubro'], texto=TESIS['texto'],
            organo=TESIS['organo'], epoca=TESIS['epoca'],
            clave_tesis=TESIS['clave_tesis'],
            registro_digital=TESIS['registro_digital'],
            fuente=TESIS['fuente'])

    def setUp(self):
        self.client.force_login(self.user)

    def _url(self):
        return reverse('demanda_asistente', args=[self.exp.pk])

    def _post(self, **datos):
        return self.client.post(self._url(), {
            'espacio': 'jurisprudencia', 'tesis_present': '1',
            'accion': 'guardar', **datos,
        })

    def _texto_docx(self) -> str:
        respuesta = self.client.get(
            reverse('demanda_capitulos_descargar', args=[self.exp.pk]))
        self.assertEqual(respuesta.status_code, 200)
        doc = Document(io.BytesIO(respuesta.content))
        return '\n'.join(p.text.strip() for p in doc.paragraphs if p.text.strip())


class EstadoJurisprudenciaTest(BaseJurisprudenciaTest):
    def test_la_jurisprudencia_es_opcional_y_no_bloquea_la_descarga(self):
        info = estado(self.exp, calculo_listo=True)
        requisito = next(r for r in info['pendientes']
                         if r['clave'] == 'jurisprudencia')

        self.assertFalse(requisito['obligatorio'])
        self.assertEqual(bloqueos(self.exp, calculo_listo=True), [])
        self.assertTrue(info['resumen']['listo'])

    def test_con_tesis_deja_de_estar_pendiente(self):
        TesisEnDemanda.objects.create(
            expediente=self.exp, jurisprudencia=self.tesis, orden=1)
        info = estado(self.exp, calculo_listo=True)

        self.assertNotIn('jurisprudencia',
                         {r['clave'] for r in info['pendientes']})

    def test_la_coherencia_avisa_cuantas_tesis_lleva_el_escrito(self):
        TesisEnDemanda.objects.create(
            expediente=self.exp, jurisprudencia=self.tesis, orden=1)
        textos = [c['texto'] for c in estado(self.exp, calculo_listo=True)['coherencias']]

        self.assertTrue(any('1 criterio jurisprudencial' in t for t in textos), textos)


class EspacioJurisprudenciaTest(BaseJurisprudenciaTest):
    def test_el_espacio_lista_la_biblioteca_y_su_captura(self):
        respuesta = self.client.get(self._url() + '?espacio=jurisprudencia')

        self.assertEqual(respuesta.status_code, 200)
        body = respuesta.content.decode('utf-8')
        self.assertIn('id="sec-jurisprudencia"', body)
        self.assertIn(self.tesis.rubro, body)
        self.assertIn(f'name="tesis_lib" value="{self.tesis.pk}"', body)
        self.assertIn('name="nueva-rubro"', body)
        self.assertIn('name="nueva_guardar_en_biblioteca"', body)
        self.assertIn('Así se leerá en el escrito', body)

    def test_el_espacio_se_abre_aunque_el_expediente_tenga_hoja_de_prestaciones(self):
        """Antes, cualquier expediente con hoja abría siempre Estrategia."""
        from .models import HojaPrestaciones
        HojaPrestaciones.objects.create(expediente=self.exp, datos={})

        respuesta = self.client.get(self._url() + '?espacio=jurisprudencia')
        body = respuesta.content.decode('utf-8')
        self.assertIn('id="sec-jurisprudencia"', body)
        self.assertIn(self.tesis.rubro, body)

        respuesta = self.client.get(self._url() + '?espacio=documento')
        self.assertIn('id="cap-jurisprudencia"',
                      respuesta.content.decode('utf-8'))

    def test_una_tesis_desactivada_ya_elegida_sigue_visible_para_quitarla(self):
        """Si se desactiva después de elegirla, el escrito la imprimiría igual."""
        TesisEnDemanda.objects.create(
            expediente=self.exp, jurisprudencia=self.tesis, orden=1)
        self.tesis.activa = False
        self.tesis.save(update_fields=['activa'])

        body = self.client.get(
            self._url() + '?espacio=jurisprudencia').content.decode('utf-8')

        self.assertIn(f'name="tesis_lib" value="{self.tesis.pk}"', body)
        self.assertIn('Desactivada', body)

    def test_marcar_una_tesis_la_liga_al_expediente_con_su_argumento(self):
        respuesta = self._post(**{
            'tesis_lib': [str(self.tesis.pk)],
            f'argumento_{self.tesis.pk}': 'Se invoca por el salario real.',
            f'orden_{self.tesis.pk}': '2',
        })

        self.assertEqual(respuesta.status_code, 302)
        seleccion = TesisEnDemanda.objects.get(expediente=self.exp)
        self.assertEqual(seleccion.jurisprudencia, self.tesis)
        self.assertEqual(seleccion.argumento, 'Se invoca por el salario real.')
        self.assertEqual(seleccion.orden, 2)

    def test_desmarcar_una_tesis_la_quita_sin_borrar_la_biblioteca(self):
        TesisEnDemanda.objects.create(
            expediente=self.exp, jurisprudencia=self.tesis, orden=1)

        self._post()

        self.assertFalse(TesisEnDemanda.objects.filter(expediente=self.exp).exists())
        self.assertTrue(Jurisprudencia.objects.filter(pk=self.tesis.pk).exists())

    def test_capturar_una_tesis_nueva_la_deja_solo_en_este_caso(self):
        respuesta = self._post(**{
            'nueva-tipo': 'tesis_aislada',
            'nueva-tema': 'horas_extras',
            'nueva-rubro': 'HORAS EXTRA. SU PAGO ES OBLIGATORIO.',
            'nueva-texto': 'Texto de la tesis aislada.',
            'nueva-registro_digital': '2020999',
        })

        self.assertEqual(respuesta.status_code, 302)
        nueva = Jurisprudencia.objects.get(rubro='HORAS EXTRA. SU PAGO ES OBLIGATORIO.')
        self.assertEqual(nueva.expediente, self.exp)
        self.assertTrue(TesisEnDemanda.objects.filter(
            expediente=self.exp, jurisprudencia=nueva).exists())

    def test_capturar_una_tesis_con_la_casilla_la_guarda_en_la_biblioteca(self):
        self._post(**{
            'nueva-tipo': 'jurisprudencia',
            'nueva-tema': 'despido',
            'nueva-rubro': 'DESPIDO. CARGA DE LA PRUEBA.',
            'nueva-texto': 'Texto.',
            'nueva_guardar_en_biblioteca': 'on',
        })

        nueva = Jurisprudencia.objects.get(rubro='DESPIDO. CARGA DE LA PRUEBA.')
        self.assertIsNone(nueva.expediente)

    def test_no_se_puede_colar_una_tesis_de_otro_expediente(self):
        otro_cliente = Cliente.objects.create(nombre='OTRO', curp='OTRO850315HBCRRS01')
        otro = Expediente.objects.create(cliente=otro_cliente, asesor=self.user)
        ajena = Jurisprudencia.objects.create(
            expediente=otro, rubro='TESIS DE OTRO CASO', texto='…')

        self._post(**{'tesis_lib': [str(ajena.pk)]})

        self.assertFalse(TesisEnDemanda.objects.filter(
            expediente=self.exp, jurisprudencia=ajena).exists())

    def test_una_tesis_sin_rubro_no_se_guarda_y_lo_dice(self):
        respuesta = self._post(**{
            'nueva-tipo': 'tesis_aislada',
            'nueva-tema': 'otro',
            'nueva-texto': 'Texto sin rubro.',
        })

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Jurisprudencia.objects.filter(texto='Texto sin rubro.').exists())
        self.assertIn('El rubro es obligatorio', respuesta.content.decode('utf-8'))


class DocumentoJurisprudenciaTest(BaseJurisprudenciaTest):
    def test_el_docx_trae_el_apartado_despues_del_derecho(self):
        TesisEnDemanda.objects.create(
            expediente=self.exp, jurisprudencia=self.tesis,
            argumento='Se invoca por el salario real.', orden=1)

        texto = self._texto_docx()

        self.assertIn('JURISPRUDENCIA:', texto)
        self.assertIn('PRIMA DE ANTIGÜEDAD.', texto)
        self.assertIn('Registro digital: 2020123', texto)
        self.assertIn('Se invoca por el salario real.', texto)
        self.assertGreater(texto.find('JURISPRUDENCIA:'),
                           texto.find('CAPÍTULO DE DERECHO:'))

    def test_sin_tesis_el_docx_no_trae_el_apartado(self):
        texto = self._texto_docx()
        self.assertNotIn('JURISPRUDENCIA', texto)
