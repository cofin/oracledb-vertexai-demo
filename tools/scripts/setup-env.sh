#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

set -e

BLUE='\033[1;34m'
GREEN='\033[1;32m'
NC='\033[0m'
INFO="${BLUE}ℹ${NC}"
OK="${GREEN}✓${NC}"

# 1. Configure uv (Python)
echo -e "${INFO} Configuring uv.toml..."
cat <<EOF > uv.toml
exclude-dependencies = ["fastapi", "uvicorn", "starlette", "sse-starlette", "sqlalchemy", "alembic", "sqlalchemy-spanner"]
EOF

# Detect if running on internal Linux (Rodete)
if [ -f "/etc/os-release" ] && grep -q "rodete" /etc/os-release; then
    echo -e "${INFO} Detected internal environment (Rodete)."

    # Append PyPI index to uv.toml
    cat <<EOF >> uv.toml

[[index]]
name = "pypi"
url = "https://pypi.org/simple"
default = true
EOF
    echo -e "${OK} uv.toml updated with public index."

    # Configure npm/bun (JavaScript)
    if [ ! -f ".npmrc" ]; then
        echo -e "${INFO} Creating .npmrc to force public NPM registry..."
        echo "registry=https://registry.npmjs.org" > .npmrc
        echo -e "${OK} .npmrc created."
    else
        if ! grep -q "registry=https://registry.npmjs.org" .npmrc; then
            echo "registry=https://registry.npmjs.org" >> .npmrc
            echo -e "${OK} Appended registry to .npmrc."
        else
            echo -e "${INFO} .npmrc already configured. Skipping."
        fi
    fi
else
    echo -e "${INFO} Not running on Rodete. Skipping specific env setup."
fi
