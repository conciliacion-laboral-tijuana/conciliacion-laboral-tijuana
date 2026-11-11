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

## Privacidad

El dictado usa la Web Speech API del navegador. En Chrome/Edge **el audio lo
procesa el servicio del navegador**, no el servidor del despacho. Para datos
reales conviene mover la transcripción al servidor con un modelo local
(pendiente); mientras tanto, la pantalla lo advierte al pie.

Sin dictado (Firefox, navegador sin permisos de micrófono) la pantalla funciona
igual escribiendo el dato.

## Arquitectura

```
expedientes/captura_voz.py       guion, parseo de fechas/dinero/hora/modalidad
expedientes/views.py             captura_voz + captura_voz_interpretar
templates/expedientes/captura_voz.html
static/js/captura_voz.js         wizard, micrófono, resumen y guardado
expedientes/tests_captura_voz.py 35 pruebas
```

El endpoint `POST /expedientes/<pk>/captura-voz/interpretar/` recibe
`{campo, texto}` y devuelve `{valor, etiqueta, aviso, error}`. Así las reglas
viven en Python y el navegador sólo conversa.

## Pruebas

```bash
.venv/Scripts/python.exe manage.py test expedientes.tests_captura_voz \
    --settings=config.settings_test
```

Cubren la interpretación (fechas en palabras, dinero, hora, modalidad), que no
se invente nada, el marcado de lo ya capturado, los permisos, el guardado
parcial, que el tipo de separación no cambie y el endpoint de interpretación.

## Limitaciones de esta versión

- Necesita un expediente ya creado (no crea uno desde cero).
- No captura tipo de separación, IMSS, prestaciones ni representación.
- No hay «narración libre» (un relato que llene varios campos a la vez).
- La transcripción es del navegador, no del servidor.
- No incluye la subida de fotos de documentos.
