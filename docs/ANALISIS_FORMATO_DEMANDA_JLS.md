# Análisis del formato del despacho: qué agregar al motor por capítulos

**Fuente analizada:** `DEMANDA JOSE LUIS SANTAMARIA RAMIREZ.docx` (139 párrafos, 1 tabla de 40×4).
**Motor comparado:** `expedientes/redaccion/` (7 capítulos + firma), `expedientes/demanda_estado.py`, `expedientes/hoja_prestaciones.py`, `core/laboral/`.
**Fecha:** 19 de octubre de 2026.
**Objeto:** detectar qué le falta a la automatización por capítulos para producir el escrito que los abogados del despacho realmente presentan.

---

## 0. Resumen ejecutivo

El motor ya reproduce la **estructura** del formato del despacho: los siete capítulos, el proemio con apoderados y cédulas, los dos demandados, la tabla semanal de jornada y el capítulo de derecho salen casi palabra por palabra. La brecha no está en la arquitectura: está en **lo que el escrito dice dentro de cada capítulo** y en **cuatro o cinco detalles de forma** que un abogado nota de inmediato.

Cinco conclusiones:

1. **Numeración de hechos.** El motor escribe `PRIMERO.-`, `SEGUNDO.-`; el despacho escribe `1.-`, `2.-`, `9.1.-`. Es una diferencia de una línea de código que afecta el documento completo.
2. **Datos que ya están en la base y no se imprimen.** Hay diez banderas de condición que se calculan y **ningún módulo consume**: salarios caídos, prueba testimonial, prueba de informes, ofrecimiento patronal, lugar de trabajo, entre otras. Ahí está el ahorro más grande con el menor riesgo.
3. **El capítulo de prestaciones está incompleto** frente al escrito real: horas extras en un solo renglón (el escrito las separa en dobles y triples con su conteo), sin salarios caídos ni intereses, sin reconocimiento de antigüedad y sin el cierre de «cualquier otra prestación» con suplencia de la queja.
4. **La separación se narra en un solo acto.** El caso JLS tiene tres días (16, 17 y 18 de julio), con un primer impedimento, una oferta de renuncia y un candado con reemplazo. El modelo solo tiene `fecha_despido` + `modalidad_despido`: no puede contar eso, y es el corazón del escrito.
5. **El escrito manual se contradice y el motor no puede hacerlo.** La indemnización son exactamente 90 × salario diario mientras el hecho 6 afirma que se reclama al salario diario **integrado**; el hecho 7 declara 72 horas semanales (30 extras) mientras el cuadro y las prestaciones reclaman 84 horas y 42 extras; hay cuatro errores de número-en-letra y dos fechas que no cuadran. Eso es exactamente lo que la automatización elimina, y es el argumento más fuerte para el área de abogados.

**Orden recomendado de trabajo:** Ola 1 (forma, sin migraciones) → Ola 2 (prestaciones y pruebas con datos existentes) → Ola 3 (modelo nuevo: actos de separación, testigos, modificación de jornada) → Ola 4 (edición del escrito y biblioteca de cláusulas).

---

## 1. Método

Comparé el documento entregado contra el estándar que el motor dice reproducir (`docs/referencia/demanda_injustificado_estandar.txt`) y contra el código de cada capítulo. Después verifiqué con aritmética las cifras del escrito y revisé qué claves del adaptador (`expedientes/redaccion/adaptador.py`) tienen bandera en `condiciones.py` pero no se usan en ningún módulo de redacción.

Las referencias `archivo.py:línea` apuntan al código actual.

---

## 2. Mapa capítulo por capítulo

