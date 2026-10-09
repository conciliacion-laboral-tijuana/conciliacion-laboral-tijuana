(function () {
  const form = document.getElementById('acordeonForm');
  if (!form) return;
  const tuvo = document.getElementById('id_tuvo_imss');
  const confirmado = document.getElementById('id_imss_confirmado');
  const details = document.getElementById('imss-detalles');
  function imss() { if (details) details.hidden = !(tuvo.checked && confirmado.checked); }
  if (tuvo && confirmado) { tuvo.addEventListener('change', imss); confirmado.addEventListener('change', imss); imss(); }
  document.getElementById('agregar-semana').addEventListener('click', function () {
    const total = document.getElementById('id_semanas-TOTAL_FORMS');
    const index = Number(total.value);
    if (index >= 520) return;
    const template = document.getElementById('semana-empty');
    const wrapper = document.createElement('div');
    wrapper.innerHTML = template.innerHTML.replaceAll('__prefix__', index);
    document.getElementById('semanas-rows').append(...wrapper.childNodes);
    total.value = index + 1;
    const state = document.getElementById('id_prestaciones-extras_estado');
    state.value = 'si';
    state.dispatchEvent(new Event('change', {bubbles: true}));
  });
  function invalidate(event) {
    if (!event.target.name || event.target.name === 'seccion_abierta') return;
    const summary = document.getElementById('calculo-final-resumen');
    if (summary.dataset.vigente === '1') {
      summary.hidden = true;
      document.getElementById('calculo-modificado').hidden = false;
    }
  }
  form.addEventListener('input', invalidate);
  form.addEventListener('change', invalidate);
})();
