// ══════════════════════════════════════════════════════════════════════════
//  Conciliación BC — Asistente · Service Worker (MV3)
//
//  Puntos de comunicación:
//    popup  →  background : { action: 'tareas' }                    → lista tareas
//    popup  →  background : { action: 'abrir', taskId }             → abre el portal
//    content → background : { action: 'datos', taskId }             → datos para llenar
//    content → background : { action: 'reportar', payload }         → folio/acuse a la app
// ══════════════════════════════════════════════════════════════════════════

const CONFIG_KEY = 'config';

// ─── Configuración (URL de la app + token) ───────────────────────────────

async function getConfig() {
  const stored = await chrome.storage.local.get(CONFIG_KEY);
  return stored[CONFIG_KEY] || { apiUrl: '', token: '' };
}

async function saveConfig(config) {
  await chrome.storage.local.set({ [CONFIG_KEY]: config });
}

// ─── API de la app ────────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const config = await getConfig();
  if (!config.apiUrl || !config.token) {
    throw new Error('Configura primero la URL de la app y tu token (clic derecho en el ícono → Opciones).');
  }
  const url = config.apiUrl.replace(/\/+$/, '') + path;
  const headers = {
    'Authorization': `Token ${config.token}`,
    ...(options.headers || {}),
  };
  if (options.body && typeof options.body !== 'string') {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }
  const res = await fetch(url, { ...options, headers });
  let data = null;
  try { data = await res.json(); } catch (_) { /* no JSON */ }
  if (!res.ok) {
    const msg = (data && data.error) || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

// ─── Mensajes ─────────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    switch (message.action) {

      case 'tareas': {
        const data = await apiFetch('/api/extension/tareas/');
        sendResponse({ ok: true, tareas: data.tareas || [] });
        break;
      }

      case 'abrir': {
        // El popup pidió llenar una tarea: abrir el portal en una pestaña.
        const data = await apiFetch('/api/extension/tareas/');
        const tarea = (data.tareas || []).find(t => t.id === message.taskId);
        if (!tarea) {
          sendResponse({ ok: false, error: 'La tarea ya no está pendiente (¿otro asesor la tomó?).' });
          break;
        }
        // Guardar los datos para que el content script los tome al cargar
        await chrome.storage.session.set({ tareaActiva: tarea });
        const tab = await chrome.tabs.create({ url: tarea.portal.url_solicitud, active: true });
        sendResponse({ ok: true, tabId: tab.id, tareaId: tarea.id });
        break;
      }

      case 'datos': {
        // El content script pide los datos de la tarea activa
        const s = await chrome.storage.session.get('tareaActiva');
        const tarea = s.tareaActiva || null;
        if (tarea && message.taskId && tarea.id !== message.taskId) {
          sendResponse({ ok: false, error: 'La tarea activa no coincide.' });
          break;
        }
        sendResponse({ ok: !!tarea, tarea });
        break;
      }

      case 'captura': {
        // Screenshot de la pestaña (para el espejo en vivo)
        try {
          const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
          const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'png' });
          sendResponse({ ok: true, dataUrl });
        } catch (e) {
          sendResponse({ ok: false, error: e.message });
        }
        break;
      }

      case 'reportar': {
        const result = await apiFetch(`/api/extension/tareas/${message.taskId}/reportar/`, {
          method: 'POST',
          body: message.payload,
        });
        // Limpiar tarea activa al terminar
        await chrome.storage.session.remove('tareaActiva');
        sendResponse({ ok: true, result });
        break;
      }

      case 'guardarConfig': {
        await saveConfig(message.config);
        sendResponse({ ok: true });
        break;
      }

      case 'getConfig': {
        sendResponse({ ok: true, config: await getConfig() });
        break;
      }

      default:
        sendResponse({ ok: false, error: `Acción desconocida: ${message.action}` });
    }
  })().catch(err => {
    console.error('[background] Error:', err);
    sendResponse({ ok: false, error: err.message });
  });
  return true; // respuesta asíncrona
});
