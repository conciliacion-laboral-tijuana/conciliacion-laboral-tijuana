import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
Path('work').mkdir(exist_ok=True)
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings_test'
import django
django.setup()

from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings
from django.test.utils import get_runner
from playwright.sync_api import sync_playwright
from expedientes.models import HojaPrestaciones, Cliente, Expediente
from datetime import date
from decimal import Decimal


class ConstructorNavegador(StaticLiveServerTestCase):
    def test_captura_calculo_aprobacion_y_edicion(self):
        user = User.objects.create_user('navegador_hoja', password='test-only')
        user.profile.rol = 'abogada'
        user.profile.save()
        cliente = Cliente.objects.create(nombre='Cliente navegador', curp='AAAA900101HBCBBB01',
            salario=Decimal('18000'), fecha_ingreso=date(2024,1,1), fecha_salida=date(2026,7,1),
            puesto='Operador', empresa='Empresa ejemplo', imss_confirmado=True, tuvo_imss=True)
        exp = Expediente.objects.create(cliente=cliente, asesor=user, tipo_despido='injustificado')
        self.client.force_login(user)
        errors = []
        with sync_playwright() as p:
            executable = '/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None
            browser = p.chromium.launch(executable_path=executable, headless=True, args=['--no-sandbox'])
            context = browser.new_context(viewport={'width':1280,'height':900})
            context.add_cookies([{'name':settings.SESSION_COOKIE_NAME, 'value':self.client.cookies[settings.SESSION_COOKIE_NAME].value, 'url': self.live_server_url}])
            page = context.new_page()
            # External styling does not participate in this local functional test.
            def asset(route):
                if route.request.url.startswith(self.live_server_url):
                    route.continue_()
                elif 'tailwindcss' in route.request.url:
                    route.fulfill(status=200, body='window.tailwind={};', content_type='application/javascript')
                else:
                    route.abort()
            page.route('**/*', asset)
            on_page_error = lambda err: errors.append(str(err))
            page.on('pageerror', on_page_error)
            page.goto(self.live_server_url + f'/expedientes/{exp.pk}/demanda/asistente/')
            page.wait_for_function("document.getElementById('demanda-preview-status').textContent !== 'Cargando vista previa…'")
            page.locator('[data-acordeon-toggle="prestaciones"]').click()
            page.locator('#id_prestaciones-salario_integrado').fill('650')
            page.locator('#id_prestaciones-extras_estado').select_option('no')
            page.locator('#id_prestaciones-datos_confirmados').check()
            for row in page.locator('[id^="id_vacaciones-"][id$="-confirmado"]').all():
                row.check()
            page.locator('#id_vacaciones-0-disfrutados').fill('12')
            page.locator('#id_vacaciones-0-prima_pagada').fill('1800')
            # Dynamic row construction, deletion and management counters.
            page.locator('#agregar-semana').click()
            page.locator('#id_semanas-0-semana').fill('2026-06-08')
            page.locator('#id_semanas-0-salario_diario').fill('600')
            for dia in ('lunes','martes','miercoles','jueves'):
                page.locator('#id_semanas-0-' + dia).fill('3')
            page.locator('button[name="accion"][value="calcular"]').click()
            page.wait_for_load_state('domcontentloaded')
            try:
                page.wait_for_selector('button[value="aprobar"]', timeout=10000)
            except Exception:
                Path('work/e2e-constructor-fallo.html').write_text(page.content())
                print('URL:', page.url, 'Errores JS:', errors)
                print('Errores visibles:', page.locator('.errorlist').all_text_contents())
                print('Validez:', page.evaluate("Array.from(document.getElementById('acordeonForm').elements).filter(e=>e.willValidate && !e.validity.valid).map(e=>[e.name,e.value,e.validationMessage])"))
                print('Estado:', page.locator('#demanda-preview-status').text_content())
                print('Hoja:', list(HojaPrestaciones.objects.values('datos','huella')))
                raise
            hoja = HojaPrestaciones.objects.get(expediente=exp)
            self.assertTrue(hoja.resultado)
            self.assertIsNone(hoja.aprobado_en)
            self.assertEqual(page.locator('input[name="revision_calculo"]').input_value(), hoja.huella)
            page.locator('button[value="aprobar"]').click()
            page.wait_for_load_state('domcontentloaded')
            page.wait_for_selector('text=Importes aprobados para la demanda.')
            hoja.refresh_from_db()
            self.assertIsNotNone(hoja.aprobado_en)
            self.assertFalse(errors, errors)
            # The external Quill editor is outside this offline constructor test.
            page.remove_listener('pageerror', on_page_error)
            page.locator('button[value="finalizar"]').click()
            page.wait_for_url('**/demanda/')
            self.assertIn('dado de alta ante el IMSS', page.content())
            self.assertIn('Desglose de prestaciones por periodos', page.content())
            browser.close()


if __name__ == '__main__':
    result = get_runner(settings)(interactive=False, verbosity=1).run_tests(['prueba_constructor_navegador.ConstructorNavegador'])
    raise SystemExit(bool(result))
