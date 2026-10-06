# ⚖️ Despacho Laboral — Documentación Funcional del Sistema

> **Sistema:** Aplicación web para la gestión de expedientes laborales de un despacho de abogados en Tijuana, México
> **Nombre del producto:** Conciliación Laboral Tijuana — Despacho Laboral
> **Tecnología:** Django 5.x · Tailwind CSS · HTMX · PostgreSQL/SQLite · Celery + Redis · Selenium
> **Última actualización:** Agosto de 2026

---

## 1. Qué hace el sistema

`Despacho Laboral` es una **plataforma de gestión de casos (CRM + flujo de trabajo legal)**
para un despacho de abogados laboralistas. Administra el ciclo de vida completo de una
reclamación laboral — desde el primer contacto con el cliente, pasando por la etapa de
conciliación prejudicial obligatoria ante el *Centro de Conciliación Laboral (CCL)* de
Baja California, hasta el acuerdo (convenio) o la presentación de una **demanda laboral**
formal.

Más allá del seguimiento de casos, la plataforma automatiza las partes más repetitivas y
propensas a error de la práctica:

- **Cálculo de prestaciones laborales** (aguinaldo, prima vacacional, prima de antigüedad,
  indemnización constitucional, etc.) calculados automáticamente conforme a la Ley Federal
  del Trabajo (LFT).
- **Generación de documentos legales** a partir de plantillas HTML reutilizables
  (machotes) con inyección automática de datos.
- **Envío automatizado de solicitudes de conciliación** al portal oficial del gobierno de
  BC (`app.conciliacionbc.gob.mx`) — tanto del lado del servidor como mediante una
  extensión de Chrome complementaria.
- **Notificaciones por WhatsApp** a los clientes (manuales, automáticas por cambio de
  estado y recordatorios).
- **Un módulo financiero completo** (pagos, gastos, nómina, comisiones, caja diaria,
  préstamos entre socios, distribución de utilidades) organizado por oficina y por semana
  de trabajo.

---

## 2. Usuarios, roles y permisos

### 2.1 Roles (5)

| Rol | Clave | Alcance |
|-----|-------|---------|
| **Superadmin** | `superadmin` | Acceso total: admin de Django, todos los dashboards, matriz de permisos, gestión de usuarios |
| **Administrativo** | `admin` | Ve todos los casos, reportes de productividad, montos totales, exportaciones a Excel, acceso al admin de Django |
| **Asesor** | `asesor` | Solo ve y edita **sus propios** casos; dashboard personal con estadísticas |
| **Abogada** | `abogada` | Dashboard dedicado para la abogada del despacho (visión general de casos y documentos) |
| **Finanzas** | `finanzas` | Dashboard financiero y acceso al módulo de finanzas (cuenta como admin para permisos) |

### 2.2 Capacidades del perfil (`UserProfile`)

Cada perfil de usuario cuenta además con:

- **`puede_generar_documentos`** — bandera que otorga acceso a los generadores de
  documentos legales (demanda, machotes, documentos legales). Desactivada por defecto.
- **`api_token`** — token personal de API que usa la extensión de Chrome para
  autenticarse contra la API de la aplicación. Se genera automáticamente al crear el
  perfil y se puede regenerar (invalidando el anterior) desde la página *Extensión de
  Chrome*.

### 2.3 Auditoría de permisos (`PermisoAuditLog`)

Cada vez que un superadmin/admin modifica el rol de un usuario, sus permisos de
documentos u otros privilegios, se registra una **entrada de auditoría**: a quién se
modificó, quién lo modificó, la acción (`cambio_rol`, `cambio_docs`, `mixto`) y el
detalle (ej: `Rol: asesor → admin`).

### 2.4 Módulo de superadmin

- **Dashboard de superadmin** — panel de administración de la plataforma.
- **Matriz de permisos** (`matriz_permisos`) — cuadrícula para gestionar el rol y el
  permiso de generación de documentos de cada usuario, con **exportación a Excel**.
- **Cargar datos demo** — siembra de datos de prueba con un clic (usuarios/casos).

### 2.5 Autenticación y seguridad

- Inicio/cierre de sesión y flujo completo de **restablecimiento de contraseña** por
  correo (SMTP configurable; backend de consola por defecto en desarrollo).
- Redirección automática al dashboard correspondiente según el rol tras iniciar sesión.
- Endurecimiento en producción: redirección HTTPS, cookies seguras, detección automática
  del dominio de Railway, `DEBUG`/`SECRET_KEY`/`ALLOWED_HOSTS` controlados por entorno.

---

## 3. Gestión de casos (Módulo Expedientes)

### 3.1 Clientes (`Cliente`)

Ficha de cliente enriquecida diseñada específicamente para la conciliación laboral:

- **Identidad:** nombre, **CURP** (único), RFC, teléfono, WhatsApp, correo, fecha de
  nacimiento, género.
