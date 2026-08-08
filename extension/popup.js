// ══════════════════════════════════════════════════════════════════════════
//  Conciliación BC — Asistente · Popup
// ══════════════════════════════════════════════════════════════════════════

document.getElementById('btn-opciones').addEventListener('click', e => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});

async function init() {
  const cargando = document.getElementById('cargando');
  const lista = document.getElementById('lista');
  const vacio = document.getElementById('vacío');
  const avisoConfig = document.getElementById('aviso-config');

  try {
    // Verificar configuración
    const cfgResp = await chrome.runtime.sendMessage({ action: 'getConfig' });
    const config = (cfgResp && cfgResp.config) || {};
    if (!config.apiUrl || !config.token) {
      avisoConfig.style.display = 'block';
    }

    const resp = await chrome.runtime.sendMessage({ action: 'tareas' });
    cargando.style.display = 'none';

    if (!resp.ok) {
      avisoConfig.style.display = 'block';
      avisoConfig.textContent = `⚠️ ${resp.error}`;
      return;
    }

    const tareas = resp.tareas || [];
    if (tareas.length === 0) {
      vacio.style.display = 'block';
      return;
    }

    lista.style.display = 'block';
    lista.innerHTML = '';
    for (const t of tareas) {
      const card = document.createElement('div');
      card.className = 'card';
      card.innerHTML = `
        <div class="titulo">📁 ${t.expediente.numero} — ${t.cliente.nombre}</div>
        <div class="sub">${t.cliente.empresa_nombre || 'Empresa'}</div>
        <div class="folio">CURP: ${t.cliente.curp || '—'}</div>
        <button class="btn btn-primario" data-id="${t.id}">🚀 Llenar en el portal</button>
      `;
      card.querySelector('button').addEventListener('click', async e => {
        const btn = e.target;
        btn.disabled = true;
        btn.textContent = 'Abriendo el portal…';
        const resp2 = await chrome.runtime.sendMessage({ action: 'abrir', taskId: t.id });
        if (!resp2.ok) {
          btn.disabled = false;
          btn.textContent = `⚠️ ${resp2.error}`;
        } else {
          btn.textContent = '✅ Portal abierto — llena el formulario ahí';
          window.close();
        }
      });
      lista.appendChild(card);
    }
  } catch (e) {
    cargando.style.display = 'none';
    avisoConfig.style.display = 'block';
    avisoConfig.textContent = `⚠️ Error: ${e.message}`;
  }
}

init();
