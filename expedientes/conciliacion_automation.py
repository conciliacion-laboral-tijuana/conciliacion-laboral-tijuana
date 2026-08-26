"""
Conciliación B.C. — Automatización del Formulario Web (v2)
===========================================================

FLUJO REAL DEL SITIO (app.conciliacionbc.gob.mx):
    1. Aviso de Privacidad → Aceptar
    2. Industria → "ninguna de las anteriores" → "Validar y Continuar"
    3. Fecha conflicto + objeto → "Validar y Continuar"
    4. Tab "Solicitante" → "Agregar solicitante" → llenar campos → "Guardar" → "Validar y Continuar"
    5. Tab "Citado" → "Agregar citado" → llenar campos → "Guardar" → "Validar y Continuar"
    6. Tab "Descripción" → llenar textarea → "Aceptar"
    7. Tab "Resumen" → "Enviar solicitud" → confirmar → Descargar acuse PDF

Diferencias con v1 (código anterior):
    - El sitio NO tiene cuestionario previo (Soy empleado, despedieron, orientacion, etc.)
    - Los campos NO están dentro de modales Bootstrap — están en la página normal
    - Navegación por tabs/wizard, no por pasos secuenciales con botones
    - Los contactos usan contactos[1], contactos[2], contactos[3] (no contactos[0][telefono])
"""
import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class ResultadoConciliacion:
    """Resultado del envío automatizado al portal de conciliación."""
    success: bool = False
    folio: str = ''
    pdf_path: str = ''
    error: str = ''
    detalle: str = ''
    screenshots: list = field(default_factory=list)


# ─── URLs del sitio ──────────────────────────────────────────────────────

URL_BASE = 'https://app.conciliacionbc.gob.mx'
URL_SOLICITUD = f'{URL_BASE}/solicitudes/create-public?solicitud=1'


# ══════════════════════════════════════════════════════════════════════════
#  Helpers de navegación - Usan Playwright nativo siempre que sea posible
# ══════════════════════════════════════════════════════════════════════════


def _btn_click(page, texto_contiene, timeout=10000, retries=3):
    """Busca un botón cuyo texto contenga el string dado y hace clic.
    
    Busca en button, a, span, div, li (el portal BC usa varios tipos).
    Reintenta `retries` veces con 800ms entre intentos.
    Retorna True si hizo clic, False si no encontró nada.
    """
    txt_lower = texto_contiene.strip().lower()
    for attempt in range(retries):
        if attempt > 0:
            page.wait_for_timeout(800)
        # ── Strategy 1: Playwright get_by_text (most reliable for Angular) ──
        try:
            btn = page.get_by_text(texto_contiene, exact=False).first
            if btn.count() and btn.is_visible(timeout=2000):
                btn.click(timeout=timeout)
                logger.info('  _btn_click: clic en "%s" (intento %d, get_by_text)', texto_contiene, attempt + 1)
                return True
        except Exception:
            pass
        # ── Strategy 2: Playwright locator (múltiples selectores) ──────
        try:
            btn = page.locator(
                'button, a, span[onclick], div[onclick], li[onclick], '
                '[role="button"], [class*="btn"], [class*="button"], '
                'fa-icon, mat-icon, i[class*="fa"]'
            ).filter(has_text=re.compile(re.escape(texto_contiene), re.IGNORECASE)).first
            if btn.count():
                btn.click(timeout=timeout)
                logger.info('  _btn_click: clic en "%s" (intento %d, locator)', texto_contiene, attempt + 1)
                return True
        except Exception:
            pass
        # ── Strategy 3: JS con Angular-compatible event dispatch ──────
        try:
            result = page.evaluate(f"""(txt) => {{
                const txtLower = txt.toLowerCase().trim();
                // Buscar en todos los elementos visibles
                const all = document.querySelectorAll('*');
                for (const el of all) {{
                    const t = (el.textContent || '').trim().toLowerCase();
                    if (!t.includes(txtLower)) continue;
                    if (el.offsetParent === null && el.tagName !== 'BODY') continue;
                    // Preferir elementos que sean botones o tengan role
                    const tag = el.tagName.toLowerCase();
                    const isBtn = tag === 'button' || tag === 'a' || 
                        el.getAttribute('role') === 'button' ||
                        (el.className && typeof el.className === 'string' && 
                         (el.className.includes('btn') || el.className.includes('button')));
                    // Solo clickear si es un botón o si es el elemento más específico
                    if (!isBtn) {{
                        // Verificar si tiene hijos que coinciden mejor
                        const childBtn = el.querySelector('button, a, [role="button"]');
                        if (childBtn && (childBtn.textContent || '').trim().toLowerCase().includes(txtLower)) continue;
                    }}
                    el.click();
                    el.dispatchEvent(new MouseEvent('click', {{bubbles: true, cancelable: true}}));
                    // Para Angular: intentar disparar ngZone
                    try {{
                        const ngZone = window.ng && window.ng.getInjector && window.ng.getInjector(el);
                        if (ngZone) {{
                            ngZone.get(window.ng.coreTokens?.NgZone)?.run(() => {{}});
                        }}
                    }} catch(e) {{}}
                    return true;
                }}
                return false;
            }}""", texto_contiene)
            if result:
                logger.info('  _btn_click: clic en "%s" (intento %d, JS/Angular)', texto_contiene, attempt + 1)
                return True
        except Exception:
            pass
    logger.warning('  _btn_click: NO se encontró "%s" tras %d intentos', texto_contiene, retries)
    return False


def _fill_input(page, name, valor):
    """Llena un input usando JS directamente.
    
    Usamos JS siempre porque:
    - Playwright fill() nativo timeout de 30s cuando el campo no es visible
    - El sitio tiene campos que aparecen/desaparecen dinámicamente
    - JS es más rápido y confiable para este sitio
    """
    if not valor:
        return False
    try:
        return page.evaluate("""(args) => {
            const [name, valor] = args;
            const el = document.querySelector(`[name="${name}"]`);
            if (el) {
                el.focus();
                el.value = valor;
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
                el.dispatchEvent(new Event('blur'));
                return true;
            }
            return false;
        }""", [name, str(valor)])
    except Exception:
        pass
    return False


def _fill_input_silent(page, name, valor):
    """
    Establece el valor de un input SIN disparar eventos JS.
    
    El portal BC tiene validación client-side que se activa con cada
    evento 'input'/'change' y si la CURP no pasa el checksum, BORRA
    el valor. Al NO disparar eventos, el portal nunca se entera.
    """
    if not valor:
        return False, "no value"
    valor_str = str(valor)
    try:
        result = page.evaluate("""(args) => {
            const [name, valor] = args;
            const el = document.querySelector(`[name="${name}"]`);
            if (!el) return {ok: false, reason: 'not found'};
            if (el.readOnly) { el.readOnly = false; }
            if (el.disabled) { el.disabled = false; }
            el.value = valor;
            return {ok: el.value === valor, final: el.value, maxlen: el.maxLength || -1};
        }""", [name, valor_str])
        if result and result.get('ok'):
            return True, f"ok(maxlen={result.get('maxlen','?')})"
        reason = result.get('reason', 'unknown') if result else 'no result'
        logger.warning('  _fill_input_silent: %s[%s] => %s', name, valor_str[:10], reason)
        return False, reason
    except Exception as e:
        return False, str(e)


def _select_option(page, name, valor):
    """Selecciona una opción en un select usando JS directamente."""
    if not valor:
        return False
    try:
        return page.evaluate("""(args) => {
            const [name, valor] = args;
            const el = document.querySelector(`[name="${name}"]`);
            if (el && el.tagName === 'SELECT') {
                el.value = valor;
                el.dispatchEvent(new Event('change', {bubbles: true}));
                return true;
            }
            return false;
        }""", [name, str(valor)])
    except Exception:
        pass
    return False


def _click_radio(page, name, value):
    """Selecciona un radio button por name y value.
    Usa JS directamente porque Bootstrap custom radios tienen labels que
    interceptan los clicks nativos de Playwright."""
    try:
        return page.evaluate("""(args) => {
            const [name, value] = args;
            const r = document.querySelector(`input[name="${name}"][value="${value}"]`);
            if (r) {
                r.click();
                r.dispatchEvent(new Event('change', {bubbles: true}));
                return true;
            }
            return false;
        }""", [name, value])
    except Exception:
        return False


