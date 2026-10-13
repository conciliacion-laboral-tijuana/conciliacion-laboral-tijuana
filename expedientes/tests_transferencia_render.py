from datetime import date
from decimal import Decimal as D

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Cliente, Expediente


class SolicitarTransferenciaRenderTests(TestCase):
    """Regresión: transferencia_form.html usaba el filtro get_item sin cargar la librería."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('asesor_transf', password='x')
        cls.user.profile.rol = 'asesor'
        cls.user.profile.save()
        cliente = Cliente.objects.create(nombre='Cliente Transf', curp='AAAA900101HBCBBB01')
        cls.exp = Expediente.objects.create(cliente=cliente, asesor=cls.user)

    def test_get_renderiza_formulario_transferencia(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse('solicitar_transferencia', args=[self.exp.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Solicitar Transferencia')
