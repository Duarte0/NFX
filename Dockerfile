# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.12

# Ambiente de desenvolvimento do NFX INOV.
#
# Esta imagem existe antes da aplicação: oferece as ferramentas necessárias
# para o Codex planejar e, futuramente, criar e validar o projeto. Os estágios
# de runtime serão definidos apenas depois do PRD e da arquitetura.
FROM python:${PYTHON_VERSION}-slim-bookworm AS dev

ARG NODE_MAJOR=22
ARG GRAPHIFYY_VERSION=0.9.32

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:${PATH}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        gnupg \
        less \
        openssh-client \
        postgresql-client \
        procps \
        ripgrep \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg \
        -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" \
        > /etc/apt/sources.list.d/docker.list \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x \
        -o /tmp/nodesource_setup.sh \
    && bash /tmp/nodesource_setup.sh \
    && rm -f /tmp/nodesource_setup.sh \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        docker-ce-cli \
        docker-compose-plugin \
        nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN npm install --global @openai/codex \
    && python -m pip install "graphifyy==${GRAPHIFYY_VERSION}"

WORKDIR /workspace

CMD ["sleep", "infinity"]
