# -*- coding: utf-8 -*-
"""Pruebas del motor de redacción por capítulos.

Verifican que la demanda generada cumpla el estándar del despacho
(`docs/referencia/demanda_injustificado_estandar.pdf`) y, sobre todo, que los
MONTOS que aparecen en el capítulo de prestaciones sean exactamente los que
produjo el motor legal: una cifra distinta en la demanda es un riesgo real.
"""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from expedientes.models import Cliente, Expediente
from expedientes.redaccion import capitulos, generar_texto_completo
from expedientes.redaccion.condiciones import evaluar_condiciones
from expedientes.redaccion.derecho import _ordenar
from expedientes.redaccion.prestaciones import _horas_legibles


def _datos(**extra) -> dict:
    """Datos mínimos de un caso de despido injustificado."""
    datos = {
        'actor_nombre': 'JUAN PEREZ LOPEZ',
        'actor_nacionalidad': 'mexicana',
        'actor_domicilio': 'CALLE FALSA 123, TIJUANA, BAJA CALIFORNIA',
        'actor_ciudad': 'Tijuana',
        'actor_estado': 'Baja California',
        'apoderados': [{'nombre': 'Ricardo Peñaloza Cruz', 'cedula': '7593879'}],
        'autorizados': [{'nombre': 'Adriana Luna Peñaloza'}],
        'demandada_razon_social': 'ACME, S.A. DE C.V.',
        'demandada_nombre_comercial': 'ACME',
        'demandada_domicilio': 'AV. INDUSTRIAL 500, TIJUANA, BAJA CALIFORNIA',
        'puesto': 'SOLDADOR',
        'actividades': 'la fabricación y ensamble de estructuras metálicas',
        'tipo_contrato_texto': 'por tiempo indefinido',
        'fecha_ingreso': None,
        'fecha_despido': None,
        'salario_tipo': 'mensual',
        'modalidad_despido': 'verbal',
        'hubo_documento_despido': False,
        'despido_comunicado_por': 'el personal de Recursos Humanos',
        'despido_lugar': 'el domicilio de la demandada',
        'despido_frase': 'YA NO ES NECESARIO EL USO DE TUS SERVICIOS',
        'hora_despido': '14:45',
        'horario_entrada': '07:00',
        'horario_salida': '17:00',
        'dias_trabajo': 'lunes a viernes',
        'dia_descanso': 'sábado y domingo',
        'horas_semanales': 48,
        'jornada': 'diurna',
        'imss_confirmado': True,
        'tuvo_imss': False,
        'folio': 'CCL-2026-12345',
        'fecha_tramite': None,
        'testigos': 'Mariano (líder de línea)',
        'documentos_prueba': '',
        'circunstancias_despido': '',
        'tipo_despido': 'injustificado',
        'reclama_indemnizacion': True,
        'reclama_prima_antiguedad': True,
        'reclama_vacaciones': True,
        'reclama_prima_vacacional': True,
        'reclama_aguinaldo': True,
        'reclama_salarios_caidos': True,
        'reclama_constancia': True,
    }
    datos.update(extra)
    return datos


def _calculo() -> dict:
    """Cálculo de ejemplo con la forma que produce `calculo_para_demanda`."""
    return {
        'success': True,
        'total': Decimal('1000.00'),
        'salario_diario': Decimal('66.67'),
        'salario_diario_integrado': Decimal('66.67'),
        'salario_integrado_componentes': {},
        'años_completos': 4,
        'años_trabajados': 4.08,
        'accion': {'accion': 'indemnizacion', 'procede': True},
        'aguinaldo': {'monto': Decimal('328.78')},
        'vacaciones': {'monto': Decimal('1306.00'), 'dias': 19},
        'prima_vacacional': {'monto': Decimal('326.50')},
        'prima_antiguedad': {'monto': Decimal('21582.35'), 'tope_aplicado': False},
        'indemnizacion': {'monto': Decimal('6000.30')},
        'indemnizacion_20dias': {'monto': Decimal('0')},
        'vacaciones_vencidas': {'monto': Decimal('0'), 'dias': 0},
        'horas_extras': {'monto': Decimal('0'), 'por_semana': []},
        'salarios_devengados': {'monto': Decimal('0')},
        'dias_festivos': {'monto': Decimal('0')},
        'descanso_semanal': {'monto': Decimal('0')},
    }


class _ExpedienteStub:
    """Sustituto mínimo del Expediente: sólo lo que usa `_filas_prestaciones`."""

    tipo_despido = 'injustificado'


def _datos_con_expediente(**extra) -> dict:
    """Datos con el expediente adjunto, como lo entrega el adaptador real."""
    return _datos(_expediente=_ExpedienteStub(), **extra)


