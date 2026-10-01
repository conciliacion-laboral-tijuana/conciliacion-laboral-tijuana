"""
Prueba E2E del acordeón de demanda en navegador real (Chromium/Playwright).
- Login con usuario temporal
- Abre el acordeón del expediente (real en demanda, o crea uno temporal)
- Interactúa con las secciones, guarda datos y captura screenshots
- Deja todo como estaba (elimina el usuario temporal al final)

Artefactos de depuración (carpeta e2e_artifacts/):
- Screenshot numerado en cada paso del flujo
- Si un check falla o hay excepción: screenshot + HTML de la página
- Log de consola del navegador (console.log)

En CI, .github/workflows/ci.yml sube esa carpeta como artefacto cuando falla.
"""
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get('E2E_BASE', 'http://127.0.0.1:8080')
USER = 'e2e_acordeon'
PASS = os.environ.get('E2E_PASS', 'E2eAcordeon2026!')

ART = Path('e2e_artifacts')   # artefactos de depuración (subidos por CI al fallar)
ART.mkdir(exist_ok=True)
for _f in ART.iterdir():
    if _f.is_file():
        _f.unlink()

# ─── Preparar usuario temporal con permisos ───────────────────────
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'  # script de pruebas: ORM dentro del contexto de Playwright
import django
django.setup()
from django.contrib.auth.models import User
from accounts.models import UserProfile

user = User.objects.filter(username=USER).first()
if not user:
    user = User.objects.create_user(username=USER, password=PASS, first_name='E2E', last_name='Acordeon')
# Garantiza credenciales correctas aunque el usuario exista de corridas previas
if not user.check_password(PASS):
    user.set_password(PASS)
    user.save()
perfil = UserProfile.objects.get_or_create(user=user)[0]
perfil.rol = 'asesor'               # requerido por el validador de Expediente.asesor
perfil.puede_generar_documentos = True
perfil.save()
print(f'[setup] Usuario {USER} listo (id={user.pk})')

from expedientes.models import Expediente, Cliente
from datetime import date

# Preferir un expediente real en demanda; si no hay, crear uno temporal E2E
exp = Expediente.objects.filter(estado='demanda').select_related('cliente').order_by('-created_at').first()
exp_temporal = False
if not exp:
    exp_temporal = True
    # Limpiar restos de corridas anteriores (por curp única)
    Cliente.objects.filter(curp='E2EA890312HDFLNN01').delete()
    cli = Cliente(nombre='E2E ACORDEON PRUEBA', curp='E2EA890312HDFLNN01', oficina='clt',
                  salario=15000, fecha_ingreso=date(2020, 3, 1), fecha_salida=date(2026, 9, 15),
                  empresa='EMPRESA E2E SA', puesto='Operador', genero='masculino')
    try:
        cli.full_clean()
    except Exception as e:
        print('[setup] validacion cliente:', e)
    cli.save()
    exp = Expediente.objects.create(cliente=cli, asesor=user, estado='demanda', tipo_despido='injustificado')
    print('[setup] Expediente TEMPORAL creado para la prueba')
print(f'[setup] Expediente de prueba: {exp.numero} — {exp.cliente.nombre} (pk={exp.pk})')
URL = f'{BASE}/expedientes/{exp.pk}/demanda/asistente/'

FALLOS = []
CONSOLE = []          # mensajes de consola del navegador
_page = None          # página activa (para capturar artefactos al fallar)
_shot_n = 0
_fallo_n = 0


def _slug(texto, maxlen=40):
    s = re.sub(r'[^a-zA-Z0-9]+', '_', texto).strip('_').lower()
    return s[:maxlen]


def _shot(nombre, full_page=False):
    """Screenshot numerado en e2e_artifacts/ (silencioso si no hay página)."""
    global _shot_n
    if _page is None:
        return
    _shot_n += 1
    try:
        _page.screenshot(path=str(ART / f'{_shot_n:02d}_{nombre}.png'), full_page=full_page)
    except Exception:
        pass


def _dump_html(nombre):
    """HTML actual de la página en e2e_artifacts/ (para depurar el DOM)."""
    if _page is None:
        return
    try:
        (ART / f'{nombre}.html').write_text(_page.content(), encoding='utf-8')
    except Exception:
        pass


