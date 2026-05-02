#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

set -euxo pipefail

host_arch="$(uname -m)"
if [ -z "${PYAPP_BUILD_PYTHON:-}" ]; then
    if [ "${host_arch}" = "aarch64" ] || [ "${host_arch}" = "arm64" ]; then
        export PYAPP_BUILD_PYTHON="cpython-3.13.12-linux-aarch64-gnu"
    else
        export PYAPP_BUILD_PYTHON="cpython-3.13.12-linux-x86_64-gnu"
    fi
fi
if [ -z "${PYAPP_BUILD_TARGET:-}" ]; then
    if [ "${host_arch}" = "aarch64" ] || [ "${host_arch}" = "arm64" ]; then
        export PYAPP_BUILD_TARGET="aarch64-unknown-linux-gnu"
    else
        export PYAPP_BUILD_TARGET="x86_64-unknown-linux-gnu"
    fi
fi
export UV_PYTHON="${UV_PYTHON:-${PYAPP_BUILD_PYTHON}}"

current_version=$(uv run python -c "from app.__metadata__ import __version__; print(__version__)")

export HATCH_BUILD_LOCATION="dist"
export CARGO_PROFILE_RELEASE_BUILD_OVERRIDE_DEBUG="true"
export RUST_BACKTRACE="full"
export BZIP2_SYS_STATIC="1"
export LZMA_API_STATIC="1"
export PYAPP_VERSION="v0.29.0"
export PYAPP_DIR="dist/.scratch"
export PYAPP_PROJECT_NAME="app"
export PYAPP_PROJECT_VERSION="${current_version}"
export PYAPP_PYTHON_VERSION="3.13"
export PYAPP_EXEC_SPEC="app.__main__:run_cli"
export PYAPP_DISTRIBUTION_VARIANT_CPU="v1"
export PYAPP_UV_ENABLED="true"
export PYAPP_FULL_ISOLATION="true"
export PYAPP_DISTRIBUTION_EMBED="true"

rm -Rf "${PYAPP_DIR}"
git clone --quiet --depth 1 --branch "${PYAPP_VERSION}" https://github.com/ofek/pyapp "${PYAPP_DIR}"
sed -i 's/bzip2 = "\([^"]*\)"/bzip2 = { version = "\1", features = ["static"] }/' "${PYAPP_DIR}/Cargo.toml"
sed -i '/\[dependencies\]/a bzip2-sys = { version = "*", features = ["static"] }' "${PYAPP_DIR}/Cargo.toml"

uv build --wheel
wheel_path="$(realpath "dist/app-${current_version}-py3-none-any.whl")"
export PYAPP_PROJECT_PATH="${wheel_path}"

uv export --frozen --no-dev --no-editable --no-hashes --no-header --no-emit-project > dist/requirements.txt
echo "${wheel_path}" >> dist/requirements.txt

uv run tools/bundler.py build \
  --target "${PYAPP_BUILD_TARGET}" \
  --requirements dist/requirements.txt \
  --output "dist/python-dist-${PYAPP_BUILD_TARGET}.tar.gz" \
  --pyapp-dir "${PYAPP_DIR}" \
  --install-root "~/.config" \
  --project-name "cymbal-coffee" \
  --python-version "3.13"

export PYAPP_DISTRIBUTION_PATH="$(realpath "dist/python-dist-${PYAPP_BUILD_TARGET}.tar.gz")"
export PYAPP_DISTRIBUTION_EMBED="true"
export PYAPP_DISTRIBUTION_PYTHON_PATH="python/bin/python3"
export PYAPP_SKIP_INSTALL="true"
export PYAPP_ALLOW_UPDATES="true"
unset PYAPP_PROJECT_DEPENDENCY_FILE

cd "${PYAPP_DIR}"
if [ "$(uname -s)" = "Linux" ]; then
    if ! command -v cargo-zigbuild &> /dev/null; then
        echo "ERROR: cargo-zigbuild is required for Linux onefile builds to target glibc 2.17." >&2
        exit 1
    fi
    if ! command -v zig &> /dev/null; then
        echo "ERROR: zig is required by cargo-zigbuild for Linux onefile builds." >&2
        exit 1
    fi
    echo "Using cargo-zigbuild for glibc 2.17 backwards compatibility..."
    cargo zigbuild --release --target "${PYAPP_BUILD_TARGET}.2.17"
    cd -
    cp "${PYAPP_DIR}/target/${PYAPP_BUILD_TARGET}/release/pyapp" dist/coffee
else
    cargo build --release
    cd -
    cp "${PYAPP_DIR}/target/release/pyapp" dist/coffee
fi

chmod +x dist/coffee
