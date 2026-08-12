"""
Tests para el módulo de finanzas (finanzas).

Cubre:
  - Lógica de negocio de los modelos (cálculos automáticos, propiedades).
  - Validación de formularios (coherencia tipo/categoría en caja).
  - Vistas: control de acceso por rol, dashboard, CRUD, API, exportaciones
    y confirmación de distribuciones.

Uso:
    uv run python manage.py test finanzas
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from expedientes.models import Cliente, Expediente
from finanzas.forms import CashMovementForm
from finanzas.models import (
    Agreement,
    CashMovement,
    Commission,
    Employee,
    Expense,
    Honorario,
    Office,
    Partner,
    PartnerLoan,
    PartnerProfit,
    PartnerUtilitySummary,
    Payroll,
    ProfitDistribution,
    SettlementPayment,
    WorkWeek,
)


def _usuario(username='admin_test', rol='admin', password='clave123'):
    """Crea un usuario con rol (el perfil se crea automáticamente)."""
    user = User.objects.create_user(username=username, password=password)
    user.profile.rol = rol
    user.profile.save()
    return user


def _oficina(nombre='Plaza Patria Test'):
    return Office.objects.create(nombre=nombre)


def _cliente(nombre='Cliente Finanzas Test', oficina='plaza_patria'):
    return Cliente.objects.create(nombre=nombre, oficina=oficina)


def _expediente(cliente, asesor, **kwargs):
    defaults = {'estado': 'convenio', 'tipo_despido': 'injustificado'}
    defaults.update(kwargs)
    return Expediente.objects.create(cliente=cliente, asesor=asesor, **defaults)


class BaseFinanzasTestCase(TestCase):
    """Setup compartido: admin logueado + objetos base."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = _usuario('admin_finanzas', 'admin')
        cls.oficina = _oficina()
        cls.cliente = _cliente()
        cls.asesor = _usuario('asesor_finanzas', 'asesor')
        cls.expediente = _expediente(cls.cliente, cls.asesor)

    def setUp(self):
        self.client = Client()
        self.assertTrue(self.client.login(username='admin_finanzas', password='clave123'))


# ══════════════════════════════════════════════════════════════════════
#  MODELOS — cálculos automáticos
# ══════════════════════════════════════════════════════════════════════


class CalculosAutomaticosTests(BaseFinanzasTestCase):
    def test_commission_calcula_monto_automaticamente(self):
        """Commission.save() debe calcular monto_comision = convenio × % / 100."""
        c = Commission.objects.create(
            expediente=self.expediente, asesor=self.asesor,
            fecha=date.today(), monto_convenio=Decimal('100000.00'),
            porcentaje=Decimal('5.00'), oficina=self.oficina,
            registrado_por=self.admin,
        )
        self.assertEqual(c.monto_comision, Decimal('5000.00'))
        self.assertEqual(c.estado, 'pendiente')

    def test_payroll_calcula_total_pagado(self):
        """Payroll.save() debe calcular total_pagado = salario - descuentos."""
        emp = Employee.objects.create(
            nombre='Empleado Test', puesto='administrativo',
            periodo_pago='quincenal', salario=Decimal('8000.00'),
            oficina=self.oficina,
        )
        p = Payroll.objects.create(
            empleado=emp, fecha_pago=date.today(), periodo='quincenal',
            salario_pagado=Decimal('8000.00'), descuentos=Decimal('1200.00'),
            oficina=self.oficina, registrado_por=self.admin,
        )
        self.assertEqual(p.total_pagado, Decimal('6800.00'))

    def test_honorario_calcula_monto_y_actualiza_convenio(self):
        """Honorario.save() calcula monto y suma el total en Agreement.honorarios."""
        convenio = Agreement.objects.create(
            cliente=self.cliente, oficina=self.oficina, fecha=date.today(),
            monto_convenio=Decimal('200000.00'), responsable=self.admin,
            creado_por=self.admin,
        )
        h = Honorario.objects.create(
            convenio=convenio, porcentaje=Decimal('30.00'),
            registrado_por=self.admin,
        )
        self.assertEqual(h.monto_calculado, Decimal('60000.00'))
        convenio.refresh_from_db()
        self.assertEqual(convenio.honorarios, Decimal('60000.00'))

    def test_agreement_honorarios_pendientes_y_pagados(self):
        """Las propiedades de Agreement separan pendientes de pagados."""
        convenio = Agreement.objects.create(
            cliente=self.cliente, oficina=self.oficina, fecha=date.today(),
            monto_convenio=Decimal('100000.00'), responsable=self.admin,
            creado_por=self.admin,
        )
        Honorario.objects.create(convenio=convenio, porcentaje=Decimal('30.00'),
                                 registrado_por=self.admin, estado='pagado')
        Honorario.objects.create(convenio=convenio, porcentaje=Decimal('10.00'),
                                 registrado_por=self.admin, estado='pendiente')

        self.assertEqual(convenio.honorarios_pagados, Decimal('30000.00'))
        self.assertEqual(convenio.honorarios_pendientes, Decimal('10000.00'))


