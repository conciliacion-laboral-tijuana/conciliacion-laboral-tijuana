# 📲 Extensión de Chrome — Conciliación BC

Llena automáticamente el formulario de conciliación del portal de Baja California
(`app.conciliacionbc.gob.mx`) **en el navegador del asesor**, para que:

- El portal no detecte navegación automatizada (se crea pero no se traba al final)
- El asesor pueda resolver CAPTCHA / validaciones en vivo
- El acuse PDF se descargue directamente en su computadora
- La app guarde el **folio** y el **acuse** automáticamente en el expediente

---

## 1. Instalación (una sola vez por computadora)

1. Abre Chrome y ve a **`chrome://extensions`**
2. Activa el **Modo de desarrollador** (interruptor arriba a la derecha)
3. Haz clic en **"Cargar descomprimida"**
4. Selecciona la carpeta **`extension/`** de este proyecto
5. La extensión **"Conciliación BC — Asistente"** queda instalada

## 2. Configurar (una sola vez)

1. Haz clic en el ícono de la extensión → **⚙️ Opciones**
2. Pega la **URL de la app** (ej. `https://tu-app.railway.app`)
3. Pega tu **token personal**:
   - Entra a la app → abre cualquier expediente → **Enviar a Conciliación** → verás el
     enlace a la página **"Extensión de Chrome"** (o entra directo a `/extension/config/`)
   - Copia el token que aparece ahí
4. **💾 Guardar configuración** (verifica la conexión automáticamente)

## 3. Cómo usarla (por caso)

1. En la app, abre el expediente → **Enviar a Conciliación**
2. Elige **"📲 Desde mi navegador (Extensión de Chrome)"**
3. Haz clic en el ícono de la extensión → verás la tarea pendiente → **🚀 Llenar en el portal**
4. Se abre el portal con el formulario **ya llenado** (aviso, industria, fecha, solicitante,
   empresa, descripción)
5. **Revisa los datos** → resuelve el CAPTCHA si aparece → da clic en **"Enviar solicitud"**
6. En la página del acuse, haz clic en **"🔍 Ya envié, detectar acuse"**
   (o se detecta automáticamente)
7. La extensión guarda el **folio** en la app, descarga el **acuse PDF** y lo adjunta
   al expediente 🎉

## Fallback

Si la extensión no puede descargar el acuse automáticamente, descárgalo tú desde el
portal y súbelo con el flujo manual de la app: **Expediente → Subir acuse de conciliación**.