| # | Capítulo | Cómo lo trae el escrito JLS | Cómo lo entrega el motor | Veredicto |
|---|---|---|---|---|
| — | Carátula | `INICIO.` / `ACTOR. –` / `ACCIÓN. - DESPIDO` / Tribunal / `P R E S E N T E.-` | Igual, pero `ACCIÓN.- DESPIDO INJUSTIFICADO` | Casi igual · ajustar etiqueta |
| 1 | Proemio | actor, domicilio, 3 apoderados con cédula, facultades, constancia | Igual, texto íntegro y correcto | **Igual** · falta ciudad/estado del domicilio |
| 2 | Demandados | I. moral · II. **persona física nombrada** (el patrón real) | I. fórmula «quien resulte responsable de la fuente de trabajo» · II. moral · + adicionales | Funciona, pero no usa los adicionales en pruebas |
| 3 | Prestaciones | 14 numerales: indemnización, vacaciones prop., prima vac. prop., aguinaldo, prima antigüedad, constancia, 3 comprobantes, horas extras **dobles**, horas extras **triples**, «cualquier otra», salarios caídos + intereses, antigüedad | 9-11 numerales, **sin** dobles/triples separados, **sin** salarios caídos, **sin** antigüedad, **sin** cierre de suplencia | **Brecha principal** |
| 4 | Anexo jornada | Tabla 39 semanas, mismas 4 columnas, con párrafo «Anexo el siguiente recuadro…» | Tabla con las **mismas 4 columnas** desde `detalle_semanas` | **Igual en estructura** · cambia el título (`CAPÍTULO DE` vs `Anexo`) y el contenido de «jornada ordinaria» |
| 5 | Hechos | 9 hechos, numeración `1.-` con subnumerales `9.1`, `9.2`, sin hecho de conciliación | 14 hechos, `PRIMERO`–`DÉCIMO CUARTO`, incluye conciliación, falta de pago y testigos | **Brecha de forma y de contenido** |
| 6 | Pruebas | 8: confesional moral, confesional codemandado PF, confesional hechos propios, **testimonial con domicilio y citación**, inspección (nómina+asistencia+contratos), inspección PF, presuncional, instrumental | 10-12: confesional moral, confesional fuente, confesional propios, interrogatorio libre, 4 inspecciones, documental, documental del cliente, presuncional, instrumental | **Falta la testimonial**; sobran 4 inspecciones fragmentadas |
| 7 | Derecho | 123, 8, 10, 11, 13, 16, 17, 19, 20, 22, 24, 25, 37, 47-XV, 48, 50, 59, 60, 66-68, 69, 70, 73-78, 84, 89, 162, 346; procedimiento 685-891 | Lista idéntica, y agrega 66-68 solo si hay horas extras | **Igual** |
| — | Cierre | *(no trae: el documento termina en derecho)* | `PROTESTO LO NECESARIO` + nombre del actor | **Motor mejor** |

Lo que el motor ya hace igual o mejor y conviene defender en la presentación al despacho:

- Los importes en número y letra salen del cálculo, no se escriben a mano (`prestaciones._importe`).
- Cita el artículo 76 LFT para vacaciones; el escrito manual cita el 179.
- Cierra con protesto y firma.
- Ya trae la tabla semanal de 39 renglones sin capturarla a mano.
- Distingue cinco tipos de separación con redactado propio (`hechos._cierre_separacion`).

---

## 3. Hallazgos A — datos capturados que el motor no imprime

Esta es la lista más rentable: el dato **ya existe** en `Cliente` y ya viaja en el diccionario del adaptador. Solo falta el párrafo.

| Dato | Dónde está | Bandera calculada | Quién debería imprimirlo | Situación |
|---|---|---|---|---|
| `reclama_salarios_caidos` | `adaptador.py:249` | `condiciones.py:80` | `prestaciones.py` | **Bandera muerta**: ningún módulo la lee |
| `prueba_testimonial` | `adaptador.py:331` | `condiciones.py:98` | `pruebas.py` | **Bandera muerta**: no existe bloque testimonial |
| `prueba_informes` | `adaptador.py:332` | `condiciones.py:101` | `pruebas.py` | **Bandera muerta**: no existe bloque de informes |
| `hubo_ofrecimiento` / `monto_ofrecido` | `models.py:166,169` → `adaptador.py:119` | `condiciones.py:67` | `hechos.py` | **Bandera muerta**: el ofrecimiento no se narra nunca |
| `lugar_trabajo` | `models.py:184` → `adaptador.py:80` | `condiciones.py:68` | `hechos.py` | **Bandera muerta** |
| `incluir_testigos` / `incluir_documentos` / `incluir_actividades` | `condiciones.py:60-62` | calculadas | `hechos.py` / `pruebas.py` | El texto se imprime por otro camino; la bandera no sirve para nada |
| `empresa_actividad` (giro del patrón) | `models.py:79` | — | `demandados.py` / `hechos.py` | **Ni siquiera se expone** en el adaptador |
| `imss_salario_inferior` / `imss_salario_diario` | `models.py:58-59` → `adaptador.py:103-104` | — | `hechos.py` | Se expone y se ignora: solo se usa `incluir_imss` genérico |
| `despido_persona_puesto` | `models.py:163` → `adaptador.py:116` | — | `hechos.py` | Se expone y no se usa |
| `demandados_adicionales` | `models.py:677` → `adaptador.py:172` | — | `pruebas.py` | Se usa en demandados, **no** en pruebas |