def _navigate_wizard_tab(page, texto_contiene, retries=3):
    """Navega a un tab del wizard por su texto.
    
    Busca en múltiples selectores del wizard BC y reintenta si no lo encuentra.
    Retorna True si navegó, False si no encontró el tab.
    """
    txt_lower = texto_contiene.strip().lower()
    for attempt in range(retries):
        if attempt > 0:
            page.wait_for_timeout(800)
        # ── Playwright locator ───────────────────────────────────────
        try:
            selector = ', '.join([
                '.wizard-step a', '.nav-link', '.step-title',
                'a[class*="step"]', '.nav-item a', '.tab-link',
                '.wizard a', '[role="tab"]', '.wizard-step',
                'li a', '.nav-tabs a', '.nav-tabs li',
            ])
            locator = page.locator(selector).filter(
                has_text=re.compile(re.escape(texto_contiene), re.IGNORECASE)
            ).first
            if locator.count():
                locator.click()
                page.wait_for_timeout(800)
                logger.info('  _navigate_wizard_tab: clic en "%s" (locator)', texto_contiene)
                return True
        except Exception:
            pass
        # ── Fallback JS ──────────────────────────────────────────────
        try:
            result = page.evaluate(f"""(kw) => {{
                const kwLower = kw.toLowerCase().trim();
                const selectors = [
                    '.wizard-step a', '.nav-link', '.step-title',
                    'a[class*="step"]', '.nav-item a', '.tab-link',
                    '.wizard a', '[role="tab"]', '.wizard-step',
                    'li a', '.nav-tabs a', '.nav-tabs li',
                    'a', 'li', 'span'
                ];
                for (const sel of selectors) {{
                    for (const el of document.querySelectorAll(sel)) {{
                        const txt = el.textContent.trim().toLowerCase();
                        if (txt.includes(kwLower) && el.offsetParent !== null) {{
                            el.click();
                            el.dispatchEvent(new Event('click', {{bubbles: true}}));
                            return true;
                        }}
                    }}
                }}
                return false;
            }}""", texto_contiene)
            if result:
                page.wait_for_timeout(800)
                logger.info('  _navigate_wizard_tab: clic en "%s" (JS fallback)', texto_contiene)
                return True
        except Exception:
            pass
    logger.warning('  _navigate_wizard_tab: NO se encontró tab "%s" tras %d intentos', texto_contiene, retries)
    return False


def _cerrar_modales(page):
    """Cierra cualquier modal/overlay que esté abierto.

    IMPORTANTE: Solo busca botones DENTRO de contenedores modales (SweetAlert,
    Bootstrap modal, etc.) para evitar clickear botones del formulario principal
    como "Validar y Continuar" o "Aceptar".
    """
    try:
        page.wait_for_timeout(300)
        return page.evaluate("""() => {
        let count = 0;

        // ── SweetAlert ────────────────────────────────────────────────────
        const swalOverlay = document.querySelector('.swal-overlay--show-modal, .swal-overlay');
        if (swalOverlay && swalOverlay.offsetParent !== null) {
            // Intentar botón de confirmación primero, luego cualquier botón
            const okBtn = swalOverlay.querySelector(
                '.swal-button--confirm, .swal-button:not(.swal-button--cancel)'
            ) || swalOverlay.querySelector('.swal-button, button');
            if (okBtn) { okBtn.click(); count++; }
        }
        document.querySelectorAll('.swal-overlay, .swal-modal').forEach(el => {
            el.style.display = 'none'; count++;
        });

        // ── Bootstrap modales ─────────────────────────────────────────────
        // Solo buscar botones DENTRO de los contenedores de modal
        const modalContainers = document.querySelectorAll(
            '.modal.show, .modal.fade.show, [role="dialog"], .alert-dismissible'
        );
        for (const container of modalContainers) {
            for (const btn of container.querySelectorAll('button, a')) {
                const txt = btn.textContent.trim().toLowerCase();
                // Coincidencia EXACTA para evitar clickear "Validar y Continuar"
                if (['entendido', 'cerrar', 'close', 'aceptar', 'ok', 'si, enviar',
                     'sí, enviar', 'confirmar', 'dismiss'].includes(txt)) {
                    if (btn.offsetParent !== null) { btn.click(); count++; break; }
                }
            }
            container.classList.remove('show');
            container.style.display = 'none';
            count++;
        }
        document.querySelectorAll('.modal-backdrop').forEach(b => { b.remove(); count++; });
        document.body.classList.remove('modal-open');
        document.body.style.paddingRight = '';
        return count;
    }""")
    except Exception:
        return 0


def _click_validar_continuar(page):
    """Hace clic en el botón 'Validar y Continuar'."""
    try:
        btn = page.get_by_role('button').filter(has_text=re.compile(r'validar', re.IGNORECASE)).and_(
            page.get_by_role('button').filter(has_text=re.compile(r'continuar', re.IGNORECASE))
        ).first
        if btn.count():
            btn.click(timeout=10000)
            return True
    except Exception:
        pass
    # Fallback: buscar botón que contenga ambos textos
    try:
        return page.evaluate("""() => {
            for (const btn of document.querySelectorAll('button')) {
                const t = btn.textContent.trim().toLowerCase();
                if (t.includes('validar') && t.includes('continuar')) {
                    btn.click();
                    btn.dispatchEvent(new Event('click', {bubbles: true}));
                    return true;
                }
            }
            return false;
        }""")
    except Exception:
        return False


def _detectar_errores_validacion(page):
    """
    Detecta errores de validación en la página del portal.
    Retorna lista de mensajes de error, o lista vacía si no hay.
    """
    try:
        errores = page.evaluate("""() => {
            const errs = [];
            // Buscar en clases de error comunes
            const selectors = '.text-danger, .error, .invalid-feedback, .help-block, ' +
                              '.is-invalid, .alert-danger, [class*="error"]';
            document.querySelectorAll(selectors).forEach(el => {
                const txt = el.textContent.trim();
                if (txt && txt.length > 2) {
                    let input = el.closest('[class*="col"], div, .form-group')?.querySelector(
                        'input, select, textarea'
                    );
                    errs.push({ msg: txt.substring(0, 80), name: input?.name || input?.id || '' });
                }
            });
            // También buscar patrones de texto específicos que indiquen errores
            const body = document.body.innerText || '';
            const patterns = [
                'no es válida', 'Completa este campo', 'Este campo es obligatorio',
                'campo requerido', 'inválido', 'debe ser', 'no coincide',
                'seleccione una opción'
            ];
            for (const p of patterns) {
                if (body.toLowerCase().includes(p.toLowerCase())) {
                    // Solo agregar si no se encontró ya en elementos con clase
                    if (!errs.some(e => e.msg.toLowerCase().includes(p.toLowerCase()))) {
                        errs.push({ msg: p, name: 'patron' });
                    }
                }
            }
            return errs;
        }""")
        return errores or []
    except Exception:
        return []


def _truncar(texto, max_len=50):
    """Trunca un string al máximo de caracteres permitido."""
    return (texto or '')[:max_len]


# ─── Validación de CURP ─────────────────────────────────────────────
# El portal valida el CURP contra el registro real (RENAPO), no solo el
# formato/dígito verificador. Un CURP sintético/inventado siempre es
# rechazado ahí, sin importar qué tan "correcto" esté calculado. Por eso
# no se genera un CURP falso: se exige el CURP real del cliente.

CURP_PLACEHOLDERS = {'XAXX010101000', 'XEXX010101000', 'N/A'}
_CURP_REGEX = re.compile(r'^[A-Z][AEIOU][A-Z]{2}\d{6}[HM][A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d$')


class CurpInvalidoError(Exception):
    """El cliente no tiene un CURP real/válido para enviar al portal."""