- **Domicilio particular:** calle, número, código postal, colonia — se ensambla en
  `direccion_completa`.
- **Datos del patrón:** empresa, actividad económica, teléfono, razón social, domicilio
  completo y referencias.
- **Tipo de persona del patrón** (física / moral) — se usa en el formulario del portal de
  conciliación.
- **Datos laborales:** puesto, **salario mensual**, periodo de pago (diario/semanal/
  quincenal/mensual), horas semanales, jornada (diurna/nocturna/mixta), fecha de ingreso,
  fecha de salida.
- **Fuente de captación:** cómo se enteró el cliente del despacho (Facebook, Google,
  recomendación, WhatsApp, TikTok, TV/radio, volante…).
- **Asignación de oficina** (Plaza Patria, Otay, CLT).
- **Seguimiento de asesoría gratuita:** si se ofreció la asesoría gratuita semanal, si se
  agendó y en qué fecha.
- Indexado para búsquedas rápidas por CURP, nombre y fecha de asesoría.

### 3.2 Expedientes (`Expediente`)

- **Numeración automática** `AAAA-####` (año + secuencial), única y no editable.
- Asignado a un **asesor** (asesor jurídico).
- **Montos:** monto reclamado (`monto_reclamado`) y monto de convenio (`monto_convenio`).
- **Programación de audiencias** con fecha/hora y resultado registrado.
- **Datos de conciliación:** tipo de despido (justificado/injustificado/voluntario/
  rescisión/otro), prestaciones reclamadas, **folio** y fecha de trámite.
- **Seguimiento:** fecha de próxima acción, notas internas, prioridad (baja/media/alta).
- **Interruptor de automatización WhatsApp por caso** (`notificar_whatsapp_auto`).

#### Máquina de estados con transiciones validadas

```
nuevo → solicitud → citatorio → audiencia → no_notificado ─┐
                                        ├→ reprogramacion ─┤
                                        ├→ convenio ───────┤
                                        ├→ sin_conciliacion─┼→ demanda → audiencia/convenio/cerrado
                                        └→ cerrado (desde cualquier estado)
```

El modelo **rechaza transiciones ilegales** (ej. saltar de `nuevo` a `audiencia`) con un
mensaje claro que enumera las transiciones permitidas. Cada estado tiene un color
asociado para las insignias de la interfaz.

### 3.3 Documentos (`Documento`)

- Subida de PDFs/imágenes por caso con clasificación por tipo (INE, contrato, evidencia,
  screenshot/captura, citatorio, PDF, otro) y descripción; se registra quién subió y cuándo.
- Organizados en disco por año/mes.

### 3.4 Notas e historial de actividad

- **Notas** — notas libres por caso con autor y fecha.
- **Movimientos** — rastro de auditoría automático de cada acción: creación, cambio de
  estado, actualización, subida de documento, nota agregada, resultado de audiencia
  (quién, cuándo, qué cambió).

### 3.5 Notificaciones (campana)

Notificaciones internas para el usuario: transferencias, avisos, mensajes del sistema,
recordatorios. Cada notificación puede llevar un enlace; se pueden marcar como leídas
individualmente o **todas de una vez**.

### 3.6 Solicitudes de transferencia entre asesores

Cuando un asesor no puede asistir a una audiencia (conflicto de horario, etc.):

- Solicita una **transferencia** del caso, opcionalmente sugiriendo un asesor destino,
  con un motivo obligatorio.
- El área administrativa revisa la solicitud, opcionalmente **reasigna** a otro asesor y
  aprueba o rechaza con un comentario.
- Estados: pendiente → aprobada / rechazada / cancelada. Las notificaciones mantienen
  informados a todos.

### 3.7 Avisos obligatorios del administrador

- El administrador crea avisos/pendientes con título, contenido, prioridad y **fecha de
  vencimiento opcional** (se ocultan automáticamente al vencer).
- Se muestran en el dashboard de todos los asesores y administradores; los usuarios
  pueden marcarlos como **leídos/entendidos** (se registra por usuario mediante M2M).

### 3.8 Búsqueda global y filtros

- **Búsqueda global** en expedientes, clientes, folios y empresas.
- Filtros avanzados en la lista de expedientes; los asesores solo ven sus propios casos.

### 3.9 Calendario

- **Calendario de audiencias** (`calendario`) que agrega todas las audiencias programadas.

### 3.10 Reportes y exportaciones

- **Exportación a Excel** de expedientes.
- **Reportes administrativos** (`reportes_admin`) — productividad y totales por asesor.
- **PDF por expediente** (`pdf_expediente`) generado con WeasyPrint.

---

## 4. Dashboards (por rol)

| Dashboard | Qué muestra |
|-----------|-------------|
| **Asesor** | KPIs personales, sus casos por estado, próximas acciones/audiencias, tareas pendientes, avisos |
| **Abogada** | Vista orientada a la abogada del despacho (casos y documentos) |
| **Admin** | Todos los casos, reportes de productividad, montos totales, avisos, acciones de exportación |
| **Finanzas** | KPIs financieros (ver módulo de Finanzas) |
| **Superadmin** | Panel de administración de la plataforma + matriz de permisos |

