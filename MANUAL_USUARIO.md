# 📘 Manual de Usuario — Despacho Laboral

> **Para:** Asesores, personal administrativo (admins) y superadmin
> **Sistema:** Conciliación Laboral Tijuana — Despacho Laboral
> **Versión:** 1.0 · Agosto 2026

Este manual explica **paso a paso** cómo hacer el trabajo diario en el sistema: desde
crear un cliente y su expediente, hasta enviar la conciliación al portal, generar
documentos legales, comunicarte con el cliente por WhatsApp y gestionar los reportes.

---

## Índice

1. [Primeros pasos](#1-primeros-pasos)
2. [El dashboard del asesor](#2-el-dashboard-del-asesor)
3. [Registrar un cliente](#3-registrar-un-cliente)
4. [Crear un expediente (caso)](#4-crear-un-expediente-caso)
5. [La ficha del expediente](#5-la-ficha-del-expediente)
6. [Cálculos laborales](#6-cálculos-laborales)
7. [Solicitud de conciliación](#7-solicitud-de-conciliación)
8. [Enviar al portal de conciliación](#8-enviar-al-portal-de-conciliación)
9. [Extensión de Chrome](#9-extensión-de-chrome)
10. [Documentos legales (machotes y demanda)](#10-documentos-legales-machotes-y-demanda)
11. [WhatsApp](#11-whatsapp)
12. [Transferencias de casos](#12-transferencias-de-casos)
13. [Notificaciones y avisos](#13-notificaciones-y-avisos)
14. [Sección de administración](#14-sección-de-administración)
15. [Búsqueda global](#15-búsqueda-global)
16. [Solución de problemas comunes](#16-solución-de-problemas-comunes)
17. [Referencia rápida de estados](#17-referencia-rápida-de-estados)

---

## 1. Primeros pasos

### 1.1 Iniciar sesión

1. Abre la URL de la aplicación en tu navegador (Chrome recomendado).
2. Escribe tu **usuario** y **contraseña**.
3. Presiona **Iniciar sesión**.

Al entrar, el sistema te lleva automáticamente a tu dashboard según tu rol
(asesor → dashboard del asesor; admin → dashboard administrativo).

### 1.2 ¿Olvidaste tu contraseña?

1. En la pantalla de login, haz clic en **¿Olvidaste tu contraseña?**
2. Escribe tu correo y presiona **Enviar**.
3. Abre el correo y sigue el enlace para crear una nueva contraseña.

### 1.3 Cerrar sesión

Usa el botón **Salir** en el menú superior. Cierra sesión siempre que te
alejes de tu equipo.

### 1.4 Navegación general

- **Menú superior:** accesos a tu dashboard, expedientes, clientes, calendario, reportes
  (según tu rol) y tu nombre de usuario (para cerrar sesión).
- **🔔 Campana de notificaciones:** avisos del sistema, transferencias y recordatorios.
  Haz clic en una notificación para ir a donde te lleva.
- **🔍 Búsqueda global:** siempre disponible en la parte superior.

---

## 2. El dashboard del asesor

Al entrar verás tu panel personal con:

| Sección | Qué contiene |
|---------|--------------|
| **Avisos y Pendientes de la Semana** | Avisos obligatorios del administrador (🔴 alta, 🟡 media, 🟢 baja prioridad). Léelos y márcalos como vistos cuando el administrador lo pida. |
| **Tarjetas de estadísticas** | Total de casos, casos activos, casos cerrados, pendientes y **alertas** (casos que requieren tu atención). |
| **Próximas Audiencias** | Tus audiencias programadas con fecha y hora. Haz clic para abrir el expediente. |
| **Próximas Asesorías Gratuitas** | Clientes con asesoría gratuita agendada. Haz clic para ver/editar al cliente. |
| **Mis Casos Recientes** | Tus casos más recientes con número, cliente, estado y prioridad. Botón **Ver** para abrir cada uno y **Ver todos →** para la lista completa. |

> ⚠️ **Importante:** como asesor solo ves **tus** casos. Si un caso no aparece,
> probablemente está asignado a otro asesor o aún no te lo asignan.

---

## 3. Registrar un cliente

1. Ve a **Clientes → Nuevo cliente** (o desde el dashboard, en el menú superior).
2. Llena los datos en secciones:
   - **Identidad:** nombre completo, CURP, RFC, teléfono, WhatsApp, correo, fecha de
     nacimiento y género.
   - **Dirección particular:** calle, número, código postal y colonia.
   - **Datos del patrón (empresa):** nombre, actividad económica, teléfono, razón
     social, domicilio y referencias.
   - **Empleo:** puesto, salario mensual, periodo de pago, horas semanales, jornada,
     fecha de ingreso y fecha de salida/despido.
   - **Captación y oficina:** cómo se enteró del despacho y qué oficina atendió
     (Plaza Patria, Otay, CLT).
   - **Asesoría gratuita:** marca si se ofreció, si se agendó y la fecha.
3. Consejos:
   - **CURP:** si no la tienes, usa el **Generador de CURP** (sección utilidades) y
     cópiala.
   - **Empresa:** escribe el nombre y usa el **buscador de empresas** que aparece para
     autocompletar nombre y domicilio del catálogo. Si no aparece, captúralo a mano.
4. Presiona **Guardar**.

> 💡 **Dato clave:** mientras más completo esté el cliente, más automático será todo lo
> demás (formularios, documentos y envío al portal). Los datos del cliente se usan en
> TODOS los documentos.

---

## 4. Crear un expediente (caso)

1. Ve a **Expedientes → Nuevo expediente**.
2. Selecciona el **cliente** (busca por nombre o CURP). Si no existe, créalo primero.
3. Selecciona el **asesor asignado** (por defecto eres tú).
4. Completa los datos del caso:
   - **Monto reclamado** y **monto convenio** (si ya hay acuerdo).
   - **Tipo de despido** (justificado, injustificado, voluntario, rescisión, otro).
   - **Prestaciones reclamadas** (texto libre).
   - **Fecha de audiencia**, **próxima acción** y **prioridad** (baja/media/alta).
   - **Notas internas** (opcional).
5. Presiona **Guardar**.

El sistema genera el **número de expediente automáticamente** (formato `AAAA-####`,
ej. `2026-0042`) — no lo puedes cambiar.

---

## 5. La ficha del expediente

Al abrir un expediente (`Ver` en tu lista) encuentras todo el caso en una sola pantalla:

### 5.1 Barra de acciones (parte superior)

| Botón | Qué hace |
|-------|----------|
| **Cálculos** | Abre el cálculo laboral del caso. |
| **WhatsApp** | Envía mensajes al cliente. |
| **Solicitud** | Llena el formato oficial de solicitud de conciliación. |
| **🌐 Conciliación ▾** | Menú desplegable con: Envío Automático, Descargar Formulario (PDF) y Subir Acuse manual. |
| **Documentos** | Catálogo de machotes para generar documentos (solo si tienes permiso). |
| **Demanda / Asistente de Demanda** | Genera la demanda laboral (solo si tienes permiso). |
| **Transferir** | Solicita transferir el caso a otro asesor. |
| **Editar / Editar Cliente** | Modifica el expediente o los datos del cliente. |
| **PDF** | Descarga el expediente en PDF. |

### 5.2 Información del caso

- Asesor, cliente (con CURP), empresa, oficina, fecha de creación.
- **Formulario de Conciliación:** tipo de despido, folio de trámite, fecha de trámite,
  resultado de audiencia y prestaciones reclamadas.
- **Montos:** monto reclamado y monto convenio.
- **Fechas:** audiencia, próxima acción, última actualización.
- **Notas internas** del expediente.

### 5.3 Cambiar el estado del caso

1. En el bloque **Cambiar Estado**, el sistema muestra **solo las transiciones
   permitidas** desde el estado actual (botones de colores).
2. Haz clic en el estado nuevo (ej. **Solicitud creada** cuando envíes la solicitud).
3. La página se recarga y el estado queda actualizado. El sistema **no permite saltos
   inválidos** (ej. de "Nuevo" a "Audiencia" directamente).

### 5.4 Registrar el resultado de una audiencia

Cuando el caso está en **Audiencia programada**, aparece el bloque
**Registrar Resultado de Audiencia** con 4 tarjetas:

- ❌ **No notificado** → se genera una nueva audiencia.
- 🤝 **Convenio** → te pide capturar el **monto del convenio** antes de guardar.
- 🚫 **Sin conciliación** → el caso queda listo para preparar la demanda.
- 🔄 **Reprogramar** → nueva fecha.

Haz clic en la tarjeta correspondiente; si es convenio, escribe el monto y confirma.

### 5.5 Documentos del caso

1. En el bloque **Documentos**, selecciona el archivo (PDF, imagen…).
2. Escribe una **descripción** (ej. "INE del cliente") y elige el **tipo**
   (INE, contrato, evidencia, screenshot, citatorio, PDF, otro).
3. Presiona **Subir Documento**.
4. Cada documento muestra quién lo subió y cuándo. Puedes abrirlo (clic en el nombre) o
   eliminarlo con **Eliminar**.

### 5.6 Notas y seguimiento

- Escribe una nota en **Notas y Seguimiento** y presiona **Agregar Nota**.
- Las notas quedan en un **timeline** con autor y fecha (como un chat interno del caso).
- La **Línea de Tiempo** al final muestra todo el historial de movimientos del
  expediente (creación, cambios de estado, documentos, notas, audiencias).

---

## 6. Cálculos laborales

### 6.1 Calcular prestaciones de un caso

1. Abre el expediente y presiona **Cálculos** (o desde la lista de expedientes).
2. Revisa los datos base (salario, fechas, periodo de pago). El sistema calcula el
   **salario diario**, **días trabajados** y **años de servicio**.
3. Marca/desmarca con **checkboxes** qué conceptos incluir (aguinaldo, vacaciones,
   prima vacacional, prima de antigüedad, indemnización 90 días, 20 días por año,
   vacaciones vencidas, horas extras, salarios devengados, días festivos).
4. Para conceptos semiautomáticos, captura los datos extra (ej. **días de vacaciones
   vencidas**, **cantidad de horas extra**, **días festivos**).
5. Presiona **Calcular / Guardar**. Verás el **desglose por concepto** con su artículo
   de la LFT, el **tope aplicado** (si aplica) y el **total**.

> 💡 **Override de vacaciones:** si el caso no corresponde a los días por antigüedad
> (ej. ya se pagaron algunos años), captura en el campo "Días de vacaciones a pagar
> (manual)" los días realmente adeudados. El sistema lo indica con la bandera
> *override aplicado*.

### 6.2 Simulación rápida (sin crear caso)

1. Ve a **Simulación Rápida** (sección cálculos).
2. Captura salario, fechas de ingreso y salida, y periodo de pago.
3. Presiona **Simular** para ver el desglose completo. Ideal para cotizar una
   asesoría antes de abrir el caso.

> ⚠️ Los valores legales (UMA, salario mínimo, días de aguinaldo, etc.) los actualiza el
> administrador. No modifiques nada en el panel de admin de Django a menos que sepas lo
> que haces.

---

## 7. Solicitud de conciliación

El formato oficial **"Solicitud de Conciliación"** del Centro de Conciliación Laboral de
Baja California se llena con los datos del expediente (la mayoría vienen prellenados y
solo se editan desde la ficha del cliente).

1. Abre el expediente y presiona **Solicitud**.
2. Revisa los datos del trabajador, dirección, empleo y empresa (son de solo lectura).
3. Captura lo que sí se edita:
   - **Fecha del conflicto**, **horas semanales**, **periodo de pago**.
   - **Objeto de la solicitud** (puedes marcar varios: Despido, Terminación voluntaria,
     Derecho de antigüedad, Rescisión, Pago de prestaciones, Preferencia, Ascenso,
     Acoso laboral).
   - **Quién entregará el citatorio** (el solicitante o el notificador del centro).
   - **Discapacidad** (motriz, visual, auditiva, psicosocial, habla) si aplica.
   - **Traductor** (señas / lengua de origen) si aplica.
   - **Firma:** nombre del firmante y fecha.
4. Opciones al terminar:
   - **💾 Guardar borrador** — guarda en tu navegador (mismo equipo) para continuar
     después.
   - **✅ Guardar solicitud** — guarda el formato en el expediente.
5. Puedes **Imprimir** el formato desde el botón superior.

---

## 8. Enviar al portal de conciliación

El envío al portal oficial (`app.conciliacionbc.gob.mx`) tiene **3 modos**. En el
expediente, abre **🌐 Conciliación ▾ → Envío Automático** y elige:

### Modo A — 🤖 Automático (Headless) *(recomendado)*

1. En la pantalla de confirmación, revisa el **resumen de datos** que se enviarán
   (cliente, CURP, teléfono, empresa, tipo de despido, folio actual).
2. Si el expediente ya tiene folio, el sistema te lo advierte (se generará uno nuevo).
3. Selecciona **Automático (Headless)** y presiona **🚀 Enviar al Portal de Conciliación**.
4. El navegador automatizado trabaja en segundo plano; la página te muestra el
   **progreso en vivo** con capturas de pantalla y tiempo transcurrido.
5. Al terminar, el sistema **guarda el folio** en el expediente y **adjunta el PDF del
   acuse**. Verás el resultado en el bloque **🌐 Envíos al Portal de Conciliación** de la
   ficha del expediente.

### Modo B — 👁️ Visible (Debug)

Igual que el automático, pero el navegador se abre en pantalla para que veas cada paso.
Útil para detectar por qué un envío falla.

### Modo C — 📲 Desde mi navegador (Extensión de Chrome)

Cuando la automatización se traba (CAPTCHA, cambios en el portal), usa la extensión que
llena el formulario **en tu propio navegador** y tú das el clic final. Detalles en la
[sección 9](#9-extensión-de-chrome).

### 8.1 Si el envío falla

- En la ficha del expediente, el bloque de envíos muestra **❌ Error** con el motivo.
- Presiona **🔄 Reintentar** para volver a intentarlo.
- Si sigue fallando, usa el **Modo C (extensión)** o el **fallback manual**:

### 8.2 Fallback manual — subir el acuse

1. En el expediente, abre **🌐 Conciliación ▾**.
2. En **📄 Subir PDF Manual**, selecciona el PDF del acuse descargado del portal y
   presiona **📥 Subir Acuse y Extraer Datos**.
3. El sistema **lee el acuse automáticamente** y te muestra una **vista previa**:
   folio, solicitante, empresa citada, fecha del conflicto, tipo de despido y unidad.
4. Revisa los valores detectados vs. los actuales (marca los que son nuevos o difieren)
   y presiona **Confirmar** para guardarlos en el expediente.

### 8.3 Descargar el formulario prellenado

En **🌐 Conciliación ▾ → 📥 Descargar Formulario** obtienes el PDF del formato de
solicitud ya llenado, para presentarlo manualmente en el centro si así se requiere.

---

## 9. Extensión de Chrome

### 9.1 Instalación (una vez por computadora)

1. Abre Chrome y ve a **`chrome://extensions`**.
2. Activa el **Modo de desarrollador** (interruptor arriba a la derecha).
3. Haz clic en **"Cargar descomprimida"** y selecciona la carpeta de la extensión
   (descárgala desde la app: **Extensión de Chrome → Descargar paquete (.zip)** y
   descomprímela).
4. La extensión **"Conciliación BC — Asistente"** queda instalada.

### 9.2 Configuración (una vez)

1. Haz clic en el ícono de la extensión → **⚙️ Opciones**.
2. Pega la **URL de la app** (ej. `https://tu-app.railway.app`).
3. Pega tu **token personal**:
   - En la app: abre cualquier expediente → **Enviar a Conciliación** → enlace a
     **"Extensión de Chrome"** (o entra a `/extension/config/`).
   - Copia el token que aparece ahí. Si se filtra, regenera uno nuevo desde esa misma
     página.
4. **💾 Guardar configuración** (verifica la conexión automáticamente).

### 9.3 Uso por caso

1. En la app, abre el expediente → **Enviar a Conciliación** → elige
   **"📲 Desde mi navegador (Extensión de Chrome)"** → **Enviar**.
2. Haz clic en el ícono de la extensión → verás la tarea pendiente →
   **🚀 Llenar en el portal**.
3. Se abre el portal con el formulario **ya llenado**. **Revisa los datos**, resuelve el
   CAPTCHA si aparece y haz clic en **"Enviar solicitud"**.
4. En la página del acuse, haz clic en **"🔍 Ya envié, detectar acuse"** (o se detecta
   solo). La extensión guarda el **folio** en la app, descarga el **acuse PDF** y lo
   adjunta al expediente.
5. Si la descarga automática del acuse falla, descárgalo del portal y súbelo con el
   flujo manual ([sección 8.2](#82-fallback-manual--subir-el-acuse)).

---

## 10. Documentos legales (machotes y demanda)

> 🔒 **Permiso:** solo usuarios con el permiso **"Puede generar documentos legales"**
> (configurado por el administrador) ven los botones de Documentos/Demanda. Si no los
> ves, pídelo al administrador.

Los **machotes** son plantillas reutilizables (demanda laboral, carta finiquito, convenio,
solicitud, citatorio…) que se llenan automáticamente con los datos del expediente
mediante **marcadores** como `{{ nombre_cliente }}`, `{{ empresa }}`, `{{ salario }}`,
`{{ curp }}`, etc.

---

### 10.1 El generador de documentos (desde el expediente)

1. Abre el expediente y presiona **Documentos**.
2. Arriba verás una **barra de completitud** con el estado de los datos del expediente
   (ej. `12/15 completos`) y un enlace para **editar el expediente** si faltan datos.
3. Las plantillas están **agrupadas por categoría** (Demanda Laboral, Carta Finiquito,
   Convenio, Solicitud, Citatorio, Otro). Cada tarjeta muestra:
   - **Ícono y nombre** de la plantilla, tipo de despido y jurisdicción.
   - Los **marcadores disponibles** que se rellenarán (hasta 5 visibles).
4. Cada plantilla tiene 2 botones:
   - **Preparar y generar** → revisas que no falten datos y generas (sección 10.2).
   - **Editar** → abre el editor directamente con los datos ya insertados (sección 10.3).

---

### 10.2 Preparar el documento (revisar datos antes de generar)

1. Presiona **Preparar y generar** en la plantilla elegida.
2. **Barra de completitud:** porcentaje de datos completos (verde ≥80%, ámbar ≥50%,
   rojo <50%) con mensaje orientativo.
3. **Checklist por secciones** (👤 Cliente, 💼 Empleo, 🏢 Empresa, 📋 Expediente): cada
   campo muestra ✓ (completo) o ! (faltante) con su valor actual y un botón **Editar**
   que abre el formulario correspondiente para corregirlo al momento.
4. **Resumen de cálculos** (columna derecha): aguinaldo, vacaciones, prima vacacional,
   prima de antigüedad (con aviso de tope), indemnización y **TOTAL**, calculados con
   los datos del expediente. Enlace a **Ver cálculo completo →**.
5. **Marcadores disponibles:** chips con los `{{ marcadores }}` que se inyectarán.
6. **Vista previa de valores inyectados:** los valores que se insertarán; los que
   aparecen en **rojo** (ej. `[CURP]`, `[MONTO]`) indican datos faltantes.
7. Presiona **✅ Generar documento** (si faltan datos, el botón cambia a
   **⚠️ Generar de todas formas**) → se abre el editor con el texto ya llenado.

---

### 10.3 Editor del documento

1. El documento se abre en un **editor de texto enriquecido** (Quill) con los datos del
   caso **ya insertados** — puedes editar cualquier parte libremente.
2. Botones:
   - **👁️ Vista previa** — ve el documento limpio (modal) antes de descargar.
   - **📄 Descargar Word** — genera el `.docx` listo para imprimir/firmar (también con
     `Ctrl+Shift+D`).
3. **Auto-guardado:** cada 30 segundos se guarda un **borrador local** en tu navegador;
   si cierras sin querer, al volver se restaura. Ojo: si cambias de equipo, el borrador
   no viaja contigo.
4. Al final de la página verás **otras plantillas similares** para cambiar rápido.
5. ⚠️ Descarga siempre el documento; los cambios no editados se pierden al cerrar.

---

### 10.4 Catálogo de machotes (gestionar plantillas)

Entra a **Machotes → Catálogo** (menú o desde el botón **Documentos** del expediente):

1. **Buscar y filtrar:** busca por nombre/descripción/archivo y filtra por **categoría**
   (muestra el conteo por categoría). Botón **Limpiar filtros**.
2. Cada plantilla (agrupada por categoría) muestra su ícono, nombre, descripción,
   archivo de origen, y etiquetas de **★ Favorito**, tipo de despido y jurisdicción.
3. Acciones por plantilla:
   - **👁️ Vista previa** — despliega el contenido HTML de la plantilla en pantalla.
   - **✏️ Editar** — abre el editor de plantilla (sección 10.5).
   - **Renombrar** — cambia el nombre sin abrir el editor (modal).
   - **🗑️ Eliminar** — borra la plantilla (pide confirmación, no se puede deshacer).
4. Botón **📤 Subir nueva demanda (Word)** en la parte superior → sección 10.6.

> 💡 Los **machotes favoritos** aparecen primero en el editor de demanda. Marca la
> estrella desde el editor o el admin.

---

### 10.5 Editar una plantilla (machote)

1. Desde el catálogo, presiona **Editar** en la plantilla.
2. **Datos de la plantilla:** nombre, descripción, **categoría**, **tipo de despido**,
   **jurisdicción** (Federal / Estatal BC / Ambas) e **ícono** (emoji).
3. **Contenido:** editor de texto enriquecido; escribe los **marcadores**
   `{{ variable }}` donde quieras que se inserten datos del expediente.
4. **💾 Guardar cambios** (`Ctrl+Shift+S`). Los cambios aplican a todos los expedientes
   futuros.
5. En la parte inferior hay un bloque **🗑️ Eliminar plantilla** (con confirmación).

---

### 10.6 Subir una demanda Word como plantilla (importar .docx)

1. Desde el **Catálogo de Machotes**, presiona **📤 Subir nueva demanda (Word)**.
2. Selecciona un archivo **`.docx`** (demanda, finiquito, convenio, solicitud o
   citatorio ya redactados).
3. El sistema lo **convierte en plantilla reutilizable**: los datos específicos
   (fechas, salarios, CURP, RFC, teléfonos) se reemplazan automáticamente por
   **marcadores** (`{{ fecha }}`, `{{ salario }}`, `{{ curp }}`…).
4. **Clasificación automática por el nombre del archivo:** si el nombre contiene
   `demanda` → Demanda Laboral; `finiquito` → Carta Finiquito; `convenio` → Convenio;
   `solicitud` → Solicitud; `citatorio` → Citatorio; cualquier otro → Otro.
5. Si el archivo ya se importó antes, se muestra un aviso y **no se duplica**.
6. La plantilla queda disponible en el catálogo y en el generador de documentos.

---

### 10.7 Asistente de Demanda (paso a paso)

Guía de **4 pasos** para no omitir ningún dato. En el expediente, presiona
**Asistente de Demanda**:

- **Paso 1 — Datos del actor (trabajador):** nombre (aparecerá arriba y en la firma),
  CURP, RFC, teléfono, WhatsApp, email, fecha de nacimiento, género, cómo supo del
  despacho y oficina. (Los obligatorios están marcados con `*`.)
- **Paso 2 — Datos de empleo:** puesto, **salario** (necesario para los cálculos),
  periodo de pago, horas semanales, jornada, **fecha de ingreso** y **fecha de salida**.
- **Paso 3 — Datos de la empresa/patrón:** usa el **buscador de empresas** del catálogo
  para autocompletar, o captura nombre, razón social, actividad, tipo de persona
  (física/moral), teléfono, domicilio y referencias.
- **Paso 4 — Revisión final:**
  - **🔒 Datos críticos** — lista de lo que falta (si algo aparece en rojo "FALTA",
    regresa a completarlo).
  - **⚖️ Tipo de despido** — selecciónalo; **los cálculos se ajustan automáticamente**.
  - **🧮 Cálculo automático** — tabla con aguinaldo, vacaciones, prima vacacional,
    prima de antigüedad, indemnización y **TOTAL**.
  - **✍️ Verificación de la firma** — confirma que el nombre del actor aparezca arriba
    y abajo (evita que quede el nombre de una demanda anterior).

Al terminar, presiona **✨ Generar demanda y editar** → se abre el editor con todo
insertado. Puedes volver atrás en cualquier paso con **Anterior**.

---

### 10.8 Editor de Demanda

1. **Selector de plantillas por tipo de despido** (Injustificado, Justificado,
   Voluntario, Rescisión, Otro) — la recomendada para cada tipo trae la etiqueta
   **RECOMENDADO**. Cambia con un clic (o `Ctrl+Shift+1..5`).
2. **Machotes de casos reales** (si existen): plantillas importadas de `.docx` de casos
   anteriores, con **estrella para marcarlas como favoritas**. Al cargarlas, los
   marcadores se reemplazan con los datos del expediente actual.
3. ⚠️ Si al cliente le **faltan datos críticos**, verás una alerta roja y la descarga
   queda **bloqueada** hasta completarlos (enlace directo al asistente).
4. Botones: **👁️ Vista previa**, **📑 Guardar como machote** (sección 10.9) y
   **📄 Descargar Word** (`Ctrl+Shift+D`).
5. **Auto-guardado** del borrador local cada 30 segundos (se restaura al volver).
6. Al cambiar de plantilla o machote, si ya editaste contenido te pedirá confirmación
   (para que no pierdas tu trabajo).

---

### 10.9 Guardar como machote (reutilizar tu versión)

1. En el editor de demanda (o de documento), presiona **📑 Guardar como machote**.
2. Escribe un **nombre** descriptivo (ej. "Demanda por despido injustificado con
   vacaciones vencidas").
3. El sistema **convierte los datos del cliente en marcadores** automáticamente, para
   que la plantilla sirva en otros casos.
4. **Guardar machote** → queda en el catálogo disponible para todo el equipo.

---

### 10.10 Generar la demanda directamente

- En el expediente, presiona **Demanda** → se abre el editor con la demanda ya generada
  (plantilla según el tipo de despido, datos y cálculos integrados).

> 💡 El administrador también puede crear plantillas desde el **admin de Django**
> (Machotes → Añadir) o con el comando `importar_machotes` (convierte un lote de
> archivos .docx).

---

## 11. WhatsApp

### 11.1 Enviar un mensaje

1. En el expediente, presiona **WhatsApp** (botón verde).
2. Elige una **plantilla** (recordatorio de audiencia, citatorio, seguimiento de
   convenio, seguimiento, solicitud de documentos o mensaje personalizado).
3. Revisa el mensaje (puedes editarlo) y el destino (WhatsApp o teléfono del cliente).
4. Elige cómo enviarlo:
   - **Enlace wa.me** (gratis): se abre WhatsApp con el mensaje listo; tú presionas
     enviar.
   - **API Twilio** (si está configurada): se envía directo desde el sistema.
5. Presiona **Enviar**. El mensaje queda en el **historial** con su estado
   (pendiente / enviado / fallido).

### 11.2 Mensajes automáticos por cambio de estado

- El expediente tiene un interruptor **🤖 Activo/Inactivo** en la sección WhatsApp.
- Con **Activo**, cada cambio de estado genera un mensaje automático al cliente
  (caso registrado, solicitud creada, citatorio, audiencia, convenio, demanda, cierre…).
- Los mensajes generados aparecen en la ficha como **Mensajes Automáticos** con estado
  *pendiente*; el administrador los envía con el comando programado.

> ⚠️ Verifica siempre que el número del cliente tenga el **código de país** (ej.
> `+52...`) para que los enlaces funcionen.

---

## 12. Transferencias de casos

Si no puedes atender un caso (audiencia simultánea, conflicto de horario, etc.):

1. Abre el expediente → **Transferir**.
2. Explica el **motivo** (obligatorio) y opcionalmente **sugiere un asesor destino**.
3. Presiona **Enviar solicitud**.
4. La administración revisa, **reasigna** si lo considera y aprueba o rechaza.
5. Puedes **cancelar** tu solicitud mientras esté pendiente (botón en el historial).
6. El estado y las notificaciones te mantienen informado del resultado.

---

## 13. Notificaciones y avisos

- **🔔 Campana:** notificaciones de transferencias, avisos y recordatorios. Haz clic en
  una para abrirla; usa **marcar todas como leídas** para limpiar la campana.
- **Avisos y Pendientes:** los publica la administración en tu dashboard. Léelos a
  diario: pueden contener instrucciones, cambios de proceso o pendientes de la semana.

---

## 14. Sección de administración

*(Solo usuarios con rol administrativo, superadmin o finanzas)*

### 14.1 Reportes y exportación

1. Ve a **Reportes**.
2. Consulta productividad por asesor, montos totales y estadísticas del despacho.
3. Usa **Exportar Excel** para descargar la información y trabajarla fuera del sistema.

### 14.2 Gestionar transferencias

1. Ve a **Transferencias** (lista de solicitudes pendientes).
2. Revisa el motivo y el asesor sugerido.
3. Decide: **Aprobar** (con o sin reasignación a otro asesor, dejando un comentario
   opcional) o **Rechazar** (con comentario).
4. Al aprobar, el expediente queda asignado al nuevo asesor y se notifica a todos.

### 14.3 Crear avisos y pendientes

1. Ve a **Avisos → Crear aviso**.
2. Captura **título**, **contenido**, **prioridad** (alta/media/baja) y
   **fecha de vencimiento** (opcional; al vencer el aviso deja de mostrarse).
3. Presiona **Publicar**. El aviso aparece en el dashboard de todos.

### 14.4 Matriz de permisos (superadmin)

1. Ve a **Superadmin → Matriz de permisos**.
2. Cambia el **rol** de los usuarios y/o el permiso **"puede generar documentos"**.
3. Presiona **Guardar**. Cada cambio queda **auditado** (quién, cuándo y qué cambió).
4. Puedes **exportar la matriz a Excel** para respaldarla.
5. Usa **Cargar datos demo** solo en ambientes de prueba.

> ⚠️ Cambiar el rol de un asesor le quita el acceso a sus casos en el dashboard del
> asesor. Hazlo solo cuando sea intencional.

### 14.5 Configuración legal (panel de Django)

Cuando cambien los valores legales (UMA, salario mínimo, días de aguinaldo, etc.):

1. Entra al **admin de Django** (enlace desde el menú, solo admin/superadmin).
2. Busca **Configuraciones Legales** y edita la fila activa con los nuevos valores.
3. Guarda. Los cálculos nuevos usan los valores actualizados (los existentes se pueden
   recalcular desde cada expediente con **Cálculos**).

---

## 15. Búsqueda global

- Escribe en la barra de búsqueda: número de expediente, nombre del cliente, CURP,
  folio o empresa.
- El resultado te lleva directo al expediente o cliente que buscas.

---

## 16. Solución de problemas comunes

| Problema | Solución |
|----------|----------|
| No veo un expediente | Verifica que esté asignado a ti; si lo está y no aparece, escribe al administrador. |
| "No se puede cambiar el estado" | El sistema solo permite transiciones válidas. Revisa el orden del proceso (ej. debes crear la solicitud antes de pasar a citatorio). |
| El envío automático falla | Reintenta; si sigue fallando usa la **extensión de Chrome** o sube el acuse manualmente. |
| La extensión no responde | Verifica URL + token en Opciones; regenera el token si lo cambiaste en la app. |
| El documento sale con `[CURP]` o `[MONTO]` | Falta ese dato en el cliente/expediente. Usa la pantalla de **Preparar** para editarlo. |
| No veo los botones Documentos/Demanda | Necesitas el permiso **"Puede generar documentos legales"** — pídelo al administrador. |
| WhatsApp no abre | Confirma el número con código de país (+52) en la ficha del cliente. |
| La campana tiene muchas notificaciones | Marca **todas como leídas**; las pendientes se limpian. |

---

## 17. Referencia rápida de estados

| Estado | Significado | Siguientes pasos típicos |
|--------|-------------|--------------------------|
| 🟦 **Nuevo** | Caso recién creado | Llenar solicitud de conciliación |
| 🟪 **Solicitud creada** | Formato de solicitud listo | Enviar al portal / generar citatorio |
| 🟨 **Citatorio generado** | Citatorio preparado | Programar audiencia |
| 🟨 **Audiencia programada** | Fecha de audiencia asignada | Asistir y registrar resultado |
| 🟥 **No notificado** | No se pudo notificar | Nueva audiencia / reprogramación |
| 🟧 **Reprogramación** | Audiencia reprograda | Nueva fecha de audiencia |
| 🟩 **Convenio** | Se llegó a acuerdo | Registrar monto y dar seguimiento de pagos |
| ⬜ **Sin conciliación** | No hubo acuerdo | Preparar demanda |
| 🟥 **Demanda** | Demanda presentada | Seguimiento del juicio |
| ⬛ **Cerrado** | Caso terminado | (sin más acciones) |

---

*¿Dudas? Contacta al administrador del sistema o al área de soporte del despacho.*