**Consecuencia visible:** en el caso JLS el codemandado es una persona física nombrada (OSMARK JAVIER FLORES ARAGÓN). El motor lo pondría en el capítulo de demandados, pero las confesionales y las inspecciones seguirían ofreciéndose solo contra «la moral» y «quien resulte responsable de la fuente de trabajo» (`pruebas.py:164`). Un abogado pediría confesional contra esa persona por su nombre.

---

## 4. Hallazgos B — forma y estilo del despacho

| # | Detalle | Escrito del despacho | Motor actual | Arreglo |
|---|---|---|---|---|
| B1 | Numeración de hechos | `1.-`, `2.-`, `9.1.-` | `PRIMERO.-`, `SEGUNDO.-` (`demanda.py:72` + `_ordinal`, `demanda_generator.py:469`) | Cambiar el ensamblado a numeral arábigo; la referencia del propio despacho usa `1.-` |
| B2 | Etiqueta de la acción | `ACCIÓN. - DESPIDO` | `ACCIÓN.- DESPIDO INJUSTIFICADO` | Hacer configurable la etiqueta por despacho |
| B3 | Título del anexo | «Anexo el siguiente recuadro para mayor comprensión…» | `CAPÍTULO DE JORNADA SEMANAL` | Párrafo de enlace configurable |
| B4 | Frases de enlace | «Basándome para ello en los siguientes puntos de hechos y consideraciones legales:» / «A efecto de acreditar los hechos vertidos en la presente demanda se ofrecen las siguientes:» | El motor salta directo de la introducción al capítulo | Agregar las dos frases |
| B5 | Punto tras el título de cada prueba | `1.- LA CONFESIONAL POR POSICIONES a cargo de…` | `1.- LA CONFESIONAL POR POSICIONES. a cargo de…` (`salida.py:343-346` agrega `'. '`) | Quitar el punto o ponerlo en mayúsculas con dos puntos |
| B6 | Domicilio del actor | `BOULEVARD DÍAZ ORDAZ #12649 LOCAL 10-B PRIMER NIVEL DEL CENTRO COMERCIAL PLAZA PATRIA, FRACCIONAMIENTO EL PARAÍSO de la ciudad de Tijuana, Baja California` | `BULEVAR DÍAZ ORDAZ, #12649, COL. LOCAL 10-B PRIMER NIVEL, CENTRO COMERCIAL PLAZA PATRIA, FRACC. EL PARAÍSO, CP 22106` | `models.py:305-314`: no prefijar «Col.» cuando la colonia ya trae local/fraccionamiento; agregar ciudad y estado; normalizar «BULEVAR»→«BOULEVARD» |
| B7 | Hechos que el estándar no trae | 9 hechos | 14: agrega conciliación, falta de pago y testigos | Hacerlos opcionales por caso |

B1 es el más visible: el motor dice que reproduce el estándar del despacho, pero el estándar (`docs/referencia/demanda_injustificado_estandar.txt:502-628`) numera `1.-` a `9.-`. Es una discrepancia contra el propio estándar, no solo contra el caso JLS.

---

## 5. Hallazgos C — contenido que el escrito trae y el motor no puede producir

### C1. La separación ocurre en varios actos (el más importante)

El escrito narra tres días y los numera como `9`, `9.1` y `9.2`:

- **16/07/2026, 15:00** — un compañero le avisa por teléfono, estando en su domicilio, que no se presente; se presenta a las 20:00 y **le impiden el acceso**. Testigo presente.
- **17/07/2026** — lo dejan entrar, el patrón le dice que «ya se acabó el trabajo», le ofrece **pagarle solo las vacaciones** y le pone a la firma una hoja con la leyenda «renuncia»; se niega; lo invitan a retirarse.
- **18/07/2026** — encuentra el centro de trabajo **con candado** y a otra persona cubriendo su turno.

El hecho 9 cierra con la fórmula del artículo 47 (parte final): la separación fue en contra de su voluntad y sin aviso escrito.

El motor solo tiene un acto: `fecha_despido`, `hora_despido`, `modalidad_despido`, `despido_frase`, `despido_comunicado_por`, `despido_lugar` (`hechos._texto_despido`, `hechos.py:270-339`). Con esos campos el abogado **no puede** contar el 17 ni el 18, y esos dos días son los que acreditan que no hubo renuncia.

**Propuesta:** modelo `ActoDespido` (hijo de `Expediente`), con `orden`, `fecha`, `hora`, `tipo` (comunicación verbal / impedimento de acceso / ofrecimiento de renuncia / entrega de documento / candado o reemplazo / otro), `lugar`, `quien`, `frase`, `testigos_presentes`, `detalle`. El capítulo de hechos emite un hecho por acto, numerado `9`, `9.1`, `9.2`, y un párrafo de cierre con la fórmula del art. 47.

### C2. Testimonial con domicilio y solicitud de citación

El escrito ofrece la testimonial así: nombre, **domicilio completo**, calidad, y la razón por la que **solicita que el Tribunal la cite** (no puede presentarla porque la testigo necesita justificar la inasistencia en su trabajo), más el objeto de la prueba.

Hoy `testigos` es un `TextField` libre (`models.py:206`) que solo alimenta un hecho («podrán ser corroborados por…») y una bandera que nadie lee. **No hay bloque testimonial en `pruebas.py`.**

**Propuesta:** modelo `Testigo` (`nombre`, `domicilio`, `telefono`, `calidad`, `hechos_que_atestigua`, `solicita_citacion`, `orden`) y bloque de prueba que arme el texto con la fórmula de citación. Mantener el `TextField` como respaldo para casos viejos.

### C3. Modificación de condiciones de trabajo

El escrito dice que la jornada original era de 8 horas de lunes a viernes con un descanso variable y que **a partir de marzo de 2025** se amplió a 12 horas diarias de lunes a domingo en turno nocturno, sin día de descanso y en jornada corrida. Es el sustento de las horas extras y de la jornada excesiva.

El motor afirma lo contrario: «la jornada que se me fijó desde un principio y que vine desempeñando consistió…» (`hechos.py:121-132`). Si el asesor captura la jornada modificada, el escrito **miente sobre el origen**, y el patrón lo puede usar en la contestación.

**Propuesta:** campos `jornada_modificada` (bool), `fecha_modificacion`, `horario_entrada_original`, `horario_salida_original`, `dias_trabajo_original`, `dia_descanso_original`, `motivo_modificacion`; y un hecho condicional con la fórmula «contrario a la oferta de trabajo que me fue hecha… a partir de [mes/año] las condiciones me fueron modificadas».

### C4. Giro de la demandada (identificación de la fuente de trabajo)

El hecho 2 describe a qué se dedica la demandada («establecimiento dedicado a actividades de comercio y prestación de espacios para la actividad comercial, funcionando como centro comercial…»). Sirve para acreditar la existencia y la titularidad de la fuente de trabajo.

`empresa_actividad` existe en el modelo (`models.py:79`, «Actividad económica del patrón») y **el adaptador ni lo expone**. Es un campo capturado y perdido.

### C5. Oferta patronal y presión para firmar renuncia

El escrito narra que el patrón ofreció pagarle **solo las vacaciones** y condicionó cualquier pago a la firma de la renuncia («si no le firmaba la renuncia no le daría cantidad alguna»). `hubo_ofrecimiento`, `monto_ofrecido`, `se_firmo_renuncia` y `despido_frase` existen; solo `se_firmo_renuncia` se usa, para la impugnación anticipada.