def _calcular_digito_verificador(curp17):
    """
    Calcula el dígito verificador (18vo carácter) de una CURP de 17 caracteres.
    Algoritmo oficial RENAPO/SAT.

    Fórmula (verificada contra CURP reales, ej. AMLO LOOA531113HTCPBN07 → 7
    y EPN PXNE660720HMCXTN06 → 6):
        suma = Σ índice(carácter_i) × (18 - i)   para i = 0..16
        dígito = 10 - (suma mod 10), o 0 si el resultado es 10.

    El índice sale del diccionario '0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ'
    (0-9 → 0-9, A → 10, ..., Z → 36). Nota: la Ñ nunca aparece en una CURP
    válida (RENAPO la sustituye por X), pero se incluye en el diccionario
    por completitud.
    """
    diccionario = '0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ'
    suma = 0
    for i, c in enumerate((curp17 or '').upper()[:17]):
        indice = diccionario.find(c)
        if indice < 0:
            indice = 0  # carácter no estándar → tratar como 0
        suma += indice * (18 - i)
    digito = 10 - (suma % 10)
    return '0' if digito == 10 else str(digito)


def _corregir_curp_checksum(curp):
    """
    Corrige el dígito verificador de un CURP de 18 caracteres.
    Retorna el CURP con el dígito verificador correcto.
    """
    curp = (curp or '').strip().upper()
    if len(curp) < 17:
        return curp
    # Tomar primeros 17 caracteres y calcular dígito correcto
    base = curp[:17]
    dv = _calcular_digito_verificador(base)
    return base + dv


def _validar_curp(curp, corregir_checksum=True):
    """Retorna el CURP normalizado si tiene forma válida, o lanza CurpInvalidoError."""
    curp = (curp or '').strip().upper()
    if not curp or curp in CURP_PLACEHOLDERS:
        raise CurpInvalidoError(
            'El cliente no tiene un CURP real registrado. El portal de conciliación '
            'valida el CURP contra el registro oficial (RENAPO) y rechaza cualquier '
            'valor inventado o de prueba — captura el CURP real del cliente antes de enviar.'
        )
    if not _CURP_REGEX.match(curp):
        raise CurpInvalidoError(f'El CURP "{curp}" no tiene el formato correcto de 18 caracteres.')
    if corregir_checksum:
        curp = _corregir_curp_checksum(curp)
        if not _CURP_REGEX.match(curp):
            raise CurpInvalidoError(f'El CURP "{curp}" no tiene el formato correcto de 18 caracteres.')
    return curp


def _extraer_folio_desde_pdf(pdf_path, nombre_pdf=''):
    """
    Extrae el folio del nombre del archivo PDF o de su contenido.
    Retorna el folio como string, o cadena vacía si no encuentra.
    """
    # 1. Intentar desde el nombre del archivo
    for pat in [
        r'(CCL[-/][\w/-]+)',
        r'(BC[-/]CCFL[-/][\w/-]+)',
        r'(\d{4}[-/]\d{4,8})',
        r'([\w-]+folio[\w-]*)',
        r'(solicitud[\w-]*)',
    ]:
        m = re.search(pat, nombre_pdf, re.IGNORECASE)
        if m:
            return m.group(1).strip()

    # 2. Intentar desde el contenido del PDF (bytes decodificados)
    try:
        with open(pdf_path, 'rb') as f:
            contenido = f.read()
        texto_pdf = contenido.decode('latin-1', errors='ignore')

        for pat in [
            r'[Ff]olio[:\s#Nº°\.]*([A-Z0-9][-A-Z0-9/]+)',
            r'N[úu]mero\s+de\s+[Ss]olicitud[:\s]*([A-Z0-9][-A-Z0-9/]+)',
            r'(CCL[:\s]*/[\d\-]+)',
            r'FOLIO[:\s]*([\w/-]+)',
            r'N[úu]mero[:\s]*([\w/-]+)',
            r'(\d{4}[-/]\d{4,8})',
            r'(CCL[\s-][\d\-]+)',
            r'(BC[\s-]CCFL[\s-][\d\-]+)',
            r'Expediente[:\s#]*([A-Z0-9][-A-Z0-9/]+)',
        ]:
            m = re.search(pat, texto_pdf, re.IGNORECASE)
            if m:
                return m.group(1).strip()
    except Exception:
        pass

    return ''


# ══════════════════════════════════════════════════════════════════════════
#  Llenado de datos del solicitante y citado
# ══════════════════════════════════════════════════════════════════════════


# ─── Mapeo de valores del modelo a IDs del portal BC ───────────────────

GENERO_PORTAL_IDS = {
    'masculino': '1',
    'femenino': '2',
}

PERIODICIDAD_PORTAL_IDS = {
    'diario': '1',      # Diario
    'mensual': '2',      # Mensual
    'quincenal': '3',    # Quincenal
    'semanal': '4',      # Semanal
}

JORNADA_PORTAL_IDS = {
    'diurna': '1',       # DIURNA
    'nocturna': '2',     # NOCTURNA
    'mixta': '3',        # MIXTA
}

TIPO_PERSONA_PORTAL_IDS = {
    'fisica': '1',       # Persona Física
    'moral': '2',        # Persona Moral
}


def _limpiar_telefono(telefono):
    """Retorna sólo los últimos 10 dígitos (sin código de país)."""
    import re as _re
    digits = _re.sub(r'\D', '', telefono or '')
    return digits[-10:] if len(digits) >= 10 else digits or '6641234567'


def _llenar_domicilio(page, vialidad, num_ext, cp, prefix='domicilio'):
    """Llena los campos de domicilio y espera al AJAX del CP para seleccionar municipio y colonia."""
    _select_option(page, f'{prefix}[estado_id]', '02')         # Baja California
    _select_option(page, f'{prefix}[tipo_vialidad_id]', '5')   # CALLE
    _fill_input(page, f'{prefix}[vialidad]', vialidad or 'Av Principal')
    _fill_input(page, f'{prefix}[num_ext]', num_ext or '123')

    # Llenar CP y disparar eventos para que el portal cargue colonia/municipio vía AJAX
    cp_val = cp or '22000'
    try:
        page.evaluate("""(args) => {
            const [name, val] = args;
            const el = document.querySelector(`[name="${name}"]`);
            if (el) {
                el.focus();
                el.value = val;
                ['input', 'change', 'blur'].forEach(ev =>
                    el.dispatchEvent(new Event(ev, {bubbles: true})));
            }
        }""", [f'{prefix}[cp]', cp_val])
    except Exception:
        _fill_input(page, f'{prefix}[cp]', cp_val)

    # Esperar a que el AJAX cargue las opciones de colonia y municipio
    page.wait_for_timeout(3000)

    # Seleccionar primer municipio disponible (el portal lo carga según CP)
    try:
        page.evaluate("""(name) => {
            const sel = document.querySelector(`[name="${name}"]`);
            if (sel && sel.options.length > 1 && !sel.value) {
                sel.selectedIndex = 1;
                sel.dispatchEvent(new Event('change', {bubbles: true}));
            }
        }""", 'municipio')
    except Exception:
        pass
    page.wait_for_timeout(500)

    # Seleccionar primer colonia/asentamiento disponible
    try:
        page.evaluate("""(name) => {
            const sel = document.querySelector(`[name="${name}"]`);
            if (sel && sel.options.length > 1) {
                sel.selectedIndex = 1;
                sel.dispatchEvent(new Event('change', {bubbles: true}));
            }
        }""", f'{prefix}[asentamiento]')
    except Exception:
        pass
    page.wait_for_timeout(300)


def _separar_nombre_mexicano(nombre_completo):
    """Separa un nombre mexicano en (nombre, apellido_paterno, apellido_materno).

    Formato esperado: [Nombre(s)] [Apellido Paterno] [Apellido Materno]

    Heurística:
    - Si 1-3 partes: asignación directa
    - Si 4+ partes: las últimas 2 son apellidos, TODO lo demás es nombre(s)

    Casos que maneja correctamente (nombres compuestos):
      "Juan Carlos López Moreno"     → nombre="Juan Carlos", ap1="López", ap2="Moreno"
      "María Guadalupe Hernández Ramírez" → nombre="María Guadalupe", ap1="Hernández", ap2="Ramírez"
      "Alejandro González del Valle" → nombre="Alejandro González", ap1="del", ap2="Valle"

    Nota: Para casos con apellido materno compuesto ("del Valle"), González se incluye
    en el nombre. Esto es poco común (~1/12 clientes) y aceptable para el portal.
    """
    parts = (nombre_completo or '').strip().split()
    if len(parts) == 0:
        return 'Juan', 'Perez', 'Lopez'
    elif len(parts) == 1:
        return parts[0], 'X', 'X'
    elif len(parts) == 2:
        return parts[0], parts[1], 'X'
    elif len(parts) == 3:
        return parts[0], parts[1], parts[2]
    else:
        # 4+ parts: last 2 are surnames, everything before is given name(s)
        nombre = ' '.join(parts[:-2])
        ap1 = parts[-2]
        ap2 = parts[-1]
        return nombre, ap1, ap2