---

## 5. Motor de Cálculo Laboral (Cálculo Laboral)

### 5.1 Reglas legales configurables (`LegalConfig`)

Todos los parámetros legales viven en un objeto `ReglasLegales`
(`core/laboral/rules.py`) que se construye desde la fila de `LegalConfig` guardada en la base
de datos y editable desde el admin de Django — **sin necesidad de tocar código cuando cambian
las leyes** (`LegalConfig.to_reglas()` es el puente):

- **UMA** diaria (2026: $117.31), salario mínimo general ($315.04) y **salario mínimo de la
  Zona Libre de la Frontera Norte** ($440.87; Tijuana está en la ZLFN).
- **Días de aguinaldo** (mínimo legal: 15).
- **% de prima vacacional** (mínimo 25%).
- **Prima de antigüedad:** días por año (12) y **tope = 2 × salario mínimo del área
  geográfica** (arts. 485/486 LFT): frontera $881.74 · general $630.08. **No es 2 × UMA**
  ($234.62), que era el error anterior.
- **Días de indemnización** (3 meses = 90) y **20 días por año** (art. 50 fr. II).
- **Criterio de vacaciones antes del primer año** (proporcional / ninguna).
- **Modo de salario integrado** (por conceptos del art. 84 o por porcentaje).
- **Años exigidos para prima de antigüedad en renuncia voluntaria** (15, art. 162 fr. III).
- Solo una configuración puede estar *activa* a la vez; al guardar una se desactivan las demás.

### 5.1b Tablas graduales (reforma DOF 01-05-2026)

La reducción de la jornada es **gradual**, así que se modela por año y no como constante:

| Año | Jornada ordinaria máx. semanal (art. 59 + transitorio Segundo) | Horas al doble máx. por semana (art. 66 + transitorio Cuarto) |
|-----|----------------------------------------------|-------------------------------------------------------------|
| 2026 | 48 | 9 |
| 2027 | 46 | 9 |
| 2028 | 44 | 10 |
| 2029 | 42 | 11 |
| 2030 | 40 | 12 |

Lo que excede el límite del art. 66 se paga al triple (art. 68) con un máximo de **4 horas
extra por semana**; la jornada ordinaria más la extraordinaria nunca puede exceder 12 horas
diarias.

### 5.2 Modelo temporal de la relación laboral (`PeriodoLaboral`)

Cada concepto ya no comparte una misma cifra de "días trabajados".
`core/laboral/periodo.py` descompone la relación en el periodo que exige cada artículo:

```
RELACIÓN LABORAL
├── antigüedad exacta (aniversarios cumplidos, bisiesto-aware) + fracción del ciclo
├── aniversario vigente / próximo aniversario
├── días del AÑO CALENDARIO en curso  → aguinaldo (art. 87)
├── ciclos de vacaciones (uno por año de servicio) → arts. 76 y 81
│   ├── derecho del último año cumplido, no disfrutado
│   └── proporcional del ciclo en curso
└── semanas trabajadas → topes de horas extra (arts. 66 y 68)
```

Consecuencias:

- **El aguinaldo** es proporcional a los días trabajados **del año calendario en curso**, no a
  toda la antigüedad (art. 87: "conforme al tiempo que hubieren trabajado"). Un trabajador con
  5 años despedido el 15 de septiembre de 2026 cobra 258/365, no 5 años de aguinaldo.
- **Las vacaciones** se calculan por ciclo de aniversario: el derecho del último año
  completado **más** la parte proporcional del año en curso. La proporcionalidad se aplica
  **una sola vez** (antes se aplicaba dos veces, dejando los días al cuadrado).
- **La antigüedad** se mide por aniversarios cumplidos, no con `días / 365`: los años
  bisiestos no distorsionan y quien termina justo en su aniversario da una cifra exacta.

### 5.3 Tabla de vacaciones (Reforma LFT 2022)

| Años de servicio | 1 | 2 | 3 | 4 | 5 | 6-10 | 11-15 | 16-20 | 21-25 | 26-30 |
|-------------------|---|---|---|---|---|-------|-------|-------|-------|-------|
| Días | 12 | 14 | 16 | 18 | 20 | 22 | 24 | 26 | 28 | 30 |

Antes del primer aniversario el derecho es 0 bajo el criterio mayoritario (el art. 76 exige
"más de un año de servicios"); el criterio `proporcional` también está disponible y es
configurable por caso.

### 5.3 Conceptos calculados