class CondicionesTest(TestCase):
    """Las banderas deciden qué aparece, nunca cuánto."""

    def test_despido_sin_aviso_incluye_impugnacion_de_renuncia(self):
        cond = evaluar_condiciones(_datos(se_firmo_renuncia=True))
        self.assertTrue(cond['incluir_renuncia'])

    def test_sin_renuncia_firmada_no_impugna(self):
        cond = evaluar_condiciones(_datos(se_firmo_renuncia=False))
        self.assertFalse(cond['incluir_renuncia'])

    def test_imss_solo_se_alega_si_se_confirmo_que_no_hubo(self):
        # Sin confirmar, afirmar la falta de alta sería inventar un hecho.
        self.assertFalse(evaluar_condiciones(_datos(imss_confirmado=False))['incluir_imss'])
        # Confirmado y con IMSS: tampoco se alega.
        self.assertFalse(evaluar_condiciones(
            _datos(imss_confirmado=True, tuvo_imss=True))['incluir_imss'])
        # Confirmado y sin IMSS: sí se alega.
        self.assertTrue(evaluar_condiciones(
            _datos(imss_confirmado=True, tuvo_imss=False))['incluir_imss'])

    def test_horas_extras_requieren_que_se_hayan_tenido_y_reclamado(self):
        self.assertFalse(evaluar_condiciones(
            _datos(tuvo_horas_extras=False, reclama_horas_extras=True)
        )['incluir_horas_extras'])
        self.assertFalse(evaluar_condiciones(
            _datos(tuvo_horas_extras=True, reclama_horas_extras=False)
        )['incluir_horas_extras'])
        self.assertTrue(evaluar_condiciones(
            _datos(tuvo_horas_extras=True, reclama_horas_extras=True)
        )['incluir_horas_extras'])

    def test_aviso_entregado_quita_el_alegato_del_art_47(self):
        self.assertTrue(evaluar_condiciones(
            _datos(hubo_documento_despido=False))['incluir_sin_aviso'])
        self.assertFalse(evaluar_condiciones(
            _datos(hubo_documento_despido=True))['incluir_sin_aviso'])


class EstructuraTest(TestCase):
    """Los siete capítulos del estándar deben existir."""

    def setUp(self):
        self.datos = _datos_con_expediente()
        self.calculo = _calculo()
        self.cap = capitulos(self.datos, self.calculo, 'injustificado')

    def test_capitulos_presentes(self):
        for clave in ('caratula', 'proemio', 'demandados', 'introduccion',
                      'prestaciones', 'jornada', 'hechos', 'pruebas', 'derecho'):
            self.assertIn(clave, self.cap)

    def test_demandados_son_dos_fuente_y_moral(self):
        self.assertEqual(len(self.cap['demandados']), 2)
        self.assertIn('QUIEN RESULTE RESPONSABLE DE LA FUENTE DE TRABAJO',
                      self.cap['demandados'][0])
        self.assertIn('"ACME"', self.cap['demandados'][0])
        self.assertIn('A la MORAL "ACME, S.A. DE C.V."', self.cap['demandados'][1])

    def test_proemio_lleva_apoderados_con_cedula_y_autorizados(self):
        proemio = self.cap['proemio']
        self.assertIn('Ricardo Peñaloza Cruz', proemio)
        self.assertIn('7593879', proemio)
        self.assertIn('Adriana Luna Peñaloza', proemio)
        self.assertIn('692, frac. I, 693 y 696', proemio)

    def test_hechos_numerados_con_ordinales(self):
        self.assertTrue(self.cap['hechos'])
        self.assertTrue(self.cap['hechos'][0].startswith('PRIMERO.-'))
        self.assertTrue(self.cap['hechos'][1].startswith('SEGUNDO.-'))

    def test_pruebas_incluyen_confesional_e_inspeccion_por_demandado(self):
        titulos = [p['titulo'] for p in self.cap['pruebas']]
        self.assertEqual(titulos.count('LA CONFESIONAL POR POSICIONES'), 2)
        self.assertEqual(titulos.count('LA INSPECCIÓN OCULAR'), 4)
        self.assertIn('INTERROGATORIO LIBRE', titulos)
        self.assertIn('LA DOCUMENTAL PRIVADA', titulos)

    def test_hecho_conserva_instancia_conciliatoria_con_folio(self):
        unidos = ' '.join(self.cap['hechos'])
        self.assertIn('CCL-2026-12345', unidos)
        self.assertIn('instancia conciliatoria', unidos)

    def test_accion_reinstalacion_se_declara_y_no_pide_indemnizacion(self):
        calculo = _calculo()
        calculo['accion'] = {'accion': 'reinstalacion', 'procede': True}
        cap = capitulos(self.datos, calculo, 'injustificado')
        unidos = ' '.join(cap['hechos'])
        self.assertIn('REINSTALACIÓN', unidos)

    def test_sin_folio_no_se_inventa_numero_de_expediente(self):
        cap = capitulos(_datos_con_expediente(folio=''), self.calculo, 'injustificado')
        unidos = ' '.join(cap['hechos'])
        self.assertNotIn('expediente número', unidos)
        self.assertIn('constancia de no conciliación', unidos)


