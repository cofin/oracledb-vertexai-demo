# syntax=docker/dockerfile:1.7
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

# =============================================================================
# Distroless Onefile Container - Cymbal Coffee Demo
# =============================================================================
# This image runs the official PyApp onefile binary so container behavior stays
# aligned with the standalone release artifact.
# =============================================================================

ARG RUN_IMAGE=gcr.io/distroless/cc-debian12:nonroot
ARG PYTHON_VERSION=3.13
ARG DEBIAN_VERSION=bookworm
ARG BUILDER_IMAGE=python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION}

# =============================================================================
# Stage 1: Runtime Prep
# =============================================================================
FROM ${BUILDER_IMAGE} AS prep

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libaio1 \
        tini \
        unzip \
    && rm -rf /var/cache/apt/archives/* /var/lib/apt/lists/* /var/log/* /tmp/*

COPY tools/scripts/install_oracle_client.sh /tmp/
RUN /tmp/install_oracle_client.sh

ARG TARGETARCH
RUN ARCH_DIR=$([ "$TARGETARCH" = "arm64" ] && echo "aarch64-linux-gnu" || echo "x86_64-linux-gnu") \
    && mkdir -p /runtime-libs/lib /runtime-libs/usr/lib /app/bin /app/wallet \
    && cp -a /lib/${ARCH_DIR} /runtime-libs/lib/ \
    && cp -a /usr/lib/${ARCH_DIR} /runtime-libs/usr/lib/ \
    && if [ -e "/runtime-libs/usr/lib/${ARCH_DIR}/libaio.so.1t64" ] && [ ! -e "/runtime-libs/usr/lib/${ARCH_DIR}/libaio.so.1" ]; then \
        ln -s libaio.so.1t64 "/runtime-libs/usr/lib/${ARCH_DIR}/libaio.so.1"; \
    fi

WORKDIR /app
COPY dist/coffee-${TARGETARCH}-linux-gnu /app/bin/coffee
RUN chmod +x /app/bin/coffee

ENV HOME=/app \
    TNS_ADMIN=/app/wallet \
    WALLET_LOCATION=/app/wallet

RUN /app/bin/coffee upgrade --help

# =============================================================================
# Stage 2: Final Runtime
# =============================================================================
FROM ${RUN_IMAGE} AS runner

ENV PATH="/app/bin:$PATH" \
    HOME=/app \
    PYTHONUNBUFFERED=1 \
    LD_LIBRARY_PATH="/opt/oracle/instantclient" \
    TNS_ADMIN=/app/wallet \
    WALLET_LOCATION=/app/wallet \
    TMPDIR=/tmp

COPY --from=prep /runtime-libs/lib/ /lib/
COPY --from=prep /runtime-libs/usr/lib/ /usr/lib/
COPY --from=prep /etc/ld.so.cache /etc/ld.so.cache
COPY --from=prep /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

COPY --from=prep /opt/oracle /opt/oracle
COPY --from=prep /usr/bin/tini /usr/local/bin/tini

COPY --from=prep --chown=65532:65532 /app/.config/cymbal-coffee /app/.config/cymbal-coffee
COPY --from=prep --chown=65532:65532 /app/bin /app/bin
COPY --from=prep --chown=65532:65532 /app/wallet /app/wallet
COPY --from=prep --chown=65532:65532 /tmp /tmp

WORKDIR /app
USER nonroot

EXPOSE 8080
VOLUME ["/app/wallet"]

ENTRYPOINT ["/usr/local/bin/tini", "--", "coffee"]
CMD ["run", "--host", "0.0.0.0", "--port", "8080"]

LABEL org.opencontainers.image.title="Cymbal Coffee Demo" \
      org.opencontainers.image.description="Distroless container wrapping the PyApp onefile release" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.base.name="gcr.io/distroless/cc-debian12:nonroot"