class WorkWeekTests(BaseFinanzasTestCase):
    def test_semana_actual_crea_y_reutiliza(self):
        """semana_actual() crea la semana que cubre hoy y la reutiliza."""
        w1 = WorkWeek.semana_actual()
        self.assertIsNotNone(w1.pk)
        self.assertEqual(w1.estado, 'abierta')
        hoy = timezone.now().date()
        self.assertLessEqual(w1.fecha_inicio, hoy)
        self.assertGreaterEqual(w1.fecha_fin, hoy)

        w2 = WorkWeek.semana_actual()
        self.assertEqual(w1.pk, w2.pk, 'No debe crear una semana duplicada')

    def test_semana_actual_reutiliza_aunque_este_cerrada(self):
        """semana_actual() devuelve la semana que cubre hoy aunque esté cerrada
        (no crea duplicados: la 'semana actual' es la que contiene la fecha)."""
        w1 = WorkWeek.semana_actual()
        w1.estado = 'cerrada'
        w1.save()
        w2 = WorkWeek.semana_actual()
        self.assertEqual(w1.pk, w2.pk, 'No debe duplicar la semana que cubre hoy')

    def test_totales_semana_suman_ingresos_y_gastos(self):
        """total_ingresos/total_gastos/balance combinan caja, pagos, gastos y nómina."""
        semana = WorkWeek.semana_actual()
        fecha = semana.fecha_inicio

        # Ingresos: 1 pago de convenio + 1 ingreso de caja
        SettlementPayment.objects.create(
            fecha=fecha, cliente=self.cliente, expediente=self.expediente,
            monto=Decimal('5000.00'), forma_pago='efectivo',
            oficina=self.oficina, registrado_por=self.admin,
        )
        CashMovement.objects.create(
            oficina=self.oficina, fecha=fecha, tipo='ingreso',
            categoria='anticipo', monto=Decimal('1000.00'),
            registrado_por=self.admin,
        )
        # Gastos: 1 gasto operativo + 1 egreso de caja + 1 nómina
        Expense.objects.create(
            fecha=fecha, categoria='renta', monto=Decimal('2000.00'),
            oficina=self.oficina, registrado_por=self.admin,
        )
        CashMovement.objects.create(
            oficina=self.oficina, fecha=fecha, tipo='egreso',
            categoria='papeleria', monto=Decimal('500.00'),
            registrado_por=self.admin,
        )
        emp = Employee.objects.create(
            nombre='Emp Nómina', salario=Decimal('3000.00'), oficina=self.oficina,
        )
        Payroll.objects.create(
            empleado=emp, fecha_pago=fecha, salario_pagado=Decimal('3000.00'),
            descuentos=Decimal('0.00'), oficina=self.oficina,
            registrado_por=self.admin,
        )

        self.assertEqual(semana.total_ingresos, Decimal('6000.00'))
        self.assertEqual(semana.total_gastos, Decimal('5500.00'))
        self.assertEqual(semana.balance, Decimal('500.00'))

    def test_movimiento_fuera_de_la_semana_no_cuenta(self):
        """Un movimiento fuera del rango de la semana no altera los totales."""
        semana = WorkWeek.semana_actual()
        CashMovement.objects.create(
            oficina=self.oficina, fecha=semana.fecha_fin + timedelta(days=30),
            tipo='ingreso', categoria='convenio', monto=Decimal('99999.00'),
            registrado_por=self.admin,
        )
        self.assertEqual(semana.total_ingresos, Decimal('0'))

    def test_semana_actual_crea_nueva_cuando_la_anterior_no_cubre_hoy(self):
        """Si la semana guardada no cubre hoy, se crea una nueva."""
        pasada = WorkWeek.objects.create(
            numero=99, fecha_inicio=date(2020, 1, 6), fecha_fin=date(2020, 1, 12),
            estado='cerrada',
        )
        actual = WorkWeek.semana_actual()
        self.assertNotEqual(pasada.pk, actual.pk)