class MontosTest(TestCase):
    """Los montos de la demanda deben ser los del motor legal, en número y letra."""

    def setUp(self):
        self.calculo = _calculo()
        self.cap = capitulos(_datos_con_expediente(), self.calculo, 'injustificado')

    def _buscar(self, fragmento: str) -> str:
        for renglon in self.cap['prestaciones']:
            if fragmento in renglon.upper():
                return renglon
        self.fail(f'No se encontró el renglón que contiene {fragmento!r}')

    def test_indemnizacion_con_monto_en_numero_y_letra(self):
        renglon = self._buscar('INDEMNIZACIÓN')
        self.assertIn('$6,000.30', renglon)
        self.assertIn('seis mil pesos 30/100 M.N.', renglon)

    def test_prima_antiguedad_usa_monto_del_motor(self):
        renglon = self._buscar('PRIMA DE ANTIGÜEDAD')
        self.assertIn('$21,582.35', renglon)
        self.assertIn('veintiún mil quinientos ochenta y dos pesos 35/100 M.N.', renglon)

    def test_aguinaldo_vacaciones_y_prima_vacacional_aparecen(self):
        self.assertIn('$328.78', self._buscar('AGUINALDO'))
        self.assertIn('$1,306.00', self._buscar('VACACIONES'))
        self.assertIn('$326.50', self._buscar('PRIMA VACACIONAL'))

    def test_no_se_reclama_indemnizacion_en_renuncia_voluntaria(self):
        datos = _datos(reclama_indemnizacion=False)
        cap = capitulos(_datos_con_expediente(reclama_indemnizacion=False), self.calculo, 'voluntario')
        unidos = ' '.join(cap['prestaciones'])
        self.assertNotIn('INDEMNIZACIÓN', unidos.upper())

    def test_sin_calculo_no_se_inventan_cifras(self):
        cap = capitulos(_datos_con_expediente(), {'success': False}, 'injustificado')
        unidos = ' '.join(cap['prestaciones'])
        self.assertNotIn('$', unidos)

    def test_constancia_y_comprobantes_fiscales_se_incluyen(self):
        unidos = ' '.join(self.cap['prestaciones'])
        self.assertIn('CONSTANCIA DE SERVICIOS', unidos)
        for instituto in ('Fondo Nacional de la Vivienda', 'Seguro Social',
                          'Administración Tributaria'):
            self.assertIn(instituto, unidos)


class DerechoTest(TestCase):
    """El capítulo de derecho: constitucional al frente, luego orden numérico."""

    def test_constitucional_va_al_frente(self):
        ordenados = _ordenar(['84', '123 Constitucional Frac. XXII', '8', '48'])
        self.assertEqual(ordenados[0], '123 Constitucional Frac. XXII')
        self.assertEqual(ordenados[1:], ['8', '48', '84'])

    def test_horas_extras_agregan_articulos_66_a_68(self):
        con = capitulos(_datos_con_expediente(tuvo_horas_extras=True, reclama_horas_extras=True),
                        _calculo(), 'injustificado')['derecho']
        self.assertIn('66', con)
        self.assertIn('68', con)

    def test_sin_horas_extras_no_invoca_los_articulos_de_horas_extras(self):
        sin = capitulos(_datos_con_expediente(tuvo_horas_extras=False),
                        _calculo(), 'injustificado')['derecho']
        self.assertNotIn(', 66,', sin)
        self.assertIn('685 al 891', sin)


class JornadaTest(TestCase):
    """El anexo de jornada semanal (págs. 4-5 del estándar)."""

    def _calculo_con_semanas(self) -> dict:
        calculo = _calculo()
        calculo['horas_extras'] = {
            'monto': Decimal('7011.09'),
            'dobles': Decimal('7.6'),
            'triples': Decimal('0'),
            'tipo': 'dobles',
            'semanas': [
                {
                    'inicio': date(2025, 9, 22),
                    'fin': date(2025, 9, 26),
                    'dobles': Decimal('2'),
                    'triples': Decimal('0'),
                    'bruto': Decimal('200'),
                    'pagado': Decimal('0'),
                    'pendiente': Decimal('200'),
                    'dias': [
                        {'fecha': date(2025, 9, 26), 'entrada': '07:00',
                         'ordinaria': '15:00', 'salida': '17:00',
                         'horas': Decimal('2')},
                    ],
                },
            ],
        }
        return calculo

    def test_filas_jornada_tienen_las_cuatro_columnas_del_estandar(self):
        from expedientes.redaccion.jornada import filas_jornada

        filas = filas_jornada(
            _datos(horario_entrada='07:00', horario_salida='17:00'),
            self._calculo_con_semanas(),
        )
        self.assertEqual(len(filas), 1)
        fila = filas[0]
        self.assertEqual(fila['jornada_semanal'], '22/09/25 - 26/09/25')
        self.assertEqual(fila['jornada_ordinaria'], '07:00 hrs - 17:00 hrs')
        self.assertIn('15:00 a 17:00', fila['jornada_extra'])
        self.assertEqual(fila['horas'], '2 horas dobles')

    def test_sin_horas_extras_no_hay_anexo(self):
        from expedientes.redaccion.jornada import filas_jornada

        self.assertEqual(filas_jornada(_datos(), _calculo()), [])

    def test_capitulo_de_jornada_se_emite_solo_con_semanas(self):
        con = capitulos(_datos_con_expediente(), self._calculo_con_semanas(),
                        'injustificado')['jornada']
        self.assertTrue(con['filas'])
        self.assertEqual(con['encabezados'],
                         ['JORNADA SEMANAL', 'JORNADA ORDINARIA',
                          'JORNADA EXTRA', 'HORAS EXTRAS'])

        sin = capitulos(_datos_con_expediente(), _calculo(), 'injustificado')['jornada']
        self.assertFalse(sin['filas'])

    def test_docx_incluye_la_tabla_de_jornada(self):
        from docx import Document

        from expedientes.redaccion.salida import _configurar, _tabla
        from expedientes.redaccion.jornada import ENCABEZADOS, filas_jornada

        filas = filas_jornada(_datos(horario_entrada='07:00', horario_salida='17:00'),
                              self._calculo_con_semanas())
        doc = Document()
        _configurar(doc)
        _tabla(doc, ENCABEZADOS, [[f['jornada_semanal'], f['jornada_ordinaria'],
                                   f['jornada_extra'], f['horas']] for f in filas])

        self.assertEqual(len(doc.tables), 1)
        tabla = doc.tables[0]
        self.assertEqual(len(tabla.columns), 4)
        self.assertEqual(tabla.rows[0].cells[0].text, 'JORNADA SEMANAL')
        self.assertEqual(tabla.rows[1].cells[0].text, '22/09/25 - 26/09/25')


