/* Espacio de trabajo de la demanda: guardado automático, estado en vivo y
   salto al campo que falta.

   Antes esto era `demanda_live.js`: enviaba TODO el formulario cada 800 ms y
   reemplazaba un iframe con el documento. Ahora cada espacio tiene sólo sus
   campos, el autoguardado pide únicamente el estado (compacto) y los huecos del
   documento son enlaces al campo, no un iframe aparte. */
(function () {
  const form = document.getElementById('demandaForm');
  if (!form) return;

  const espacio = form.dataset.espacio || 'datos';
  const chip = document.getElementById('dem-chip');
  const estadoGuardado = document.getElementById('dem-guardado');
  const csrf = form.querySelector('input[name="csrfmiddlewaretoken"]');

  let temporizador = null;
  let pendiente = false;
  let enviando = null;
  let guardadoPendiente = false;
  let navegando = false;

  function aviso(texto) {
    if (estadoGuardado) estadoGuardado.textContent = texto;
  }

  // ─── Estado en vivo ──────────────────────────────────────────────
  function pintarChip(resumen) {
    if (!chip || !resumen) return;
    if (resumen.listo) {
      chip.className = 'dem-chip verde';
      chip.textContent = resumen.completo
        ? 'Sin datos pendientes: la demanda se puede presentar'
        : 'Se puede presentar · ' + resumen.opcionales + ' precisiones del relato por afinar';
    } else {
      chip.className = 'dem-chip ambar';
      let texto = 'Falta' + (resumen.obligatorios === 1 ? '' : 'n') + ' ' +
        resumen.obligatorios + ' requisito' + (resumen.obligatorios === 1 ? '' : 's') +
        ' para poder presentar';
      if (resumen.decisiones) {
        texto += ' · ' + resumen.decisiones +
          (resumen.decisiones === 1 ? ' es una decisión' : ' son decisiones') + ' del abogado';
      }
      chip.textContent = texto;
    }
  }

  function pintarBloques(porBloque) {
    if (!porBloque) return;
    document.querySelectorAll('.bloque[id^="sec-"]').forEach(function (seccion) {
      const chipBloque = seccion.querySelector('.bloque-estado');
      if (!chipBloque) return;
      const info = porBloque[seccion.id.slice(4)] || { obligatorios: 0, opcionales: 0 };
      if (info.obligatorios) {
        chipBloque.className = 'bloque-estado falta';
        chipBloque.textContent = 'Falta' + (info.obligatorios === 1 ? '' : 'n') +
          ' ' + info.obligatorios;
      } else {
        chipBloque.className = 'bloque-estado ok';
        chipBloque.textContent = '✓ Completo';
      }
    });
  }

  function mostrarErrores(errores) {
    if (!errores) return;
    const lista = Object.entries(errores).flatMap(function (par) {
      return par[1].map(function (mensaje) { return par[0] + ': ' + mensaje; });
    });
    if (lista.length) aviso('Sin guardar. ' + lista.join(' · '));
  }

  // ─── Envío ───────────────────────────────────────────────────────
  function enviar(conDocumento) {
    if (enviando) return enviando;
    const datos = new FormData(form);
    datos.set('guardar_borrador', '1');
    datos.set('compacto', '1');
    aviso('Guardando…');
    enviando = fetch(form.dataset.previewUrl, {
      method: 'POST',
      body: datos,
      credentials: 'same-origin',
      keepalive: Boolean(conDocumento),
      headers: { 'X-CSRFToken': csrf ? csrf.value : '' }
    })
      .then(function (respuesta) {
        if (respuesta.redirected) throw new Error('La sesión expiró. Inicia sesión de nuevo.');
        return respuesta.json();
      })
      .then(function (resultado) {
        pendiente = false;
        pintarChip(resultado.resumen);
        pintarBloques(resultado.por_bloque);
        if (resultado.errores) {
          mostrarErrores(resultado.errores);
          return;
        }
        aviso(resultado.guardado ? 'Borrador guardado.' : 'Sin cambios que guardar.');
      })
      .catch(function (error) {
        aviso('Sin guardar. ' + error.message);
      })
      .finally(function () { enviando = null; });
    return enviando;
  }

  function programar() {
    if (espacio === 'documento') return;
    pendiente = true;
    guardadoPendiente = true;
    aviso('Cambios pendientes de guardar…');
    clearTimeout(temporizador);
    temporizador = setTimeout(function () { enviar(false); }, 700);
  }

  if (espacio !== 'documento') {
    form.addEventListener('input', programar);
    form.addEventListener('change', programar);
  }

  // ─── No perder lo escrito al cambiar de espacio ──────────────────
  document.addEventListener('click', function (evento) {
    const enlace = evento.target.closest('a[href]');
    if (!enlace || !guardadoPendiente) return;
    const destino = enlace.getAttribute('href') || '';
    if (destino.charAt(0) === '#' || enlace.target === '_blank') return;
    if (enlace.dataset.espacio && enlace.dataset.espacio === espacio) return;
    evento.preventDefault();
    clearTimeout(temporizador);
    enviar(true).finally(function () { window.location.href = enlace.href; });
  });

  // El envío del propio formulario no se bloquea: el servidor guarda y
  // redibuja la página. Sin esta marca, el aviso de «cambios sin guardar»
  // aparecería justo al pulsar Guardar, Calcular o Aprobar, que son las
  // acciones que resuelven el pendiente.
  form.addEventListener('submit', function () {
    navegando = true;
    clearTimeout(temporizador);
  });

  window.addEventListener('beforeunload', function (evento) {
    if (navegando) return;
    if (pendiente || guardadoPendiente) {
      evento.preventDefault();
      evento.returnValue = '';
    }
  });

  // ─── Ir al campo que falta (enlaces de hueco del documento) ──────
  function enfocarDestino() {
    const hash = location.hash || '';
    if (hash.length < 2) return;
    const destino = document.getElementById(decodeURIComponent(hash.slice(1)));
    if (!destino) return;
    const grupo = destino.closest('[id^="grupo-"]') || destino;
    grupo.scrollIntoView({ behavior: 'smooth', block: 'center' });
    grupo.classList.add('grupo-destino');
    setTimeout(function () { grupo.classList.remove('grupo-destino'); }, 1600);
    if (destino.matches('input, textarea, select')) {
      destino.focus({ preventScroll: true });
    }
  }
  enfocarDestino();
  window.addEventListener('hashchange', enfocarDestino);
})();
