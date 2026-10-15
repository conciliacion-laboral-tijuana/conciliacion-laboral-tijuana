"""
Prueba E2E del ESPACIO DE TRABAJO DE LA DEMANDA en navegador real
(Chromium/Playwright).

Antes recorría el «acordeón de demanda»: siete bloques en una sola página, un
iframe de vista previa y un solo formulario. Ahora recorre los tres espacios
(datos · estrategia · documento), comprueba que el semáforo de cada bloque
refleja lo capturado, que el autoguardado funciona y que un hueco del documento
lleva al campo que lo completa.

- Login con usuario temporal
- Crea SIEMPRE un expediente temporal: la prueba captura domicilio, modalidad
  de la separación y confirmación del IMSS, así que no puede tocar un caso real
- Captura en los tres espacios, guarda y captura screenshots
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

# Expediente TEMPORAL siempre: la prueba captura datos (domicilio, modalidad,
# IMSS) y no puede permitirse modificar un expediente real de la base.
exp_temporal = True
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

        # ─── 2. Espacio de datos ───────────────────────────────────
        page.goto(URL)
        page.wait_for_load_state('networkidle')
        check('Espacio de trabajo carga (HTTP 200)', 'asistente' in page.url)
        check('Los tres espacios se anuncian', page.locator('.dem-tab').count() == 3)
        check('Hay un solo formulario', page.locator('form#demandaForm').count() == 1)
        for bloque in ('trabajador', 'laboral', 'empresa', 'representacion'):
            check(f'Bloque #{bloque} en Datos', page.locator(f'#sec-{bloque}').count() == 1)
        check('La separación NO está en Datos', page.locator('#sec-despido').count() == 0)
        check('El domicilio del actor se captura aquí',
              page.locator('#id_direccion_calle').count() == 1)
        # El semáforo tiene que ser real: con el nombre y la CURP capturados pero
        # SIN domicilio, el bloque del actor no puede decir «Completo». El
        # semáforo anterior pintaba verde la sección con un solo campo lleno.
        check('El semáforo del actor no miente con el domicilio vacío',
              'Completo' not in page.locator('#sec-trabajador .bloque-estado').inner_text(),
              page.locator('#sec-trabajador .bloque-estado').inner_text())
        _shot('espacio_datos', full_page=True)

        # ─── 3. Autoguardado y estado en vivo ──────────────────────
        page.fill('#id_direccion_calle', 'Calle E2E 123')
        page.wait_for_function(
            "document.getElementById('dem-guardado').textContent.indexOf('guardado') >= 0",
            timeout=8000)
        exp.cliente.refresh_from_db()
        check('El autoguardado persiste sin pulsar Guardar',
              exp.cliente.direccion_calle == 'Calle E2E 123',
              repr(exp.cliente.direccion_calle))
        try:
            page.wait_for_function(
                "document.querySelector('#sec-trabajador .bloque-estado')"
                ".textContent.indexOf('Completo') >= 0",
                timeout=8000)
            completo = True
        except Exception:
            completo = False
        check('Al capturar el domicilio el bloque queda completo', completo,
              page.locator('#sec-trabajador .bloque-estado').inner_text())

        # ─── 4. Confirmación del IMSS (bloque propio, en Estrategia) ─
        page.click('.dem-tab[data-espacio="estrategia"]')
        page.wait_for_load_state('networkidle')
        check('La pestaña lleva a Estrategia', 'espacio=estrategia' in page.url, page.url)
        for bloque in ('despido', 'imss', 'prestaciones'):
            check(f'Bloque #{bloque} en Estrategia', page.locator(f'#sec-{bloque}').count() == 1)
        check('La hoja de prestaciones está plegada pero presente',
              page.locator('#sec-prestaciones #agregar-semana').count() == 1)
        check('El semáforo del IMSS arranca en falta',
              'Falta' in page.locator('#sec-imss .bloque-estado').inner_text())
        page.locator('#id_imss_confirmado').check()
        page.locator('#id_tuvo_imss').check()
        page.click('button[name=accion][value=guardar]')
        page.wait_for_load_state('networkidle')
        check('Guardar permanece en Estrategia', 'espacio=estrategia' in page.url, page.url)
        page.wait_for_function(
            "document.querySelector('#sec-imss .bloque-estado').textContent.indexOf('Completo') >= 0",
            timeout=8000)
        _shot('espacio_estrategia', full_page=True)

        # ─── 5. La separación: modalidad y hechos ──────────────────
        page.locator('#sec-despido input[name="modalidad_despido"][value="verbal"]').check()
        page.fill('textarea[name=circunstancias_despido]',
                  'El día de la separación me entregaron carta de despido sin causa explicada, '
                  'y me indicaron que recogería mi finiquito la semana siguiente.')
        page.fill('textarea[name=testigos]', 'Juan Pérez\nMaría López')
        page.fill('textarea[name=documentos_prueba]', 'Carta de despido\nRecibos de nómina\nCapturas de WhatsApp')
        page.click('button[name=accion][value=guardar]')
        page.wait_for_load_state('networkidle')
        exp.cliente.refresh_from_db()
        check('Circunstancias guardadas en BD',
              'carta de despido' in (exp.cliente.circunstancias_despido or '').lower())
        check('Testigos guardados en BD', 'Juan Pérez' in (exp.cliente.testigos or ''))
        check('Modalidad guardada en BD', exp.cliente.modalidad_despido == 'verbal',
              repr(exp.cliente.modalidad_despido))
        check('El bloque de la separación queda completo tras decidir',
              'Completo' in page.locator('#sec-despido .bloque-estado').inner_text(),
              page.locator('#sec-despido .bloque-estado').inner_text())

        # ─── 6. El documento: índice, huecos y coherencia ──────────
        page.click('.dem-tab[data-espacio="documento"]')
        page.wait_for_load_state('networkidle')
        check('La pestaña lleva al Documento', 'espacio=documento' in page.url, page.url)
        check('El índice lista los capítulos del escrito',
              page.locator('.indice ol li').count() >= 7,
              str(page.locator('.indice ol li').count()))
        check('El escrito se muestra capítulo por capítulo',
              page.locator('.hoja .capitulo-doc').count() >= 6)
        check('El panel de coherencia tiene avisos',
              page.locator('.aviso').count() > 0)
        huecos = page.locator('a.hueco-doc')
        check('Los datos que faltan son huecos enlazados', huecos.count() > 0,
              str(huecos.count()))

        # El hueco lleva al campo que lo completa
        if huecos.count():
            href = huecos.first.get_attribute('href')
            check('El hueco apunta a un espacio y a un campo',
                  'espacio=' in href and '#' in href, href)
            huecos.first.click()
            page.wait_for_load_state('networkidle')
            destino = page.evaluate("document.activeElement ? document.activeElement.id : ''")
            check('Al llegar, el campo del hueco queda enfocado', bool(destino),
                  f'activo={destino!r} url={page.url}')
        _shot('espacio_documento', full_page=True)

        # ─── 7. Verificación visual: sin desbordes ──────────────────
        overflow = page.evaluate("""() => {
            const docW = document.documentElement.clientWidth;
            return document.documentElement.scrollWidth > docW + 2;
        }""")
        check('Sin scroll horizontal (sin desbordes)', not overflow)

        # ─── 8. Flujo finalizar → editor de demanda ─────────────────
        page.click('button[name=accion][value=finalizar]')
        page.wait_for_load_state('networkidle')
        check('Finalizar redirige al editor',
              '/demanda/' in page.url and '/asistente/' not in page.url, page.url)
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
print('\n[EXITO] Todos los checks del espacio de trabajo pasaron en navegador real.')
print(f'[artefactos] Screenshots del flujo en: {ART.resolve()}')