class DescargaCapitulosTest(TestCase):
    """El endpoint que entrega el .docx con el formato de capítulos."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import User

        from expedientes.models import Cliente, Expediente

        cls.user = User.objects.create_user('abogada_capitulos')
        cls.user.profile.rol = 'abogada'
        cls.user.profile.save()
        cls.ajeno = User.objects.create_user('asesor_ajeno')
        cls.ajeno.profile.rol = 'asesor'
        cls.ajeno.profile.save()

        # Este cliente representa un caso PRESENTABLE: el guard de descarga exige
        # que no queden huecos obligatorios (domicilio del actor para
        # notificaciones, modalidad de la separación, etc.), no sólo los datos
        # críticos y el cálculo aprobado.
        cls.cliente = Cliente.objects.create(
            nombre='GUSTAVO GUTIERREZ PEREZ',
            curp='GUPG850315HBCRRS08',
            salario=Decimal('2000.00'),
            fecha_ingreso=date(2022, 4, 1),
            fecha_salida=date(2026, 4, 30),
            imss_confirmado=True,
            tuvo_imss=False,
            puesto='SOLDADOR ARMADO',
            empresa='JEIMEX',
            empresa_razon_social='JEIMEX, S.A. DE C.V.',
            empresa_calle='Boulevard Héroes de la Independencia',
            empresa_numero='10351',
            direccion_calle='Calle Segunda',
            direccion_numero='2200',
            direccion_colonia='Zona Centro',
            direccion_cp='22000',
            modalidad_despido='verbal',
        )
        cls.exp = Expediente.objects.create(
            cliente=cls.cliente, asesor=cls.user, tipo_despido='injustificado',
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _url(self):
        from django.urls import reverse
        return reverse('demanda_capitulos_descargar', args=[self.exp.pk])

    def test_devuelve_un_docx_con_los_capitulos(self):
        respuesta = self.client.get(self._url())

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta['Content-Type'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        self.assertIn('attachment', respuesta['Content-Disposition'])
        self.assertEqual(respuesta.content[:2], b'PK', 'no es un DOCX válido')

    def test_no_descarga_si_falta_un_hueco_obligatorio(self):
        """Sin domicilio del actor el .docx salía con «[DOMICILIO PARA NOTIFICACIONES]».

        El guard ya no se limita a los datos críticos y al cálculo aprobado:
        bloquea el escrito que se presenta mientras quede cualquier hueco
        obligatorio, y manda a la pantalla donde se ve la lista.
        """
        self.cliente.direccion_calle = ''
        self.cliente.direccion_numero = ''
        self.cliente.direccion_colonia = ''
        self.cliente.direccion_cp = ''
        self.cliente.save(update_fields=['direccion_calle', 'direccion_numero',
                                         'direccion_colonia', 'direccion_cp'])

        respuesta = self.client.get(self._url())

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('espacio=documento', respuesta['Location'])

    def test_el_docx_trae_los_encabezados_de_capitulo(self):
        import io

        from docx import Document

        respuesta = self.client.get(self._url())
        doc = Document(io.BytesIO(respuesta.content))
        textos = [p.text.strip() for p in doc.paragraphs]

        for encabezado in ('CAPÍTULO DE PRESTACIONES:', 'CAPÍTULO DE HECHOS:',
                           'PRUEBAS', 'CAPÍTULO DE DERECHO:'):
            self.assertIn(encabezado, textos, f'falta {encabezado!r} en el DOCX')

    def test_exige_sesion_iniciada(self):
        self.client.logout()
        respuesta = self.client.get(self._url())
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/accounts/login/', respuesta['Location'])

    def test_no_permite_descargar_expediente_de_otro_asesor(self):
        """Con permiso de documentos pero sin ser su expediente → 404."""
        self.ajeno.profile.puede_generar_documentos = True
        self.ajeno.profile.save()
        self.client.force_login(self.ajeno)

        respuesta = self.client.get(self._url())
        self.assertEqual(respuesta.status_code, 404)

    def test_asesor_sin_permiso_de_documentos_es_redirigido(self):
        respuesta = self.client.get(self._url())
        self.assertEqual(respuesta.status_code, 200)

        otro = Expediente.objects.create(
            cliente=Cliente.objects.create(
                nombre='OTRO TRABAJADOR', curp='OTRO850315HBCRRS01',
                salario=Decimal('1000.00'), fecha_ingreso=date(2024, 1, 1),
                fecha_salida=date(2026, 1, 1),
            ),
            asesor=self.user, tipo_despido='injustificado',
        )
        self.client.force_login(self.ajeno)
        from django.urls import reverse
        respuesta = self.client.get(
            reverse('demanda_capitulos_descargar', args=[otro.pk])
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/dashboard/asesor/', respuesta['Location'])


class RepresentacionTest(TestCase):
    """Apoderados y autorizados: se capturan en el acordeón y alimentan el proemio."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import User

        cls.user = User.objects.create_user('abogada_rep')
        cls.user.profile.rol = 'abogada'
        cls.user.profile.puede_generar_documentos = True
        cls.user.profile.save()

        cls.cliente = Cliente.objects.create(
            nombre='CLIENTE REPRESENTACION', curp='REPR850315HBCRRS02',
            salario=Decimal('8000.00'), fecha_ingreso=date(2024, 1, 1),
            fecha_salida=date(2026, 1, 1), puesto='AUXILIAR', empresa='ACME',
            empresa_razon_social='ACME, S.A. DE C.V.',
        )
        cls.exp = Expediente.objects.create(
            cliente=cls.cliente, asesor=cls.user, tipo_despido='injustificado',
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _payload_representacion(self, apoderados, autorizados, existentes_ap=(),
                                existentes_aut=()):
        """Arma el POST del acordeón con los formsets de representación."""
        data = {
            'accion': 'guardar', 'seccion_abierta': 'representacion',
            'nombre': self.cliente.nombre, 'curp': self.cliente.curp,
            'apoderados-TOTAL_FORMS': str(len(existentes_ap) + len(apoderados)),
            'apoderados-INITIAL_FORMS': str(len(existentes_ap)),
            'apoderados-MIN_NUM_FORMS': '0', 'apoderados-MAX_NUM_FORMS': '1000',
            'autorizados-TOTAL_FORMS': str(len(existentes_aut) + len(autorizados)),
            'autorizados-INITIAL_FORMS': str(len(existentes_aut)),
            'autorizados-MIN_NUM_FORMS': '0', 'autorizados-MAX_NUM_FORMS': '1000',
        }
        i = 0
        for ap in existentes_ap:
            data[f'apoderados-{i}-id'] = str(ap.pk)
            data[f'apoderados-{i}-nombre'] = ap.nombre
            data[f'apoderados-{i}-cedula_profesional'] = ap.cedula_profesional
            data[f'apoderados-{i}-orden'] = str(ap.orden)
            i += 1
        for nombre, cedula in apoderados:
            data[f'apoderados-{i}-nombre'] = nombre
            data[f'apoderados-{i}-cedula_profesional'] = cedula
            data[f'apoderados-{i}-orden'] = str(i + 1)
            i += 1
        i = 0
        for aut in existentes_aut:
            data[f'autorizados-{i}-id'] = str(aut.pk)
            data[f'autorizados-{i}-nombre'] = aut.nombre
            data[f'autorizados-{i}-orden'] = str(aut.orden)
            i += 1
        for nombre in autorizados:
            data[f'autorizados-{i}-nombre'] = nombre
            data[f'autorizados-{i}-orden'] = str(i + 1)
            i += 1
        return data

    def test_el_acordeon_muestra_la_seccion_de_representacion(self):
        from django.urls import reverse

        respuesta = self.client.get(
            reverse('demanda_asistente', args=[self.exp.pk]) + '?seccion=representacion'
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'sec-representacion')
        self.assertContains(respuesta, 'apoderados-TOTAL_FORMS')

    def test_guarda_apoderados_con_cedula_y_autorizados(self):
        from django.urls import reverse

        respuesta = self.client.post(
            reverse('demanda_asistente', args=[self.exp.pk]),
            self._payload_representacion(
                apoderados=[('Ricardo Peñaloza Cruz', '7593879'),
                            ('Hans Luna Hernández', '6223421')],
                autorizados=['Adriana Carolina Luna Peñaloza'],
            ),
        )
        self.assertEqual(respuesta.status_code, 200)

        apoderados = list(self.exp.apoderados.order_by('orden'))
        self.assertEqual([a.nombre for a in apoderados],
                         ['Ricardo Peñaloza Cruz', 'Hans Luna Hernández'])
        self.assertEqual([a.cedula_profesional for a in apoderados],
                         ['7593879', '6223421'])
        self.assertEqual(
            [a.nombre for a in self.exp.autorizados.all()],
            ['Adriana Carolina Luna Peñaloza'],
        )

    def test_los_apoderados_llegan_al_proemio_del_documento(self):
        from expedientes.models import ApoderadoLegal, AutorizadoNotificacion

        ApoderadoLegal.objects.create(
            expediente=self.exp, nombre='Ricardo Peñaloza Cruz',
            cedula_profesional='7593879', orden=1)
        AutorizadoNotificacion.objects.create(
            expediente=self.exp, nombre='Adriana Carolina Luna Peñaloza', orden=1)

        from expedientes.redaccion import datos_de_expediente

        datos = datos_de_expediente(self.exp)
        cap = capitulos(datos, _calculo(), 'injustificado')

        self.assertIn('Ricardo Peñaloza Cruz', cap['proemio'])
        self.assertIn('7593879', cap['proemio'])
        self.assertIn('Adriana Carolina Luna Peñaloza', cap['proemio'])
        self.assertIn('692, frac. I, 693 y 696', cap['proemio'])

    def test_copiar_representacion_del_expediente_anterior(self):
        from django.urls import reverse

        from expedientes.models import ApoderadoLegal, AutorizadoNotificacion

        ApoderadoLegal.objects.create(
            expediente=self.exp, nombre='Ricardo Peñaloza Cruz',
            cedula_profesional='7593879', orden=1)
        AutorizadoNotificacion.objects.create(
            expediente=self.exp, nombre='Adriana Carolina Luna Peñaloza', orden=1)

        otro_cliente = Cliente.objects.create(
            nombre='OTRO CLIENTE', curp='OTRO850315HBCRRS03',
            salario=Decimal('5000'), fecha_ingreso=date(2024, 1, 1),
            fecha_salida=date(2026, 1, 1),
        )
        nuevo = Expediente.objects.create(
            cliente=otro_cliente, asesor=self.user, tipo_despido='injustificado',
        )
        self.assertEqual(nuevo.apoderados.count(), 0)

        respuesta = self.client.post(
            reverse('copiar_representacion', args=[nuevo.pk]))
        self.assertEqual(respuesta.status_code, 302)

        self.assertEqual(nuevo.apoderados.count(), 1)
        self.assertEqual(nuevo.autorizados.count(), 1)
        self.assertEqual(nuevo.apoderados.first().cedula_profesional, '7593879')

    def test_copiar_representacion_no_duplica(self):
        from django.urls import reverse

        from expedientes.models import ApoderadoLegal

        ApoderadoLegal.objects.create(
            expediente=self.exp, nombre='Ricardo Peñaloza Cruz',
            cedula_profesional='7593879', orden=1)

        otro_cliente = Cliente.objects.create(
            nombre='CLIENTE DOS', curp='CLIE850315HBCRRS04',
            salario=Decimal('5000'), fecha_ingreso=date(2024, 1, 1),
            fecha_salida=date(2026, 1, 1),
        )
        nuevo = Expediente.objects.create(
            cliente=otro_cliente, asesor=self.user, tipo_despido='injustificado',
        )
        url = reverse('copiar_representacion', args=[nuevo.pk])
        self.client.post(url)
        self.client.post(url)

        self.assertEqual(nuevo.apoderados.count(), 1)

    def test_campos_nuevos_de_la_hoja_de_datos_se_guardan(self):
        """Los campos del estándar deben persistir por el acordeón, no sólo existir."""
        from django.urls import reverse

        respuesta = self.client.post(
            reverse('demanda_asistente', args=[self.exp.pk]),
            {
                'accion': 'guardar', 'seccion_abierta': 'despido',
                'nombre': self.cliente.nombre, 'curp': self.cliente.curp,
                'hora_despido': '16:20',
                'despido_persona_puesto': 'gerente de planta',
                'se_firmo_renuncia': 'on',
                'actividades': 'Corte industrial y alineación micrométrica',
                'tipo_contrato': 'determinado',
                'horario_entrada': '08:30', 'horario_salida': '18:30',
                'dias_trabajo': 'lunes a sábado', 'dia_descanso': 'domingo',
                'ciudad': 'Mexicali',
            },
        )
        self.assertEqual(respuesta.status_code, 200)

        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.hora_despido, '16:20')
        self.assertEqual(self.cliente.despido_persona_puesto, 'gerente de planta')
        self.assertTrue(self.cliente.se_firmo_renuncia)
        self.assertEqual(self.cliente.actividades,
                         'Corte industrial y alineación micrométrica')
        self.assertEqual(self.cliente.tipo_contrato, 'determinado')
        self.assertEqual(self.cliente.horario_entrada, '08:30')
        self.assertEqual(self.cliente.horario_salida, '18:30')
        self.assertEqual(self.cliente.dias_trabajo, 'lunes a sábado')
        self.assertEqual(self.cliente.dia_descanso, 'domingo')
        self.assertEqual(self.cliente.ciudad, 'Mexicali')