| Concepto | Artículo | Tipo | Base de cálculo |
|----------|----------|------|-----------------|
| Aguinaldo proporcional | Art. 87 LFT | automático | días del año calendario en curso |
| Vacaciones (año cumplido + proporcional) | Arts. 76 y 81 LFT | automático | ciclo de aniversario |
| Prima vacacional | Art. 80 LFT | automático | 25% de las vacaciones |
| Prima de antigüedad (con piso y tope de zona) | Arts. 162, 485 y 486 LFT | según tipo de despido | salario diario con piso/techo del área |
| Indemnización constitucional (90 días) | Art. 50 fr. III LFT | según tipo de despido | **salario diario integrado** |
| Indemnización 20 días por año | Art. 50 fr. II LFT | según tipo de despido | **salario diario integrado** |
| Vacaciones de ciclos anteriores (días manuales) | Art. 79 LFT | semiautomático | salario diario |
| Horas extras: dobles + excedentes | Arts. 66 y 68 LFT | semiautomático | valor hora según jornada (art. 61) |
| Salarios devengados (monto manual) | Art. 48 LFT | manual | — |
| Días festivos laborados | Arts. 74-75 LFT | semiautomático | 3 × salario diario |
| Días de descanso semanal laborados | Arts. 69 y 73 LFT | semiautomático | 2 × salario diario |

### 5.4 Salario diario vs. salario diario integrado (arts. 84 y 89 LFT)

El motor separa las dos bases porque la ley lo hace:

- **Salario diario** = salario ÷ 30 / 15 / 7 / 1 (art. 89). Base de aguinaldo, vacaciones,
  prima vacacional, horas extras, festivos.
- **Salario diario integrado** = salario diario + parte proporcional de los conceptos del
  art. 84 (cuota diaria, gratificaciones, ayudas, comisiones, prestaciones en especie). Base
  de las **indemnizaciones** (90 días y 20 días por año).

Ambas cifras aparecen en la pantalla de cálculo y se asientan en la demanda ("Salario
diario: $X · Salario diario integrado: $Y"). La prima de antigüedad usa su propia base (piso
y techo del salario mínimo del área, arts. 485/486) — nunca la UMA.

### 5.5 Las horas extras son estructuradas, nunca un factor promedio

Una cantidad total de horas no contiene información jurídica: el límite de horas al doble es
semanal y depende del año, y lo que lo excede se paga al triple. Por eso el motor recibe
`horas_extra_normales` (art. 66) y `horas_extra_excedentes` (art. 68). Si sólo se captura un
total, se reparte contra los topes semanales del año (9 + 4 h en 2026) en lugar de aplicar el
antiguo factor promedio de 2.5×. El valor de la hora sigue la duración de la jornada
(8 / 7 / 7.5 h, art. 61 LFT).

### 5.6 Procedencia por tipo de terminación (arts. 46, 50 y 162 LFT)

La indemnización no es una prestación automática:
`ReglasLegales.restricciones_por_tipo()` decide según la causa de terminación, y la demanda,
la pantalla y el recálculo comparten esa única regla:

| Terminación | 90 días (art. 50 fr. III) | 20 días/año (art. 50 fr. II) | Prima de antigüedad (art. 162) |
|-------------|------------------------------|--------------------------------|--------------------------------|
| Despido injustificado | ✔ | ✔ | ✔ |
| Rescisión (arts. 51-52) | ✔ | ✔ | ✔ |
| Despido justificado | ✘ (art. 46) | ✘ | ✔ (fr. III) |
| Renuncia voluntaria | ✘ | ✘ | ✔ sólo con 15 años o más |

Las prestaciones ordinarias (aguinaldo, vacaciones, prima vacacional, horas extras) se deben
en todos los casos.

### 5.7 Narrativa del despido (art. 47 LFT)

Los HECHOS de la demanda se arman con campos **estructurados** capturados en el acordeón, no con
un solo texto libre. Cada modalidad tiene redactado propio, porque la forma de la separación tiene
consecuencia jurídica:

| Modalidad | Redactado | Nota legal |
|-----------|-----------|------------|
| `verbal` | Despido verbal sin documento; cita a quien comunicó, dónde y la frase textual | Sin aviso escrito se presume la separación injustificada (art. 47 LFT) |
| `escrito` | Recepción del documento de terminación; cita el motivo consignado | Si el documento no consigna causa, el hecho lo hace constar |
| `acceso` | Se presentó al centro de trabajo y se le impidió el acceso | La negativa de acceso equivale a la separación |
| `otro` | Explicación libre del asesor | — |

Campos que alimentan el redactado: `modalidad_despido`, `hubo_documento_despido`,
`despido_comunicado_por`, `despido_lugar`, `despido_frase`, `despido_documento_motivo`,
`despido_otra_modalidad`, `lugar_trabajo` y `circunstancias_despido` (anotaciones libres, que se
suman al final).

`construir_hechos()` es la **fuente única** de la narrativa: la consumen tanto el generador DOCX
como el HTML, de modo que ambas descargas dicen exactamente lo mismo.

### 5.8 Acción preferida (arts. 48 y 49 LFT)

