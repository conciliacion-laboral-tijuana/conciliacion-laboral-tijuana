# 📘 Manual de Administración — Despacho Laboral

> **Para:** Administrativos, finanzas y superadmin
> **Sistema:** Conciliación Laboral Tijuana — Despacho Laboral
> **Versión:** 1.0 · Agosto 2026

Este manual cubre las tareas de **administración** del sistema: gestión de usuarios y
permisos, actualización de la configuración legal, operación del **módulo financiero**
completo y los comandos de administración.

> 📖 Complementa al *Manual de Usuario* (trabajo diario de asesores) y a la
> *Documentación Funcional* (visión completa del sistema).

---

## Índice

1. [Roles administrativos](#1-roles-administrativos)
2. [Gestión de usuarios y matriz de permisos](#2-gestión-de-usuarios-y-matriz-de-permisos)
3. [Configuración legal](#3-configuración-legal)
4. [Avisos y pendientes](#4-avisos-y-pendientes)
5. [Gestión de transferencias](#5-gestión-de-transferencias)
6. [Comandos de administración](#6-comandos-de-administración)
7. [Módulo financiero — introducción](#7-módulo-financiero--introducción)
8. [Oficinas y semanas de trabajo](#8-oficinas-y-semanas-de-trabajo)
9. [Caja diaria (ingresos y egresos)](#9-caja-diaria-ingresos-y-egresos)
10. [Pagos de convenios](#10-pagos-de-convenios)
11. [Gastos operativos](#11-gastos-operativos)
12. [Convenios y honorarios](#12-convenios-y-honorarios)
13. [Comisiones](#13-comisiones)
14. [Empleados y nómina](#14-empleados-y-nómina)
15. [Socios y préstamos](#15-socios-y-préstamos)
16. [Distribución de utilidades](#16-distribución-de-utilidades)
17. [Dashboard financiero y reportes](#17-dashboard-financiero-y-reportes)
18. [Buenas prácticas de consistencia](#18-buenas-prácticas-de-consistencia)
19. [Solución de problemas comunes](#19-solución-de-problemas-comunes)

---

## 1. Roles administrativos

| Rol | Acceso administrativo |
|-----|-----------------------|
| **Superadmin** | Todo: matriz de permisos, admin de Django, superadmin dashboard, finanzas |
| **Administrativo (admin)** | Reportes, avisos, transferencias, admin de Django, finanzas |
| **Finanzas** | Dashboard financiero y módulo de finanzas (no gestiona usuarios) |

> ⚠️ Los cambios de **rol** y **permisos** de usuarios quedan **auditados**
> automáticamente (quién, cuándo y qué cambió). Úsalo con criterio.

---

## 2. Gestión de usuarios y matriz de permisos

### 2.1 Crear un usuario nuevo

1. Entra al **admin de Django** (enlace desde el menú, solo admin/superadmin).
2. En **Usuarios → Añadir usuario**, captura usuario, contraseña y datos de contacto.
3. Al guardar, el perfil se crea automáticamente (rol **asesor** por defecto).
4. Ajusta el rol y permisos desde la **Matriz de permisos** (abajo) o desde el perfil
   del usuario en el admin.

### 2.2 Matriz de permisos

1. Ve a **Superadmin → Matriz de permisos**.
2. Verás una tabla con todos los usuarios y sus columnas:
   - **Rol** (superadmin, admin, asesor, abogada, finanzas).
   - **¿Puede generar documentos?** — habilita los botones Documentos/Demanda en los
     expedientes (generadores de machotes y demanda laboral).
   - **Token API** — token personal para la extensión de Chrome.
3. Haz los cambios y presiona **Guardar**.

**Para cada cambio que hagas:**

| Acción | Qué pasa |
|--------|----------|
| Cambiar rol | El usuario cambia de dashboard y de alcance de visibilidad. |
| Habilitar/deshabilitar "puede generar documentos" | Se conceden/revocan los generadores de documentos legales. |
| Regenerar token | El token anterior deja de funcionar (hazlo si se filtró). |

4. Usa **Exportar Excel** para descargar la matriz y respaldarla.

> ⚠️ Cambiar el rol de un asesor **le quita el acceso a sus casos** en el dashboard del
> asesor. Hazlo solo cuando sea intencional (ej. ascenso a administrativo).

### 2.3 Tokens de la extensión de Chrome

- Cada usuario ve su token en **Ajustes → Extensión de Chrome** (o `/extension/config/`).
- Si un token se filtró, el propio usuario puede **regenerarlo** desde ahí; también
  puedes hacerlo desde el perfil en el admin.

### 2.4 Cargar datos demo

Usa **Superadmin → Cargar datos demo** **solo en ambientes de prueba** (nunca en
producción con datos reales). Crea usuarios y casos de ejemplo.

---

## 3. Configuración legal

Los valores legales del cálculo laboral viven en **Configuraciones Legales**
(modelo `LegalConfig`) y se editan **sin tocar código** cuando cambian las leyes.

### 3.1 Qué parámetros se configuran

| Parámetro | Uso | Valor de referencia (2024) |
|-----------|-----|---------------------------|
| **UMA diaria** | Base para topes y cálculos | $108.57 |
| **Salario mínimo general** | Cálculos y topes | $248.93 |
| **Salario mínimo frontera (ZLF)** | Zona Libre Frontera Norte | $374.89 |
| **Días de aguinaldo** | Aguinaldo proporcional | 15 |
| **% prima vacacional** | Prima sobre vacaciones | 25% |
| **Días por año (prima antigüedad)** | Prima de antigüedad | 12 |
| **Tipo de tope** | 2× UMA / 2× SM / 2× SM frontera | UMA |
| **Múltiplo del tope** | Multiplicador del tope | 2 |
| **Días de indemnización** | Indemnización constitucional | 90 |

### 3.2 Cómo actualizarla (ej. al inicio de cada año)

1. Entra al **admin de Django** → **Configuraciones Legales**.
2. Abre la fila **activa** (solo puede haber una activa; si creas otra y la marcas como
   activa, las demás se desactivan solas).
3. Actualiza la **UMA**, el **salario mínimo** y el **salario mínimo frontera** con los
   valores oficiales publicados (DOF), y cualquier otro parámetro que haya cambiado.
4. Guarda. Los **cálculos nuevos** usan los valores actualizados al instante.

### 3.3 Recalcular cálculos existentes

Los cálculos ya guardados conservan su histórico. Para actualizarlos con las reglas
nuevas, entra a cada expediente → **Cálculos** y guarda de nuevo (se recalcula con los
valores vigentes). El modelo `CalculoLaboral.recalcular()` hace lo mismo por programa.

> ⚠️ **No** cambies estos valores sin confirmar el dato oficial. Un error en la UMA o el
> salario mínimo altera **todos** los cálculos del despacho.

---

## 4. Avisos y pendientes

1. Ve a **Avisos → Crear aviso** (o desde el dashboard administrativo).
2. Captura:
   - **Título** y **contenido** (instrucciones, pendientes, cambios de proceso).
   - **Prioridad:** alta (🔴) / media (🟡) / baja (🟢).
   - **Fecha de vencimiento** (opcional): al vencer, el aviso deja de mostrarse
     automáticamente.
3. Presiona **Publicar**. Aparece en el dashboard de todos los asesores y admins.
4. Los avisos se pueden desactivar (bandera **Activo**) en el admin de Django.

> 💡 Usa el vencimiento para pendientes con fecha límite; usa prioridad alta solo para
> lo urgente (si no, los avisos pierden peso).

---

## 5. Gestión de transferencias

Cuando un asesor solicita transferir un caso (ej. audiencia simultánea):

1. Ve a **Transferencias** → verás las solicitudes **pendientes** con el motivo y el
   asesor sugerido (si lo hay).
2. Decide:
   - **Aprobar:** puedes **reasignar** a otro asesor antes de aprobar y dejar un
     comentario. Al aprobar, el expediente cambia de asesor y se notifica a todos.
   - **Rechazar:** deja un comentario para que el asesor entienda el motivo.
3. El asesor puede **cancelar** su solicitud mientras siga pendiente.

> 💡 Revisa las transferencias a diario: un caso pendiente de reasignación puede dejar
> una audiencia sin atender.

---

## 6. Comandos de administración

Los comandos se ejecutan en el servidor (consola). Ejemplos útiles:

```bash
# Enviar recordatorios de próximas acciones/audiencias (próximos 3 días)
uv run python manage.py enviar_recordatorios

# Simular primero (no envía nada)
uv run python manage.py enviar_recordatorios --days=7 --dry-run

# Enviar mensajes de WhatsApp automáticos pendientes
uv run python manage.py enviar_whatsapp_automatico

# Importar citas del CLT.xlsx como expedientes con audiencias
uv run python manage.py importar_clt

# Importar catálogo de empresas y domicilios (idempotente, no duplica)
uv run python manage.py importar_empresas

# Importar plantillas .docx como machotes
uv run python manage.py importar_machotes
```

> ⚠️ La automatización de WhatsApp requiere configuración de Twilio (env vars
> `TWILIO_*`). Sin Twilio, los mensajes quedan como **enlaces wa.me** para abrir
> manualmente. Consulta `--help` de cada comando para más opciones.

---

## 7. Módulo financiero — introducción

El módulo está organizado por **oficina** y por **semana de trabajo**. Todo lo que se
registra tiene responsable (`registrado_por`) para auditoría.

### Cómo se calculan los totales (importante)

| Total | Se compone de |
|-------|---------------|
| **Ingresos** | Pagos de convenios (SettlementPayment) + Ingresos de caja |
| **Gastos** | Gastos operativos (Expense) + Egresos de caja + Nómina (Payroll) |
| **Utilidad** | Ingresos − Gastos |
| **Semana** | Ingresos (caja + pagos) − Gastos (caja + gastos + nómina) |

> ⚠️ Para **no duplicar** registros, usa cada módulo para su propósito: los pagos de
> convenios van en **Pagos de Convenios**; los gastos con factura en **Gastos
> Operativos**; la caja diaria es para el **efectivo del día a día**. Evita registrar lo
> mismo en dos lados.

---

## 8. Oficinas y semanas de trabajo

### 8.1 Oficinas

1. Ve a **Oficinas** (admin de Django o menú de finanzas) → **Nueva oficina**.
2. Captura nombre, dirección, teléfono y responsable.
3. Usa la bandera **Activa** para desactivar una oficina **sin eliminarla** (la operación
   histórica se conserva).

### 8.2 Semanas de trabajo

1. Ve a **Semanas** → la semana actual se **crea automáticamente** (lunes–domingo) la
   primera vez que se consulta.
2. Las semanas se pueden **crear/editar** (número, fechas) y **cerrar** cuando el
   período termina.
3. Cada semana muestra **ingresos, gastos y balance** calculados con las fechas del rango.

> 💡 Cierra la semana al terminar el período para congelar el reporte y revisar la
> siguiente semana con calma.

---

## 9. Caja diaria (ingresos y egresos)

### 9.1 Registrar un movimiento

1. Ve a **Caja → Nuevo movimiento**.
2. Captura:
   - **Fecha** y **oficina**.
   - **Tipo:** 💰 Ingreso o 💸 Egreso.
   - **Categoría** (las opciones cambian según el tipo; el sistema valida la coherencia):
     - *Ingresos:* pago de convenio, pago de cliente, anticipo, devolución, otro.
     - *Egresos:* papelería, gasolina, renta, luz, agua, internet, teléfono, viáticos,
       comisiones, honorarios, otro.
   - **Monto** y **descripción**.
   - **Referencia** (opcional): N° de expediente, factura o nota relacionada.
3. Presiona **✅ Registrar movimiento**.

### 9.2 Lista y filtros

- La lista permite filtrar por **tipo, oficina, categoría y rango de fechas** y buscar
  por descripción/referencia.
- Muestra **totales de ingresos y egresos** del listado filtrado.
- Edita o elimina movimientos desde la lista (queda registro del responsable original).

> 💡 Usa el campo **referencia** (ej. número de expediente) para poder rastrear después
> de qué caso salió o entró el dinero.

---

## 10. Pagos de convenios

1. Ve a **Pagos de Convenios → Nuevo**.
2. Captura **fecha**, **cliente**, **expediente**, **monto** y **forma de pago**
   (efectivo, transferencia, cheque, tarjeta crédito/débito, depósito, otro).
3. Selecciona la **oficina** que recibe el pago y agrega notas si hace falta.
4. Guarda. El pago se suma automáticamente a los **ingresos** del período y de la semana.

> 💡 Estos pagos alimentan el dashboard (Ingresos por Pagos) y el detalle del convenio
> en **Convenios → detalle → Pagos**.

---

## 11. Gastos operativos

1. Ve a **Gastos → Nuevo gasto** (admin de Django).
2. Captura:
   - **Fecha**, **categoría** (renta, luz, agua, internet, teléfono, papelería,
     publicidad, sueldos, gasolina, mantenimiento, impuestos, equipo, muebles, seguros,
     honorarios profesionales, otro).
   - **Monto**, **descripción**, **proveedor** y **folio fiscal/factura**.
   - **Oficina** a la que pertenece.
3. Guarda. Se suma a los **gastos operativos** del período.

> 💡 Guarda el **folio fiscal** siempre: facilita la conciliación contable y fiscal.

---

## 12. Convenios y honorarios

### 12.1 Registrar un convenio

1. Ve a **Convenios → Nuevo convenio**.
2. Captura **cliente**, **empresa/contraparte**, **oficina**, **fecha**, **monto del
   convenio** y **responsable** (abogado/asesor).
3. Estado inicial: **Pendiente de firma**. Ve actualizándolo conforme avanza
   (firmado → pagado / pagado parcialmente / cancelado).
4. Guarda. El campo **honorarios totales** se calcula solo al ir agregando honorarios.

### 12.2 Agregar honorarios

1. En el detalle del convenio, presiona **Nuevo honorario** (o desde el menú).
2. Elige el **porcentaje** (25/30/35/40/50%) — el **monto se calcula automáticamente**
   (monto del convenio × % ÷ 100).
3. Captura fecha estimada de pago y estado (pendiente / pagado / cancelado).
4. El convenio muestra **honorarios pagados y pendientes** en tiempo real.

> 💡 Revisa periódicamente los convenios con honorarios **pendientes** para dar
> seguimiento de cobranza.

---

## 13. Comisiones

1. Cuando un asesor cierra un convenio, crea su comisión en **Comisiones → Nueva**.
2. Captura **expediente**, **asesor**, **fecha**, **monto del convenio**, **%** de
   comisión y **oficina**.
3. El **monto de comisión se calcula automáticamente** (monto × % ÷ 100).
4. Marca el **estado** (pendiente / pagada / cancelada) y la **fecha de pago** cuando se
   pague.
5. Las comisiones **pagadas** aparecen en el dashboard financiero por oficina y asesor.

> 💡 Coordina comisiones con nómina: al pagar la comisión, regístrala también como
> egreso de caja (categoría "Comisiones") o en nómina según tu proceso, **sin duplicar**.

---

## 14. Empleados y nómina

### 14.1 Alta de empleados

1. Ve a **Empleados → Nuevo** (admin de Django).
2. Captura nombre, **puesto** (administrativo, asesor jurídico, supervisor, contador,
   recepcionista, auxiliar, director…), **periodo de pago** (semanal/quincenal/mensual),
   **salario**, teléfono, correo y **oficina**.
3. Desactiva con la bandera **Activo** cuando alguien deje de trabajar (no lo borres).

### 14.2 Pagos de nómina

1. Ve a **Pagos de Nómina → Nuevo**.
2. Selecciona **empleado** y captura:
   - **Fecha de pago**, **período** (semanal/quincenal/mensual/extraordinario/aguinaldo/
     prima vacacional/bono) y el rango del período.
   - **Salario pagado** y **descuentos** (ISR, IMSS…).
3. El **total pagado se calcula solo** (salario − descuentos).
4. Guarda con la **oficina** correspondiente.

> 💡 Usa los períodos **aguinaldo**, **prima vacacional** y **bono** para esos pagos
> especiales: quedan diferenciados en los reportes.

---

## 15. Socios y préstamos

### 15.1 Socios

1. Ve a **Socios → Nuevo socio**.
2. Captura **nombre**, **% de participación** (ej. 25.00 = 25%) y datos de contacto.
3. La ficha del socio muestra sus **préstamos otorgados/recibidos** y **saldos**.

### 15.2 Préstamos entre socios

1. Ve a **Préstamos → Nuevo préstamo**.
2. Selecciona **socio origen** (quién presta) y **socio destino** (quién recibe),
   monto, fecha y concepto.
3. Estado: **pendiente** → **pagado** (con fecha de pago) cuando se liquide.
4. El **saldo neto** de cada socio (otorgados − recibidos) se calcula automáticamente.

> 💡 Esto reemplaza las notas informales tipo "le debo a…": todo queda registrado con
> fecha, concepto y responsable.

---

## 16. Distribución de utilidades

### 16.1 Crear una distribución

1. Ve a **Distribuciones → Nueva distribución**.
2. Selecciona el **convenio** que genera la utilidad.
3. El sistema **calcula automáticamente**:
   - **Monto del convenio** y **honorarios** (del convenio).
   - **Comisiones** (relacionadas al cliente).
   - **Retenciones/ISR** y **gastos relacionados** (captúralos si aplican).
   - **Utilidad neta** = monto − honorarios − comisiones − retenciones − gastos.
4. Guarda. Se generan automáticamente las **participaciones de todos los socios
   activos** (utilidad neta × % de participación) y se actualizan los **resúmenes**.
5. Estado inicial: **borrador** → **distribuida** cuando la revisas.

### 16.2 Confirmar la distribución

1. En el detalle, revisa las participaciones de cada socio.
2. Presiona **✅ Confirmar distribución** (solo admin/superadmin).
3. Al confirmar, los **resúmenes por socio** (utilidad generada / pagada / pendiente) se
   actualizan.
4. Cuando se pague a un socio, marca su participación como **pagada** con fecha.

> ⚠️ Confirma solo cuando los números estén correctos. Una confirmación es un evento
> contable; los ajustes posteriores deben justificarse.

---

## 17. Dashboard financiero y reportes

### 17.1 Dashboard financiero

1. Ve a **Dashboard Financiero**.
2. Filtra por **período** (Este mes / Este año / Histórico) y **oficina**.
3. Verás:
   - **Tarjetas:** ingresos (pagos + caja), gastos (operación + nómina), **utilidad** y
     margen, y nº de oficinas activas.
   - **Barras Ingresos vs Gastos.**
   - **Gráfica de flujo de caja mensual (12 meses)** — se actualiza con los filtros vía
     API.
   - **Resumen por oficina** (ingresos, gastos, utilidad, margen, comisiones pagadas).
   - **Gastos por categoría** y **formas de pago** más usadas.
   - **Productividad por asesor** (casos, convenios, monto recuperado, comisiones).
   - **Movimientos de caja recientes.**
4. Usa **Exportar Excel** para descargar todo en un archivo con **5 hojas**: Resumen
   Global, Gastos por Categoría, Formas de Pago, Asesores y Movimientos de Caja.

> 💡 La exportación aplica **los mismos filtros** que tengas seleccionados y usa la
> misma lógica de totales que el dashboard (no hay diferencias entre pantalla y Excel).

### 17.2 Reporte de convenios

1. Ve a **Reportes → Convenios**.
2. Filtra por **período** (semanal / mensual / anual), año, mes, semana y oficina.
3. El reporte muestra:
   - **Totales:** convenios, monto, honorarios, y conteo por estado (pagados,
     pendientes, firmados, cancelados) + promedio.
   - **Por oficina**, **por estado**, **por responsable** y **top 10 clientes**.
   - **Evolución mensual** (gráfica) en la vista anual.
   - **Listado detallado** de convenios del período.
4. **Exportar Excel** descarga el detalle con los mismos filtros.

### 17.3 Flujo mensual por API

El endpoint `api_flujo_mensual` (JSON) alimenta la gráfica del dashboard. También puedes
consumirlo para reportes externos (requiere rol admin/superadmin/finanzas).

---

## 18. Buenas prácticas de consistencia

1. **Un registro, un propósito:** convenios → Pagos de Convenios; facturas → Gastos
   Operativos; efectivo diario → Caja. Evita duplicar.
2. **Siempre la oficina correcta** en cada movimiento: los reportes por sucursal
   dependen de ello.
3. **Fecha real** del evento (no la fecha de captura) para que los reportes por período
   sean exactos.
4. **Referencias en caja:** anota el N° de expediente o factura para trazabilidad.
5. **Cierra semanas y confirma distribuciones** a tiempo; no dejes períodos abiertos
   eternamente.
6. **Auditoría:** todo registro guarda quién lo hizo. Si algo se capturó mal, **edita**
   (no borres sin justificación) para conservar el rastro.
7. **Revisa el dashboard a diario:** detecta montos atípicos o movimientos sin
   categoría correcta.

---

## 19. Solución de problemas comunes

| Problema | Solución |
|----------|----------|
| La matriz de permisos no muestra a un usuario nuevo | Revisa que el usuario exista en el admin de Django; el perfil se crea automáticamente al crearlo. |
| Cambié un rol y el usuario "desapareció" | Es normal: cambió su dashboard. Regresa el rol anterior si fue un error. |
| La UMA/salario mínimo se actualizó pero los cálculos viejos no cambian | Es correcto: guarda/recalcula cada cálculo para aplicar los valores vigentes. |
| Los totales del dashboard no coinciden con la caja | Revisa duplicados: un pago de convenio registrado también como ingreso de caja se cuenta dos veces. |
| No puedo confirmar una distribución | Solo admin/superadmin pueden confirmar. |
| La semana actual no aparece | Se crea automáticamente al consultar **Semanas**; también puedes crearla a mano. |
| El Excel del dashboard "no trae todo" | La exportación respeta los filtros activos; quita filtros para el histórico completo. |
| Un asesor no ve sus botones de documentos | Verifica el permiso "puede generar documentos" en la matriz de permisos. |

---

*¿Dudas? Contacta al superadmin del sistema o al área de soporte técnico.*
