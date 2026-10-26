---
type: Guide
title: Bash Styleguide
description: Bash scripting style, SPDX headers, strict safety flags, uv invocation, and Linux/macOS portability
tags:
  - styleguide
  - bash
  - shell
---

# Bash and Shell Scripting Guide

Conventions for shell automation scripts under `tools/scripts/` (`tools/scripts/setup-env.sh`, `tools/scripts/build-onefile-package.sh`, `tools/scripts/record-live-demos.sh`).

## Scope: Bash vs. Python Tooling

- Keep Bash scripts focused on OS bootstrap, binary packaging, and process orchestration.
- Implement structured database, OCI/ADB, wallet, JSON, and demo workflows in typed Python modules under `tools/` exposed via `uv run python manage.py ...` or `uv run coffee ...`.
- Always invoke Python entry points through `uv run` (`uv run python ...`, `uv run coffee ...`) rather than bare `python`, `python3`, or global `pip`.

## Header and Strict Mode Template

Every `.sh` file starts with `#!/usr/bin/env bash` on line 1, followed immediately by the SPDX license header (`tools/license_headers.py`) and strict execution flags:

```bash
#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
```

Flag behavior:

- `-e`: Exit immediately when an unguarded command returns a non-zero exit code.
- `-u`: Treat unset variables as errors (use `${VAR:-default}` when an optional environment variable may be unset).
- `-o pipefail`: Propagate failures from any stage of a pipeline.

When testing a command that is expected to fail, guard it explicitly with `if ! cmd; then ... fi` so `-e` remains active across the rest of the script.

## Variables, Quoting, and Arrays

- Use `UPPER_SNAKE_CASE` with `readonly` for script constants and exported environment variables (`ORACLE_HOST`, `UV_PYTHON`).
- Use `lower_snake_case` with `local` for variables inside functions.
- Quote all variable and command expansions (`"${variable}"`, `"$(command)"`).
- Require mandatory environment variables with parameter check syntax:

```bash
: "${ORACLE_PASSWORD:?ERROR: ORACLE_PASSWORD must be set}"
readonly ORACLE_PORT="${ORACLE_PORT:-1521}"
```

- Construct dynamic argument lists with Bash arrays instead of space-delimited strings or `eval`:

```bash
run_packaging() {
    local target_arch="$1"
    local -a build_args=(
        "--target" "${target_arch}"
        "--project-name" "cymbal-coffee"
        "--python-version" "3.13"
    )
    uv run python tools/bundler.py build "${build_args[@]}"
}
```

## Functions, Logging, and Cleanup Traps

- Send diagnostic logs, warnings, and errors to `stderr` (`>&2`) so `stdout` stays clean for data capture.
- Register an `EXIT` trap whenever creating temporary files or directories with `mktemp` so resources are cleaned up on normal exit or failure:

```bash
log_info() {
    printf '[INFO] %s\n' "$*" >&2
}

log_error() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

require_command() {
    local binary="$1"
    if ! command -v "${binary}" >/dev/null 2>&1; then
        log_error "Required command not found: ${binary}"
    fi
}

TEMP_DIR="$(mktemp -d)"
cleanup() {
    local exit_code=$?
    if [[ -d "${TEMP_DIR:-}" ]]; then
        rm -rf "${TEMP_DIR}"
    fi
    exit "${exit_code}"
}
trap cleanup EXIT INT TERM
```

## Conditionals and Iteration

- Prefer `[[ ... ]]` over `[ ... ]` in `bash` scripts to prevent word splitting and pathname expansion inside conditionals.
- Prefer `$(...)` over backticks for command substitution.
- Read line-oriented command or file input with `while IFS= read -r line` rather than `for item in $(...)`:

```bash
while IFS= read -r sql_file; do
    log_info "Checking ${sql_file}"
done < <(find "${REPO_ROOT}/src/app/db/sql" -name '*.sql' | sort)
```

## Linux and macOS Portability

Developer scripts should run cleanly on Linux (`x86_64`, `aarch64`) and macOS (`arm64`, `x86_64`):

- Detect architecture and kernel with `uname -m` (`aarch64` / `arm64` vs. `x86_64`) and `uname -s` (`Linux` vs. `Darwin`), as done in `tools/scripts/build-onefile-package.sh`.
- Check for either `docker` or `podman` before invoking container CLI commands directly, or delegate container lifecycle operations to `uv run python manage.py infra ...` (`tools/oracle/container.py`).
- Avoid GNU-only `sed -i` flags without checking platform behavior when a script runs on macOS; for portable in-place text edits across platforms, prefer a short `uv run python` helper.
