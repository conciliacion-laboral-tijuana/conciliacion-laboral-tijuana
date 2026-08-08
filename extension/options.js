// ══════════════════════════════════════════════════════════════════════════
//  Conciliación BC — Asistente · Opciones
// ══════════════════════════════════════════════════════════════════════════

const status = document.getElementById('status');
const btnGuardar = document.getElementById('guardar');

async function cargarConfig() {
  const resp = await chrome.runtime.sendMessage({ action: 'getConfig' });
  if (resp && resp.ok && resp.config) {
    document.getElementById('apiUrl').value = resp.config.apiUrl || '';
    document.getElementById('token').value = resp.config.token || '';
  }
}

btnGuardar.addEventListener('click', async () => {
  const apiUrl = document.getElementById('apiUrl').value.trim().replace(/\/+$/, '');
  const token = document.getElementById('token').value.trim();

  if (!apiUrl || !token) {
    status.textContent = '❌ Completa ambos campos.';
    status.className = 'err';
    return;
  }

  btnGuardar.disabled = true;
  btnGuardar.textContent = 'Verificando…';
  status.textContent = '';
  status.className = '';

  try {
    // Solicitar permiso de host para el dominio de la app (si es un dominio
    // custom que no está en host_permissions del manifest)
    try {
      await chrome.permissions.request({ origins: [apiUrl + '/*'] });
    } catch (_) { /* el usuario puede añadir el dominio manualmente */ }

    const resp = await chrome.runtime.sendMessage({
      action: 'guardarConfig',
      config: { apiUrl, token },
    });
    if (!resp.ok) throw new Error(resp.error);

    // Verificar que el token funcione
    const check = await chrome.runtime.sendMessage({ action: 'tareas' });
    if (check.ok) {
      status.textContent = '✅ Configuración guardada y verificada. ¡Listo para usar!';
      status.className = 'ok';
    } else {
      status.textContent = `⚠️ Guardada, pero la app respondió: ${check.error}`;
      status.className = 'err';
    }
  } catch (e) {
    status.textContent = `❌ Error: ${e.message}`;
    status.className = 'err';
  } finally {
    btnGuardar.disabled = false;
    btnGuardar.textContent = '💾 Guardar configuración';
  }
});

cargarConfig();