El art. 48 LFT da al trabajador una **elección** entre la reinstalación en el puesto que
desempeñaba y la indemnización de tres meses de salario. No son prestaciones acumulables: son
acciones excluyentes. El campo `Cliente.accion_preferida` captura la elección y
`ReglasLegales.accion_posible()` la resuelve:

| Situación | Resultado |
|-----------|-----------|
| `reinstalacion` con ≥ 1 año y despido injustificado o rescisión | **Procede**: la indemnización de 3 meses sale del total y el petitorio pide reinstalación + salarios caídos |
| `reinstalacion` con < 1 año | **No procede** (art. 49 fr. I LFT): se mantiene la indemnización y el motor explica por qué |
| `reinstalacion` en despido justificado o renuncia voluntaria | **No procede** (art. 46 LFT) |
| `indemnizacion` | Siempre procede si el tipo de separación genera responsabilidad |

Cuando la elección es la reinstalación pero no procede, la pantalla del acordeón muestra una
advertencia (`advertencias_accion`) antes de generar la demanda, para que el asesor no formule una
acción imposible.

### 5.4 Cálculo por caso (`CalculoLaboral`)

- Un cálculo por expediente que guarda una **instantánea de los datos de entrada** para
  conservar el histórico.
- **Casillas de verificación** que permiten al asesor elegir qué conceptos incluir (5 conceptos
  base activos por defecto). Los conceptos que dependen de la causa de terminación los
  enciende o apaga la ley, no la casilla.
- **Sustitución manual** de los días de vacaciones realmente adeudados (cuando algunos
  años ya se pagaron o disfrutaron) — se muestra con el indicador *override aplicado*.
- Capturas para los **componentes del salario integrado**, el **desglose de horas extras**
  (dobles / excedentes) y los **días de descanso semanal laborados**.
- Muestra salario diario, salario diario integrado, días trabajados, antigüedad exacta, la
  base del aguinaldo en días del año calendario, el desglose del ciclo de vacaciones, el piso
  y el tope aplicados a la prima de antigüedad, el detalle por concepto con referencia legal y
  el **total**.
- **Recálculo automático** cuando cambian los datos del cliente/expediente o las reglas
  legales (`recalcular`).
- **Simulación rápida** (`simulacion-rapida`) — estimación instantánea para un prospecto
  sin crear un caso: captura salario, fechas, zona salarial, jornada y tipo de terminación y
  obtén el desglose completo.
- La **demanda usa el cálculo guardado**, así que lo que se reclama siempre coincide con lo
  que se le mostró al cliente en pantalla.

---

## 6. Generación de Documentos Legales

### 6.1 Machotes (plantillas HTML reutilizables)

- Plantillas categorizadas como: **Demanda Laboral, Carta Finiquito, Convenio,
  Solicitud, Citatorio, Otro**; con jurisdicción (Federal / Estatal BC / Ambas), tipo de
  despido opcional, ícono, bandera de activo y orden.
- Los machotes **favoritos** aparecen primero en el editor.
- El cuerpo de la plantilla es HTML con **marcadores** como `{{ nombre }}`,
  `{{ empresa }}`, etc.

### 6.2 Motor de inyección de marcadores (`marcadores.py`)

- ~40 marcadores con **datos reales del caso**: cliente, empresa, expediente, fechas (en
  español, ej. "1 de enero de 2024"), formato de salarios **y prestaciones calculadas**
  (aguinaldo, vacaciones, indemnización…) obtenidas automáticamente del motor de cálculo.
- Los datos faltantes se muestran como marcadores visibles (`[CURP]`, `[MONTO]`, …) en
  lugar de espacios en blanco o errores — el usuario sabe exactamente qué completar.
- **Verificador de completitud**: lista qué campos están completos/incompletos por
  sección (Cliente, Empleo, Empresa, Expediente) con **enlaces directos de edición** y un
  porcentaje de completitud.

### 6.3 Flujo de documentos

1. Elegir un machote del catálogo (o desde el expediente).
2. **Preparar** — ver qué datos faltan y corregirlos con un clic.
3. **Editar/vista previa** del documento renderizado en el navegador.
4. **Generar/descargar** como PDF.
5. Opcionalmente **guardar el documento editado como nuevo machote** (la biblioteca de
   plantillas del equipo crece de forma orgánica).

### 6.4 Importar machotes desde Word

- Los archivos `.docx` (ej. una carpeta con demandas existentes) se convierten en
  plantillas HTML mediante el comando `importar_machotes` o la importación web,
  conservando los marcadores cuando es posible.
- La biblioteca de plantillas se administra desde el admin de Django o desde la interfaz
  de machotes.

### 6.5 Generador de Demanda Laboral (`demanda_generator.py`)

- Genera una **demanda laboral mexicana profesional** (Word `.docx`) con todos los datos
  del caso, cálculos integrados y formato listo para imprimir y firmar.
