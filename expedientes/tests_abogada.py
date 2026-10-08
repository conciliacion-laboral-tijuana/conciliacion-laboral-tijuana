from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Expediente


class PortalAbogadaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('juridico', password='test')
        self.user.profile.rol = 'abogada'
        self.user.profile.save()
        self.client.force_login(self.user)

    def test_menu_sencillo_y_otros_roles(self):
        response = self.client.get(reverse('dashboard_abogada'))
        self.assertContains(response, 'Crear demanda')
        self.assertNotContains(response, '¿Qué hiciste hoy?')
        self.assertNotContains(response, '>Calendario</a>')
        self.assertNotContains(response, '>Machotes</a>')
        self.user.profile.rol = 'asesor'
        self.user.profile.save()
        response = self.client.get(reverse('dashboard_asesor'))
        self.assertContains(response, '>Calendario</a>')

    def test_crear_demanda_y_abrir_asistente(self):
        response = self.client.post(reverse('dashboard_abogada'), {'nombre': 'Cliente nuevo'})
        expediente = Expediente.objects.get(cliente__nombre='Cliente nuevo')
        self.assertRedirects(response, reverse('demanda_asistente', args=[expediente.pk]))
        self.assertEqual(expediente.asesor, self.user)
        self.assertEqual(expediente.cliente.created_by, self.user)

    def test_acceso_otros_roles_y_anonimo(self):
        self.user.profile.rol = 'asesor'
        self.user.profile.save()
        self.assertEqual(self.client.post(reverse('dashboard_abogada'), {'nombre': 'No crear'}).status_code, 403)
        self.assertFalse(Expediente.objects.exists())
        self.client.logout()
        self.assertEqual(self.client.get(reverse('dashboard_abogada')).status_code, 302)
