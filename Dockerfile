# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.12

FROM node:22-bookworm-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:${PYTHON_VERSION}-slim-bookworm AS app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
CMD ["python", "backend/manage.py", "runserver", "0.0.0.0:8000"]

FROM nginx:1.27-alpine AS runtime-proxy
COPY deploy/nginx/runtime.conf /etc/nginx/nginx.conf

FROM app AS test
COPY requirements-dev.txt ./
RUN python -m pip install --no-cache-dir -r requirements-dev.txt
COPY tests/ ./tests/

# Isolated, synthetic browser-validation image. Chrome and Edge are installed as
# their branded Linux packages; Firefox is Playwright's Firefox build.
FROM node:22-bookworm-slim AS browser-test
ENV DEBIAN_FRONTEND=noninteractive PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
RUN npx playwright install --with-deps firefox > /tmp/playwright-install.log 2>&1 \
    || { cat /tmp/playwright-install.log; exit 1; }
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable microsoft-edge-stable \
    && rm -rf /var/lib/apt/lists/*
COPY frontend/ ./
CMD ["npm", "run", "test:browser"]

# The development tool image remains available, but follows runtime/test stages so legacy Docker
# builders do not build it when targeting an application image.
FROM python:${PYTHON_VERSION}-slim-bookworm AS dev
ARG NODE_MAJOR=22
ARG GRAPHIFYY_VERSION=0.9.32
ENV DEBIAN_FRONTEND=noninteractive PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/root/.local/bin:${PATH}
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates curl git gnupg less make openssh-client postgresql-client procps ripgrep jq \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" > /etc/apt/sources.list.d/docker.list \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x -o /tmp/nodesource_setup.sh \
    && bash /tmp/nodesource_setup.sh && rm -f /tmp/nodesource_setup.sh \
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin nodejs \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root ANTES de instalar pacotes
RUN useradd -m -u 1000 -s /bin/bash devuser \
    && mkdir -p /home/devuser/.codex \
    && mkdir -p /home/devuser/.npm-global \
    && mkdir -p /home/devuser/.local/bin \
    && chown -R devuser:devuser /home/devuser

USER devuser
ENV HOME=/home/devuser \
    PATH=/home/devuser/.npm-global/bin:/home/devuser/.local/bin:${PATH} \
    NPM_CONFIG_PREFIX=/home/devuser/.npm-global

# Agora instale como devuser
RUN npm install --global @openai/codex && python -m pip install --user "graphifyy==${GRAPHIFYY_VERSION}"

WORKDIR /workspace
CMD ["sleep", "infinity"]