**Propuesta:** hecho condicional con la oferta, el monto y la condicionalidad del pago, y un campo `ofrecimiento_condicionado_a_renuncia` (bool).

### C6. Capítulo de prestaciones incompleto

| Falta | Fundamento | Nota |
|---|---|---|
| Horas extras separadas en **dobles** y **triples**, cada una con su conteo y periodo | arts. 66 y 68 LFT | `hoja_prestaciones.py:455` ya produce `dobles` y `triples`; `prestaciones.py:147-155` emite un solo renglón |
| **Salarios caídos** con tope de 12 meses | art. 48 LFT (reforma 2019) | Bandera muerta; el escrito los reclama sin tope |
| **Intereses** al 2% mensual sobre los salarios caídos | art. 48 LFT | No existe |
| **Reconocimiento de la antigüedad** | art. 158 LFT | No existe; es prestación declarativa, sin monto |
| Cierre de «cualquier otra prestación» con **suplencia de la queja deficiente** | art. 685 LFT | No existe; solo hay texto libre `otras_prestaciones_detalle` |
| «Vacaciones **proporcionales**» con el **ciclo en curso** | arts. 76-81 LFT | `prestaciones._periodo_vacaciones` (`prestaciones.py:200-208`) usa ingreso→despido, no el aniversario; y no dice «proporcionales» |

El último punto es sustantivo y no solo de estilo. En el escrito, las vacaciones proporcionales abarcan **del 23 de septiembre de 2025 al 16 de julio de 2026** (el ciclo en curso); el motor escribe **del 1 de abril de 2022 al 30 de abril de 2026** (toda la relación), lo que lee como si reclamara cuatro años de vacaciones.

### C7. Pruebas faltantes o mal dimensionadas

- **Testimonial**: no existe (ver C2).
- **Informes a IMSS / INFONAVIT / SAT**: no existe, aunque se reclaman los comprobantes fiscales de los tres institutos. La prestación y la prueba deberían ir juntas.
- **Constancia de no conciliación como documental**: el proemio y el hecho de conciliación la mencionan, pero no se ofrece en el capítulo de pruebas. El escrito la exhibe como documento base (art. 684-A LFT).
- **Fragmentación**: el motor ofrece 4 inspecciones (nómina y asistencia × 2 demandados); el escrito real ofrece **una por demandado** que agrupa recibos, listas de raya, controles de asistencia y contratos, con un objeto de 5 puntos. Las dos formas son defendibles; conviene poder elegir.
- **Pruebas contra codemandados adicionales**: no se generan (ver Hallazgo A).

### C8. Anexo de jornada: el contenido de «jornada ordinaria»

Las columnas coinciden. Lo que cambia es cómo se llena la segunda: el escrito describe **dónde termina la jornada ordinaria de la semana** («20:00 del lunes a las 02:00 del jueves — 42 horas»), es decir, aplica el tope semanal del turno nocturno (42 h), y de ahí cuenta lo extra. El motor pone el rango diario («20:00 hrs - 08:00 hrs»).

`core/laboral/rules.py:153` ya tiene los topes por turno (8 h diurna, 7.5 mixta, 7 nocturna → 48/45/42 semanales). Usarlos daría el cuadro que el despacho usa y, de paso, **detectaría jornadas ilegales** (el escrito declara 12 h diarias de lunes a domingo: 84 h semanales, contra un tope de 42 h en turno nocturno).

### C9. Derecho: artículos que faltan según lo que se reclame

El motor ya agrega 66-68 cuando hay horas extras y 51-52 en rescisión. Faltarían, condicionados: **56 y 57** (modificación de condiciones), **61** (jornada por turno), **158** (antigüedad), **685** (suplencia), **784, 804 y 828** (pruebas), y **47 parte final** ya está.

---

## 6. Hallazgos D — lo que el escrito manual hace mal y el motor no puede hacer

Esta sección es la que conviene mostrar al área de abogados: no es crítica al escrito, es la demostración de que la automatización aporta algo que la revisión humana no alcanza a cubrir todos los días.

