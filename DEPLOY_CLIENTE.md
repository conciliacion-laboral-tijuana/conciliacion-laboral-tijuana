# 🚀 Despliegue del sistema en la cuenta del despacho (Conciliación Laboral Tijuana)

Guía para dejar el sistema **completamente operativo** en la cuenta propia del
despacho (GitHub + Railway), de modo que el despacho pague y controle su propio
servidor, sin depender de la cuenta original.

## Arquitectura (cómo funciona)

```
Desarrollo (despacho-laboral)
    │  push a main
    ▼
deskiziarecords/despacho-laboral  ← repo original (donde se desarrolla)
    │  GitHub Action "Mirror" (automática, en cada push)
    ▼
conciliacion-laboral-tijuana/conciliacion-laboral-tijuana  ← repo del despacho
    │  Railway conecta este repo → auto-deploy en cada push
    ▼
Railway del despacho  ← el despacho paga y administra
```

El flujo es **unidireccional**: se desarrolla en la cuenta original y el espejo
se encarga de copiar el código a la cuenta del despacho automáticamente.

---

## Paso 0 — Requisitos

- [ ] Cuenta de GitHub del despacho: **conciliacion-laboral-tijuana** (ya existe ✅)
- [ ] Credenciales de esa cuenta (email + contraseña) disponibles
- [ ] Cuenta de correo para crear la cuenta de Railway

---

## Paso 1 — Crear el repositorio en la cuenta del despacho

1. Inicia sesión en GitHub con la cuenta **conciliacion-laboral-tijuana**
2. Ve a **New repository** (botón verde "+" arriba a la derecha)
3. Nombre: `conciliacion-laboral-tijuana`
4. Visibilidad: **Private** (IMPORTANTE: contiene datos reales de clientes)
5. **NO** marcar "Add a README file" ni "Add .gitignore" ni "Choose a license"
   (debe quedar vacío para que el espejo pueda copiar todo sin conflictos)
6. Click en **Create repository**

---

## Paso 2 — Agregar la deploy key (permite que la cuenta original copie el código)

1. En el repo recién creado, ve a **Settings → Deploy keys → Add deploy key**
2. Título: `despacho-laboral-mirror`
3. Pegar esta clave pública EXACTA (incluyendo el prefijo `ssh-ed25519`):

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIE8Ptu6dAcFknsDlxnor6upN9F81dKpbBFfXnh+DjpsB despacho-laboral-mirror
```

4. **ACTIVAR la casilla "Allow write access"** (sin esto el espejo no puede subir código)
5. Click en **Add key**

> ⚠️ Hasta que no se hagan los pasos 1 y 2, el espejo automático fallará
> silenciosamente. Primero crea el repo y agrega la key, y avísanos para
> activar la sincronización.

---

## Paso 3 — Crear la cuenta de Railway del despacho y desplegar

1. Ve a **https://railway.app** → **Login**
2. Regístrate con el correo del despacho (o continúa con la cuenta de GitHub
   del despacho si prefieres)
3. Click en **New Project**
4. Elige **Deploy from GitHub repo**
   - Autoriza la integración de Railway con la cuenta de GitHub del despacho
   - Selecciona el repo `conciliacion-laboral-tijuana` (el que creaste en el Paso 1)
5. Railway detectará automáticamente el `Dockerfile` y empezará a construir
6. **Agregar base de datos PostgreSQL**:
   - Click en el proyecto → **New** → **Database** → **PostgreSQL**
   - Railway inyecta `DATABASE_URL` automáticamente (el sistema ya lo detecta)
7. **Agregar Redis** (recomendado, para tareas automáticas de WhatsApp/Celery):
   - Click en el proyecto → **New** → **Database** → **Redis**
8. **Configurar variables de entorno**:
   - Ve a la pestaña **Variables** del servicio web (el que corre el código)
   - Agregar las siguientes variables:
     - `SECRET_KEY` → usar una clave segura nueva (se te puede generar una)
     - `DEBUG` → `False` (¡IMPORTANTE! en producción)
     - `DJANGO_SUPERUSER_USERNAME` → `admin`
     - `DJANGO_SUPERUSER_EMAIL` → correo del despacho
     - `DJANGO_SUPERUSER_PASSWORD` → contraseña fuerte para el admin
     - `ALLOWED_HOSTS` → deja vacío (Railway agrega el dominio automáticamente)
9. Esperar a que termine el build y el deploy (5-10 min la primera vez)

---

## Paso 4 — Obtener el dominio y verificar

1. En el proyecto, ve al servicio web → pestaña **Settings** → **Networking**
2. Click en **Generate Domain** (obtienes una URL tipo `xxx.up.railway.app`)
3. Abrir esa URL en el navegador → debe aparecer la pantalla de **login**
4. Iniciar sesión con:
   - Usuario: `admin`
   - Contraseña: la que configuraste en `DJANGO_SUPERUSER_PASSWORD`
5. El sistema crea automáticamente (en el primer arranque):
   - Superusuario `admin` con rol **superadmin**
   - Usuarios de prueba: `admin1`-`admin4` / `asesor1`-`asesor15`
   - Datos de demostración (si `seed_datos` está habilitado)

---

## Uso diario

- **El despacho paga y administra su propia cuenta de Railway** (pueden ver
  costos, logs, reiniciar servicios, cambiar el dominio, etc.)
- **Cada cambio de código** que se haga en la cuenta original (push a `main`)
  se copia automáticamente al repo del despacho y Railway lo redespliega solo
- **Soporte técnico**: la cuenta original conserva acceso al repo del despacho
  como deploy key, para seguir corrigiendo y mejorando el sistema

---

## Preguntas frecuentes

**¿El despacho puede editar el código directamente en su repo?**
Sí, pero **no se recomienda**: la siguiente sincronización automática desde la
cuenta original sobrescribiría esos cambios. Los cambios de código se hacen
mejor desde la cuenta original.

**¿Qué pasa si el despacho deja de pagar Railway?**
El servicio se pausa. Como la cuenta es del despacho, ellos controlan el pago
y pueden reactivarlo cuando quieran. El código siempre está en su repo de GitHub.

**¿Se pierde algo al transferir?**
No se transfiere nada: es una **copia espejo**. La cuenta original conserva su
repo completo y el historial de git.

**¿Y los datos (expedientes, clientes, finanzas)?**
Los datos viven en la base de datos PostgreSQL de Railway, que es del despacho.
No se ven afectados por los cambios de código.