- Un **asistente paso a paso** (`demanda_asistente`) guía por las secciones de la demanda;
  un **generador directo** produce el documento en un solo clic.
- Se descarga como `.docx` para edición/firma.

---

## 7. Automatización de Conciliación (Portal de Baja California)

El sistema se integra con el portal oficial `app.conciliacionbc.gob.mx` en **dos modos**.

### 7.1 Automatización del lado del servidor (`conciliacion_automation.py` + Celery)

- Llena el flujo real de varias fases del portal: aviso de privacidad → industria → fecha
  del conflicto y objeto → trabajador (solicitante) → empresa (citado) → descripción → envío.
- Se ejecuta **headless** (servidor) o en **modo visible/debug**.
- Se ejecuta de forma asíncrona mediante un **worker de Celery** (o fallback con threads
  si no hay Redis) para que las peticiones HTTP nunca expiren.
- Página de progreso en vivo (`conciliacion_procesando`) que muestra **capturas de
  pantalla del navegador** y el tiempo transcurrido; soporta reintentos.
- Al completarse: captura el **folio**, guarda el **PDF del acuse** en el expediente y
  marca la TareaConciliacion como completada con bitácoras completas.
- Comando de gestión `enviar_solicitud_conciliacion` para envíos por lotes/CLI.

### 7.2 Parser de acuse (`acuse_parser.py`)

Cuando hay un PDF de acuse oficial disponible (descargado automáticamente o subido
manualmente), el sistema **extrae su texto con PyMuPDF** y autocompleta el expediente:

- Folio (ej. `TIJ/26427/2026`), fecha de solicitud, solicitante, empresa citada, fecha del
  conflicto, objeto, unidad de conciliación.
- **Mapea el objeto de la conciliación → tipo de despido** (ej. "Despido" →
  injustificado).
- **Pantalla de vista previa** que compara los valores detectados con los actuales
  (marcando los nuevos o los que difieren) y permite al asesor **confirmar** antes de guardar.

### 7.3 Extensión de Chrome — "Conciliación BC Asistente"

Para cuando se detecta navegación automatizada o hay que resolver un CAPTCHA a mano, la
**extensión de Chrome complementaria (Manifest V3)** llena el formulario del portal **en
el navegador del propio asesor**:

- El asesor hace clic en *Enviar a Conciliación → Desde mi navegador (Extensión de
  Chrome)*.
- La extensión muestra las tareas pendientes (número de expediente, cliente, empresa,
  CURP) en su popup.
- **🚀 Llenar en el portal** abre el portal con el formulario **ya llenado** (aviso de
  privacidad, industria, fechas, trabajador, empresa, descripción) mediante un content
  script — el portal ve una sesión dirigida por una persona.
- El asesor revisa, resuelve CAPTCHAs en vivo y hace clic en *Enviar solicitud* él mismo.
- **🔍 Ya envié, detectar acuse** — la extensión detecta el folio, descarga el PDF del
  acuse, toma una captura de pantalla y **reporta todo a la API de la aplicación**
  (autenticada con el token personal del usuario), adjuntando el PDF al expediente.
- Pantalla de opciones que guarda la URL de la app + token y verifica la conexión.
- El paquete de la extensión se puede **descargar como .zip** desde la app
  (`/extension/descargar/`), listo para cargarse descomprimido en Chrome.

### 7.4 Fallbacks manuales

- Subir el PDF del acuse manualmente (`subir-conciliacion`) y luego previsualizar/
  confirmar los datos parseados.
- Descargar un **formulario de conciliación prellenado (PDF)** para presentarlo
  manualmente en el centro.
- Subir el acuse mediante el flujo normal de documentos.

---

## 8. Integración con WhatsApp

Dos métodos de envío:

1. **Deep links (wa.me)** — gratis; abre WhatsApp con un mensaje pre-llenado.
2. **API de WhatsApp de Twilio** — mensajes enviados desde el servidor (requiere
   credenciales de Twilio); cae automáticamente al deep link cuando no está configurado.

### Funcionalidades

- **Plantillas** para: recordatorio de audiencia, citatorio, seguimiento de convenio,
  seguimiento general, solicitud de documentos y mensajes personalizados — con variables
  (`{cliente}`, `{fecha}`, `{asesor}`…).
- **Mensajes automáticos por cambio de estado**: cada estado del expediente tiene un
  mensaje configurado (caso nuevo, solicitud creada, citatorio, audiencia, no notificado,
  reprogramación, convenio, sin conciliación, demanda, cerrado). Interruptor por caso
  para activar/desactivar.
- **Historial de mensajes** por caso con estado (pendiente/enviado/fallido), canal y
  bitácoras de error.
- Normalización de números mexicanos (agrega el código de país 52 y limpia formatos
  comunes).
- Comando de gestión `enviar_whatsapp_automatico` para vaciar mensajes pendientes (con
  opciones `--dry-run` y `--send-twilio`).

---