### D1. La indemnización no corresponde con lo que el hecho 6 afirma

| Concepto | Cifra | Verificación |
|---|---|---|
| Indemnización constitucional | $43,325.10 | 43,325.10 ÷ 90 = **481.39** = salario **diario** exacto |
| Hecho 6 | — | «reclamando la indemnización … a salario diario **integrado**, en términos del artículo 84» |

O el SDI es igual al diario —y entonces el alegato del artículo 84 no aporta nada— o la cifra está calculada a salario diario y no al integrado, que es lo que el propio escrito afirma. El motor no puede producir esa ambigüedad: el SDI sale del cálculo y la prestación se calcula sobre él.

### D2. La prima de antigüedad no reconcilia con la antigüedad declarada

$37,904.52 ÷ $481.39 = **78.74 días**. Con ingreso el 23/09/2019 y salida el 16/07/2026 (6.81 años) corresponden 6.81 × 12 = **81.74 días**. Faltan tres días de salario (≈ $1,440).

### D3. Errores de número en letra

| Numeral | Cifra | Texto |
|---|---|---|
| Vacaciones | $7,718.06 | «siete mil setecientos **diecioco** pesos» |
| Aguinaldo | $3,284.00 | «tres mil **dosciento** ochenta y cuatro pesos» |
| Horas extras dobles | $42,241.97 | «**(pesos 97/100** Moneda Nacional)» — sin la cantidad en letra |
| Horas extras triples | $232,330.84 | «**(pesos 00/100)**» — sin cantidad en letra **y con centavos equivocados** |

El motor genera el importe en letra desde el número (`importe_en_letras`): $6,000.30 → «seis mil pesos 30/100 M.N.». Ese error no puede ocurrir.

### D4. Fechas que no cuadran

- Comprobantes INFONAVIT: «del día **23** de septiembre de 2019»; comprobantes SAT: «del día **13** de septiembre de 2019». Mismo periodo, dos fechas.
- Tabla de jornada, renglón 38: «**29/07/26** - 06/07/26» sobre una serie semanal que va de junio a julio.

### D5. Las horas extras no cuadran entre los hechos y las prestaciones

| Fuente | Jornada semanal | Horas extras por semana |
|---|---|---|
| Hecho 7 | «doce horas (12) diarias … **setenta y dos (72) horas semanales**» | 72 − 42 = **30** |
| Tabla de jornada (39 renglones) y prestaciones 10 y 11 | 12 h × **7 días** = **84** | 9 dobles + 33 triples = **42** |

La propia narrativa —12 horas de lunes a domingo— da 84 horas semanales, no 72, y el cuadro y las prestaciones reclaman 42 horas extras semanales, no 30. La diferencia son 12 horas por semana: 468 horas en las 39 semanas del periodo, y una parte importante del monto reclamado ($274,572.81 entre dobles y triples). Es el punto más vulnerable del escrito en la contestación, y no es un error de dedo: es la narrativa de los hechos y el desglose de prestaciones capturados por dos caminos distintos.

El motor no puede producir esa divergencia porque el hecho y la prestación salen del mismo `detalle_semanas`. Convertirlo en una verificación automática (horas semanales declaradas vs. horas del cuadro) es de las cosas de mayor valor que puede aportar la automatización.

### D6. Faltantes de forma en el propio escrito

- No trae cierre: termina en el capítulo de derecho, sin protesto ni firma.
- Testimonial: «testigo mexicana mayor de edad, **de nacionalidad mexicana**» (redundante) y «**solicito sean citados**» en plural para una sola testigo.
- La confesional del numeral 2 y la de hechos propios del numeral 3 se ofrecen contra **la misma persona**, con el mismo apercibimiento repetido íntegro.

Nada de esto invalida el escrito. Todo esto es lo que un generador automático deja de producir por construcción.

---

## 7. Propuesta por olas

Esfuerzo estimado en jornadas de una persona con el código en la mano. **S** < 3 h · **M** ≈ 1 día · **G** 2-3 días.

### Ola 1 — Forma: que el documento se vea como el del despacho (sin migraciones)