class CashMovementModelTests(BaseFinanzasTestCase):
    def test_clean_rechaza_categoria_incoherente(self):
        """Un ingreso con categoría de egreso debe lanzar ValidationError."""
        m = CashMovement(
            oficina=self.oficina, fecha=date.today(), tipo='ingreso',
            categoria='papeleria', monto=Decimal('100'), registrado_por=self.admin,
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            m.full_clean()

    def test_clean_acepta_categoria_coherente(self):
        """Ingreso con categoría de ingreso pasa la validación sin errores."""
        m = CashMovement(
            oficina=self.oficina, fecha=date.today(), tipo='ingreso',
            categoria='convenio', monto=Decimal('100'), registrado_por=self.admin,
        )
        m.full_clean()  # no debe lanzar

    def test_clean_acepta_egreso_con_categoria_egreso(self):
        """Egreso con categoría de egreso pasa la validación sin errores."""
        m = CashMovement(
            oficina=self.oficina, fecha=date.today(), tipo='egreso',
            categoria='papeleria', monto=Decimal('100'), registrado_por=self.admin,
        )
        m.full_clean()  # no debe lanzar


class PartnerTests(BaseFinanzasTestCase):
    def test_saldos_prestamos_y_saldo_neto(self):
        """Los saldos del socio suman préstamos otorgados/recibidos pendientes."""
        a = Partner.objects.create(nombre='Socio A', porcentaje_participacion=Decimal('60.00'))
        b = Partner.objects.create(nombre='Socio B', porcentaje_participacion=Decimal('40.00'))

        # A presta 5000 a B (pendiente) y 1000 (pagado)
        PartnerLoan.objects.create(
            socio_origen=a, socio_destino=b, monto=Decimal('5000.00'),
            fecha=date.today(), concepto='Préstamo 1', registrado_por=self.admin,
        )
        PartnerLoan.objects.create(
            socio_origen=a, socio_destino=b, monto=Decimal('1000.00'),
            fecha=date.today(), concepto='Préstamo 2', estado='pagado',
            registrado_por=self.admin,
        )
        # B presta 2000 a A (pendiente)
        PartnerLoan.objects.create(
            socio_origen=b, socio_destino=a, monto=Decimal('2000.00'),
            fecha=date.today(), concepto='Préstamo 3', registrado_por=self.admin,
        )

        self.assertEqual(a.saldo_prestamos_otorgados, Decimal('5000.00'))
        self.assertEqual(a.saldo_prestamos_recibidos, Decimal('2000.00'))
        self.assertEqual(a.saldo_neto, Decimal('3000.00'))
        self.assertEqual(b.saldo_neto, Decimal('-3000.00'))

    def test_loan_saldo_pendiente(self):
        """saldo_pendiente devuelve el monto solo si está pendiente."""
        a = Partner.objects.create(nombre='Socio X')
        b = Partner.objects.create(nombre='Socio Y')
        loan = PartnerLoan.objects.create(
            socio_origen=a, socio_destino=b, monto=Decimal('500.00'),
            fecha=date.today(), concepto='Test', registrado_por=self.admin,
        )
        self.assertEqual(loan.saldo_pendiente, Decimal('500.00'))
        loan.estado = 'pagado'
        loan.save()
        self.assertEqual(loan.saldo_pendiente, Decimal('0'))


class ProfitDistributionTests(BaseFinanzasTestCase):
    def test_calcular_utilidad_neta(self):
        """La utilidad neta descuenta honorarios, comisiones, retenciones y gastos."""
        convenio = Agreement.objects.create(
            cliente=self.cliente, oficina=self.oficina, fecha=date.today(),
            monto_convenio=Decimal('100000.00'), responsable=self.admin,
            creado_por=self.admin,
        )
        Honorario.objects.create(convenio=convenio, porcentaje=Decimal('30.00'),
                                 registrado_por=self.admin)
        Commission.objects.create(
            expediente=self.expediente, asesor=self.asesor, fecha=date.today(),
            monto_convenio=Decimal('100000.00'), porcentaje=Decimal('5.00'),
            oficina=self.oficina, registrado_por=self.admin,
        )
        # En el flujo real la vista obtiene el convenio desde la BD (fresco).
        convenio.refresh_from_db()

        dist = ProfitDistribution.objects.create(
            convenio=convenio, fecha=date.today(), creado_por=self.admin,
            retenciones=Decimal('1000.00'), gastos_relacionados=Decimal('500.00'),
        )
        # monto 100000 − honorarios 30000 − comisión 5000 − retención 1000 − gastos 500
        self.assertEqual(dist.utilidad_neta, Decimal('63500.00'))
        self.assertEqual(dist.monto_convenio, Decimal('100000.00'))

    def test_generar_participaciones_y_resumen(self):
        """La distribución genera participaciones por socio y actualiza resúmenes."""
        convenio = Agreement.objects.create(
            cliente=self.cliente, oficina=self.oficina, fecha=date.today(),
            monto_convenio=Decimal('100000.00'), responsable=self.admin,
            creado_por=self.admin,
        )
        Partner.objects.create(nombre='Socio 1', porcentaje_participacion=Decimal('60.00'))
        Partner.objects.create(nombre='Socio 2', porcentaje_participacion=Decimal('40.00'))

        from finanzas.views import _generar_participaciones
        dist = ProfitDistribution.objects.create(
            convenio=convenio, fecha=date.today(), creado_por=self.admin,
        )
        _generar_participaciones(dist)

        self.assertEqual(dist.partner_profits.count(), 2)
        total = sum((pp.monto for pp in dist.partner_profits.all()), Decimal('0'))
        self.assertEqual(total, dist.utilidad_neta, 'La suma de participaciones = utilidad neta')

        # Confirmar → los resúmenes de los socios acumulan la utilidad
        dist.estado = 'confirmada'
        dist.save()
        for pp in dist.partner_profits.all():
            resumen, _ = PartnerUtilitySummary.objects.get_or_create(partner=pp.partner)
            resumen.actualizar()
            self.assertEqual(resumen.utilidad_generada, pp.monto)
            self.assertEqual(resumen.utilidad_pendiente, pp.monto)


# ══════════════════════════════════════════════════════════════════════
#  FORMULARIOS
# ══════════════════════════════════════════════════════════════════════


class CashMovementFormTests(BaseFinanzasTestCase):
    def test_ingreso_con_categoria_ingreso_valido(self):
        form = CashMovementForm(data={
            'oficina': self.oficina.pk, 'fecha': '2026-01-15',
            'tipo': 'ingreso', 'categoria': 'convenio', 'monto': '100.00',
            'descripcion': 'Pago',
        }, user=self.admin)
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_egreso_con_categoria_egreso_valido(self):
        """Regresión: antes el form solo ofrecía categorías de ingreso y
        rechazaba todo egreso con 'papeleria no es una de las opciones'."""
        form = CashMovementForm(data={
            'oficina': self.oficina.pk, 'fecha': '2026-01-15',
            'tipo': 'egreso', 'categoria': 'papeleria', 'monto': '100.00',
            'descripcion': 'Papelería',
        }, user=self.admin)
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_ingreso_con_categoria_egreso_invalido(self):
        form = CashMovementForm(data={
            'oficina': self.oficina.pk, 'fecha': '2026-01-15',
            'tipo': 'ingreso', 'categoria': 'papeleria', 'monto': '100.00',
        }, user=self.admin)
        self.assertFalse(form.is_valid())
        self.assertIn('categoria', form.errors)

    def test_edicion_de_egreso_usa_categorias_de_egreso(self):
        """Al editar un egreso existente, el select debe ofrecer categorías de egreso."""
        egreso = CashMovement.objects.create(
            oficina=self.oficina, fecha=date.today(), tipo='egreso',
            categoria='gasolina', monto=Decimal('50.00'), registrado_por=self.admin,
        )
        form = CashMovementForm(instance=egreso, user=self.admin)
        opciones = dict(form.fields['categoria'].choices)
        self.assertIn('gasolina', opciones)
        self.assertNotIn('convenio', opciones, 'Las categorías de ingreso no deben aparecer al editar un egreso')

    def test_cambiar_tipo_al_editar_usa_categorias_del_post(self):
        """Al editar y cambiar el tipo (ingreso → egreso), el POST manda sobre
        el tipo guardado en la instancia (regresión del fix de choices)."""
        ingreso = CashMovement.objects.create(
            oficina=self.oficina, fecha=date.today(), tipo='ingreso',
            categoria='convenio', monto=Decimal('100.00'), registrado_por=self.admin,
        )
        form = CashMovementForm(data={
            'oficina': self.oficina.pk, 'fecha': '2026-01-15',
            'tipo': 'egreso', 'categoria': 'papeleria', 'monto': '75.00',
        }, instance=ingreso, user=self.admin)
        self.assertTrue(form.is_valid(), form.errors.as_json())
        self.assertEqual(form.cleaned_data['tipo'], 'egreso')


# ══════════════════════════════════════════════════════════════════════
#  VISTAS — control de acceso por rol
# ══════════════════════════════════════════════════════════════════════


class AccesoPorRolTests(TestCase):
    """El módulo financiero es exclusivo de admin / superadmin / finanzas."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = _usuario('admin_acceso', 'admin')
        cls.superadmin = _usuario('super_acceso', 'superadmin')
        cls.finanzas = _usuario('finanzas_acceso', 'finanzas')
        cls.asesor = _usuario('asesor_acceso', 'asesor')

    def setUp(self):
        self.client = Client()

    def _urls(self):
        return [
            reverse('dashboard_financiero'),
            reverse('cashmovement_list'),
            reverse('partner_list'),
            reverse('workweek_list'),
            reverse('partnerloan_list'),
            reverse('agreement_list'),
            reverse('profitdistribution_list'),
            reverse('reporte_convenios'),
        ]

    def _login(self, username):
        self.client.login(username=username, password='clave123')

    def test_anonimo_redirige_al_login(self):
        for url in self._urls():
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, f'{url} debe redirigir al login')
            self.assertIn('/accounts/login/', resp.url or '', f'{url} debe ir al login')

    def test_asesor_bloqueado(self):
        """Un asesor autenticado recibe 403 (PermissionDenied) en todas las vistas."""
        self._login('asesor_acceso')
        for url in self._urls():
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 403, f'{url} debe bloquear al asesor')

    def test_roles_permitidos_acceden(self):
        for username in ['admin_acceso', 'super_acceso', 'finanzas_acceso']:
            self._login(username)
            for url in self._urls():
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200, f'{url} debe cargar para {username}')
            self.client.logout()

    def test_api_flujo_mensual_permisos(self):
        # Anónimo → login
        resp = self.client.get(reverse('api_flujo_mensual'))
        self.assertEqual(resp.status_code, 302)

        # Asesor → 403
        self._login('asesor_acceso')
        resp = self.client.get(reverse('api_flujo_mensual'))
        self.assertEqual(resp.status_code, 403)

        # Admin → 200 JSON con los 12 meses
        self._login('admin_acceso')
        resp = self.client.get(reverse('api_flujo_mensual'))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data['labels']), 12)
        self.assertEqual(len(data['ingresos']), 12)
        self.assertEqual(len(data['gastos']), 12)

    def test_exportaciones_redirigen_al_asesor(self):
        """Un asesor no puede exportar: redirige al dashboard de asesor."""
        self._login('asesor_acceso')
        for url in [
            reverse('exportar_dashboard_financiero_excel'),
            reverse('exportar_reporte_convenios_excel'),
        ]:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, url)
            self.assertEqual(resp.url, reverse('dashboard_asesor'), url)

    def test_exportaciones_admin_generan_excel(self):
        """Un admin recibe un .xlsx válido del dashboard y del reporte."""
        self._login('admin_acceso')
        for url in [
            reverse('exportar_dashboard_financiero_excel'),
            reverse('exportar_reporte_convenios_excel'),
        ]:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, url)
            self.assertEqual(
                resp['Content-Type'],
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
            self.assertIn('attachment; filename=', resp['Content-Disposition'])
            self.assertGreater(len(resp.content), 1000, 'El Excel no puede estar vacío')


# ══════════════════════════════════════════════════════════════════════
#  VISTAS — flujos CRUD
# ══════════════════════════════════════════════════════════════════════


class CashMovementViewTests(BaseFinanzasTestCase):
    def test_crear_ingreso(self):
        url = reverse('cashmovement_create')
        resp = self.client.post(url, {
            'oficina': self.oficina.pk, 'fecha': '2026-01-15',
            'tipo': 'ingreso', 'categoria': 'convenio', 'monto': '1500.00',
            'descripcion': 'Pago de convenio', 'referencia': 'EXP-1',
        })
        self.assertEqual(resp.status_code, 302)
        m = CashMovement.objects.get(tipo='ingreso')
        self.assertEqual(m.monto, Decimal('1500.00'))
        self.assertEqual(m.registrado_por, self.admin)

    def test_crear_egreso(self):
        """Regresión: antes el POST de un egreso fallaba la validación de categoría."""
        url = reverse('cashmovement_create')
        resp = self.client.post(url, {
            'oficina': self.oficina.pk, 'fecha': '2026-01-15',
            'tipo': 'egreso', 'categoria': 'papeleria', 'monto': '300.00',
            'descripcion': 'Compra de papelería',
        })
        self.assertEqual(resp.status_code, 302)
        m = CashMovement.objects.get(tipo='egreso')
        self.assertEqual(m.categoria, 'papeleria')

    def test_crear_ingreso_con_categoria_egreso_es_rechazado(self):
        url = reverse('cashmovement_create')
        resp = self.client.post(url, {
            'oficina': self.oficina.pk, 'fecha': '2026-01-15',
            'tipo': 'ingreso', 'categoria': 'papeleria', 'monto': '100.00',
        })
        self.assertEqual(resp.status_code, 200, 'Debe re-renderizar el form con errores')
        self.assertFalse(CashMovement.objects.exists())

    def test_listado_filtra_por_tipo(self):
        CashMovement.objects.create(
            oficina=self.oficina, fecha=date.today(), tipo='ingreso',
            categoria='convenio', monto=Decimal('100.00'), registrado_por=self.admin,
        )
        CashMovement.objects.create(
            oficina=self.oficina, fecha=date.today(), tipo='egreso',
            categoria='renta', monto=Decimal('50.00'), registrado_por=self.admin,
        )
        resp = self.client.get(reverse('cashmovement_list'), {'tipo': 'egreso'})
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode('utf-8', errors='replace')
        self.assertIn('Renta', body)
        # Los totales del listado filtrado se calculan
        self.assertIn('$50', body)

    def test_editar_movimiento(self):
        m = CashMovement.objects.create(
            oficina=self.oficina, fecha=date.today(), tipo='ingreso',
            categoria='convenio', monto=Decimal('100.00'), registrado_por=self.admin,
        )
        resp = self.client.post(reverse('cashmovement_update', args=[m.pk]), {
            'oficina': self.oficina.pk, 'fecha': '2026-02-01',
            'tipo': 'ingreso', 'categoria': 'anticipo', 'monto': '250.00',
            'descripcion': 'Actualizado',
        })
        self.assertEqual(resp.status_code, 302)
        m.refresh_from_db()
        self.assertEqual(m.monto, Decimal('250.00'))
        self.assertEqual(m.categoria, 'anticipo')

    def test_eliminar_movimiento(self):
        m = CashMovement.objects.create(
            oficina=self.oficina, fecha=date.today(), tipo='ingreso',
            categoria='convenio', monto=Decimal('100.00'), registrado_por=self.admin,
        )
        resp = self.client.post(reverse('cashmovement_delete', args=[m.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(CashMovement.objects.filter(pk=m.pk).exists())


class PartnerViewTests(BaseFinanzasTestCase):
    def test_crear_y_listar_socio(self):
        resp = self.client.post(reverse('partner_create'), {
            'nombre': 'Hans Müller', 'porcentaje_participacion': '50.00',
            'telefono': '6641234567', 'email': 'hans@despacho.mx', 'activo': 'on',
        })
        self.assertEqual(resp.status_code, 302)
        partner = Partner.objects.get(nombre='Hans Müller')
        self.assertEqual(partner.porcentaje_participacion, Decimal('50.00'))

        resp = self.client.get(reverse('partner_list'), {'q': 'Hans'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Hans Müller')

    def test_detalle_socio_muestra_prestamos(self):
        partner = Partner.objects.create(nombre='Socio Detalle')
        otro = Partner.objects.create(nombre='Socio Otro')
        PartnerLoan.objects.create(
            socio_origen=partner, socio_destino=otro, monto=Decimal('750.00'),
            fecha=date.today(), concepto='Préstamo test', registrado_por=self.admin,
        )
        resp = self.client.get(reverse('partner_detail', args=[partner.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Préstamo test')


class WorkWeekViewTests(BaseFinanzasTestCase):
    def test_crear_semana(self):
        resp = self.client.post(reverse('workweek_create'), {
            'numero': '1', 'fecha_inicio': '2026-01-05', 'fecha_fin': '2026-01-11',
            'estado': 'abierta', 'notas': '',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(WorkWeek.objects.filter(numero=1).exists())

    def test_listado_filtra_por_estado(self):
        WorkWeek.objects.create(numero=1, fecha_inicio=date(2026, 1, 5),
                                fecha_fin=date(2026, 1, 11), estado='abierta')
        WorkWeek.objects.create(numero=2, fecha_inicio=date(2026, 1, 12),
                                fecha_fin=date(2026, 1, 18), estado='cerrada')
        resp = self.client.get(reverse('workweek_list'), {'estado': 'cerrada'})
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode('utf-8', errors='replace')
        self.assertNotIn('Semana 1', body)


class PartnerLoanViewTests(BaseFinanzasTestCase):
    def test_crear_prestamo(self):
        a = Partner.objects.create(nombre='Socio A')
        b = Partner.objects.create(nombre='Socio B')
        resp = self.client.post(reverse('partnerloan_create'), {
            'socio_origen': a.pk, 'socio_destino': b.pk,
            'monto': '1200.00', 'fecha': '2026-01-20',
            'concepto': 'Préstamo entre socios', 'estado': 'pendiente',
        })
        self.assertEqual(resp.status_code, 302)
        loan = PartnerLoan.objects.get()
        self.assertEqual(loan.monto, Decimal('1200.00'))
        self.assertEqual(loan.registrado_por, self.admin)


class AgreementViewTests(BaseFinanzasTestCase):
    def test_crear_convenio_establece_creado_por(self):
        resp = self.client.post(reverse('agreement_create'), {
            'cliente': self.cliente.pk, 'empresa': 'Empresa Contraparte SA',
            'oficina': self.oficina.pk, 'fecha': '2026-02-10',
            'monto_convenio': '80000.00', 'estado': 'firmado',
            'responsable': self.admin.pk, 'notas': '',
        })
        self.assertEqual(resp.status_code, 302)
        convenio = Agreement.objects.get(cliente=self.cliente)
        self.assertEqual(convenio.monto_convenio, Decimal('80000.00'))
        self.assertEqual(convenio.creado_por, self.admin)

    def test_detalle_muestra_honorarios(self):
        convenio = Agreement.objects.create(
            cliente=self.cliente, oficina=self.oficina, fecha=date.today(),
            monto_convenio=Decimal('50000.00'), responsable=self.admin,
            creado_por=self.admin,
        )
        Honorario.objects.create(convenio=convenio, porcentaje=Decimal('30.00'),
                                 registrado_por=self.admin)
        convenio.refresh_from_db()
        resp = self.client.get(reverse('agreement_detail', args=[convenio.pk]))
        self.assertEqual(resp.status_code, 200)
        # El template usa floatformat:2 (sin intcomma) → '$15000.00'
        self.assertContains(resp, '$15000.00')  # 30% de 50000

    def test_crear_honorario_desde_convenio(self):
        convenio = Agreement.objects.create(
            cliente=self.cliente, oficina=self.oficina, fecha=date.today(),
            monto_convenio=Decimal('50000.00'), responsable=self.admin,
            creado_por=self.admin,
        )
        # '30.0' es el valor que envía el <select> (las choices son floats 30.00)
        resp = self.client.post(reverse('honorario_create'), {
            'convenio': convenio.pk, 'porcentaje': '30.0',
            'estado': 'pendiente', 'fecha_estimada': '', 'fecha_pagado': '', 'notas': '',
        })
        self.assertEqual(resp.status_code, 302)
        convenio.refresh_from_db()
        self.assertEqual(convenio.honorarios, Decimal('15000.00'))


class ProfitDistributionViewTests(BaseFinanzasTestCase):
    def setUp(self):
        super().setUp()
        Partner.objects.create(nombre='Socio 1', porcentaje_participacion=Decimal('100.00'))

    def test_crear_distribucion_genera_participaciones(self):
        # El form de distribución solo acepta convenios firmados/pagados/parciales
        convenio = Agreement.objects.create(
            cliente=self.cliente, oficina=self.oficina, fecha=date.today(),
            monto_convenio=Decimal('50000.00'), estado='firmado',
            responsable=self.admin, creado_por=self.admin,
        )
        resp = self.client.post(reverse('profitdistribution_create'), {
            'convenio': convenio.pk, 'fecha': '2026-03-01',
            'descripcion': 'Distribución test', 'retenciones': '0.00',
            'gastos_relacionados': '0.00', 'estado': 'borrador', 'notas': '',
        })
        self.assertEqual(resp.status_code, 302)
        dist = ProfitDistribution.objects.get(convenio=convenio)
        self.assertEqual(dist.utilidad_neta, Decimal('50000.00'))
        self.assertEqual(dist.partner_profits.count(), 1)
        pp = dist.partner_profits.get()
        self.assertEqual(pp.monto, Decimal('50000.00'))

    def test_confirmar_distribucion_solo_admin_superadmin(self):
        """Un rol 'finanzas' puede ver pero NO confirmar distribuciones."""
        convenio = Agreement.objects.create(
            cliente=self.cliente, oficina=self.oficina, fecha=date.today(),
            monto_convenio=Decimal('30000.00'), responsable=self.admin,
            creado_por=self.admin,
        )
        dist = ProfitDistribution.objects.create(
            convenio=convenio, fecha=date.today(), creado_por=self.admin,
        )
        from finanzas.views import _generar_participaciones
        _generar_participaciones(dist)

        # Usuario finanzas no puede confirmar
        user_fin = _usuario('finanzas_confirma', 'finanzas')
        self.client.login(username='finanzas_confirma', password='clave123')
        resp = self.client.post(reverse('profitdistribution_confirmar', args=[dist.pk]))
        self.assertEqual(resp.status_code, 302)
        dist.refresh_from_db()
        self.assertEqual(dist.estado, 'borrador', 'Un usuario finanzas no puede confirmar')

        # El admin sí
        self.client.login(username='admin_finanzas', password='clave123')
        resp = self.client.post(reverse('profitdistribution_confirmar', args=[dist.pk]))
        self.assertEqual(resp.status_code, 302)
        dist.refresh_from_db()
        self.assertEqual(dist.estado, 'confirmada')
        # El resumen del socio acumuló la utilidad
        resumen = PartnerUtilitySummary.objects.get()
        self.assertGreater(resumen.utilidad_generada, 0)


class ReporteConveniosViewTests(BaseFinanzasTestCase):
    def test_reporte_mensual_muestra_totales(self):
        Agreement.objects.create(
            cliente=self.cliente, oficina=self.oficina, fecha=date.today(),
            monto_convenio=Decimal('10000.00'), responsable=self.admin,
            creado_por=self.admin,
        )
        resp = self.client.get(reverse('reporte_convenios'))
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode('utf-8', errors='replace')
        self.assertIn('$10000', body)  # floatformat sin intcomma en el reporte

    def test_reporte_anual_genera_evolucion(self):
        hoy = timezone.now().date()
        Agreement.objects.create(
            cliente=self.cliente, oficina=self.oficina, fecha=hoy,
            monto_convenio=Decimal('2000.00'), responsable=self.admin,
            creado_por=self.admin,
        )
        resp = self.client.get(reverse('reporte_convenios'), {'periodo': 'anual'})
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode('utf-8', errors='replace')
        self.assertIn('Evolución', body)

    def test_reporte_semanal_semana_actual(self):
        resp = self.client.get(reverse('reporte_convenios'), {'periodo': 'semanal'})
        self.assertEqual(resp.status_code, 200)


class DashboardFinancieroViewTests(BaseFinanzasTestCase):
    def test_dashboard_muestra_totales(self):
        SettlementPayment.objects.create(
            fecha=date.today(), cliente=self.cliente, expediente=self.expediente,
            monto=Decimal('1000.00'), forma_pago='efectivo',
            oficina=self.oficina, registrado_por=self.admin,
        )
        Expense.objects.create(
            fecha=date.today(), categoria='renta', monto=Decimal('400.00'),
            oficina=self.oficina, registrado_por=self.admin,
        )
        resp = self.client.get(reverse('dashboard_financiero'))
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode('utf-8', errors='replace')
        # El template usa floatformat:0|intcomma con locale es-MX → separador de miles = '.'
        self.assertIn('$1.000', body)   # ingresos
        self.assertIn('$400', body)     # gastos
        self.assertIn('$600', body)     # utilidad

    def test_dashboard_filtro_por_oficina(self):
        """Al filtrar por oficina, los totales GLOBALES solo cuentan esa oficina
        (la tabla 'Resumen por Oficina' siempre lista todas, por diseño)."""
        otra = Office.objects.create(nombre='Oficina B')
        SettlementPayment.objects.create(
            fecha=date.today(), cliente=self.cliente, expediente=self.expediente,
            monto=Decimal('5000.00'), forma_pago='transferencia',
            oficina=otra, registrado_por=self.admin,
        )
        # Sin filtro: la oficina B aporta 5000 al total global
        resp = self.client.get(reverse('dashboard_financiero'))
        body = resp.content.decode('utf-8', errors='replace')
        self.assertIn('$5.000', body)

        # Con filtro en self.oficina (sin pagos): el total global es 0
        resp = self.client.get(reverse('dashboard_financiero'), {'oficina': self.oficina.pk})
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode('utf-8', errors='replace')
        # La card de Ingresos global debe quedar en 0 con el filtro
        self.assertIn('>$0</div>', body, 'El total global debe excluir pagos de otras oficinas')