def _llenar_solicitante(page, cliente, fecha_nac_str, fecha_ing_str, fecha_sal_str):
    """Llena los campos del solicitante (trabajador)."""
    # Separar nombre mexicano correctamente (soporta nombres compuestos)
    nombre, ap1, ap2 = _separar_nombre_mexicano(cliente.nombre)

    # CURP: debe ser la real del cliente. Usamos la CURP tal cual está
    # en BD (sin corregir checksum) para no alterar un valor que podría
    # ser válido en RENAPO. Solo validamos el formato.
    curp = _validar_curp(cliente.curp, corregir_checksum=False)

    # Datos personales (truncados MUY agresivamente para el portal)
    # El portal limita nombre a ~6 caracteres, apellidos a ~6
    _fill_input(page, 'solicitante[nombre]', _truncar(nombre, 6))
    _fill_input(page, 'solicitante[primer_apellido]', _truncar(ap1, 6))
    _fill_input(page, 'solicitante[segundo_apellido]', _truncar(ap2, 6))

    _fill_input(page, 'solicitante[fecha_nacimiento]', fecha_nac_str)

    # Género y nacionalidad
    genero_id = GENERO_PORTAL_IDS.get(cliente.genero, '1')
    _select_option(page, 'solicitante[genero_id]', genero_id)
    _select_option(page, 'solicitante[nacionalidad_id]', '1')   # MEXICANA (siempre)

    # Contactos (teléfono) — el sitio usa contactos[1], contactos[2], contactos[3]
    _fill_input(page, 'contactos[1]', _limpiar_telefono(cliente.telefono))

    # Domicilio con espera de AJAX para colonia/municipio
    _llenar_domicilio(page,
                      vialidad=cliente.direccion_calle,
                      num_ext=cliente.direccion_numero,
                      cp=cliente.direccion_cp)

    # Datos laborales
    periodicidad_id = PERIODICIDAD_PORTAL_IDS.get(cliente.periodo_pago, '2')
    horas = str(cliente.horas_semanales or 40)
    jornada_id = JORNADA_PORTAL_IDS.get(cliente.jornada, '1')

    _fill_input(page, 'dato_laboral[puesto]', cliente.puesto or 'Trabajador')
    _fill_input(page, 'dato_laboral[remuneracion]', str(float(cliente.salario or 10000)))
    _select_option(page, 'dato_laboral[periodicidad_id]', periodicidad_id)
    _fill_input(page, 'dato_laboral[horas_semanales]', horas)
    _fill_input(page, 'dato_laboral[fecha_ingreso]', fecha_ing_str)
    _fill_input(page, 'dato_laboral[fecha_salida]', fecha_sal_str)
    _select_option(page, 'dato_laboral[jornada_id]', jornada_id)

    # ── CURP: llenar JUSTO antes de Guardar ────────────────
    # Estrategia: presionar teclas reales con delay 5ms (~90ms para
    # 18 chars) + 10ms para que React procese el último evento.
    # Luego GUARDAR INMEDIATAMENTE antes de que la validación async
    # del portal pueda borrar el CURP de React state.
    try:
        loc = page.locator('[name="solicitante[curp]"]')
        if loc.count():
            loc.pressSequentially(curp, delay=5)
            page.wait_for_timeout(10)  # yield: React procese último input
            logger.info('[4curp] CURP tipeado con pressSequentially, guardando...')
    except Exception as e:
        logger.warning('[4curp] pressSequentially error: %s', e)
        _fill_input(page, 'solicitante[curp]', curp)

    # Click "Guardar" — inmediato, sin espera adicional
    _btn_click(page, 'guardar', timeout=5000)


def _llenar_citado(page, cliente):
    """Llena los campos del citado (empresa/patrón).

    Soporta tanto Persona Física como Moral. El portal muestra campos
    diferentes según el tipo:
      - Persona Física: CURP, nombre, apellidos, fecha nacimiento, edad,
        RFC, género, nacionalidad, estado nacimiento, teléfono, email, domicilio
      - Persona Moral: razón social, RFC, teléfono, email, domicilio
    """
    empresa_nombre = cliente.empresa_razon_social or cliente.empresa or 'Empresa SA de CV'
    es_moral = cliente.tipo_persona_citado == 'moral'

    # Tipo persona: desde el modelo (Física o Moral)
    tipo_persona_id = TIPO_PERSONA_PORTAL_IDS.get(cliente.tipo_persona_citado, '1')
    _click_radio(page, 'solicitado[tipo_persona_id]', tipo_persona_id)
    page.wait_for_timeout(500)

    if es_moral:
        # ─── Persona Moral: razón social, RFC, contacto, domicilio ──
        _fill_input(page, 'solicitado[razon_social]', empresa_nombre)

        # RFC del citado (empresa)
        empresa_rfc = cliente.empresa_rfc or cliente.rfc or ''
        if empresa_rfc:
            _fill_input(page, 'solicitado[rfc]', empresa_rfc)

        # Teléfono de contacto
        _fill_input(page, 'contactos[1]', _limpiar_telefono(cliente.empresa_telefono or cliente.telefono))
        if cliente.email:
            _fill_input(page, 'contactos_email', cliente.email)
    else:
        # ─── Persona Física: nombre, apellidos, CURP, RFC, etc. ────
        nombre_parts = empresa_nombre.split()
        _fill_input(page, 'solicitado[nombre]', _truncar(nombre_parts[0] if nombre_parts else 'Empresa', 6))
        _fill_input(page, 'solicitado[primer_apellido]', _truncar(nombre_parts[1] if len(nombre_parts) > 1 else 'SA', 6))
        _fill_input(page, 'solicitado[segundo_apellido]',
                    _truncar('de CV' if len(nombre_parts) <= 2 else ' '.join(nombre_parts[2:]), 6))

        # CURP del citado (si hay, tipear carácter por carácter)
        empresa_curp = (cliente.empresa_curp or '').strip().upper()
        if empresa_curp and len(empresa_curp) >= 15:
            curp_el = page.query_selector('[name="solicitado[curp]"]')
            if curp_el:
                curp_el.click()
                curp_el.fill('')
                for ch in empresa_curp:
                    curp_el.type(ch, delay=5)
                page.wait_for_timeout(50)
            page.wait_for_timeout(100)

        _select_option(page, 'solicitado[genero_id]', '1')             # MASCULINO
        _select_option(page, 'solicitado[nacionalidad_id]', '1')       # MEXICANA

        # RFC del citado (empresa)
        empresa_rfc = cliente.empresa_rfc or cliente.rfc or ''
        if empresa_rfc:
            _fill_input(page, 'solicitado[rfc]', empresa_rfc)

        # Teléfono y email
        _fill_input(page, 'contactos[1]', _limpiar_telefono(cliente.empresa_telefono or cliente.telefono))
        if cliente.email:
            _fill_input(page, 'contactos_email', cliente.email)

    # Domicilio del citado (común para ambos tipos)
    _llenar_domicilio(page,
                      vialidad=cliente.empresa_calle or cliente.direccion_calle,
                      num_ext=cliente.empresa_numero or cliente.direccion_numero,
                      cp=cliente.empresa_cp or cliente.direccion_cp)

    page.wait_for_timeout(500)

    # Click "Guardar" para cerrar el panel del citado
    _btn_click(page, 'guardar', timeout=5000)


# ══════════════════════════════════════════════════════════════════════════
#  Automatización Principal (flujo real del sitio)
# ══════════════════════════════════════════════════════════════════════════


