# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

ARG BUILDER_IMAGE=python:3.12-slim-bookworm
# =============================================================================
# Stage 1: Python Base
# =============================================================================
FROM ${BUILDER_IMAGE} AS python-base

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        build-essential git tini libaio1 unzip curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/cache/apt/archives/* /var/lib/apt/lists/* /var/log/* /tmp/* \
    && mkdir -p /app

# Install Oracle Instant Client
COPY tools/scripts/install_oracle_client.sh /tmp/
RUN /tmp/install_oracle_client.sh
ARG LD_LIBRARY_PATH=""
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient:${LD_LIBRARY_PATH}

# Install uv (Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# =============================================================================
# Stage 2: Builder
# =============================================================================
FROM python-base AS builder

ARG UV_INSTALL_ARGS="--no-dev"

ENV GRPC_PYTHON_BUILD_WITH_CYTHON=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_CACHE=1 \
    UV_SYSTEM_PYTHON=1 \
    PATH="/app/.venv/bin:/usr/local/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /app

# Copy dependency files first (better layer caching)
COPY pyproject.toml uv.lock README.md ./
COPY package.json package-lock.json ./

# Install JS dependencies (root-level package.json post Ch 4 flatten)
RUN npm ci

# Create venv and install Python dependencies
RUN uv venv \
    && uv sync ${UV_INSTALL_ARGS} --frozen --no-install-project --no-editable \
    && uv export ${UV_INSTALL_ARGS} --frozen --no-hashes --no-emit-project --output-file=requirements.txt

# Copy application source (post-flatten src/ holds app/ + resources/ + templates/ + tests/)
COPY tools ./tools/
COPY manage.py ./manage.py
COPY vite.config.ts tsconfig.json ./
COPY src/ ./src/

# Build frontend bundles via Vite, then build the Python wheel
RUN npm run build \
    && uv sync ${UV_INSTALL_ARGS} --frozen --no-editable \
    && uv build --wheel

# =============================================================================
# Stage 3: Runner
# =============================================================================
FROM python-base AS runner

ARG LITESTAR_APP="app.server.asgi:create_app"

ENV PATH="/app/.venv/bin:/usr/local/bin:$PATH" \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_CACHE=1 \
    UV_SYSTEM_PYTHON=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    HOME="/app" \
    LITESTAR_APP="${LITESTAR_APP}"

RUN addgroup --system --gid 65532 nonroot \
    && adduser --no-create-home --system --uid 65532 nonroot \
    && chown -R nonroot:nonroot /app

COPY --from=builder --chown=65532:65532 /app/dist /tmp/
WORKDIR /app
RUN uv pip install --quiet --disable-pip-version-check /tmp/*.whl \
    && rm -rf /tmp/* \
    && chown -R nonroot:nonroot /app

USER nonroot
STOPSIGNAL SIGINT
EXPOSE 8080

ENTRYPOINT ["tini", "--"]
CMD ["coffee", "run", "--port", "8080", "--host", "0.0.0.0"]
VOLUME /app