## 9. Importaciones y utilidades

### 9.1 Importación CLT (citas desde Excel)

El archivo `CLT.xlsx` (citas de conciliación pre-programadas del CCL) se importa como
**expedientes con audiencias programadas**:

- Importación por hoja (ej. pestañas mensuales), **creación automática de usuarios
  asesores** encontrados en el archivo si es necesario, y opciones de limpieza para datos
  de prueba.
- La CURP es opcional al importar y se captura después (para que los números fluyan rápido).

### 9.2 Catálogo de empresas (`Empresa`)

- Importación desde `Empresas y Domicilios.xlsx` — **idempotente**, nombres normalizados
  (mayúsculas, sin acentos, espacios compactados) para que reimportar un archivo en
  crecimiento nunca duplique registros.
- Tipo de persona detectado automáticamente; el domicilio desglosado se usa para el
  **autocompletado en el formulario de cliente** (endpoint AJAX `empresas/buscar/`).

### 9.3 Generador de CURP

Herramienta independiente para **generar una CURP válida** a partir de los datos
personales (nombre, fecha de nacimiento, género, estado) — ahorra búsquedas manuales al
dar de alta clientes.

### 9.4 Ajustes del usuario

Página de ajustes por usuario: información del perfil, teléfono, preferencia de
automatización de WhatsApp, gestión del token de API y configuración de la extensión.

---

## 10. Módulo de Finanzas

Organizado por **oficina** (sucursal) y por **semana de trabajo** para reportes operativos.

### 10.1 Oficinas

Catálogo de oficinas del despacho con dirección, teléfono, responsable y bandera de
activa. Cada oficina tiene su propia operación de ingresos/gastos/caja diaria.

### 10.2 Semanas de trabajo

El sistema financiero gira alrededor de **semanas** (lunes–domingo): la semana actual se
crea automáticamente; cada movimiento se puede atribuir a una semana. Las semanas se
pueden abrir/cerrar. Totales por semana: **ingresos** (caja + pagos de convenios),
**gastos** (caja + gastos + nómina) y **balance**, calculados dinámicamente.

### 10.3 Pagos de convenios (`SettlementPayment`)

Pagos recibidos por acuerdos (convenios): fecha, cliente, expediente, monto, forma de
pago (efectivo/transferencia/cheque/tarjeta crédito/tarjeta débito/depósito/otro),
oficina, notas y responsable del registro.

### 10.4 Gastos (`Expense`)

Gastos operativos por oficina con categoría (renta, luz, agua, internet, teléfono,
papelería, publicidad, sueldos, gasolina, mantenimiento, impuestos, equipo, muebles,
seguros, honorarios, otro), proveedor, folio fiscal/factura y responsable del registro.

### 10.5 Convenios y honorarios (`Agreement` / `Honorario`)

- **Convenios** con el cliente: monto, estado (pendiente de firma → firmado → pagado /
  pagado parcialmente / cancelado), responsable, oficina y **total de honorarios
  automático**.
- **Honorarios:** una o varias partidas por convenio con un **% de tarifa**
  (25/30/35/40/50%); el monto se calcula automáticamente (`convenio × % ÷ 100`), con
  fechas estimada/pagada y sumas de pagado/pendiente agregadas en el convenio.

### 10.6 Comisiones (`Commission`)

Comisiones de asesores sobre convenios cerrados: % configurable, **monto calculado
automáticamente**, estado (pendiente/pagada/cancelada), fecha de pago, oficina y
responsable del registro.

### 10.7 Empleados y nómina (`Employee` / `Payroll`)

- Catálogo de empleados con puesto (administrativo, asesor jurídico, supervisor,
  contador, recepcionista, auxiliar, director…), periodo de pago, salario, oficina y
  bandera de activo.
- **Pagos de nómina** por período: tipo de período (semanal/quincenal/mensual/
  extraordinario/aguinaldo/prima vacacional/bono), rango del período, salario pagado,
  descuentos (ISR/IMSS) y **total calculado automáticamente** (`salario − descuentos`),
  oficina y responsable del registro.

### 10.8 Caja diaria (`CashMovement`)

Movimientos de caja por oficina y fecha: **ingresos** (pago de convenio, pago de cliente,
anticipo, devolución, otro) o **egresos** (papelería, gasolina, renta, luz, agua,
internet, teléfono, viáticos, comisiones, honorarios, otro). La coherencia entre
categoría y tipo se **valida** (ej. un ingreso no puede tener categoría de egreso). El
campo de referencia vincula el movimiento al expediente/factura.

### 10.9 Socios, préstamos y distribución de utilidades

- **Socios (`Partner`):** % de participación por socio para el reparto de utilidades.
- **Préstamos entre socios (`PartnerLoan`):** registro formal de préstamos entre socios
  (origen → destino, monto, concepto, estado, saldo pendiente), que reemplaza las notas
  informales tipo "le debo a…".