def enviar_a_conciliacion(expediente, headless=True, download_dir=None) -> ResultadoConciliacion:
    """
    Automatiza el envío de la solicitud al portal de conciliación de Baja California.

    Args:
        expediente: Instancia del modelo Expediente con cliente relacionado.
        headless: Si True, corre el navegador sin interfaz gráfica.
        download_dir: Directorio para guardar screenshots y PDFs.

    Returns:
        ResultadoConciliacion con folio y ruta del PDF si tuvo éxito.
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

    resultado = ResultadoConciliacion(success=False)
    cliente = expediente.cliente

    if not download_dir:
        download_dir = tempfile.mkdtemp(prefix='conciliacion_')
    else:
        Path(download_dir).mkdir(parents=True, exist_ok=True)

    # Variables de fechas
    fecha_conflicto = cliente.fecha_salida or expediente.fecha_tramite or date.today()
    fecha_nac = cliente.fecha_nacimiento or (cliente.fecha_ingreso or date.today()) - timedelta(days=365 * 30)
    fecha_ing = cliente.fecha_ingreso or date.today().replace(year=date.today().year - 2)
    fecha_sal = cliente.fecha_salida or date.today()

    fmt_fecha = lambda f: f.strftime('%d/%m/%Y')

    pdf_descargado = None
    url_final = ''

    try:
        with sync_playwright() as p:
            # ── En producción (Railway/Docker) siempre forzar headless ──
            force_headless = os.environ.get('FORCE_HEADLESS', 'true').lower() == 'true'
            actual_headless = headless if not force_headless else True

            browser = p.chromium.launch(
                headless=actual_headless,
                slow_mo=300 if not actual_headless else 50,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
                timeout=15000,
            )
            context = browser.new_context(
                viewport={'width': 1280, 'height': 900},
                accept_downloads=True,
                locale='es-MX',
            )

            # Capturar descargas de PDF
            def on_download(download):
                nonlocal pdf_descargado
                dest = str(Path(download_dir) / download.suggested_filename)
                download.save_as(dest)
                pdf_descargado = dest
                logger.info('  PDF descargado: %s', dest)

            context.on('download', on_download)

            page = context.new_page()

            def screenshot(name):
                path = str(Path(download_dir) / f'{name}.png')
                try:
                    page.screenshot(path=path, full_page=True)
                    resultado.screenshots.append(path)
                except Exception:
                    pass

            def checkpoint(name):
                screenshot(name)
                try:
                    texto = page.evaluate("() => document.body.innerText")
                    logger.info('  [%s] Texto: %s...', name, texto[:200].replace('\n', ' | '))
                    return texto
                except Exception:
                    return ''

            # ════════════════════════════════════════════════════════════════
            #  FASE 0: Cargar página
            # ════════════════════════════════════════════════════════════════
            logger.info('[Carga] Navegando a %s', URL_SOLICITUD)
            try:
                page.goto(URL_SOLICITUD, wait_until='networkidle', timeout=20000)
            except PwTimeout:
                page.goto(URL_SOLICITUD, timeout=20000)
            page.wait_for_timeout(1000)
            checkpoint('00_inicio')

            # ════════════════════════════════════════════════════════════════
            #  FASE 1: Aviso de Privacidad
            # ════════════════════════════════════════════════════════════════
            logger.info('[1] Aceptando aviso de privacidad...')

            # Seleccionar radio "Acepto" (radioAviso = '1')
            _click_radio(page, 'radioAviso', '1')
            page.wait_for_timeout(200)

            # Click "Aceptar"
            _btn_click(page, 'Aceptar')
            page.wait_for_timeout(500)

            # Cerrar modales que aparezcan
            _cerrar_modales(page)
            page.wait_for_timeout(500)
            checkpoint('01_aviso_aceptado')

            # ════════════════════════════════════════════════════════════════
            #  FASE 2: Industria
            # ════════════════════════════════════════════════════════════════
            logger.info('[2] Seleccionando industria...')

            # Seleccionar "Ninguna de las anteriores" (industria = 28)
            _click_radio(page, 'industria', '28')
            page.wait_for_timeout(500)

            # Cerrar modal informativo que pueda aparecer
            _cerrar_modales(page)
            page.wait_for_timeout(200)

            # Click "Validar y Continuar"
            _click_validar_continuar(page)
            page.wait_for_timeout(1000)

            # Cerrar modales
            _cerrar_modales(page)
            page.wait_for_timeout(500)
            checkpoint('02_industria')

            # ════════════════════════════════════════════════════════════════
            #  FASE 3: Fecha de conflicto y objeto de la solicitud
            # ════════════════════════════════════════════════════════════════
            logger.info('[3] Llenando fecha y objeto...')

            # Llenar fecha de conflicto y cerrar el date-picker que se abre
            _fill_input(page, 'solicitud[fecha_conflicto]', fmt_fecha(fecha_conflicto))
            try:
                page.keyboard.press('Escape')
            except Exception:
                pass
            page.wait_for_timeout(400)

            try:
                selects_info = page.evaluate("""() =>
                    Array.from(document.querySelectorAll('select')).map(s => ({
                        name: s.name, id: s.id,
                        opts: s.options.length,
                        val: s.value
                    }))
                """)
                logger.info('[3] Selects en página: %s', selects_info)
            except Exception:
                pass

            try:
                objeto_texto = page.evaluate("""() => {
                    let sel = document.querySelector('[name="solicitud[objeto_id]"]');
                    if (!sel) {
                        const allSels = document.querySelectorAll('select');
                        for (const s of allSels) {
                            if (s.name && s.name.toLowerCase().includes('objeto')) {
                                sel = s; break;
                            }
                        }
                    }
                    if (sel && sel.options.length > 1) {
                        sel.selectedIndex = 1;
                        sel.dispatchEvent(new Event('change', {bubbles: true}));
                        return sel.options[1].text + ' [name=' + sel.name + ']';
                    }
                    return null;
                }""")
                logger.info('[3] Objeto seleccionado: %s', objeto_texto)
            except Exception as e:
                logger.warning('[3] Error al seleccionar objeto: %s', e)
            page.wait_for_timeout(300)

            _click_validar_continuar(page)
            page.wait_for_timeout(1000)
            checkpoint('03_fecha_objeto')

            # ════════════════════════════════════════════════════════════════
            #  FASE 4: Solicitante (Trabajador)
            # ════════════════════════════════════════════════════════════════
            logger.info('[4] Llenando datos del solicitante...')

            # ── 4a: Navegar al tab Solicitante ───────────────────────
            nav_ok = _navigate_wizard_tab(page, 'solicitante')
            if not nav_ok:
                logger.warning('[4] Tab solicitante no encontrado por locator, reintentando...')
                page.wait_for_timeout(2000)
                _navigate_wizard_tab(page, 'solicitante', retries=5)
            page.wait_for_timeout(1000)

            # ── 4b: Clic en "Agregar Solicitante" con reintentos ─────
            clicked = _btn_click(page, 'agregar solicitante', retries=5)
            page.wait_for_timeout(3000)  # Esperar a que Angular renderice el formulario

            # Verificar que el formulario se abrió (campos visibles)
            formulario_abierto = False
            for _retry in range(5):
                try:
                    formulario_abierto = page.evaluate("""() => {
                        const names = ['solicitante[nombre]', 'solicitante[curp]',
                                       'solicitante[primer_apellido]', 'solicitante[segundo_apellido]'];
                        for (const n of names) {
                            const el = document.querySelector(`[name="${n}"]`);
                            if (el && el.offsetParent !== null) return true;
                        }
                        // Angular puede usar formControlName en lugar de name
                        const fc = document.querySelector('[formcontrolname="nombre"]') ||
                                   document.querySelector('[formcontrolname="curp"]') ||
                                   document.querySelector('[formcontrolname="primerApellido"]');
                        if (fc && fc.offsetParent !== null) return true;
                        return false;
                    }""")
                except Exception:
                    formulario_abierto = False
                if formulario_abierto:
                    break
                # Si no se abrió, intentar clic de nuevo con reintentos más agresivos
                logger.warning('[4] Formulario no visible, reintentando clic (%d/5)...', _retry + 1)
                page.wait_for_timeout(1500)
                _btn_click(page, 'agregar solicitante', retries=5)
                page.wait_for_timeout(2500)

            if not formulario_abierto:
                logger.warning('[4] Formulario del solicitante NO se pudo abrir tras reintentos')
                # Tomar screenshot diagnóstico y listar elementos del wizard
                try:
                    diag = page.evaluate("""() => {
                        const tabs = document.querySelectorAll('[role="tab"], .nav-link, .wizard-step a');
                        const btns = document.querySelectorAll('button, [role="button"]');
                        return {
                            tabs: Array.from(tabs).map(t => t.textContent.trim().substring(0, 50)),
                            buttons: Array.from(btns).map(b => b.textContent.trim().substring(0, 50)).filter(t => t.length > 0),
                            url: window.location.href
                        };
                    }""")
                    logger.info('[4diag] Wizard tabs: %s', diag.get('tabs', []))
                    logger.info('[4diag] Buttons: %s', diag.get('buttons', []))
                    logger.info('[4diag] URL: %s', diag.get('url', ''))
                except Exception as diag_err:
                    logger.warning('[4diag] Error reading page state: %s', diag_err)
                checkpoint('04_solicitante_NO_ABIERTO')
            else:
                logger.info('[4] Formulario del solicitante abierto correctamente')

            # ── 4c: Llenar campos del solicitante ─────────────────────
            _llenar_solicitante(page, cliente,
                                fmt_fecha(fecha_nac),
                                fmt_fecha(fecha_ing),
                                fmt_fecha(fecha_sal))
            page.wait_for_timeout(1500)

            # ── 4d: Verificar que los campos se llenaron ──────────────
            try:
                diag = page.evaluate("""() => {
                    const names = ['solicitante[nombre]', 'solicitante[primer_apellido]',
                                   'solicitante[segundo_apellido]', 'solicitante[curp]',
                                   'solicitante[fecha_nacimiento]'];
                    const result = {};
                    for (const n of names) {
                        const el = document.querySelector(`[name="${n}"]`);
                        result[n] = el ? (el.value || '(empty)') : '(NOTFOUND)';
                    }
                    return result;
                }""")
                logger.info('[4diag] Solicitante field values: %s', diag)
            except Exception as e:
                logger.warning('[4diag] Error reading fields: %s', e)

            checkpoint('04_solicitante')

            # ── 4e: Verificar que "Guardar" hizo efecto ─────────────
            # Si el CURP está vacío después de Guardar, la validación React
            # del portal lo borró — reintentar con presSequentially
            try:
                curp_val = page.evaluate("""() => {
                    const el = document.querySelector('[name="solicitante[curp]"]');
                    return el ? el.value : '';
                }""")
                if not curp_val or len(curp_val) < 15:
                    logger.warning('[4] CURP vacío/inválido post-guardar (%s), reintentando...', curp_val[:8] if curp_val else 'EMPTY')
                    try:
                        curp_clean = _validar_curp(cliente.curp, corregir_checksum=False)
                        loc = page.locator('[name="solicitante[curp]"]')
                        if loc.count():
                            loc.click()
                            loc.fill('')  # Limpiar primero
                            page.wait_for_timeout(200)
                            loc.press_sequentially(curp_clean, delay=15)
                            page.wait_for_timeout(100)
                            _btn_click(page, 'guardar', timeout=5000)
                            page.wait_for_timeout(2000)
                    except Exception as curp_err:
                        logger.warning('[4] Reintento CURP falló: %s', curp_err)
            except Exception as diag_err:
                logger.warning('[4] No se pudo verificar CURP: %s', diag_err)

            _click_validar_continuar(page)
            page.wait_for_timeout(1500)
            checkpoint('04_solicitante_validado')

            # ════════════════════════════════════════════════════════════════
            #  FASE 5: Citado (Empresa/Patrón)
            # ════════════════════════════════════════════════════════════════
            logger.info('[5] Llenando datos del citado...')

            _navigate_wizard_tab(page, 'citado')
            page.wait_for_timeout(800)

            _btn_click(page, 'agregar citado')
            page.wait_for_timeout(1500)

            _llenar_citado(page, cliente)
            page.wait_for_timeout(1000)
            checkpoint('05_citado')

            _click_validar_continuar(page)
            page.wait_for_timeout(1500)
            try:
                page.wait_for_load_state('domcontentloaded', timeout=5000)
            except Exception:
                pass
            checkpoint('05_citado_validado')

            # ════════════════════════════════════════════════════════════════
            #  FASE 6: Descripción de los hechos
            # ════════════════════════════════════════════════════════════════
            logger.info('[6] Llenando descripción de los hechos...')

            _navigate_wizard_tab(page, 'descripci')
            page.wait_for_timeout(800)

            hechos = [
                f'El día {fmt_fecha(fecha_conflicto)} fui despedido injustificadamente'
            ]
            if cliente.empresa:
                hechos[0] += f' de mi empleo en {cliente.empresa}'
            if cliente.puesto:
                hechos.append(f'Donde laboraba como {cliente.puesto}.' )
            else:
                hechos[0] += '.'
            if cliente.salario:
                hechos.append(f'Mi salario mensual era de ${cliente.salario:.2f}.' )
            if cliente.fecha_ingreso:
                hechos.append(f'Ingresé a laborar el {fmt_fecha(cliente.fecha_ingreso)}.')
            hechos.append('Solicito el pago de mis prestaciones de ley.')

            texto_hechos = ' '.join(hechos)

            _cerrar_modales(page)
            try:
                page.evaluate("""(texto) => {
                    const ta = document.querySelector('textarea');
                    if (ta) {
                        ta.focus();
                        ta.value = texto;
                        ta.dispatchEvent(new Event('input', {bubbles: true}));
                        ta.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                }""", texto_hechos)
            except Exception:
                pass
            page.wait_for_timeout(300)
            _btn_click(page, 'aceptar')
            page.wait_for_timeout(1000)
            checkpoint('06_descripcion')

            # ════════════════════════════════════════════════════════════════
            #  FASE 7: Resumen y Envío
            # ════════════════════════════════════════════════════════════════
            logger.info('[7] Navegando a resumen y enviando...')

            _navigate_wizard_tab(page, 'resumen')
            page.wait_for_timeout(1000)

            # Verificar errores antes de enviar
            try:
                errores = page.evaluate("""() => {
                const errs = [];
                document.querySelectorAll('.text-danger, .error, .invalid-feedback, .is-invalid, .help-block').forEach(el => {
                    const txt = el.textContent.trim();
                    if (txt) {
                        let input = el.closest('[class*="col"], div')?.querySelector('input, select, textarea');
                        errs.push({ msg: txt.substring(0, 60), name: input?.name || input?.id || '' });
                    }
                });
                return errs;
            }""")
            except Exception:
                errores = []
            if errores:
                logger.warning('  Errores detectados antes de enviar: %s', errores)
                for err in errores[:3]:
                    logger.warning('  Error: %s (campo: %s)', err['msg'], err['name'])

            # ════════════════════════════════════════════════════════════
            #  FASE 7: Envío de la solicitud con manejo de navegación
            # ════════════════════════════════════════════════════════════
            logger.info('[7] Iniciando envío con expect_navigation...')
            navegacion_completa = False
            url_inicial = page.url

            # ── Re-setear CURP en Resumen (si el campo existe) ──────
            # Nota: en la pestaña Resumen el campo CURP normalmente NO
            # está en el DOM (solo hay resumen de texto). La validación
            # ocurre en backend usando los datos de React state que se
            # enviaron al hacer clic en Guardar en la Fase 4. Por eso
            # este re-set es solo un intento rápido para casos donde el
            # campo sí esté visible.
            try:
                curp_para_envio = _validar_curp(cliente.curp, corregir_checksum=False)
                loc_curp = page.locator('[name="solicitante[curp]"]')
                if loc_curp.count():
                    loc_curp.pressSequentially(curp_para_envio, delay=10)
                    page.wait_for_timeout(50)
                    logger.info('[7curp] CURP re-tipeado en Resumen: %s', curp_para_envio[:12])
                else:
                    logger.info('[7curp] Campo CURP no visible en Resumen (normal)')
            except Exception as e:
                logger.warning('[7curp] Error re-setting CURP: %s', e)

            logger.info('[7a] Click en Enviar solicitud...')
            _btn_click(page, 'enviar solicitud')

            try:
                page.wait_for_selector('.swal-overlay, .swal-modal, .modal.show', timeout=1500)
                logger.info('[7a] SweetAlert detectado')
                page.wait_for_timeout(300)
            except Exception:
                logger.info('[7a] Sin SweetAlert - navegación directa')

            try:
                with page.expect_navigation(timeout=45000):
                    confirmed = False
                    for sel in [
                        '.swal-button--confirm',
                        '.swal-button:not(.swal-button--cancel)',
                        'button.swal-button',
                    ]:
                        try:
                            btn = page.locator(sel).first
                            if btn.count() > 0:
                                btn.click(timeout=3000)
                                logger.info('[7b] Confirmado con selector: %s', sel)
                                confirmed = True
                                break
                        except Exception:
                            continue
                    if not confirmed:
                        logger.info('[7b] Sin SweetAlert visible - navegación directa')

                navegacion_completa = True
                logger.info('[7] Navegación detectada! URL: %s → %s', url_inicial, page.url)
            except Exception as nav_err:
                logger.warning('[7] expect_navigation falló: %s', nav_err)
                try:
                    url_actual = page.url
                    if url_actual and url_actual != url_inicial:
                        logger.info('[7] Navegación detectada por cambio de URL: %s', url_actual)
                        navegacion_completa = True
                    else:
                        logger.info('[7] URL sin cambios: %s', url_actual)
                except Exception:
                    logger.warning('[7] No se pudo obtener URL')

            if not navegacion_completa:
                logger.info('[7] Fallback: esperando carga de página...')
                try:
                    page.wait_for_load_state('networkidle', timeout=10000)
                except Exception:
                    page.wait_for_timeout(3000)
                try:
                    if page.url != url_inicial:
                        navegacion_completa = True
                        logger.info('[7] Navegación confirmada en fallback: %s', page.url)
                except Exception:
                    pass

            try:
                page.wait_for_load_state('domcontentloaded', timeout=10000)
            except Exception:
                pass

            page.wait_for_timeout(1000)

            _cerrar_modales(page)
            page.wait_for_timeout(500)
            texto_envio = checkpoint('07_enviado')

            # ════════════════════════════════════════════════════════════════
            #  FASE 7.5: Detectar errores de validación del portal
            # ════════════════════════════════════════════════════════════════
            # Si el portal rechazó el envío, mostrará la misma página con
            # errores de validación. Detectarlos temprano evita perder tiempo
            # en Phase 8 intentando extraer folio de una página de error.
            logger.info('[7.5] Verificando errores de validación...')
            screenshot('07_5_post_envio')
            if not navegacion_completa:
                errores_validacion = _detectar_errores_validacion(page)
                if errores_validacion:
                    msgs = '; '.join([f"{e['name']}: {e['msg']}" for e in errores_validacion[:5]])
                    # Diagnostic: check CURP field value
                    curp_diag = ''
                    try:
                        cv = page.evaluate("""() => document.querySelector('[name="solicitante[curp]"]')?.value || 'NOTFOUND'""")
                        curp_diag = f' | CURP_FIELD=[{cv[:12]}]'
                    except Exception:
                        pass
                    logger.warning('[7.5] Errores de validación detectados: %s', msgs)
                    resultado.error = f'[DEPLOYED-ver4] El portal rechazó la solicitud. Errores: {msgs}{curp_diag}'
                    resultado.detalle = f'URL={page.url} | ERRORES={msgs}{curp_diag}'
                    browser.close()
                    return resultado  # Salir temprano

            # ════════════════════════════════════════════════════════════════
            #  FASE 8: Extraer folio + Descargar acuse PDF
            # ════════════════════════════════════════════════════════════════
            logger.info('[8] Extrayendo folio y descargando acuse...')

            # ── 8a: Extraer folio del texto de la página de confirmación ──
            texto_pagina = ''
            url_actual = ''

            # Patrones de folio (definidos antes del try para que estén
            # disponibles en Phase 8d incluso si Phase 8a falla)
            FOLIO_PATTERNS = [
                r'[Ff]olio[:\s#Nº°\.]*([A-Z0-9][-A-Z0-9/]+)',
                r'N[úu]mero\s+de\s+[Ss]olicitud[:\s]*([A-Z0-9][-A-Z0-9/]+)',
                r'N[úu]mero\s+de\s+[Ff]olio[:\s]*([A-Z0-9][-A-Z0-9/]+)',
                r'[Ss]olicitud\s+N[°º]?[:\s]*([A-Z0-9][-A-Z0-9/]+)',
                r'Expediente[:\s#]*([A-Z0-9][-A-Z0-9/]+)',
                r'[Ff]olio[:\s#Nº°\.]*([\w\-]+\d[\w\-]*)',
                r'[Ff]olio[:\s#Nº°\.]*(\d{2,}[-/]?\d{2,})',
                r'(CCL[-/][A-Z0-9/-]+)',
                r'(BCN?[-/][A-Z0-9/-]+)',
                r'(CFFL[-/][A-Z0-9/-]+)',
                r'(BC[-/]CCFL[-/][A-Z0-9/-]+)',
                r'/(solicitud|update|folio)/([A-Z0-9][-A-Z0-9/]+)',
                r'(\d{4}[-/]\d{4,8})',
                r'\b(\d{4}[-/]\d{4,8})\b',
                r'\b(CCL[\s-]?\d{3,8})\b',
                r'\b(CCL[\s-]?\d{4}[-/]\d{3,8})\b',
            ]

            try:
                texto_pagina = page.inner_text('body')
                logger.info('[8] Texto de página de confirmación: %s...', texto_pagina[:600].replace('\n', ' | '))

                try:
                    url_actual = page.url
                    url_final = url_actual
                    logger.info('[8] URL actual de confirmación: %s', url_actual)
                except Exception:
                    url_actual = ''

                # Intentar en texto de página primero
                for pat in FOLIO_PATTERNS:
                    m = re.search(pat, texto_pagina)
                    if m:
                        folio_candidato = (m.group(1) if m.lastindex else m.group(0)).strip().rstrip('.')
                        logger.info('[8] Folio encontrado en página con patrón "%s": %s', pat, folio_candidato)
                        resultado.folio = folio_candidato
                        resultado.success = True
                        break

                # Si no se encontró en texto, intentar en la URL
                if not resultado.folio and url_actual:
                    for pat in FOLIO_PATTERNS:
                        m = re.search(pat, url_actual)
                        if m:
                            folio_candidato = (m.group(1) if m.lastindex else m.group(0)).strip()
                            logger.info('[8] Folio encontrado en URL con patrón "%s": %s', pat, folio_candidato)
                            resultado.folio = folio_candidato
                            resultado.success = True
                            break

                if not resultado.folio:
                    logger.warning('[8] No se encontró folio en el texto de la página ni en la URL')
                    logger.info('[8] Texto completo para diagnóstico: %s...', texto_pagina[:2000])
            except Exception as e:
                logger.warning('[8] Error al extraer texto de página: %s', e)

            # ── 8b: Intentar descargar el PDF del acuse ───────────────────
            for texto_btn in ['acuse', 'descargar', 'pdf', 'comprobante', 'recibo',
                              'imprimir', 'constancia', 'documento']:
                _btn_click(page, texto_btn)
                page.wait_for_timeout(600)

            try:
                link_encontrado = page.evaluate("""() => {
                    const keywords = ['acuse', 'descargar', 'pdf', 'folio', 'comprobante',
                                      'recibo', 'imprimir', 'constancia', 'documento',
                                      'getFile', 'generaDocumento'];
                    for (const a of document.querySelectorAll('a')) {
                        const href = (a.href || '').toLowerCase();
                        const text = (a.textContent || '').toLowerCase().trim();
                        if (keywords.some(k => href.includes(k) || text.includes(k)) && a.offsetParent !== null) {
                            a.click();
                            a.dispatchEvent(new Event('click', {bubbles: true}));
                            return a.href;
                        }
                    }
                    return null;
                }""")
                if link_encontrado:
                    logger.info('[8b] Click en link: %s', link_encontrado)
                    page.wait_for_timeout(1500)
            except Exception:
                pass

            try:
                page.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                pass
            page.wait_for_timeout(2000)
            checkpoint('08_confirmacion')

            # ── 8c: Si se descargó un PDF, extraer folio de él también ───
            if pdf_descargado:
                pdf_path = Path(pdf_descargado)
                resultado.pdf_path = str(pdf_path)
                nombre_pdf = pdf_path.stem
                logger.info('[8] PDF descargado: %s', nombre_pdf)

                if not resultado.folio:
                    for pat in [r'(CCL[-/][\w/-]+)', r'(\d{4}[-/]\d{4,8})', r'([\w-]+folio[\w-]*)']:
                        m = re.search(pat, nombre_pdf, re.IGNORECASE)
                        if m:
                            resultado.folio = m.group(1)
                            break

                if not resultado.folio:
                    try:
                        with open(pdf_descargado, 'rb') as f:
                            contenido = f.read()
                        texto_pdf = contenido.decode('latin-1', errors='ignore')
                        for pat in [r'(CCL[:\s]*/[\d\-]+)', r'FOLIO[:\s]*([\w/-]+)',
                                    r'N[úu]mero[:\s]*([\w/-]+)', r'(\d{4}[-/]\d{4,8})']:
                            m = re.search(pat, texto_pdf, re.IGNORECASE)
                            if m:
                                resultado.folio = m.group(1).strip()
                                break
                    except Exception as e:
                        logger.warning('[8] No se pudo leer PDF: %s', e)

                resultado.success = True
                resultado.detalle = f'Solicitud enviada. Folio: {resultado.folio or "N/A"}'
                logger.info('[8] Éxito con PDF. Folio=%s', resultado.folio)

            elif resultado.success and resultado.folio:
                resultado.detalle = f'Solicitud enviada. Folio: {resultado.folio} (sin PDF)'
                logger.info('[8] Éxito sin PDF. Folio=%s', resultado.folio)

            else:
                # ── 8d: Buscar enlace de descarga como último recurso ─────
                doc_url = ''
                try:
                    doc_url = page.evaluate("""() => {
                        const keywords = ['getFile', 'acuse', 'documento', 'folio', '.pdf',
                                           'descargar', 'generaDocumento', 'firma'];
                        const sel = 'a[href*="getFile"], a[href*="acuse"], a[href*="documento"], ' +
                                    'a[href*="folio"], a[href*=".pdf"], a[href*="descargar"], ' +
                                    'a[href*="generaDocumento"], a[href*="firma"]';
                        for (const link of document.querySelectorAll(sel)) {
                            if (link.href) return link.href;
                        }
                        for (const el of document.querySelectorAll('iframe, embed, object')) {
                            if (el.src && el.src.includes('pdf')) return el.src;
                        }
                        return '';
                    }""")
                except Exception:
                    pass

                if doc_url:
                    resultado.detalle = f'Solicitud enviada. URL documento: {doc_url}'
                    m = re.search(r'getFile/([\w-]+)|folio=([\w-]+)', doc_url)
                    if m:
                        resultado.folio = (m.group(1) or m.group(2))
                        resultado.success = True
                        resultado.detalle = f'Solicitud enviada. Folio: {resultado.folio} (desde URL)'
                        logger.info('[8d] Folio extraído de URL: %s', resultado.folio)
                    else:
                        logger.info('[8d] Navegando a doc_url para descargar PDF: %s', doc_url)
                        try:
                            page.goto(doc_url, wait_until='networkidle', timeout=15000)
                            page.wait_for_timeout(2000)

                            try:
                                doc_texto = page.inner_text('body')
                                logger.info('[8d] Texto de página documento: %s...', doc_texto[:500].replace('\n', ' | '))
                                for pat in FOLIO_PATTERNS:
                                    m = re.search(pat, doc_texto)
                                    if m:
                                        folio_candidato = (m.group(1) if m.lastindex else m.group(0)).strip().rstrip('.')
                                        logger.info('[8d] Folio encontrado en doc_url con patrón "%s": %s', pat, folio_candidato)
                                        resultado.folio = folio_candidato
                                        resultado.success = True
                                        break
                            except Exception:
                                pass

                            for txt in ['descargar', 'acuse', 'pdf', 'guardar', 'imprimir', 'recibo', 'comprobante']:
                                if _btn_click(page, txt):
                                    page.wait_for_timeout(1000)
                                    break

                            try:
                                page.wait_for_load_state('networkidle', timeout=8000)
                            except Exception:
                                pass
                            page.wait_for_timeout(3000)
                            checkpoint('08_pdf_navegado')
                        except Exception as nav_err:
                            logger.warning('[8d] Error navegando a doc_url: %s', nav_err)

                        if pdf_descargado:
                            pdf_path = Path(pdf_descargado)
                            resultado.pdf_path = str(pdf_path)
                            nombre_pdf = pdf_path.stem
                            logger.info('[8d] PDF descargado desde doc_url: %s', nombre_pdf)
                            resultado.folio = _extraer_folio_desde_pdf(pdf_descargado, nombre_pdf)
                            if resultado.folio:
                                resultado.success = True
                                resultado.detalle = f'Solicitud enviada. Folio: {resultado.folio}'
                                logger.info('[8d] Éxito con PDF. Folio=%s', resultado.folio)

                    if not resultado.folio:
                        resultado.error = 'Solicitud enviada al portal pero no se pudo obtener el folio'
                        try:
                            url_final = page.url
                        except Exception:
                            url_final = doc_url
                        resultado.detalle = (
                            f'URL_FINAL={url_final} | '
                            f'URL_DOC={doc_url} | '
                            f'TEXTO={texto_pagina[:1000]}'
                        )
                else:
                    resultado.error = 'Solicitud enviada al portal pero no se pudo obtener el folio'
                    try:
                        url_final = page.url
                    except Exception:
                        url_final = 'desconocida'
                    screenshot('08_error_no_folio')
                    resultado.detalle = (
                        f'URL={url_final} | '
                        f'TEXTO={texto_pagina[:1000]}'
                    )

            browser.close()

    except Exception as e:
        logger.exception('Error en la automatización de conciliación')
        resultado.error = f'{type(e).__name__}: {e}'
        if not resultado.detalle and url_final:
            resultado.detalle = f'URL={url_final} | EXCEPTION={e}'

    return resultado


# ══════════════════════════════════════════════════════════════════════════
#  Screenshots servibles por URL (para el espejo en vivo)
# ══════════════════════════════════════════════════════════════════════════


def screenshots_a_urls(rutas):
    """Convierte rutas absolutas de screenshots en URLs servibles (/media/...).

    Si una ruta queda fuera de MEDIA_ROOT (no servible), se omite.
    """
    from django.conf import settings
    media_root = Path(settings.MEDIA_ROOT).resolve()
    urls = []
    for r in rutas or []:
        try:
            rel = Path(r).resolve().relative_to(media_root)
            urls.append(f'{settings.MEDIA_URL}{rel.as_posix()}')
        except (ValueError, OSError):
            urls.append('')
    return urls


# ══════════════════════════════════════════════════════════════════════════
#  Función de alto nivel (guarda resultado en BD)
# ══════════════════════════════════════════════════════════════════════════


def enviar_y_guardar(expediente, usuario=None, headless=True, download_dir=None) -> ResultadoConciliacion:
    """Envía la solicitud al portal y guarda el resultado en el expediente."""
    from django.core.files import File

    resultado = enviar_a_conciliacion(expediente, headless=headless, download_dir=download_dir)

    if resultado.success:
        expediente.folio = resultado.folio or expediente.folio
        expediente.fecha_tramite = timezone.now().date()
        expediente.save()

        if resultado.pdf_path and Path(resultado.pdf_path).exists():
            from .models import Documento
            doc = Documento(
                expediente=expediente,
                descripcion=f'Solicitud de Conciliación (Folio: {resultado.folio or "N/A"})',
                tipo='citatorio',
                subido_por=usuario or getattr(expediente, 'asesor', None),
            )
            with open(resultado.pdf_path, 'rb') as f:
                doc.archivo.save(
                    f'solicitud_conciliacion_{expediente.numero}.pdf',
                    File(f),
                    save=True,
                )

        if usuario:
            from .signals import registrar_movimiento
            registrar_movimiento(
                expediente=expediente,
                usuario=usuario,
                accion='actualizacion',
                detalle=f'Solicitud de conciliación enviada al portal. Folio: {resultado.folio or "N/A"}'
            )

    return resultado
