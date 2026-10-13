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
  const dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'];
  const valor = key => document.getElementById('horario-' + key).value;
  const minutos = value => Number(value.slice(0, 2)) * 60 + Number(value.slice(3));
  function horasHorario(entrada, ordinaria, salida) {
    const inicio = minutos(entrada);
    let fin = minutos(ordinaria), cierre = minutos(salida);
    if (fin < inicio) fin += 1440;
    if (cierre < inicio) cierre += 1440;
    if (fin > cierre || cierre === inicio) throw new Error('Revisa el orden de los horarios.');
    return ((cierre - fin) / 60).toFixed(2);
  }
  document.getElementById('generar-semanas-horario').addEventListener('click', function () {
    const mensaje = document.getElementById('horario-mensaje');
    try {
      const desde = valor('desde'), hasta = valor('hasta');
      const ingreso = document.getElementById('id_fecha_ingreso').value;
      const salidaRelacion = document.getElementById('id_fecha_salida').value;
      if (!desde || !hasta || desde > hasta || !ingreso || !salidaRelacion || desde < ingreso || hasta > salidaRelacion)
        throw new Error('Indica un periodo válido dentro de las fechas de la relación laboral.');
      const entrada = valor('entrada'), ordinaria = valor('ordinaria'), salida = valor('salida');
      if (!entrada || !ordinaria || !salida || !(Number(valor('salario')) > 0) || valor('limite') === '' || Number(valor('limite')) < 0 || Number(valor('limite')) > 168)
        throw new Error('Completa horarios, salario y umbral semanal.');
      const horas = horasHorario(entrada, ordinaria, salida);
      const seleccionados = [...document.querySelectorAll('#horario-dias input:checked')].map(x => Number(x.value));
      if (!seleccionados.length || Number(horas) === 0) throw new Error('Selecciona días y un tramo extraordinario mayor que cero.');
      const propuestas = new Map();
      const iso = d => d.toISOString().slice(0, 10);
      for (let fecha = new Date(desde + 'T00:00:00Z'); iso(fecha) <= hasta; fecha.setUTCDate(fecha.getUTCDate() + 1)) {
        const dia = (fecha.getUTCDay() + 6) % 7;
        if (!seleccionados.includes(dia)) continue;
        const lunes = new Date(fecha); lunes.setUTCDate(lunes.getUTCDate() - dia);
        const key = iso(lunes);
        if (!propuestas.has(key)) propuestas.set(key, []);
        propuestas.get(key).push(dia);
      }
      const existentes = new Set([...document.querySelectorAll('#semanas-rows input[name$="-semana"]')].map(x => x.value));
      if ([...propuestas.keys()].some(key => existentes.has(key))) throw new Error('El periodo contiene semanas ya capturadas. Ajusta esas filas para conservar sus horas y pagos.');
      const total = document.getElementById('id_semanas-TOTAL_FORMS');
      if (Number(total.value) + propuestas.size > 520) throw new Error('Se permiten hasta 520 semanas.');
      for (const [semana, indices] of propuestas) {
        const index = Number(total.value);
        document.getElementById('agregar-semana').click();
        const set = (key, value) => { document.getElementById('id_semanas-' + index + '-' + key).value = value; };
        set('semana', semana); set('salario_diario', valor('salario')); set('jornada', valor('jornada')); set('limite_dobles', valor('limite')); set('pagado', '0');
        dias.forEach(dia => set(dia, '0'));
        indices.forEach(i => { const dia = dias[i]; set(dia, horas); set('entrada_' + dia, entrada); set('ordinaria_' + dia, ordinaria); set('salida_' + dia, salida); });
      }
      mensaje.textContent = propuestas.size + ' semanas generadas. Revisa ausencias, descansos, cambios de salario y pagos antes de calcular.';
      total.dispatchEvent(new Event('change', {bubbles: true}));
    } catch (error) { mensaje.textContent = error.message; }
  });
  form.addEventListener('change', function (event) {
    const match = (event.target.name || '').match(/^semanas-(\d+)-(entrada|ordinaria|salida)_(\w+)$/);
    if (!match) return;
    const prefix = 'id_semanas-' + match[1] + '-';
    const valores = ['entrada', 'ordinaria', 'salida'].map(key => document.getElementById(prefix + key + '_' + match[3]).value);
    if (valores.every(Boolean)) {
      try { document.getElementById(prefix + match[3]).value = horasHorario(...valores); } catch (_) { /* El servidor muestra el error. */ }
    }
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
