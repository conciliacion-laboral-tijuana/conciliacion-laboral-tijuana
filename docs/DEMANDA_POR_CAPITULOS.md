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

## Cómo usarlo

Desde el **Acordeón de Demanda**: botón *Descargar demanda final*.
O por URL: `GET /expedientes/<pk>/demanda/capitulos/` → `.docx`.

Antes de descargar se exige lo mismo que ya exigía el flujo anterior:
datos críticos del cliente y prestaciones calculadas y aprobadas.

### Sección 5 del acordeón: Representación legal

Los **apoderados** (con cédula profesional) y los **autorizados** para oír y
recibir notificaciones se capturan en su propia sección del acordeón y son los
que arma el proemio. Como en un despacho suelen ser siempre los mismos, el botón
**Copiar del expediente anterior** los reutiliza: toma los del expediente más
reciente que los tenga y agrega sólo los que falten (no duplica).

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
├── demanda.py       # ensamblado + texto plano
├── adaptador.py     # ÚNICO módulo que conoce Django
└── salida.py        # DOCX (python-docx directo) y HTML
```

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
> El campo está etiquetado explícitamente y el acordeón muestra el aviso
> «Captura el importe MENSUAL» con la conversión (`semanal × 4.33`).

Todos estos campos se capturan en el acordeón (secciones 1, 2 y 4) y no sólo
existen en la base: la prueba `test_campos_nuevos_de_la_hoja_de_datos_se_guardan`
verifica que persistan al guardar.

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
    --settings=config.settings_test
```

53 pruebas: estructura de los siete capítulos, condiciones, montos en número y
letra contra el cálculo, orden de los artículos, tabla de jornada, los 5 tipos de
separación, la regla de los 15 años del art. 162 fr. III, la coherencia entre
banderas y motor legal, la captura/guardado de los campos nuevos, el aislamiento
por rol del endpoint de descarga, la representación legal y una verificación
completa del documento final contra el estándar (`EstandarCompletoTest`).

Para inspeccionar la salida de un caso completo:

```bash
.venv/Scripts/python.exe probar_redaccion_capitulos.py
```

Genera `e2e_artifacts/demanda_capitulos_prueba.docx` y `.txt`.
