from decimal import Decimal

from django.test import SimpleTestCase

from .salario import a_mensual, por_periodo


class ConversionSalarioTests(SimpleTestCase):
    def test_a_mensual(self):
        self.assertEqual(a_mensual(Decimal('2000'), 'semanal'), Decimal('8571.43'))
        self.assertEqual(a_mensual(Decimal('6200'), 'quincenal'), Decimal('12400.00'))
        self.assertEqual(a_mensual(Decimal('400'), 'diario'), Decimal('12000.00'))
        self.assertEqual(a_mensual(Decimal('15000'), 'mensual'), Decimal('15000.00'))
        self.assertIsNone(a_mensual(None, 'semanal'))

    def test_ida_y_vuelta_conserva_el_monto_capturado(self):
        for monto in ('1999.99', '2000', '3333.33', '0.01', '12345.67'):
            for periodo in ('diario', 'semanal', 'quincenal', 'mensual'):
                capturado = Decimal(monto).quantize(Decimal('0.01'))
                self.assertEqual(por_periodo(a_mensual(capturado, periodo), periodo),
                                 capturado, (monto, periodo))
