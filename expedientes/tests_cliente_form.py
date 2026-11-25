from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Cliente


def get_form_errors(resp):
    try:
        return dict(resp.context['form'].errors.items())
    except Exception:
        return ''


class ClienteFormRenderTests(TestCase):
    """El error 500 al guardar cliente era una TemplateSyntaxError en cliente_form.html."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('asesor_render', password='x')
        cls.user.profile.rol = 'asesor'
        cls.user.profile.save()

    def get_url(self):
        try:
            return reverse('cliente_create')
        except Exception:
            return '/clientes/nuevo/'

    def test_get_renderiza(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.get_url())
        self.assertEqual(resp.status_code, 200)

    def test_post_invalido_muestra_errores_sin_500(self):
        self.client.force_login(self.user)
        resp = self.client.post(self.get_url(), {})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Corrige los errores del formulario')

    def test_post_valido_asesor_crea_cliente_y_expediente(self):
        self.client.force_login(self.user)
        data = self.defaults_por_tipo()
        data.update({'nombre': 'Cliente OK', 'curp': 'AAAA900101HBCBBB01', 'salario': '18000',
                     'fecha_ingreso': '2024-01-01', 'fecha_salida': '2026-07-01',
                     'puesto': 'Operador', 'empresa': 'Empresa ejemplo'})
        url = self.get_url()
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302, get_form_errors(resp))
        self.assertTrue(Cliente.objects.filter(nombre='Cliente OK').exists())

    def test_post_con_demandados_adicionales(self):
        from .models import DemandadoAdicional
        self.client.force_login(self.user)
        data = self.defaults_por_tipo()
        data.update({'nombre': 'Cliente Multi', 'curp': 'BBBB900101HBCBBB02', 'salario': '18000',
                     'fecha_ingreso': '2024-01-01', 'fecha_salida': '2026-07-01',
                     'puesto': 'Operador', 'empresa': 'Empresa ejemplo',
                     'demandados-TOTAL_FORMS': '3', 'demandados-INITIAL_FORMS': '0',
                     'demandados-MIN_NUM_FORMS': '0', 'demandados-MAX_NUM_FORMS': '1000',
                     'demandados-0-tipo_persona': 'moral', 'demandados-0-nombre': 'Grupo Ejemplo SA',
                     'demandados-1-tipo_persona': 'fisica', 'demandados-1-nombre': 'Juan Dueño',
                     # Formulario agregado y luego quitado en pantalla
                     'demandados-2-tipo_persona': 'moral', 'demandados-2-nombre': 'Borrado',
                     'demandados-2-DELETE': 'on'})
        resp = self.client.post(self.get_url(), data)
        self.assertEqual(resp.status_code, 302, get_form_errors(resp))
        cliente = Cliente.objects.get(nombre='Cliente Multi')
        self.assertEqual(
            list(cliente.demandados_adicionales.values_list('nombre', 'tipo_persona', 'orden')),
            [('Grupo Ejemplo SA', 'moral', 1), ('Juan Dueño', 'fisica', 2)])

        # Editar: quitar el primero conserva el resto
        primero, segundo = cliente.demandados_adicionales.all()
        data.update({'demandados-TOTAL_FORMS': '2', 'demandados-INITIAL_FORMS': '2',
                     'demandados-0-id': str(primero.pk), 'demandados-0-DELETE': 'on',
                     'demandados-1-id': str(segundo.pk)})
        data.pop('demandados-2-tipo_persona'); data.pop('demandados-2-nombre'); data.pop('demandados-2-DELETE')
        resp = self.client.post(reverse('cliente_update', args=[cliente.pk]), data)
        self.assertEqual(resp.status_code, 302, get_form_errors(resp))
        self.assertEqual(list(cliente.demandados_adicionales.values_list('nombre', 'orden')),
                         [('Juan Dueño', 1)])

    def test_salario_por_periodo_se_guarda_mensual_y_hechos(self):
        """El asesor captura el salario de cada pago; se guarda el mensual."""
        from decimal import Decimal
        self.client.force_login(self.user)
        data = self.defaults_por_tipo()
        data.update({'nombre': 'Cliente Semanal', 'curp': 'CCCC900101HBCBBB03',
                     'salario': '2000', 'periodo_pago': 'semanal',
                     'fecha_ingreso': '2024-01-01', 'fecha_salida': '2026-07-01',
                     'puesto': 'Operador', 'empresa': 'Empresa ejemplo',
                     'descripcion_hechos': 'Lo despidieron el lunes sin explicación.'})
        resp = self.client.post(self.get_url(), data)
        self.assertEqual(resp.status_code, 302, get_form_errors(resp))
        cliente = Cliente.objects.get(nombre='Cliente Semanal')
        self.assertEqual(cliente.salario, Decimal('8571.43'))  # 2000 × 30 / 7
        self.assertEqual(cliente.descripcion_hechos, 'Lo despidieron el lunes sin explicación.')

        # Al editar se vuelve a mostrar el monto semanal, con el nuevo título
        resp = self.client.get(reverse('cliente_update', args=[cliente.pk]))
        self.assertEqual(resp.context['form'].initial['salario'], Decimal('2000.00'))
        self.assertContains(resp, '>Salario</label>')
        self.assertContains(resp, 'Descripción de los hechos')

    def test_get_edicion_muestra_seccion_demandados(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.get_url())
        self.assertContains(resp, 'Agregar persona o empresa')
        self.assertContains(resp, 'demandados-TOTAL_FORMS')

    def defaults_por_tipo(self):
        from .forms import ClienteForm
        data = {}
        for name, field in ClienteForm().fields.items():
            val = field.initial
            if val is None:
                kind = field.__class__.__name__
                if kind in ('IntegerField', 'DecimalField'):
                    val = '1'
                elif kind == 'CharField':
                    val = 'x'
            if val is not None:
                data[name] = val
        return data


class CitadosConciliacionTests(TestCase):
    """El portal de conciliación recibe al patrón principal y a los adicionales."""

    def setUp(self):
        from .models import DemandadoAdicional
        self.cliente = Cliente.objects.create(
            nombre='Trabajador', empresa='Planta Norte', empresa_razon_social='ACME SA DE CV',
            tipo_persona_citado='moral', empresa_calle='Blvd. Industrial', empresa_numero='100',
            empresa_cp='22500', empresa_colonia='Otay', empresa_telefono='6641112233')
        DemandadoAdicional.objects.create(
            cliente=self.cliente, nombre='ACME Oficinas Corporativas SA', tipo_persona='moral',
            calle='Paseo de los Héroes', numero='9000', cp='22010', orden=1)
        DemandadoAdicional.objects.create(
            cliente=self.cliente, nombre='Juan Pérez Dueño', tipo_persona='fisica', orden=2)

    def test_citados_en_orden_con_domicilio_propio_o_del_principal(self):
        from .conciliacion_automation import citados_de_cliente
        citados = citados_de_cliente(self.cliente)
        self.assertEqual([c['nombre'] for c in citados],
                         ['ACME SA DE CV', 'ACME Oficinas Corporativas SA', 'Juan Pérez Dueño'])
        # Domicilio propio (otro CP: no hereda la colonia del principal)
        self.assertEqual((citados[1]['calle'], citados[1]['cp'], citados[1]['colonia']),
                         ('Paseo de los Héroes', '22010', ''))
        # Sin domicilio: toma el del principal
        self.assertEqual((citados[2]['calle'], citados[2]['cp'], citados[2]['colonia']),
                         ('Blvd. Industrial', '22500', 'Otay'))
        self.assertEqual(citados[2]['tipo_persona'], 'fisica')

    def test_payload_extension_incluye_todos_los_citados(self):
        from .api_extension import _serializar_tarea
        from .models import Expediente, TareaConciliacion
        asesor = User.objects.create_user('asesor_citados')
        exp = Expediente.objects.create(cliente=self.cliente, asesor=asesor)
        tarea = TareaConciliacion.objects.create(expediente=exp, modo='extension')
        datos = _serializar_tarea(tarea)['cliente']
        self.assertEqual([c['tipo_persona'] for c in datos['citados']], ['2', '2', '1'])
        # Compatibilidad con extensiones anteriores
        self.assertEqual(datos['empresa_nombre'], 'ACME SA DE CV')
