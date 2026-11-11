/* Captura de datos por voz: guion guiado + dictado.
 *
 * El servidor manda el guion (con lo ya capturado) y la interpretación de
 * fechas, dinero, hora y modalidad se hace en `captura_voz_interpretar` para
 * que las reglas vivan en un solo lugar (Python). Este archivo sólo orquesta
 * la conversación: pregunta, escucha, muestra lo que entendió y guarda.
 *
 * El audio se transcribe en el servidor (`captura_voz_transcribir`, modelo
 * local) cuando está disponible; si no, se usa el dictado del navegador.
 */
(function () {
  'use strict';

  const el = (id) => document.getElementById(id);
  const pasos = JSON.parse(el('voz-pasos').textContent);
  const config = JSON.parse(el('voz-config').textContent);
  const total = pasos.length;
  const csrfInput = document.querySelector('#voz-form input[name="csrfmiddlewaretoken"]');
  const csrf = csrfInput ? csrfInput.value : '';
  const interpretarUrl = new URL('interpretar/', window.location.href).toString();
  const usaServidor = Boolean(config.servidor && config.transcribir_url);

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;

  const panel = el('voz-panel');
  const resumen = el('voz-resumen');
  const pregunta = el('voz-pregunta');
  const ayuda = el('voz-ayuda');
  const grupo = el('voz-grupo');
  const pasoN = el('voz-paso');
  const totalN = el('voz-total');
  const barra = el('voz-barra');
  const capturados = el('voz-capturados');
  const transcripcion = el('voz-transcripcion');
  const input = el('voz-input');
  const opciones = el('voz-opciones');
  const estado = el('voz-estado');
  const mic = el('voz-mic');
  const confirmarBtn = el('voz-confirmar');
  const omitirBtn = el('voz-omitir');
  const anteriorBtn = el('voz-anterior');
  const soporte = el('voz-soporte');
  const lista = el('voz-resumen-lista');
  const guardarBtn = el('voz-guardar');
  const volverBtn = el('voz-volver');
  const errorBox = el('voz-error');

  const valores = {};
  const etiquetas = {};
  pasos.forEach(function (p) {
    if (p.valor) {
      valores[p.campo] = p.valor;
      etiquetas[p.campo] = p.etiqueta || p.valor;
    }
  });

  let idx = 0;
  const primeroPendiente = pasos.findIndex(function (p) { return !p.capturado; });
  if (primeroPendiente >= 0) idx = primeroPendiente;

  let reconocimiento = null;
  let grabadora = null;
  let flujoAudio = null;
  let temporizadorGrabacion = null;
  let grabando = false;
  let textoFinal = '';
  let etiquetaTemporal = '';
  let ultimoInterpretado = null;
  let guardando = false;

  const TIPOS_INTERPRETADOS = ['fecha', 'dinero', 'hora', 'modalidad'];

  function aviso(texto, clase) {
    estado.textContent = texto || '';
    estado.className = 'voz-estado' + (clase ? ' ' + clase : '');
  }

  function pintar() {
    if (idx >= total) {
      mostrarResumen();
      return;
    }
    const p = pasos[idx];
    pregunta.textContent = p.pregunta;
    ayuda.textContent = p.ayuda || '';
    grupo.textContent = p.grupo || '';
    pasoN.textContent = String(idx + 1);
    totalN.textContent = String(total);

    const capturadosAhora = Object.keys(valores).length;
    capturados.textContent = capturadosAhora + ' capturado' + (capturadosAhora === 1 ? '' : 's');
    barra.style.width = ((idx / total) * 100).toFixed(1) + '%';

    transcripcion.textContent = '';
    textoFinal = '';
    etiquetaTemporal = '';
    ultimoInterpretado = null;

    input.value = valores[p.campo] || '';
    if (p.tipo === 'fecha') {
      input.type = 'date';
      input.placeholder = '';
      input.removeAttribute('step');
    } else if (p.tipo === 'dinero') {
      input.type = 'number';
      input.step = '0.01';
      input.min = '0';
      input.placeholder = 'Ej. 12400.00';
    } else {
      input.type = 'text';
      input.removeAttribute('step');
      input.placeholder = p.tipo === 'hora' ? 'Ej. 14:45' : '';
    }

    if (valores[p.campo]) {
      aviso('Capturado: ' + (etiquetas[p.campo] || valores[p.campo]), 'ok');
    } else {
      aviso('Sin capturar');
    }

    opciones.innerHTML = '';
    opciones.hidden = p.tipo !== 'modalidad';
    if (p.tipo === 'modalidad') {
      (p.opciones || []).forEach(function (opcion) {
        const boton = document.createElement('button');
        boton.type = 'button';
        boton.className = 'voz-opcion' +
          (input.value === opcion.valor ? ' marcada' : '');
        boton.textContent = opcion.etiqueta;
        boton.addEventListener('click', function () {
          elegirModalidad(opcion.valor, opcion.etiqueta, boton);
        });
        opciones.appendChild(boton);
      });
    }

    mic.disabled = usaServidor ? false : !SR;
    mic.classList.remove('rec');
    mic.textContent = '🎤 Hablar';
    confirmarBtn.disabled = false;
    omitirBtn.disabled = false;
    anteriorBtn.disabled = idx === 0;
    // En el teléfono, enfocar el campo abre el teclado y tapa la pantalla.
    if (!window.matchMedia('(pointer: coarse)').matches) {
      input.focus({ preventScroll: true });
    }
  }

  function elegirModalidad(valor, etiqueta, boton) {
    input.value = valor;
    etiquetaTemporal = etiqueta;
    ultimoInterpretado = valor;
    aviso('Entendí: ' + etiqueta, 'ok');
    Array.prototype.forEach.call(opciones.children, function (hijo) {
      hijo.classList.toggle('marcada', hijo === boton);
    });
  }

  function interpretar(texto) {
    const p = pasos[idx];
    const indice = idx;
    if (TIPOS_INTERPRETADOS.indexOf(p.tipo) === -1) {
      etiquetaTemporal = texto;
      ultimoInterpretado = texto;
      aviso('Listo para confirmar', 'ok');
      return;
    }
    aviso('Interpretando…');
    fetch(interpretarUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf
      },
      body: JSON.stringify({ campo: p.campo, texto: texto })
    })
      .then(function (respuesta) { return respuesta.json(); })
      .then(function (datos) {
        if (indice !== idx) return; // el asesor ya cambió de dato
        if (datos.error) {
          ultimoInterpretado = null;
          aviso(datos.error, 'error');
          return;
        }
        input.value = datos.valor;
        etiquetaTemporal = datos.etiqueta;
        ultimoInterpretado = datos.valor;
        aviso('Entendí: ' + datos.etiqueta + (datos.aviso ? ' · ' + datos.aviso : ''),
              datos.aviso ? 'aviso' : 'ok');
      })
      .catch(function () {
        if (indice !== idx) return;
        aviso('No se pudo interpretar el dictado. Escribe el dato.', 'error');
      });
  }

  function iniciarMicrofono() {
    if (!SR || grabando) return;
    textoFinal = '';
    transcripcion.textContent = '';
    const indice = idx;
    reconocimiento = new SR();
    reconocimiento.lang = 'es-MX';
    reconocimiento.interimResults = true;
    reconocimiento.continuous = false;
    reconocimiento.maxAlternatives = 1;

    reconocimiento.onstart = function () {
      grabando = true;
      mic.classList.add('rec');
      mic.textContent = '⏹ Detener';
      aviso('Escuchando…');
    };

    reconocimiento.onresult = function (evento) {
      let interino = '';
      for (let i = evento.resultIndex; i < evento.results.length; i += 1) {
        const trozo = evento.results[i][0].transcript;
        if (evento.results[i].isFinal) {
          textoFinal = (textoFinal + ' ' + trozo).trim();
        } else {
          interino += trozo;
        }
      }
      transcripcion.textContent = (textoFinal + ' ' + interino).trim();
    };

    reconocimiento.onerror = function (evento) {
      grabando = false;
      mic.classList.remove('rec');
      mic.textContent = '🎤 Hablar';
      if (evento.error === 'not-allowed' || evento.error === 'service-not-allowed') {
        aviso('El micrófono está bloqueado. Permítelo en el navegador o escribe el dato.', 'error');
      } else if (evento.error === 'no-speech') {
        aviso('No se escuchó nada. Intenta de nuevo o escribe el dato.', 'aviso');
      } else {
        aviso('No se pudo dictar. Escribe el dato.', 'error');
      }
    };

    reconocimiento.onend = function () {
      grabando = false;
      mic.classList.remove('rec');
      mic.textContent = '🎤 Hablar';
      if (indice !== idx) return; // el asesor ya cambió de dato
      const texto = (textoFinal || transcripcion.textContent || '').trim();
      if (texto) {
        input.value = texto;
        interpretar(texto);
      }
    };

    try {
      reconocimiento.start();
    } catch (error) {
      aviso('No se pudo iniciar el micrófono. Escribe el dato.', 'error');
    }
  }

  function detenerMicrofono() {
    if (reconocimiento && grabando) {
      try { reconocimiento.stop(); } catch (error) { /* ya terminó */ }
    }
  }

  // ─── Grabación y transcripción en el servidor ──────────────────────────

  function liberarAudio() {
    if (flujoAudio) {
      flujoAudio.getTracks().forEach(function (pista) { pista.stop(); });
      flujoAudio = null;
    }
  }

  function iniciarGrabacion() {
    if (typeof MediaRecorder === 'undefined' || !navigator.mediaDevices ||
        !navigator.mediaDevices.getUserMedia) {
      aviso('Este navegador no permite grabar audio. Escribe el dato.', 'error');
      return;
    }
    aviso('Pidiendo permiso del micrófono…');
    navigator.mediaDevices.getUserMedia({ audio: true }).then(function (flujo) {
      flujoAudio = flujo;
      const tipos = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus',
        'audio/mp4', 'audio/webm'];
      let tipo = '';
      for (let i = 0; i < tipos.length; i += 1) {
        if (MediaRecorder.isTypeSupported(tipos[i])) { tipo = tipos[i]; break; }
      }
      const trozos = [];
      const rec = tipo ? new MediaRecorder(flujo, { mimeType: tipo })
        : new MediaRecorder(flujo);
      grabadora = rec;
      rec.ondataavailable = function (evento) {
        if (evento.data && evento.data.size) trozos.push(evento.data);
      };
      rec.onstop = function () {
        liberarAudio();
        grabadora = null;
        const blob = new Blob(trozos, { type: rec.mimeType || tipo || 'audio/webm' });
        grabando = false;
        mic.classList.remove('rec');
        mic.textContent = '🎤 Hablar';
        if (!blob.size) {
          aviso('No se grabó audio. Intenta de nuevo o escribe el dato.', 'aviso');
          return;
        }
        enviarAudio(blob);
      };
      rec.start();
      grabando = true;
      mic.classList.add('rec');
      mic.textContent = '⏹ Detener';
      aviso('Grabando… habla y pulsa Detener (máximo 60 segundos).');
      temporizadorGrabacion = setTimeout(detenerGrabacion, 60000);
    }).catch(function (error) {
      if (error && error.name === 'NotAllowedError') {
        aviso('El micrófono está bloqueado. Permítelo en el navegador o escribe el dato.', 'error');
      } else {
        aviso('No se pudo usar el micrófono. Escribe el dato.', 'error');
      }
    });
  }

  function detenerGrabacion() {
    if (temporizadorGrabacion) {
      clearTimeout(temporizadorGrabacion);
      temporizadorGrabacion = null;
    }
    if (grabadora && grabadora.state !== 'inactive') {
      try { grabadora.stop(); } catch (error) { /* ya terminó */ }
    }
  }

  function enviarAudio(blob) {
    const indice = idx;
    aviso('Transcribiendo el audio…');
    const datos = new FormData();
    datos.append('audio', blob, 'dictado.webm');
    fetch(config.transcribir_url, {
      method: 'POST',
      body: datos,
      headers: { 'X-CSRFToken': csrf }
    })
      .then(function (respuesta) {
        return respuesta.json().then(function (cuerpo) {
          return { ok: respuesta.ok, cuerpo: cuerpo };
        });
      })
      .then(function (resultado) {
        if (indice !== idx) return; // el asesor ya cambió de dato
        if (!resultado.ok) {
          aviso(resultado.cuerpo.error || 'No se pudo transcribir el audio.', 'error');
          return;
        }
        const texto = (resultado.cuerpo.texto || '').trim();
        if (!texto) {
          aviso(resultado.cuerpo.error ||
            'No se entendió el audio. Intenta de nuevo o escribe el dato.', 'aviso');
          return;
        }
        input.value = texto;
        interpretar(texto);
      })
      .catch(function () {
        if (indice !== idx) return;
        aviso('No se pudo transcribir el audio. Revisa la conexión o escribe el dato.', 'error');
      });
  }

  function detenerTodo() {
    if (usaServidor) {
      detenerGrabacion();
    } else {
      detenerMicrofono();
    }
  }

  function confirmar() {
    if (idx >= total) return;
    const p = pasos[idx];
    const valor = (input.value || '').trim();
    if (!valor) {
      omitir();
      return;
    }
    // Un dato interpretado (fecha, dinero, hora, modalidad) no se guarda si el
    // valor no pasó por la interpretación: primero se muestra «Entendí…».
    if (TIPOS_INTERPRETADOS.indexOf(p.tipo) !== -1 && ultimoInterpretado !== valor) {
      interpretar(valor);
      return;
    }
    valores[p.campo] = valor;
    etiquetas[p.campo] = (ultimoInterpretado === valor && etiquetaTemporal)
      ? etiquetaTemporal
      : valor;
    siguiente();
  }

  function omitir() {
    siguiente();
  }

  function siguiente() {
    detenerTodo();
    idx += 1;
    if (idx >= total) {
      mostrarResumen();
    } else {
      pintar();
    }
  }

  function anterior() {
    detenerTodo();
    if (idx === 0) return;
    idx -= 1;
    pintar();
  }

  function mostrarResumen() {
    detenerTodo();
    panel.hidden = true;
    resumen.hidden = false;
    errorBox.hidden = true;
    errorBox.innerHTML = '';
    lista.innerHTML = '';
    let capturadosFinal = 0;
    pasos.forEach(function (p) {
      const li = document.createElement('li');
      const dato = document.createElement('span');
      dato.className = 'dato';
      dato.textContent = p.pregunta.replace(/^¿/, '').replace(/\?$/, '');
      const valor = document.createElement('span');
      valor.className = 'valor';
      if (valores[p.campo]) {
        capturadosFinal += 1;
        valor.textContent = etiquetas[p.campo] || valores[p.campo];
      } else {
        valor.className = 'valor vacio';
        valor.textContent = 'Sin capturar';
      }
      li.appendChild(dato);
      li.appendChild(valor);
      lista.appendChild(li);
    });
    const encabezado = resumen.querySelector('p');
    if (encabezado) {
      encabezado.textContent = capturadosFinal + ' de ' + total +
        ' datos listos. Los que queden vacíos se capturan después.';
    }
    resumen.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function volverASeguir() {
    resumen.hidden = true;
    panel.hidden = false;
    idx = 0;
    pintar();
  }

  function guardar() {
    if (guardando) return;
    guardando = true;
    guardarBtn.disabled = true;
    const datos = new FormData();
    datos.append('accion', 'guardar');
    datos.append('csrfmiddlewaretoken', csrf);
    Object.keys(valores).forEach(function (campo) {
      if (valores[campo]) datos.append(campo, valores[campo]);
    });

    fetch(window.location.href, {
      method: 'POST',
      body: datos,
      headers: { 'X-CSRFToken': csrf }
    })
      .then(function (respuesta) {
        return respuesta.json().then(function (cuerpo) {
          return { ok: respuesta.ok, cuerpo: cuerpo };
        });
      })
      .then(function (resultado) {
        if (resultado.ok && resultado.cuerpo.guardado) {
          window.location.href = resultado.cuerpo.redirect;
          return;
        }
        const errores = resultado.cuerpo.errores || {};
        const lineas = [];
        Object.keys(errores).forEach(function (campo) {
          const paso = pasos.find(function (p) { return p.campo === campo; });
          const nombre = paso ? paso.pregunta.replace(/^¿/, '').replace(/\?$/, '') : campo;
          (errores[campo] || []).forEach(function (mensaje) {
            lineas.push('<li><strong>' + nombre + ':</strong> ' + mensaje + '</li>');
          });
        });
        errorBox.innerHTML = '<strong>No se pudo guardar:</strong><ul>' +
          (lineas.join('') || '<li>Revisa los datos e intenta de nuevo.</li>') + '</ul>';
        errorBox.hidden = false;
        guardarBtn.disabled = false;
        guardando = false;
      })
      .catch(function () {
        errorBox.innerHTML = '<strong>No se pudo guardar:</strong> revisa la conexión e intenta de nuevo.';
        errorBox.hidden = false;
        guardarBtn.disabled = false;
        guardando = false;
      });
  }

  mic.addEventListener('click', function () {
    if (grabando) {
      detenerTodo();
    } else if (usaServidor) {
      iniciarGrabacion();
    } else {
      iniciarMicrofono();
    }
  });
  confirmarBtn.addEventListener('click', confirmar);
  omitirBtn.addEventListener('click', omitir);
  anteriorBtn.addEventListener('click', anterior);
  guardarBtn.addEventListener('click', guardar);
  volverBtn.addEventListener('click', volverASeguir);

  input.addEventListener('keydown', function (evento) {
    if (evento.key === 'Enter') {
      evento.preventDefault();
      confirmar();
    }
  });

  if (usaServidor) {
    soporte.textContent = 'Tu voz se transcribe en el servidor del despacho; el audio no se envía a terceros y se borra al terminar.';
  } else if (!SR) {
    soporte.textContent = 'Este navegador no permite dictado. Puedes escribir el dato y confirmar; funciona igual.';
    mic.disabled = true;
    mic.title = 'Dictado no disponible en este navegador';
  } else {
    soporte.textContent = 'El audio se procesa con el servicio de dictado del navegador.';
  }

  window.addEventListener('beforeunload', detenerTodo);

  pintar();
})();