| # | Cambio | Archivos | Esf. |
|---|---|---|---|
| 1 | Hechos numerados `1.-`, `2.-` (y soporte de subnumeral `9.1`) | `redaccion/demanda.py:72`, `redaccion/salida.py:336` | S |
| 2 | Etiqueta de acción configurable (`DESPIDO`) | `redaccion/demanda.py:33-39` | S |
| 3 | Frases de enlace antes de hechos y de pruebas | `redaccion/demanda.py`, `redaccion/pruebas.py` | S |
| 4 | Punto tras el título de cada prueba | `redaccion/salida.py:343` | S |
| 5 | Domicilio del actor: sin «Col.» redundante, con ciudad y estado | `models.py:305-314`, `redaccion/adaptador.py:53` | S |
| 6 | Título del anexo («Anexo…» en lugar de «CAPÍTULO DE…») | `redaccion/jornada.py`, `demanda.py` | S |
| 7 | Hechos accesorios (falta de pago, testigos) opcionales | `redaccion/hechos.py:234-257` | S |
| 8 | Actualizar las pruebas que fijan el formato | `tests_redaccion_capitulos.py` | S |

**Resultado:** el DOCX se lee como el escrito del despacho sin tocar la captura. Es lo primero que el abogado va a notar.

### Ola 2 — Prestaciones y pruebas con los datos que ya existen

| # | Cambio | Archivos | Esf. |
|---|---|---|---|
| 9 | Horas extras en dos renglones (dobles / triples) con conteo y periodo | `redaccion/prestaciones.py:147`, `hechos.py:381` | S |
| 10 | Vacaciones proporcionales: ciclo en curso y la palabra «proporcionales» | `redaccion/prestaciones.py:200` | S |
| 11 | Salarios caídos con tope de 12 meses + intereses 2% (art. 48) | `redaccion/prestaciones.py`, `core/laboral/` | M |
| 12 | Reconocimiento de antigüedad (prestación sin monto) | `redaccion/prestaciones.py` | S |
| 13 | Cierre «cualquier otra prestación / suplencia de la queja» (art. 685) | `redaccion/prestaciones.py` | S |
| 14 | Bloque de **prueba testimonial** con citación | `redaccion/pruebas.py` | M |
| 15 | Bloque de **informes** a IMSS/INFONAVIT/SAT | `redaccion/pruebas.py` | S |
| 16 | Constancia de no conciliación como documental | `redaccion/pruebas.py` | S |
| 17 | Pruebas contra codemandados adicionales | `redaccion/pruebas.py:164` | S |
| 18 | Hecho de giro de la demandada (`empresa_actividad`) | `adaptador.py:64`, `hechos.py:35` | S |
| 19 | Hecho de ofrecimiento patronal + presión para firmar | `redaccion/hechos.py` | S |
| 20 | Lugar de trabajo en hechos e inspección | `redaccion/hechos.py` | S |
| 21 | Alegato de IMSS con salario inferior al real | `redaccion/hechos.py:167` | S |
| 22 | Artículos de derecho condicionados (56, 57, 61, 158, 685, 784/804/828) | `redaccion/derecho.py` | S |
| 23 | Registrar todo lo nuevo en `REQUISITOS` (semáforo y guard de descarga) | `demanda_estado.py:118+` | M |

### Ola 3 — Modelo nuevo para lo que hoy no se puede capturar

| # | Cambio | Esf. |
|---|---|---|
| 24 | `ActoDespido` (varios actos fechados) + hecho por acto y subnumerales | G |
| 25 | `Testigo` estructurado (nombre, domicilio, calidad, solicita citación) | M |
| 26 | Modificación de condiciones (jornada original vs. modificada) | M |
| 27 | Demanda de horas extras por patrón semanal recurrente (en lugar de capturar 39 semanas) | G |

El 27 merece comentario: el escrito captura 39 semanas idénticas porque el patrón es el mismo cada semana. Automatizar ese patrón («9 h dobles y 33 triples por semana, del 13/10/2025 al 13/07/2026») convierte 39 capturas en 3 datos y la tabla se genera sola.

