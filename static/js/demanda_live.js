/* Keep capture requests ordered so an older draft cannot overwrite a newer one. */
(function () {
  const form = document.getElementById('acordeonForm');
  if (!form) return;
  const status = document.getElementById('demanda-preview-status');
  const errors = document.getElementById('demanda-preview-errors');
  const frame = document.getElementById('demanda-preview-frame');
  const warning = document.getElementById('demanda-calculo-aviso');
  let revision = 0;
  let timer;
  let pending = null;
  let changed = false;
  let submitting = false;
  let nativeSubmit = false;

  function showErrors(messages) {
    errors.replaceChildren();
    for (const message of messages) {
      const item = document.createElement('li');
      item.textContent = message;
      errors.appendChild(item);
    }
  }

  async function update(save) {
    if (pending || submitting) return;
    const current = revision;
    const data = new FormData(form);
    data.set('guardar_borrador', save ? '1' : '0');
    status.textContent = save ? 'Guardando borrador…' : 'Actualizando vista previa…';
    pending = (async function () {
      try {
        const response = await fetch(form.dataset.previewUrl, {
          method: 'POST', body: data, credentials: 'same-origin',
          headers: {'X-CSRFToken': data.get('csrfmiddlewaretoken')}
        });
        if (response.redirected) throw new Error('La sesión expiró. Inicia sesión para continuar.');
        const result = await response.json();
        if (current !== revision) return;
        if (!response.ok) {
          status.textContent = 'Cambios sin guardar. Corrige los datos para actualizar la demanda.';
          showErrors(result.errores ? Object.values(result.errores).flat() : [result.error || 'No se pudo actualizar.']);
          return;
        }
        const policy = "default-src 'none'; style-src 'unsafe-inline'";
        frame.srcdoc = '<!doctype html><html lang="es"><head><meta charset="utf-8">' +
          '<meta http-equiv="Content-Security-Policy" content="' + policy + '">' +
          '<style>body{font:14px Georgia,serif;padding:24px;line-height:1.6;overflow-wrap:anywhere}table{width:100%;border-collapse:collapse}td,th{border:1px solid #ddd;padding:6px}h3{margin-top:24px}</style>' +
          '</head><body>' + result.html + '</body></html>';
        warning.hidden = !result.calculo_pendiente;
        const pendienteErrores = result.errores
          ? Object.entries(result.errores).flatMap(([campo, msgs]) =>
              msgs.map(msg => campo + ': ' + msg))
          : [];
        showErrors(pendienteErrores
          .concat((result.faltantes || []).map(label => 'Pendiente: ' + label))
          .concat(result.calculo_error ? [result.calculo_error] : []));
        if (pendienteErrores.length) {
          status.textContent = result.guardado
            ? 'Guardado parcial: revisa los campos señalados.'
            : 'Cambios sin guardar. Corrige los campos señalados.';
          changed = !result.guardado;
        } else {
          status.textContent = result.guardado ? 'Borrador guardado. Vista previa actualizada.' : 'Vista previa actualizada.';
          if (result.guardado) changed = false;
        }
      } catch (error) {
        status.textContent = 'Cambios sin guardar. ' + error.message;
      }
    })();
    await pending;
    pending = null;
    if (current !== revision && !submitting) update(true);
  }

  function schedule() {
    changed = true;
    revision += 1;
    status.textContent = 'Cambios pendientes de guardar…';
    clearTimeout(timer);
    timer = setTimeout(() => update(true), 800);
  }
  form.addEventListener('input', schedule);
  form.addEventListener('change', schedule);
  form.addEventListener('submit', async function (event) {
    if (nativeSubmit) return;
    event.preventDefault();
    if (submitting) return;
    submitting = true;
    clearTimeout(timer);
    const submitter = event.submitter;
    if (pending) await pending;
    nativeSubmit = true;
    // Browsers ignore a reentrant requestSubmit during the first submit event.
    // Resume in a separate task, preserving which action the lawyer chose.
    setTimeout(() => form.requestSubmit(submitter), 0);
  });
  window.addEventListener('beforeunload', function (event) {
    if (changed && !submitting) {
      event.preventDefault();
      event.returnValue = '';
    }
  });
  update(false);
})();
