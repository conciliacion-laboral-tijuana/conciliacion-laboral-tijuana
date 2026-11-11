# Demanda por capítulos

Generador de demandas laborales con la estructura del estándar del despacho.
Reemplaza el enfoque anterior de "tabla + lista de artículos" por el documento
real que los abogados presentan.

## Estándar de referencia

`docs/referencia/demanda_injustificado_estandar.pdf` (14 páginas) define los
siete capítulos. El texto extraído está en el `.txt` de la misma carpeta.

| # | Capítulo | Naturaleza |
|---|---|---|
| 1 | Proemio (actor, domicilio, apoderados con cédula, autorizados) | Fijo + datos |
| 2 | Demandados (fuente de trabajo + moral) | Plantilla |
| 3 | CAPÍTULO DE PRESTACIONES | **Calculado** |
| 4 | Anexo: jornada semanal y horas extras | **Calculado** |
| 5 | CAPÍTULO DE HECHOS | Variable |
| 6 | PRUEBAS | Casi todo plantilla |
| 7 | CAPÍTULO DE DERECHO | Fijo |
| 8 | Apartado JURISPRUDENCIA (opcional) | Biblioteca + selección |

El apartado 8 no viene en el estándar de 14 páginas: se agregó a petición del
despacho. Va **después del capítulo de derecho y antes de la firma**, y sólo se
imprime si el abogado eligió tesis para ese expediente.

## Cómo usarlo

Desde el **espacio Documento** del espacio de trabajo de la demanda (botón
*Descargar demanda final*). O por URL: `GET /expedientes/<pk>/demanda/capitulos/` → `.docx`.

La pantalla **Documento** muestra el mismo escrito que se descarga, capítulo por
capítulo, con los datos que faltan señalados como huecos enlazados al campo que los
completa. Para eso `salida.capitulos_html()` devuelve los capítulos por separado
(`generar_demanda_capitulos_html()` los vuelve a unir en el mismo orden).

Antes de descargar se exige lo mismo que ya exigía el flujo anterior (datos críticos del
cliente y prestaciones calculadas y aprobadas) **más** que no quede ningún hueco
obligatorio: antes el `.docx` salía con `[DOMICILIO PARA NOTIFICACIONES]` y otros
marcadores dentro del escrito que se presenta. Redactar el borrador no se bloquea; lo que
se bloquea es el documento que se lleva al Tribunal. La lista de lo que bloquea sale de
`expedientes/demanda_estado.py`, la misma que alimenta el semáforo de la pantalla.

> Para capturar los datos del actor, la relación laboral, el patrón y la separación
> **hablando** (en lugar de teclearlos), ver [`docs/CAPTURA_POR_VOZ.md`](CAPTURA_POR_VOZ.md).

### Bloque de representación legal

Los **apoderados** (con cédula profesional) y los **autorizados** para oír y recibir
notificaciones se capturan en su propio bloque del espacio **Datos** y son los que arma el
proemio. Como en un despacho suelen ser siempre los mismos, el botón **Copiar del
expediente anterior** los reutiliza: toma los del expediente más reciente que los tenga y
agrega sólo los que falten (no duplica).

También se administran desde el admin de Django, y se muestran en el proemio en
el orden capturado («con número de cédula profesional X, Y y Z respectivamente»).

## Tipos de separación soportados

El HECHO CENTRAL y los conceptos cambian según la causa, no sólo la carátula:

| Tipo | Carátula | Qué reclama | Hecho central |
|---|---|---|---|
| `injustificado` | DESPIDO INJUSTIFICADO | Todo, incl. indemnización art. 50 | Separación sin causa; art. 47 LFT |
| `rescision` | RESCISIÓN DE LA RELACIÓN LABORAL | Todo, incl. indemnización | Causas graves del patrón (art. 51 LFT) |
| `justificado` | TERMINACIÓN DE LA RELACIÓN LABORAL | **Sin** indemnización (art. 46 LFT); sí prima de antigüedad | El patrón acreditó causa |
| `voluntario` | RENUNCIA VOLUNTARIA | Sólo proporcionales; prima de antigüedad **sólo con 15 años** (art. 162 fr. III) | Renuncia del trabajador |
| `otro` | TERMINACIÓN DE LA RELACIÓN LABORAL | Genérico | Genérico |

`rescision` además agrega los artículos 51 y 52 al capítulo de derecho.

## Jurisprudencia (apartado opcional)

El espacio **Jurisprudencia** de la pantalla de la demanda permite cerrar el
escrito con las tesis que sostienen la acción. No es un capítulo obligatorio:
sin tesis seleccionadas el apartado **no aparece** (ni encabezado ni marcador) y
la demanda se presenta sólo con los artículos.