### Ola 4 — Herramientas de abogado encima del generador

| # | Cambio | Por qué |
|---|---|---|
| 28 | Editar el texto de cada capítulo y **guardarlo por expediente** | Hoy el espacio Documento es de solo lectura: el abogado no puede corregir una frase sin salir del sistema. Es la petición más previsible |
| 29 | Biblioteca de cláusulas alternativas por capítulo | El `Machote` actual es de documento completo con marcadores; falta la variante de párrafo («despido por impedimento de acceso», «despido con oferta de renuncia», etc.) |
| 30 | Semáforo de contradicciones (D1-D5 automáticos) | Comparar montos contra el cálculo, horas del cuadro contra las declaradas en hechos, fechas contra el periodo e importe en letra contra número; bloquear la descarga si difieren |
| 31 | Control de roles del área | Quién puede editar, quién aprobar y quién descargar el escrito para presentar |

---

## 8. Guardarraíles legales que la automatización debe respetar

Estos no son features, son límites. Si el motor los ignora, produce escritos improcedentes con apariencia de correctos.

1. **Salarios caídos**: máximo 12 meses y 2% mensual de intereses (art. 48 LFT, reforma 2019). El escrito los reclama «así como los intereses» sin tope; la automatización debe calcular el tope o no reclamarlos.
2. **Prima de antigüedad en renuncia voluntaria**: solo con 15 años o más (art. 162 fr. III). El motor ya lo respeta y hay prueba para los 5 tipos × 3 antigüedades.
3. **Indemnización**: siempre sobre salario diario integrado, nunca sobre el diario (art. 84). Es el error D1.
4. **IMSS**: no alegar falta de alta sin confirmación del asesor (`condiciones.py:45`).
5. **Aviso de rescisión**: sin documento, se alega el art. 47 parte final; con documento, no se puede afirmar que no hubo aviso (`incluir_sin_aviso`).
6. **Testimonial**: si el testigo no puede presentarse, hay que pedir citación por el Tribunal y expresar la razón; si no, la prueba se desahoga desierta.
7. **Constancia de no conciliación**: sin ella la demanda es improcedente (art. 684-A). Debe ir como documental, no solo mencionada.

---

## 9. Preguntas que necesito del despacho antes de implementar

1. **Numeración de hechos**: ¿`1.-` siempre, o el Tribunal acepta ordinales en algún caso?
2. **Inspecciones**: ¿una por demandado agrupando nómina, asistencia y contratos (como el escrito JLS) o separadas como hoy?
3. **Hechos accesorios**: ¿conservamos los de instancia conciliatoria, falta de pago y testigos dentro de hechos, o se mueven a otro capítulo para que el escrito quede en 9 hechos?
4. **Salarios caídos**: ¿se reclaman siempre con tope de 12 meses, o solo cuando el cliente lo pide?
5. **Demandado persona física**: ¿siempre se demanda al responsable de la fuente de trabajo por su nombre cuando se conoce, en lugar de la fórmula «quien resulte responsable»?
6. **Testigos**: ¿cuántos por caso y con qué datos mínimos (domicilio sí o sí)?
7. **Edición del escrito**: ¿el abogado edita el texto libremente y se guarda por expediente, o prefiere elegir entre variantes aprobadas?

---

## 10. Anexo — inventario de banderas muertas

Calculadas en `condiciones.py`, sin consumidor en `redaccion/`:

```
reclama_salarios_caidos     prueba_testimonial     prueba_informes
incluir_ofrecimiento        incluir_lugar_trabajo  incluir_testigos
incluir_documentos          incluir_actividades    reclama_salarios_devengados
reclama_otras_prestaciones
```

Diez banderas calculadas que no producen ni una línea de texto. Ahí empieza la Ola 2: el dato ya está, el párrafo es lo que falta.

---

### Documentos relacionados

- `docs/DEMANDA_POR_CAPITULOS.md` — arquitectura vigente del motor.
- `docs/referencia/demanda_injustificado_estandar.txt` — estándar del despacho.
- `expedientes/redaccion/` — los siete capítulos.
- `expedientes/demanda_estado.py` — fuente única de los datos faltantes.
