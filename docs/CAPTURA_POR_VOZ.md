# Captura de datos por voz

Asistente que pregunta, uno a uno, los datos que la demanda necesita y los
guarda dictando. Ataca la fricción real del flujo: capturar decenas de campos
a mano. No calcula, no aprueba y no inventa: sólo captura.

## Cómo se usa

Expediente → botón **Capturar por voz** (`/expedientes/<pk>/captura-voz/`).

La pantalla muestra el dato que toca, el valor ya capturado (si lo hay), un
botón de micrófono, **Confirmar**, **Omitir** y **Anterior**. Al final aparece
un resumen con todo lo capturado y el botón **Guardar datos**.

- El guion empieza en el **primer dato vacío**, no en el primero de la lista.
- Los datos ya capturados se pueden revisar con **Anterior**.
- **Omitir** conserva lo que ya había; no borra.
- **Guardar** manda al espacio **Datos** de la demanda con un aviso.

## Qué interpreta

El dictado no se guarda a ciegas: fechas, dinero, hora y modalidad pasan por
reglas deterministas (`expedientes/captura_voz.py`) y se muestran como
«Entendí: …» antes de confirmar.

| Dato | Ejemplo dictado | Se guarda |
|---|---|---|
| Fecha | «3 de mayo de 2022», «tres de mayo de dos mil veintidós», «03/05/2022» | `2022-05-03` |
| Salario | «doce mil cuatrocientos», «$12,400», «2 mil» | `12400.00` |
| Hora | «14:45», «2:45 pm», «2 y 45 de la tarde» | `14:45` |
| Modalidad | «verbal», «me dieron un papel», «no me dejaron entrar» | `verbal`, `escrito`, `acceso` |
| CURP | «gupg 850315 hbcrrs08» | `GUPG850315HBCRRS08` (avisa si no son 18) |

Si no se entiende, **el campo se queda vacío y se avisa**; no se adivina.

## Guardado

La vista llama a `_validar_captura_demanda`, la MISMA función del acordeón: no
hay una segunda ruta de escritura. Se guarda lo válido aunque otro campo venga
mal, y los errores se muestran por campo.

La captura por voz **no toca** el tipo de separación, el IMSS, las prestaciones
ni la representación. Eso sigue en Estrategia y Datos.

## Transcripción del audio

Hay dos modos y la pantalla elige sola el mejor disponible:

| Modo | Dónde se procesa el audio | Cuándo se usa |
|---|---|---|
| **Servidor (local)** | En el servidor del despacho, con `faster-whisper` | Si las dependencias están instaladas |
| **Navegador** | En el servicio de dictado del navegador (Google/Microsoft) | Si no hay modelo local |

### Activar el modo servidor

```bash
uv pip install -r requirements-voz.txt
```

La primera transcripción descarga el modelo (unos 150 MB para `base`) en
`WHISPER_CACHE` (`media/whisper` por defecto). El audio **no se guarda**: se
escribe en un temporal, se transcribe y se borra.

Variables de entorno (todas opcionales):

| Variable | Default | Para qué |
|---|---|---|
| `TRANSCRIPCION_BACKEND` | `auto` | `auto` (local si está instalado), `local` u `browser` |
| `WHISPER_MODEL` | `base` | `tiny`, `base`, `small`… (más grande = más preciso y más lento) |
| `WHISPER_DEVICE` | `cpu` | `cpu` o `cuda` |
| `WHISPER_COMPUTE_TYPE` | `int8` | `int8` (CPU), `float16` (GPU) |
| `WHISPER_IDIOMA` | `es` | Idioma del dictado |
| `WHISPER_CACHE` | `media/whisper` | Dónde viven los pesos del modelo |
| `WHISPER_PROMPT` | vacío | Texto de contexto para el modelo (sin datos de clientes) |
| `MAX_AUDIO_DICTADO_BYTES` | 8 MB | Tope de audio por dictado |