class TipoSeparacionTest(TestCase):
    """El hecho central y los conceptos cambian según la causa de separación."""

    def _hechos(self, tipo: str) -> str:
        return ' '.join(
            capitulos(_datos_con_expediente(), _calculo(), tipo)['hechos']
        )

    def test_injustificado_reclama_indemnizacion(self):
        unidos = self._hechos('injustificado')
        self.assertIn('fue injustificada', unidos)
        self.assertIn('indemnización que conforme a derecho', unidos)
        self.assertIn('artículo 47', unidos)

    def test_rescision_invoca_el_articulo_51(self):
        unidos = self._hechos('rescision')
        self.assertIn('artículo 51 de la Ley Federal del Trabajo', unidos)
        self.assertIn('causas graves de incumplimiento imputables al patrón', unidos)
        self.assertNotIn('fue injustificada', unidos)

    def test_renuncia_voluntaria_no_alega_despido_injustificado(self):
        unidos = self._hechos('voluntario')
        self.assertNotIn('fue injustificada', unidos)
        self.assertNotIn('indemnización que conforme a derecho', unidos)
        self.assertIn('prestaciones proporcionales', unidos)

    def test_despido_justificado_no_reclama_indemnizacion(self):
        unidos = self._hechos('justificado')
        self.assertNotIn('indemnización que conforme a derecho', unidos)
        self.assertIn('prestaciones devengadas y la prima de antigüedad', unidos)
        self.assertIn('artículo 162', unidos)

    def test_rescision_agrega_los_articulos_51_y_52_al_derecho(self):
        con = capitulos(_datos_con_expediente(), _calculo(), 'rescision')['derecho']
        self.assertIn('51', con)
        self.assertIn('52', con)

    def test_caratula_nombra_la_accion_de_cada_tipo(self):
        esperado = {
            'injustificado': 'DESPIDO INJUSTIFICADO',
            'justificado': 'TERMINACIÓN DE LA RELACIÓN LABORAL',
            'voluntario': 'RENUNCIA VOLUNTARIA',
            'rescision': 'RESCISIÓN DE LA RELACIÓN LABORAL',
            'otro': 'TERMINACIÓN DE LA RELACIÓN LABORAL',
        }
        for tipo, etiqueta in esperado.items():
            cap = capitulos(_datos_con_expediente(), _calculo(), tipo)
            self.assertEqual(cap['caratula']['accion'], etiqueta,
                             f'tipo {tipo} mal etiquetado')


