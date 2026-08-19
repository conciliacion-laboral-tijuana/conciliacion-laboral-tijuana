// ══════════════════════════════════════════════════════════════════════════
//  Conciliación BC — Asistente · Content Script
//
//  Se inyecta en app.conciliacionbc.gob.mx. Cuando hay una tarea activa
//  (guardada por el background), llena el formulario del portal fase por fase
//  y deja que EL ASESOR dé el clic final en "Enviar solicitud". Después
//  detecta el folio, descarga el acuse PDF y reporta todo a la app.
//
//  Los selectores son los mismos que usa la automatización del servidor
//  (expedientes/conciliacion_automation.py).
// ══════════════════════════════════════════════════════════════════════════

(() => {
  if (window.__conciliacionAsistenteActivo) return; // no duplicar
  window.__conciliacionAsistenteActivo = true;

  let tarea = null;
  let panel = null;
  let reportado = false;

  // ─── Helpers DOM (portados de la automatización) ────────────────────────

  const sleep = ms => new Promise(r => setTimeout(r, ms));

  function byName(name) {
    return document.querySelector(`[name="${name}"]`);
  }

  function setValue(el, value) {
    if (!el) return false;
    el.focus();
    el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.dispatchEvent(new Event('blur'));
    return true;
  }

  function selectOption(name, value) {
    const el = byName(name);
    if (!el || el.tagName !== 'SELECT') return false;
    el.value = value;
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  }

  function clickRadio(name, value) {
    const r = document.querySelector(`input[name="${name}"][value="${value}"]`);
    if (!r) return false;
    r.click();
    r.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  }

  function clickButton(texto, timeoutMs = 4000) {
    return new Promise(resolve => {
      const start = Date.now();
      const tryClick = () => {
        const btns = document.querySelectorAll('button, a');
        for (const el of btns) {
          const txt = (el.textContent || '').trim().toLowerCase();
          if (txt.includes(texto.toLowerCase()) && el.offsetParent !== null) {
            el.click();
            resolve(true);
            return;
          }
        }
        if (Date.now() - start < timeoutMs) setTimeout(tryClick, 250);
        else resolve(false);
      };
      tryClick();
    });
  }

  function navigateTab(texto) {
    const els = document.querySelectorAll('.wizard-step a, .nav-link, .step-title, a[class*="step"]');
    for (const el of els) {
      const txt = (el.textContent || '').trim().toLowerCase();
      if (txt.includes(texto.toLowerCase())) {
        el.click();
        return true;
      }
    }
    return false;
  }

  function closeModals() {
    // Cerrar SweetAlert
    const overlay = document.querySelector('.swal-overlay');
    if (overlay && overlay.offsetParent !== null) {
      const ok = overlay.querySelector('.swal-button--confirm, .swal-button:not(.swal-button--cancel)')
        || overlay.querySelector('.swal-button, button');
      if (ok) ok.click();
      overlay.style.display = 'none';
    }
    // Cerrar modales Bootstrap
    document.querySelectorAll('.modal.show, [role="dialog"]').forEach(container => {
      for (const btn of container.querySelectorAll('button, a')) {
        const txt = (btn.textContent || '').trim().toLowerCase();
        if (['entendido', 'cerrar', 'close', 'aceptar', 'ok', 'confirmar', 'dismiss'].includes(txt)
            && btn.offsetParent !== null) {
          btn.click();
          break;
        }
      }
      container.classList.remove('show');
      container.style.display = 'none';
    });
    document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
    document.body.classList.remove('modal-open');
  }

  function clickValidarContinuar(timeoutMs = 6000) {
    return new Promise(resolve => {
      const start = Date.now();
      const tryClick = () => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
          const t = (btn.textContent || '').trim().toLowerCase();
          if (t.includes('validar') && t.includes('continuar') && btn.offsetParent !== null) {
            btn.click();
            resolve(true);
            return;
          }
        }
        if (Date.now() - start < timeoutMs) setTimeout(tryClick, 250);
        else resolve(false);
      };
      tryClick();
    });
  }

  function separarNombre(nombreCompleto) {
    const parts = (nombreCompleto || '').trim().split(/\s+/);
    if (parts.length === 0) return ['Juan', 'Perez', 'Lopez'];
    if (parts.length === 1) return [parts[0], 'X', 'X'];
    if (parts.length === 2) return [parts[0], parts[1], 'X'];
    if (parts.length === 3) return parts;
    return [parts.slice(0, -2).join(' '), parts[parts.length - 2], parts[parts.length - 1]];
  }

  const truncar = (t, n) => (t || '').slice(0, n);
  const limpiarTelefono = tel => {
    const d = (tel || '').replace(/\D/g, '');
    return d.length >= 10 ? d.slice(-10) : (d || '6641234567');
  };

  async function llenarDomicilio(prefix, calle, num, cp) {
    selectOption(`${prefix}[estado_id]`, '02');          // Baja California
    selectOption(`${prefix}[tipo_vialidad_id]`, '5');    // CALLE
    setValue(byName(`${prefix}[vialidad]`), calle || 'Av Principal');
    setValue(byName(`${prefix}[num_ext]`), num || '123');

    const cpEl = byName(`${prefix}[cp]`);
    if (cpEl) {
      cpEl.focus();
      cpEl.value = cp || '22000';
      ['input', 'change', 'blur'].forEach(ev => cpEl.dispatchEvent(new Event(ev, { bubbles: true })));
    }
    await sleep(3000); // AJAX de colonia/municipio según CP

    const municipio = document.querySelector('select[name="municipio"]');
    if (municipio && municipio.options.length > 1 && !municipio.value) {
      municipio.selectedIndex = 1;
      municipio.dispatchEvent(new Event('change', { bubbles: true }));
    }
    await sleep(500);

    const asentamiento = document.querySelector(`select[name="${prefix}[asentamiento]"]`);
    if (asentamiento && asentamiento.options.length > 1) {
      asentamiento.selectedIndex = 1;
      asentamiento.dispatchEvent(new Event('change', { bubbles: true }));
    }
    await sleep(300);
  }

  // ─── Panel flotante ──────────────────────────────────────────────────────

  function crearPanel() {
    panel = document.createElement('div');
    panel.id = 'conciliacion-asistente-panel';
    panel.style.cssText = `
      position: fixed; top: 12px; right: 12px; z-index: 999999;
      width: 320px; background: #ffffff; border: 2px solid #2563eb;
      border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,.25);
      font-family: system-ui, sans-serif; font-size: 13px; color: #1f2937;
      overflow: hidden;
    `;
    panel.innerHTML = `
      <div style="background:#2563eb; color:#fff; padding:10px 14px; font-weight:600; display:flex; justify-content:space-between; align-items:center;">
        <span>🤖 Conciliación BC — Asistente</span>
        <button id="cac-cerrar" style="background:none;border:none;color:#fff;cursor:pointer;font-size:16px;">✕</button>
      </div>
      <div id="cac-estado" style="padding:12px 14px; line-height:1.5;"></div>
      <div id="cac-acciones" style="padding:0 14px 12px; display:flex; flex-direction:column; gap:8px;"></div>
      <div id="cac-pasos" style="padding:0 14px 12px; border-top:1px solid #e5e7eb;"></div>
    `;
    document.body.appendChild(panel);
    document.getElementById('cac-cerrar').addEventListener('click', () => panel.remove());
  }

  function setEstado(texto, tipo = 'info') {
    const colores = { info: '#2563eb', ok: '#16a34a', warn: '#d97706', error: '#dc2626' };
    const el = document.getElementById('cac-estado');
    if (!el) return;
    el.innerHTML = `<div style="color:${colores[tipo] || colores.info}; font-weight:500;">${texto}</div>`;
  }

  function setAcciones(botones) {
    const cont = document.getElementById('cac-acciones');
    if (!cont) return;
    cont.innerHTML = '';
    for (const b of botones) {
      const btn = document.createElement('button');
      btn.textContent = b.texto;
      btn.style.cssText = `
        padding:8px 12px; border:none; border-radius:8px; cursor:pointer; font-weight:600; font-size:13px;
        background:${b.estilo === 'verde' ? '#16a34a' : b.estilo === 'rojo' ? '#dc2626' : '#2563eb'}; color:#fff;
      `;
      btn.addEventListener('click', b.accion);
      cont.appendChild(btn);
    }
  }

  function setPasos(pasos, actual) {
    const cont = document.getElementById('cac-pasos');
    if (!cont) return;
    cont.innerHTML = pasos.map((p, i) => {
      const estado = i < actual ? '✅' : i === actual ? '⏳' : '⬜';
      return `<div style="margin:3px 0; ${i === actual ? 'font-weight:600;' : ''}">${estado} ${p}</div>`;
    }).join('');
  }

  // ─── Detección de folio ─────────────────────────────────────────────────

  const FOLIO_PATTERNS = [
    /[Ff]olio:\s*([A-Z0-9][-A-Z0-9/]+)/,
    /N[úu]mero\s+de\s+[Ss]olicitud:\s*([A-Z0-9][-A-Z0-9/]+)/,
    /N[úu]mero\s+de\s+[Ff]olio:\s*([A-Z0-9][-A-Z0-9/]+)/,
    /[Ss]olicitud\s+N[°º]?:\s*([A-Z0-9][-A-Z0-9/]+)/,
    /Expediente:\s*([A-Z0-9][-A-Z0-9/]+)/,
    /(CCL[-/][A-Z0-9/-]+)/,
    /(BCN?[-/][A-Z0-9/-]+)/,
    /(CFFL[-/][A-Z0-9/-]+)/,
    /(BC[-/]CCFL[-/][A-Z0-9/-]+)/,
    /(\d{4}[-/]\d{4,8})/,
  ];

  function extraerFolio(texto, url) {
    for (const pat of FOLIO_PATTERNS) {
      const m = (texto || '').match(pat) || (url || '').match(pat);
      if (m && m[1]) return m[1].replace(/\.$/, '').trim();
    }
    return '';
  }

  // ─── Descarga del acuse PDF → base64 ────────────────────────────────────

  async function descargarAcuse() {
    // Buscar enlaces de descarga del acuse
    const keywords = ['getFile', 'acuse', 'documento', 'folio', '.pdf', 'descargar', 'generaDocumento', 'firma'];
    const links = document.querySelectorAll('a');
    for (const a of links) {
      const href = (a.href || '').toLowerCase();
      const text = (a.textContent || '').toLowerCase().trim();
      if (keywords.some(k => href.includes(k) || text.includes(k)) && a.offsetParent !== null) {
        try {
          const res = await fetch(a.href, { credentials: 'include' });
          if (res.ok) {
            const blob = await res.blob();
            if (blob.type.includes('pdf') || a.href.toLowerCase().includes('getFile') || a.href.toLowerCase().includes('.pdf')) {
              return { nombre: (a.href.split('/').pop() || 'acuse.pdf'), b64: await blobToBase64(blob) };
            }
          }
        } catch (_) { /* probar siguiente */ }
      }
    }
    // Fallback: iframe/embed PDF
    for (const el of document.querySelectorAll('iframe, embed, object')) {
      const src = el.src || '';
      if (src.toLowerCase().includes('pdf')) {
        try {
          const res = await fetch(src, { credentials: 'include' });
          if (res.ok) {
            const blob = await res.blob();
            return { nombre: 'acuse.pdf', b64: await blobToBase64(blob) };
          }
        } catch (_) { /* sin acuse */ }
      }
    }
    return null;
  }

  function blobToBase64(blob) {
    return new Promise(resolve => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result.split(',')[1] || '');
      reader.readAsDataURL(blob);
    });
  }

  // ─── Llenado principal ──────────────────────────────────────────────────

  async function llenar() {
    if (!tarea) return;
    const PASOS = ['Aviso de privacidad', 'Industria', 'Fecha y objeto', 'Solicitante',
                   'Citado', 'Descripción', 'Resumen y envío', 'Acuse'];
    let pasoActual = 0;
    setPasos(PASOS, pasoActual);

    // ── FASE 1: Aviso de privacidad ──────────────────────────────────
    setEstado('Aceptando aviso de privacidad…');
    await sleep(1500);
    clickRadio('radioAviso', '1');
    await sleep(300);
    await clickButton('Aceptar');
    await sleep(600);
    closeModals();
    await sleep(500);
    pasoActual = 1; setPasos(PASOS, pasoActual);

    // ── FASE 2: Industria ────────────────────────────────────────────
    setEstado('Seleccionando industria…');
    clickRadio('industria', '28'); // "Ninguna de las anteriores"
    await sleep(600);
    closeModals();
    await sleep(300);
    await clickValidarContinuar();
    await sleep(1200);
    closeModals();
    await sleep(500);
    pasoActual = 2; setPasos(PASOS, pasoActual);

    // ── FASE 3: Fecha de conflicto y objeto ──────────────────────────
    setEstado('Llenando fecha de conflicto y objeto…');
    setValue(byName('solicitud[fecha_conflicto]'), tarea.cliente.fecha_conflicto);
    await sleep(500);
    const objetoSel = document.querySelector('select[name*="objeto"], select');
    if (objetoSel && objetoSel.options.length > 1) {
      objetoSel.selectedIndex = 1;
      objetoSel.dispatchEvent(new Event('change', { bubbles: true }));
    }
    await sleep(400);
    await clickValidarContinuar();
    await sleep(1200);
    pasoActual = 3; setPasos(PASOS, pasoActual);

    // ── FASE 4: Solicitante (trabajador) ─────────────────────────────
    setEstado('Llenando datos del solicitante…');
    navigateTab('solicitante');
    await sleep(1000);
    await clickButton('agregar solicitante');
    await sleep(1500);

    const c = tarea.cliente;
    const [nombre, ap1, ap2] = separarNombre(c.nombre);
    setValue(byName('solicitante[nombre]'), truncar(nombre, 6));
    setValue(byName('solicitante[primer_apellido]'), truncar(ap1, 6));
    setValue(byName('solicitante[segundo_apellido]'), truncar(ap2, 6));
    setValue(byName('solicitante[fecha_nacimiento]'), c.fecha_nacimiento);
    selectOption('solicitante[genero_id]', c.genero);
    selectOption('solicitante[nacionalidad_id]', '1'); // MEXICANA
    setValue(byName('contactos[1]'), limpiarTelefono(c.telefono));
    await llenarDomicilio('domicilio', c.direccion_calle, c.direccion_numero, c.direccion_cp);

    setValue(byName('dato_laboral[puesto]'), c.puesto);
    setValue(byName('dato_laboral[remuneracion]'), String(c.salario));
    selectOption('dato_laboral[periodicidad_id]', c.periodicidad);
    setValue(byName('dato_laboral[horas_semanales]'), c.horas_semanales);
    setValue(byName('dato_laboral[fecha_ingreso]'), c.fecha_ingreso);
    setValue(byName('dato_laboral[fecha_salida]'), c.fecha_salida);
    selectOption('dato_laboral[jornada_id]', c.jornada);

    // CURP: llenar JUSTO antes de Guardar (igual que la automatización)
    if (c.curp && c.curp.length >= 15) {
      setValue(byName('solicitante[curp]'), c.curp);
      await sleep(100);
    }
    await clickButton('Guardar', 6000);
    await sleep(1200);
    pasoActual = 4; setPasos(PASOS, pasoActual);

    setEstado('Validando solicitante…');
    await clickValidarContinuar();
    await sleep(1200);
    pasoActual = 5; setPasos(PASOS, pasoActual);

    // ── FASE 5: Citado (empresa/patrón) ──────────────────────────────
    setEstado('Llenando datos del citado (empresa)…');
    navigateTab('citado');
    await sleep(1000);
    await clickButton('agregar citado');
    await sleep(1500);

    const empresaParts = (c.empresa_nombre || 'Empresa SA de CV').split(/\s+/);
    clickRadio('solicitado[tipo_persona_id]', c.tipo_persona);
    await sleep(400);
    setValue(byName('solicitado[nombre]'), truncar(empresaParts[0] || 'Empresa', 6));
    setValue(byName('solicitado[primer_apellido]'), truncar(empresaParts[1] || 'SA', 6));
    setValue(byName('solicitado[segundo_apellido]'),
             truncar(empresaParts.length <= 2 ? 'de CV' : empresaParts.slice(2).join(' '), 6));
    selectOption('solicitado[genero_id]', '1');       // MASCULINO
    selectOption('solicitado[nacionalidad_id]', '1'); // MEXICANA
    await llenarDomicilio('domicilio', c.empresa_calle, c.empresa_numero, c.empresa_cp);
    setValue(byName('contactos[1]'), limpiarTelefono(c.empresa_telefono));
    await sleep(600);
    await clickButton('Guardar', 6000);
    await sleep(1000);
    pasoActual = 6; setPasos(PASOS, pasoActual);

    setEstado('Validando citado…');
    await clickValidarContinuar();
    await sleep(1500);
    pasoActual = 7; setPasos(PASOS, pasoActual);

    // ── FASE 6: Descripción de los hechos ────────────────────────────
    setEstado('Llenando descripción de los hechos…');
    navigateTab('descripci');
    await sleep(1000);
    const textarea = document.querySelector('textarea');
    if (textarea) {
      textarea.focus();
      textarea.value = tarea.hechos || '';
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
      textarea.dispatchEvent(new Event('change', { bubbles: true }));
    }
    await sleep(400);
    await clickButton('Aceptar');
    await sleep(1000);

    // ── FASE 7: Resumen — el asesor da el clic final ─────────────────
    navigateTab('resumen');
    await sleep(1000);
    setPasos(PASOS, 7);
    setEstado('✅ Formulario llenado. Revisa el Resumen y da clic en <strong>"Enviar solicitud"</strong>.', 'ok');
    setAcciones([
      { texto: '🔍 Ya envié, detectar acuse', estilo: 'verde', accion: detectarYReportar },
      { texto: '↻ Repetir llenado', accion: () => location.reload() },
    ]);
  }

  // ─── Detección y reporte del acuse ──────────────────────────────────────

  async function detectarYReportar() {
    if (!tarea || reportado) return;
    reportado = true;
    setEstado('Detectando folio y acuse…');
    setAcciones([]);

    await sleep(1500);

    const texto = document.body ? document.body.innerText : '';
    const url = location.href;
    const folio = extraerFolio(texto, url);

    setEstado(`📄 Folio detectado: <strong>${folio || 'pendiente'}</strong>. Buscando acuse…`, 'ok');

    // Descargar acuse PDF (si hay enlace)
    let acuse = null;
    try {
      acuse = await descargarAcuse();
    } catch (_) { /* sin acuse */ }

    // Screenshot del acuse
    let captura = null;
    try {
      const resp = await chrome.runtime.sendMessage({ action: 'captura' });
      if (resp && resp.ok) captura = resp.dataUrl.split(',')[1] || null;
    } catch (_) { /* sin captura */ }

    // Reportar a la app
    setEstado('Guardando folio y acuse en la app…');
    const payload = {
      estado: 'completado',
      folio,
      detalle: `Llenado desde la Extensión de Chrome. URL final: ${url}`,
      screenshots: captura ? [captura] : [],
    };
    if (acuse) {
      payload.acuse_pdf = acuse.b64;
      payload.acuse_nombre = acuse.nombre;
    }

    try {
      const resp = await chrome.runtime.sendMessage({
        action: 'reportar',
        taskId: tarea.id,
        payload,
      });
      if (resp && resp.ok) {
        setEstado(`🎉 ¡Listo! Folio <strong>${folio || 'N/A'}</strong> guardado en la app.`, 'ok');
        setPasos(['✅ Aviso', '✅ Industria', '✅ Fecha/objeto', '✅ Solicitante',
                  '✅ Citado', '✅ Descripción', '✅ Envío', '✅ Acuse guardado'], 8);
      } else {
        setEstado(`⚠️ Se envió al portal (folio: ${folio || 'N/A'}), pero no se pudo guardar en la app: ${resp ? resp.error : 'sin respuesta'}`, 'warn');
        setAcciones([{ texto: 'Intentar guardar de nuevo', accion: () => { reportado = false; detectarYReportar(); } }]);
      }
    } catch (e) {
      setEstado(`⚠️ Error al guardar en la app: ${e.message}. El folio ${folio || ''} ya quedó en el portal.`, 'warn');
      setAcciones([{ texto: 'Intentar de nuevo', accion: () => { reportado = false; detectarYReportar(); } }]);
    }
  }

  // ─── Inicio: pedir la tarea activa al background ────────────────────────

  async function init() {
    // Solo actuar en la página de solicitud del portal
    if (!location.pathname.includes('/solicitudes/create')) return;

    try {
      const resp = await chrome.runtime.sendMessage({ action: 'datos' });
      if (resp && resp.ok && resp.tarea) {
        tarea = resp.tarea;
        crearPanel();

        // Si la página ya NO muestra el formulario (ej. se recargó en la
        // confirmación tras el envío), no re-llenar: ir directo a detectar.
        const hayFormulario = !!byName('radioAviso') || !!byName('solicitante[nombre]');
        if (!hayFormulario) {
          setEstado('Formulario ya enviado. Detectando acuse…', 'ok');
          detectarYReportar();
          return;
        }

        setEstado('Tarea encontrada. Llenando el formulario…');
        llenar();
      }
    } catch (_) {
      // Sin background accesible — no hacer nada
    }
  }

  // Esperar un poco a que la página esté lista
  setTimeout(init, 1200);
})();