Si el modelo no está instalado, `auto` cae al dictado del navegador sin romper
la pantalla. En producción hace falta instalar las dos dependencias y darle a
`WHISPER_CACHE` un volumen persistente (o bajar los pesos en la imagen), porque
el sistema de archivos de Railway es efímero.

> `requirements-voz.txt` fija `av<19`: faster-whisper 1.2 usa `metadata_errors`,
> que PyAV 19 ya no acepta.

### Precisión: lo que hay que saber

Medido con voz sintética en español y el modelo `base`:

- **Fechas**: muy bien. «Empezó a trabajar el tres de mayo de dos mil veintidós»
  → «Empezó a trabajar el 3 de mayo de 2022».
- **Cantidades**: la cifra se entiende cuando se dicta **sola**. «Doce mil
  cuatrocientos pesos» → «12.400 pesos»; pero dentro de una frase («gana doce
  mil…») el modelo puede perder el «doce mil». Por eso la pregunta pide **sólo
  la cantidad** y la pantalla muestra «Entendí: $12,400.00 mensual» antes de
  confirmar.

Aun así, el salario es el dato más delicado: conviene confirmarlo visualmente en
el resumen y, si el importe es grande, dictarlo solo. La interpretación también
entiende `12.400` y `12,400` como doce mil cuatrocientos.

## Privacidad

- **Modo servidor**: el audio no sale del despacho; se borra al terminar y no se
  registra en logs.
- **Modo navegador**: el audio lo procesa el servicio del navegador. La pantalla
  lo advierte al pie cuando está en ese modo.

En ambos casos el texto transcripto sólo se guarda si el asesor confirma el
dato; el resumen muestra lo que se va a escribir.

Sin dictado (Firefox, navegador sin permisos de micrófono) la pantalla funciona
igual escribiendo el dato.

## Arquitectura

```
expedientes/captura_voz.py       guion, parseo de fechas/dinero/hora/modalidad
expedientes/transcripcion.py     modelo local (faster-whisper) y borrado del audio
expedientes/views.py             captura_voz + captura_voz_interpretar
                                 + captura_voz_transcribir
templates/expedientes/captura_voz.html
static/js/captura_voz.js         wizard, grabación, transcripción y guardado
expedientes/tests_captura_voz.py 36 pruebas
expedientes/tests_transcripcion.py 12 pruebas
```

Los endpoints:

- `POST /expedientes/<pk>/captura-voz/interpretar/` recibe `{campo, texto}` y
  devuelve `{valor, etiqueta, aviso, error}`.
- `POST /expedientes/<pk>/captura-voz/transcribir/` recibe el audio en
  `multipart/form-data` (campo `audio`) y devuelve `{texto, error}`.

Así las reglas y el modelo viven en Python y el navegador sólo conversa.

## Pruebas

```bash
.venv/Scripts/python.exe manage.py test expedientes.tests_captura_voz \
    expedientes.tests_transcripcion --settings=config.settings_test
```

`tests_captura_voz` cubre la interpretación (fechas en palabras, dinero, hora,
modalidad), que no se invente nada, el marcado de lo ya capturado, los permisos,
el guardado parcial y que el tipo de separación no cambie.

`tests_transcripcion` cubre el endpoint de audio sin depender del modelo:
disponibilidad, permisos, tamaño, audio sin texto y errores del modelo.

## Limitaciones de esta versión

- Necesita un expediente ya creado (no crea uno desde cero).
- No captura tipo de separación, IMSS, prestaciones ni representación.
- No hay «narración libre» (un relato que llene varios campos a la vez).
- No incluye la subida de fotos de documentos.
- La transcripción bloquea un worker mientras dura (segundos); para muchas
  capturas simultáneas conviene pasarla a una tarea de Celery.
- Los nombres propios y las CURP dictadas se revisan a mano: el modelo puede
  confundir letras.