### Biblioteca vs. tesis del caso

El modelo `Jurisprudencia` sirve para dos cosas, distinguidas por su campo
`expediente`:

| `expediente` | Uso | Dónde se ofrece |
|---|---|---|
| vacío | **Biblioteca del despacho**: se captura una vez y se reutiliza | en todos los expedientes |
| con valor | **Tesis del caso**: sólo aplica a ese juicio | sólo en ese expediente |

En la pantalla, la casilla «guardar también en la biblioteca» decide cuál de
las dos se crea al capturar una tesis nueva. La biblioteca se administra además
desde el admin de Django (`Jurisprudencia`), que permite editar rubro, texto,
órgano, época, clave, registro digital y desactivar una tesis sin borrarla.

### Qué se guarda y qué se imprime

Cada tesis se captura con lo que la cita necesita:

- `tipo` (jurisprudencia, tesis aislada o precedente), `tema` (para agrupar la
  biblioteca), `rubro` y `texto` completo;
- `organo`, `epoca`, `clave_tesis`, `registro_digital` y `fuente`;
- `notas` internas, que **no** se imprimen.

La selección vive en `TesisEnDemanda`: un registro por tesis elegida, con
`orden` y `argumento`. El `argumento` es el párrafo con el que el abogado
introduce la tesis; es opcional.

El escrito imprime, por cada tesis, en este orden:

```
[argumento, si lo hay]
“RUBRO DE LA TESIS.”                       (negritas)
Texto de la tesis.
Jurisprudencia. Tesis 2a./J. 12/2020. Segunda Sala de la Suprema Corte de
Justicia de la Nación. Undécima Época. Registro digital: 2020123.
Semanario Judicial de la Federación.
```

La cita se arma con `redaccion/jurisprudencia.py` y la comparten el DOCX, el
HTML y el editor de texto, para que no digan cosas distintas.

### Captura y guardado

La selección se guarda con el botón **Guardar jurisprudencia** (o el
*Guardar datos* inferior), no con el autoguardado: marcar y desmarcar tesis da
de baja registros y no puede depender de un temporizador. Desmarcar una tesis de
la biblioteca sólo borra el vínculo; desmarcar una tesis «sólo de este caso»
borra también la tesis.

Si una tesis de la biblioteca se **desactiva** después de haber sido elegida,
sigue apareciendo en el expediente (marcada como «Desactivada») para poder
quitarla o conservarla: el escrito imprime lo que el abogado eligió, no lo que
esté activo en el catálogo.

### Efecto en el semáforo

Es un requisito **opcional**: no aparece en `bloqueos()` y no impide descargar
el `.docx`. Mientras no haya tesis, el encabezado lo cuenta como una precisión
del relato por afinar y el panel de coherencia avisa que el apartado va vacío.


## Arquitectura

```
expedientes/redaccion/
├── condiciones.py   # qué secciones/prestaciones/pruebas aparecen
├── proemio.py       # capítulo 1
├── demandados.py    # capítulo 2
├── prestaciones.py  # capítulo 3 (montos en número y letra)
├── jornada.py       # capítulo 4 (tabla semanal)
├── hechos.py        # capítulo 5
├── pruebas.py       # capítulo 6
├── derecho.py       # capítulo 7
├── jurisprudencia.py # apartado 8 (opcional)
├── demanda.py       # ensamblado + texto plano
├── adaptador.py     # ÚNICO módulo que conoce Django
└── salida.py        # DOCX (python-docx directo) y HTML, por capítulo
```

Alrededor del motor, una sola pieza decide **qué le falta a la demanda** y qué
afirmará el escrito:

```
expedientes/demanda_estado.py
├── REQUISITOS     # cada dato que el documento necesita: campo, capítulo,
│                    marcador literal del motor y sustituto silencioso
├── estado()       # huecos + decisiones + por bloque + por capítulo + resumen
├── coherencias()  # lo que el documento va a afirmar (y las sustituciones)
└── marcar_html()  # convierte los marcadores en enlaces al campo que falta
```

Es la única fuente de verdad del semáforo del encabezado, del estado de cada bloque, de
los huecos del documento y del guard de la descarga: no pueden contradecirse.

**Regla de oro:** el motor de redacción NUNCA calcula ni inventa montos. Los
importes vienen del motor legal determinista (`core/laboral` + `LegalConfig` +
`CalculoLaboral`) a través de `demanda_generator.calculo_para_demanda`. Si no
hay cálculo disponible, los conceptos se listan **sin cifra**.

## Campos que alimentan la demanda

Se agregaron a `Cliente` en las migraciones `0040_*` y `0041_*`:

- Persona: `nacionalidad`, `ciudad`, `estado`, `hora_despido`
- Jornada: `horario_entrada`, `horario_salida`, `dias_trabajo`, `dia_descanso`
- Puesto: `actividades` (funciones del hecho del contrato)
- Despido: `despido_persona_puesto`, `hubo_ofrecimiento`, `monto_ofrecido`,
  `se_firmo_renuncia`, `hubo_discriminacion`, `tipo_discriminacion`,
  `detalle_discriminacion`
- Contrato: `tipo_contrato`

Modelos nuevos: `ApoderadoLegal` (proemio, con cédula) y
`AutorizadoNotificacion` (arts. 692, 693 y 696 LFT).

> ⚠️ `Cliente.salario` es **mensual**. El motor deriva el salario diario y el
> diario integrado; la frecuencia real del pago va en `periodo_pago`.
> El campo está etiquetado explícitamente y el espacio **Datos** muestra el aviso
> «Captura el importe MENSUAL» con la conversión (`semanal × 4.33`).

Todos estos campos se capturan en los espacios **Datos** (actor, relación laboral y
patrón) y **Estrategia** (separación, IMSS y prestaciones), y no sólo existen en la base:
la prueba `test_campos_nuevos_de_la_hoja_de_datos_se_guardan` verifica que persistan al
guardar, y `expedientes/tests_espacio_demanda.py` verifica que cada uno se capture en la
pantalla que le toca.

> El **domicilio del actor** se agregó a `WIZARD_PASOS['trabajador']`: el proemio lo exige
> y la pantalla no lo capturaba, así que el escrito salía con el marcador
> `[DOMICILIO PARA NOTIFICACIONES]`.

## Banderas vs. motor legal

`adaptador._banderas_prestaciones` delega en `_conceptos_para_demanda`, la MISMA
regla que usa el cálculo (`core.laboral`), para que las banderas de la redacción
y los montos no puedan discrepar. La prueba
`test_las_banderas_coinciden_con_el_motor_legal` lo comprueba para los 5 tipos ×
3 antigüedades (0, 6 y 16 años).

Esto corrige un riesgo real: la prima de antigüedad en renuncia voluntaria
requiere 15 años de servicios (art. 162 fr. III LFT), y afirmarla sin contar la
antigüedad sería reclamar algo improcedente.

## Condiciones que activan bloques

En `condiciones.py`. Las más importantes:

- `incluir_renuncia` ← `se_firmo_renuncia`: agrega la impugnación anticipada de
  renuncia (el estándar la incluye cuando hubo firmas en blanco).
- `incluir_imss` ← `imss_confirmado` **y** `tuvo_imss` es falso: sin confirmar no
  se alega, porque afirmarlo sería inventar un hecho.
- `incluir_sin_aviso` ← `hubo_documento_despido` falso: alimenta el alegato del
  artículo 47 LFT.
- `incluir_horas_extras` ← `tuvo_horas_extras` **y** `reclama_horas_extras`; el
  capítulo de derecho sólo invoca los artículos 66 a 68 cuando aplica.

## Hechos que se conservan del sistema anterior

El motor portado no los traía y son irrenunciables:

1. **Instancia conciliatoria con folio** (requisito de procedibilidad).
2. **Elección de acción del artículo 48 LFT**: si el cliente optó por la
   reinstalación, se declara en los hechos y no se reclama la indemnización.

## Tests

```bash
.venv/Scripts/python.exe manage.py test expedientes.tests_redaccion_capitulos \
    expedientes.tests_jurisprudencia --settings=config.settings_test
```

`tests_redaccion_capitulos` (56 pruebas): estructura de los siete capítulos,
condiciones, montos en número y letra contra el cálculo, orden de los artículos,
tabla de jornada, los 5 tipos de separación, la regla de los 15 años del art. 162
fr. III, la coherencia entre banderas y motor legal, la captura/guardado de los
campos nuevos, el aislamiento por rol del endpoint de descarga, la representación
legal y una verificación completa del documento final contra el estándar
(`EstandarCompletoTest`).

`tests_jurisprudencia` (19 pruebas): el apartado sólo aparece con tesis, la
transcripción de rubro/texto/argumento/cita, el orden, la posición después del
capítulo de derecho, que es opcional y no bloquea la descarga, la biblioteca vs.
las tesis del caso, la captura/edición de la selección, que no se pueda colar
una tesis de otro expediente y que una tesis desactivada siga visible para
poder quitarla.

Para inspeccionar la salida de un caso completo:

```bash
.venv/Scripts/python.exe probar_redaccion_capitulos.py
```

Genera `e2e_artifacts/demanda_capitulos_prueba.docx` y `.txt`.