class PrimaAntiguedadTest(TestCase):
    """Art. 162 fr. III LFT: en renuncia, la prima exige 15 años de servicios."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import User

        cls.user = User.objects.create_user('abogada_pa')
        cls.user.profile.rol = 'abogada'
        cls.user.profile.puede_generar_documentos = True
        cls.user.profile.save()

    _contador = 0

    def _expediente(self, anios: int, tipo: str = 'voluntario'):
        from datetime import timedelta

        PrimaAntiguedadTest._contador += 1
        n = PrimaAntiguedadTest._contador
        ingreso = date(2026 - anios, 1, 1) if anios else date(2026, 1, 1)
        cliente = Cliente.objects.create(
            nombre=f'TRABAJADOR {anios} ANIOS ({n})',
            curp=f'PA{n:02d}0315HBCRRS{n:01d}'.ljust(16, 'X')[:18],
            salario=Decimal('12000.00'), fecha_ingreso=ingreso,
            fecha_salida=date(2026, 6, 1), puesto='OPERADOR',
            empresa='ACME', empresa_razon_social='ACME, S.A. DE C.V.',
        )
        return Expediente.objects.create(
            cliente=cliente, asesor=self.user, tipo_despido=tipo,
        )

    def test_renuncia_con_menos_de_15_anios_no_reclama_prima(self):
        from expedientes.redaccion import datos_de_expediente

        expediente = self._expediente(6)
        datos = datos_de_expediente(expediente)
        self.assertFalse(datos['reclama_prima_antiguedad'])

        cap = capitulos(datos, _calculo(), 'voluntario')
        unidos = ' '.join(cap['prestaciones'])
        self.assertNotIn('PRIMA DE ANTIGÜEDAD', unidos.upper())

    def test_renuncia_con_15_anios_o_mas_si_reclama_prima(self):
        from expedientes.redaccion import datos_de_expediente

        expediente = self._expediente(16)
        datos = datos_de_expediente(expediente)
        self.assertTrue(datos['reclama_prima_antiguedad'])

    def test_las_banderas_coinciden_con_el_motor_legal(self):
        """Las banderas del adaptador no pueden discrepar de los conceptos legales."""
        from expedientes.demanda_generator import (_años_completos_de,
                                                   _conceptos_para_demanda)
        from expedientes.redaccion import datos_de_expediente

        for tipo in ('injustificado', 'justificado', 'voluntario', 'rescision', 'otro'):
            for anios in (0, 6, 16):
                expediente = self._expediente(anios, tipo)
                cliente = expediente.cliente
                datos = datos_de_expediente(expediente)
                conceptos = _conceptos_para_demanda(tipo, _años_completos_de(cliente))

                self.assertEqual(
                    datos['reclama_indemnizacion'],
                    conceptos['incluir_indemnizacion'],
                    f'indemnización discrepa en {tipo} con {anios} años')
                self.assertEqual(
                    datos['reclama_prima_antiguedad'],
                    conceptos['incluir_prima_antiguedad'],
                    f'prima de antigüedad discrepa en {tipo} con {anios} años')


class EstandarCompletoTest(TestCase):
    """Verifica el documento generado contra el estándar del despacho.

    Es el equivalente automatizado de revisar el DOCX contra
    `docs/referencia/demanda_injustificado_estandar.pdf`: comprueba que el
    escrito traiga, en orden y con el redactado correcto, todo lo que el
    estándar exige.
    """

    @classmethod
    def setUpTestData(cls):
        import datetime as dt
        from django.contrib.auth.models import User

        from expedientes.models import ApoderadoLegal, AutorizadoNotificacion

        cls.user = User.objects.create_user('abogada_estandar')
        cls.user.profile.rol = 'abogada'
        cls.user.profile.puede_generar_documentos = True
        cls.user.profile.save()

        cliente = Cliente.objects.create(
            nombre='GUSTAVO GUTIERREZ PEREZ', curp='GUPG850315HBCRRS08',
            telefono='6641234567', genero='masculino', nacionalidad='mexicana',
            ciudad='Tijuana', estado='Baja California',
            direccion_calle='Bulevar Díaz Ordaz', direccion_numero='12649',
            direccion_colonia='Centro Comercial Plaza Patria',
            direccion_cp='22106',
            empresa='JEIMEX', empresa_razon_social='JEIMEX, S.A. DE C.V.',
            empresa_calle='Boulevard Héroes de la Independencia',
            empresa_numero='10351', empresa_colonia='Parque Industrial El Florido',
            empresa_cp='22253',
            puesto='SOLDADOR ARMADO',
            actividades='la fabricación y ensamble de estructuras metálicas',
            tipo_contrato='indefinido',
            salario=Decimal('2000.00'), periodo_pago='semanal',
            horas_semanales=48, jornada='diurna', zona_salarial='frontera',
            fecha_ingreso=dt.date(2022, 4, 1), fecha_salida=dt.date(2026, 4, 30),
            horario_entrada='07:00', horario_salida='17:00',
            dias_trabajo='lunes a viernes', dia_descanso='sábado y domingo',
            imss_confirmado=True, tuvo_imss=False,
            modalidad_despido='verbal', hubo_documento_despido=False,
            despido_comunicado_por='el personal de Recursos Humanos',
            despido_persona_puesto='personal de Recursos Humanos',
            despido_lugar='el domicilio de la moral demandada',
            hora_despido='14:45',
            despido_frase='YA NO ES NECESARIO EL USO DE TUS SERVICIOS',
            se_firmo_renuncia=True,
            testigos='Mariano (líder de línea)',
            accion_preferida='indemnizacion',
        )
        cls.exp = Expediente.objects.create(
            cliente=cliente, asesor=cls.user, estado='demanda',
            tipo_despido='injustificado', folio='CCL-2026-12345',
            fecha_tramite=dt.date(2026, 5, 15),
        )
        for orden, (nombre, cedula) in enumerate([
            ('Ricardo Peñaloza Cruz', '7593879'),
            ('Hans Luna Hernández', '6223421'),
            ('Jose Antonio Martínez Figueroa', '6860593'),
        ], start=1):
            ApoderadoLegal.objects.create(
                expediente=cls.exp, nombre=nombre,
                cedula_profesional=cedula, orden=orden)
        AutorizadoNotificacion.objects.create(
            expediente=cls.exp, nombre='Adriana Carolina Luna Peñaloza', orden=1)

    def setUp(self):
        self.client.force_login(self.user)

    def _texto_documento(self) -> str:
        import io

        from django.urls import reverse
        from docx import Document

        respuesta = self.client.get(
            reverse('demanda_capitulos_descargar', args=[self.exp.pk]))
        self.assertEqual(respuesta.status_code, 200)
        doc = Document(io.BytesIO(respuesta.content))
        return '\n'.join(p.text.strip() for p in doc.paragraphs if p.text.strip())

    def test_documento_cumple_el_estandar_del_despacho(self):
        texto = self._texto_documento()

        comprobaciones = [
            ('Carátula ACTOR', 'ACTOR. – GUSTAVO GUTIERREZ PEREZ'),
            ('Carátula ACCIÓN', 'ACCIÓN. - DESPIDO INJUSTIFICADO'),
            ('Tribunal', 'TRIBUNAL LABORAL DEL ESTADO'),
            ('Apoderados con cédula',
             'cédula profesional 7593879, 6223421 y 6860593'),
            ('Autorizados arts. 692/693/696', '692, frac. I, 693 y 696'),
            ('Demandado I fuente de trabajo',
             'QUIEN RESULTE RESPONSABLE DE LA FUENTE DE TRABAJO'),
            ('Demandado II la moral', 'A la MORAL "JEIMEX, S.A. DE C.V."'),
            ('Capítulo de prestaciones', 'CAPÍTULO DE PRESTACIONES:'),
            ('Capítulo de hechos', 'CAPÍTULO DE HECHOS:'),
            ('Pruebas', 'PRUEBAS'),
            ('Confesional', 'CONFESIONAL POR POSICIONES'),
            ('Inspección ocular', 'INSPECCIÓN OCULAR'),
            ('Documental privada', 'DOCUMENTAL PRIVADA'),
            ('Presuncional', 'PRESUNCIONAL LEGAL Y HUMANA'),
            ('Instrumental', 'INSTRUMENTAL PÚBLICA DE ACTUACIONES'),
            ('Capítulo de derecho', 'CAPÍTULO DE DERECHO:'),
            ('Constitucional al frente', 'Artículos 123 Constitucional'),
            ('Firma final', 'PROTESTO LO NECESARIO'),
        ]
        for etiqueta, fragmento in comprobaciones:
            self.assertIn(fragmento, texto, f'falta {etiqueta!r} en el documento')

    def test_documento_incorpora_la_narrativa_capturada(self):
        texto = self._texto_documento()
        # Datos que sólo existen si los campos nuevos llegan al redactado.
        self.assertIn('14:45', texto)
        self.assertIn('YA NO ES NECESARIO EL USO DE TUS SERVICIOS', texto)
        self.assertIn('CCL-2026-12345', texto)
        self.assertIn('artículo 47', texto)
        self.assertIn('lunes a viernes', texto)
        self.assertIn('SOLDADOR ARMADO', texto)

    def test_montos_en_numero_y_letra(self):
        import re

        texto = self._texto_documento()
        # Al menos una prestación con importe y su equivalente en letra.
        self.assertRegex(texto, r'\$[\d,]+\.\d\d pesos \(')
        self.assertIn('/100 M.N.', texto)

    def test_orden_de_los_capitulos(self):
        texto = self._texto_documento()
        posiciones = [
            texto.find('CAPÍTULO DE PRESTACIONES:'),
            texto.find('CAPÍTULO DE HECHOS:'),
            texto.find('PRUEBAS'),
            texto.find('CAPÍTULO DE DERECHO:'),
        ]
        self.assertNotIn(-1, posiciones)
        self.assertEqual(posiciones, sorted(posiciones))


class FormatoTest(TestCase):
    """Detalles de formato que el estándar exige."""

    def test_horas_legibles_en_horas_y_minutos(self):
        self.assertEqual(_horas_legibles(7.6), '7 horas y 36 minutos')
        self.assertEqual(_horas_legibles(2), '2 horas')
        self.assertEqual(_horas_legibles(1), '1 hora')
        self.assertEqual(_horas_legibles(0.5), '30 minutos')

    def test_texto_completo_trae_los_encabezados_en_orden(self):
        texto = generar_texto_completo(_datos(), _calculo(), 'injustificado')
        posiciones = [
            texto.find('CAPÍTULO DE PRESTACIONES'),
            texto.find('CAPÍTULO DE HECHOS'),
            texto.find('PRUEBAS'),
            texto.find('CAPÍTULO DE DERECHO'),
        ]
        self.assertNotIn(-1, posiciones)
        self.assertEqual(posiciones, sorted(posiciones))

    def test_caratula_reporta_la_accion(self):
        cap = capitulos(_datos_con_expediente(), _calculo(), 'injustificado')
        self.assertEqual(cap['caratula']['accion'], 'DESPIDO INJUSTIFICADO')
        self.assertIn('TRIBUNAL LABORAL DEL ESTADO', cap['caratula']['tribunal'])
