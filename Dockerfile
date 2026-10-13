# ================================================
# Dockerfile para Despacho Laboral
# Compatible con Railway
# Incluye: WeasyPrint (PDFs) + Playwright (Chromium)
# ================================================

FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

# ================================================
# 1. Dependencias del sistema
#    (WeasyPrint + Playwright + PostgreSQL)
# ================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    # PostgreSQL
    libpq-dev \
    libpq5 \
    # WeasyPrint
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    shared-mime-info \
    # Playwright / Chromium
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libxshmfence1 \
    libx11-xcb1 \
    libgtk-3-0 \
    libegl1 \
    libwayland-client0 \
    libwayland-egl1 \
    libwayland-cursor0 \
    && rm -rf /var/lib/apt/lists/*

# ================================================
# 2. Instalar uv (gestor de paquetes)
# ================================================
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# ================================================
# 3. Instalar dependencias de Python
#    COPY solo pyproject.toml + uv.lock primero
#    para aprovechar caché de Docker
# ================================================
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ================================================
# 4. Instalar Chromium para Playwright
# ================================================
RUN uv run playwright install chromium && \
    uv run playwright install-deps chromium

# ================================================
# 5. Copiar código de la aplicación y script de inicio
# ================================================
COPY . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ================================================
# 6. Sincronizar proyecto (rápido, solo instala el proyecto local)
# ================================================
RUN uv sync --frozen --no-dev

# ================================================
# 7. Recolectar archivos estáticos (Whitenoise)
# ================================================
RUN uv run python manage.py collectstatic --noinput --clear

# ================================================
# 8. Configurar puerto y comando de inicio
# ================================================
EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