- **Distribución de utilidades (`ProfitDistribution` + `PartnerProfit`):**
  - Calcula automáticamente la **utilidad neta** = monto del convenio − honorarios −
    comisiones − retenciones − gastos relacionados.
  - La distribuye entre los socios según su % de participación (**participación
    individual calculada automáticamente**), con estados (borrador → distribuida →
    confirmada/cancelada).
  - **Resúmenes acumulados por socio** (generada / pagada / pendiente) que se actualizan
    automáticamente al confirmar distribuciones.

### 10.10 Dashboard financiero

- KPIs por oficina y globales; **flujo de caja mensual** con gráfica alimentada por el
  endpoint JSON `api_flujo_mensual`; **exportación a Excel** de los totales del dashboard.
- **Reporte de convenios** (`reporte_convenios`) con exportación a Excel.

---

## 11. Comandos de gestión (CLI)

| Comando | Propósito |
|---------|-----------|
| `crear_usuarios_prueba` | Crear usuarios de prueba (1 superadmin, 4 admins, 15 asesores) |
| `seed_datos` / `seed_clientes_prueba` | Sembrar casos demo (10 escenarios laborales / clientes completos con cálculos) |
| `enviar_recordatorios` | Enviar recordatorios de próximas acciones/audiencias (`--days`, `--dry-run`) |
| `enviar_solicitud_conciliacion` | Enviar solicitudes de conciliación al portal de BC desde CLI (`--headless`) |
| `enviar_whatsapp_automatico` | Vaciar mensajes automáticos de WhatsApp pendientes (`--dry-run`, `--send-twilio`) |
| `importar_clt` | Importar citas de CLT.xlsx como expedientes con audiencias |
| `importar_empresas` | Importar el catálogo de empresas y domicilios (idempotente) |
| `importar_machotes` | Convertir plantillas `.docx` en machotes (`--reload`, `--file`) |
| `migrate_sqlite_to_pg` | Migración única de datos de SQLite a PostgreSQL |

---

## 12. Resumen de integraciones

| Servicio | Uso | Configuración |
|----------|-----|---------------|
| **Selenium** | Automatización del portal (headless/debug) | incluido |
| **Celery + Redis** | Tareas en segundo plano (automatización de conciliación); fallback con threads | `REDIS_URL` |
| **Twilio** | Envío por API de WhatsApp (opcional) | variables de entorno `TWILIO_*` |
| **SMTP** | Correos de restablecimiento de contraseña (backend de consola en desarrollo) | variables de entorno `EMAIL_*` |
| **WeasyPrint** | Generación de PDFs (expediente, documentos) | incluido |
| **python-docx** | Generación de demandas en Word (.docx) | incluido |
| **PyMuPDF (fitz)** | Extracción de texto de los PDFs de acuse | incluido |
| **openpyxl** | Importaciones (CLT, empresas) y exportaciones a Excel | incluido |
| **API de la extensión de Chrome** | Endpoints REST autenticados con token para la extensión | `api_token` personal |
| **Railway** | Despliegue; detecta automáticamente dominio, PostgreSQL y Redis | variables de entorno |

---

## 13. Arquitectura y notas técnicas

- **Backend:** Django 5.x, locale `es-mx`, zona horaria `America/Mexico_City`.
- **Base de datos:** SQLite (desarrollo) / PostgreSQL (producción) vía `DATABASE_URL`;
  detección automática del entorno de Railway (`PGHOST`…).
- **Frontend:** Tailwind CSS (CDN) + **HTMX** para interacciones dinámicas (sin framework
  JS pesado); diseño responsive.
- **Archivos estáticos:** Whitenoise (`CompressedManifestStaticFilesStorage`) para servir
  en producción sin Nginx.
- **Trabajo en segundo plano:** Celery cuando hay Redis, **fallback con threads** en caso
  contrario (degradación elegante para desarrollo local).
- **Auditabilidad:** cada entidad clave (pagos, gastos, nómina, caja, préstamos,
  distribuciones, comisiones) registra `registrado_por`/`creado_por`.
- **Despliegue:** Dockerfile, configuración de Railway, entrypoint (levanta el worker de
  Celery automáticamente cuando existe Redis), receta de Nginx + Gunicorn para VPS
  (droplet) y guía de despliegue para clientes.

---

## 14. Pruebas

La suite incluye **48 pruebas** (expedientes, finanzas, automatización) que cubren la
validación de transiciones de estado, los cálculos financieros y el script de verificación
`verify_demandas_calculos.py` (usado por CI). Ejecución:

```bash
uv run python manage.py test
```

---

## 15. Inicio rápido (desarrollo)

```bash
uv sync                          # instalar dependencias
uv run python manage.py migrate  # migraciones de BD
uv run python manage.py crear_usuarios_prueba
uv run python manage.py runserver
```

Accesos de prueba: `superadmin/Admin123!` · `admin1/Admin1!` · `asesor1/Asesor1!`
