#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Google LLC
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
required-version = ">=0.8.6"
exclude-newer = "3 days"
exclude-newer-package = { sqlspec = false }
build-constraint-dependencies = [
    "hatchling==1.24.2",
    "nodeenv==1.9.1"
]
EOF


# 2. Configure npm (JavaScript)
echo -e "${INFO} Configuring .npmrc..."
if [ ! -f ".npmrc" ]; then
    echo "min-release-age=3" > .npmrc
    echo -e "${OK} .npmrc created."
else
    if ! grep -q "min-release-age=" .npmrc; then
        echo "min-release-age=3" >> .npmrc
        echo -e "${OK} Appended min-release-age to .npmrc."
    else
        sed -i 's/^min-release-age=.*/min-release-age=3/' .npmrc
        echo -e "${OK} Updated min-release-age in .npmrc."
    fi
fi

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

    # Append registry to .npmrc if not present
    if ! grep -q "registry=https://registry.npmjs.org" .npmrc; then
        echo "registry=https://registry.npmjs.org" >> .npmrc
        echo -e "${OK} Appended registry to .npmrc."
    fi
fi

