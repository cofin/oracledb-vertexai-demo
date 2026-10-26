#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail
IFS=$'\n\t'

readonly REQUIRED_PHRASE="RECORD LIVE DEMOS"

printf "Live demo recording connects to the running Oracle Autonomous AI Database Free 26ai container and Vertex AI.\n"
printf "Type '%s' to continue: " "${REQUIRED_PHRASE}"

confirmation=""
if ! IFS= read -r confirmation; then
    printf "Aborted: confirmation phrase '%s' was not provided.\n" "${REQUIRED_PHRASE}" >&2
    exit 1
fi

if [[ "${confirmation}" != "${REQUIRED_PHRASE}" ]]; then
    printf "Aborted: expected '%s'.\n" "${REQUIRED_PHRASE}" >&2
    exit 1
fi

exec uv run --group demos python manage.py demos all
