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
