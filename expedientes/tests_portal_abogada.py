from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Cliente, Expediente


class PortalAbogadaTests(TestCase):
    """Verificación del área de abogadas: dashboard + creación de demanda."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('abogada_portal', password='x')
        cls.user.profile.rol = 'abogada'
        cls.user.profile.save()
        cls.asesor = User.objects.create_user('asesor_portal', password='x')
        cls.asesor.profile.rol = 'asesor'
        cls.asesor.profile.save()

    def test_get_dashboard_abogada(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse('dashboard_abogada'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Crear demanda')

    def test_dashboard_abogada_bloqueado_para_asesor(self):
        self.client.force_login(self.asesor)
        resp = self.client.get(reverse('dashboard_abogada'))
        self.assertEqual(resp.status_code, 302)  # redirect a su dashboard

    def test_post_crea_cliente_expediente_y_redirige(self):
        self.client.force_login(self.user)
        resp = self.client.post(reverse('dashboard_abogada'), {'nombre': 'Cliente Abogada Test'})
        self.assertEqual(resp.status_code, 302)
        cliente = Cliente.objects.filter(nombre='Cliente Abogada Test').first()
        self.assertIsNotNone(cliente)
        expediente = Expediente.objects.filter(cliente=cliente).first()
        self.assertIsNotNone(expediente)
        # El redirect va al asistente de demanda del expediente nuevo
        self.assertIn(str(expediente.pk), resp['Location'])

    def test_asistente_demanda_renderiza(self):
        self.client.force_login(self.user)
        cliente = Cliente.objects.create(nombre='Cliente Asistente')
        self.exp = Expediente.objects.create(cliente=cliente, asesor=self.user)
        resp = self.client.get(reverse('demanda_asistente', args=[self.exp.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_asistente_guardar_no_500(self):
        """POST accion=guardar con formset vacío: debe responder sin 500."""
        self.client.force_login(self.user)
        cliente = Cliente.objects.create(nombre='Cliente Guardar')
        exp = Expediente.objects.create(cliente=cliente, asesor=self.user)
        resp = self.client.post(reverse('demanda_asistente', args=[exp.pk]), {'accion': 'guardar'})
        if resp.status_code >= 500:
            self.fail('500 al guardar el asistente')
        self.assertEqual(resp.status_code, 200)