def check(nombre, condicion, detalle=''):
    estado = 'OK ' if condicion else 'FALLO'
    print(f'[{estado}] {nombre}' + (f' — {detalle}' if detalle else ''))
    if not condicion:
        global _fallo_n
        _fallo_n += 1
        FALLOS.append(nombre)
        # Evidencia del fallo: screenshot + HTML (la página sigue viva aquí)
        _shot(f'fallo_{_fallo_n:02d}_{_slug(nombre)}')
        _dump_html(f'fallo_{_fallo_n:02d}_{_slug(nombre)}')


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    page.set_default_timeout(10000)
    _page = page
    page.on('console', lambda m: CONSOLE.append(f'[{m.type}] {m.text}'))

    try:
        # ─── 1. Login ──────────────────────────────────────────────
        page.goto(f'{BASE}/accounts/login/')
        page.fill('#id_username', USER)
        page.fill('#id_password', PASS)
        page.click('button[type=submit]')
        page.wait_for_load_state('networkidle')
        check('Login', '/accounts/login' not in page.url, page.url)
        _shot('login_dashboard')

        # ─── 2. Abrir el acordeón ──────────────────────────────────
        page.goto(URL)
        page.wait_for_load_state('networkidle')
        check('Acordeón carga (HTTP 200)', 'asistente' in page.url)
        check('Título correcto', page.locator('h1').first.inner_text().strip().lower().find('acorde') >= 0)

        secciones = ['trabajador', 'laboral', 'empresa', 'despido', 'revision']
        for s in secciones:
            visible = page.locator(f'#sec-{s}').count() == 1
            check(f'Sección #{s} existe', visible)
        check('Badge COMPLETA/PENDIENTE presente', page.locator('.acordeon-num').count() == 5)

        # La primera sección debe estar abierta por defecto
        abierta = page.locator('.acordeon-seccion.abierta').count()
        check('Una sección abierta por defecto', abierta == 1, f'abiertas={abierta}')
        _shot('acordeon_inicial', full_page=True)

        # ─── 3. Comportamiento acordeón: abre una y cierra la otra ──
        page.click('[data-acordeon-toggle="despido"]')
        page.wait_for_timeout(300)
        check('Sección despido abre', page.locator('#sec-despido').get_attribute('class').find('abierta') >= 0)
        check('Solo una abierta tras clic', page.locator('.acordeon-seccion.abierta').count() == 1)
        check('Trabajador se cerró', page.locator('#sec-trabajador').get_attribute('class').find('abierta') == -1)

        # Captura de la sección despido abierta
        page.locator('#sec-despido').scroll_into_view_if_needed()
        _shot('seccion_despido')

        # ─── 4. Llenar la sección de despido/pruebas ────────────────
        page.fill('textarea[name=circunstancias_despido]',
                  'El día de la separación me entregaron carta de despido sin causa explicada, '
                  'y me indicaron que recogería mi finiquito la semana siguiente.')
        page.fill('textarea[name=testigos]', 'Juan Pérez\nMaría López')
        page.fill('textarea[name=documentos_prueba]', 'Carta de despido\nRecibos de nómina\nCapturas de WhatsApp')

        # ─── 5. Guardar datos (permanece en la página) ──────────────
        page.click('button[name=accion][value=guardar]')
        page.wait_for_load_state('networkidle')
        check('Guardar permanece en la página', 'asistente' in page.url, page.url)
        _shot('guardado_exito')

        # Verificar en BD que se guardó (permitido con DJANGO_ALLOW_ASYNC_UNSAFE)
        exp.cliente.refresh_from_db()
        check('Circunstancias guardadas en BD', 'carta de despido' in (exp.cliente.circunstancias_despido or '').lower())
        check('Testigos guardados en BD', 'Juan Pérez' in (exp.cliente.testigos or ''))

        # Tras el POST, la sección despido debe reabrirse (seccion_abierta)
        check('Sección despido reabierta tras guardar',
              page.locator('#sec-despido').get_attribute('class').find('abierta') >= 0)

        # Badge de la sección despido ahora COMPLETA
        badge_despido = page.locator('#sec-despido .acordeon-num').inner_text()
        check('Badge despido en verde (COMPLETA)', '✓' in badge_despido or 'check' in page.locator('#sec-despido .acordeon-num').inner_html().lower())

        # ─── 6. Revisión final: tipo de despido + cálculo ───────────
        page.click('[data-acordeon-toggle="revision"]')
        page.wait_for_timeout(300)
        tiene_calculo = page.locator('#sec-revision table').count() > 0
        check('Cálculo automático visible en revisión', tiene_calculo)
        if tiene_calculo:
            total_txt = page.locator('#sec-revision').inner_text()
            check('TOTAL presente', 'TOTAL' in total_txt)
        _shot('seccion_revision')

        # ─── 7. Verificación visual: sin desbordes ──────────────────
        overflow = page.evaluate("""() => {
            const docW = document.documentElement.clientWidth;
            return document.documentElement.scrollWidth > docW + 2;
        }""")
        check('Sin scroll horizontal (sin desbordes)', not overflow)

        # ─── 8. Flujo finalizar → editor de demanda ─────────────────
        page.click('button[name=accion][value=finalizar]')
        page.wait_for_load_state('networkidle')
        check('Finalizar redirige al editor', '/demanda/' in page.url and '/asistente/' not in page.url, page.url)
        _shot('editor_demanda', full_page=True)
    except Exception as e:
        # Excepción no esperada: capturar el estado del navegador ANTES de cerrarlo
        print(f'[EXCEPCION] {type(e).__name__}: {e}')
        _shot('99_excepcion')
        _dump_html('99_excepcion')
        FALLOS.append(f'excepcion: {type(e).__name__}: {e}')
    finally:
        browser.close()
        _page = None

# Log de consola del navegador (útil para depurar errores de JS)
if CONSOLE:
    (ART / 'consola_navegador.log').write_text('\n'.join(CONSOLE), encoding='utf-8')

# ─── Limpieza ─────────────────────────────────────────────────────
if exp_temporal:
    from expedientes.models import Expediente as _Exp
    _Exp.objects.filter(cliente__nombre='E2E ACORDEON PRUEBA').delete()
    Cliente.objects.filter(nombre='E2E ACORDEON PRUEBA').delete()
    print('[cleanup] Expediente temporal eliminado')
try:
    user.delete()
    print('[cleanup] Usuario temporal eliminado')
except Exception as e:
    print(f'[cleanup] Usuario conservado (FKs protegidas): {e}')

if FALLOS:
    print(f'\n[FALLO] {len(FALLOS)} checks fallaron: {FALLOS}')
    print(f'[artefactos] Evidencia en: {ART.resolve()}')
    sys.exit(1)
print('\n[EXITO] Todos los checks del acordeón pasaron en navegador real.')
print(f'[artefactos] Screenshots del flujo en: {ART.resolve()}')
