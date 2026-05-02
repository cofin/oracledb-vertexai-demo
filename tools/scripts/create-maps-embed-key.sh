#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

readonly API_SERVICE="maps-embed-backend.googleapis.com"
readonly KEY_DISPLAY_NAME="oracledb-vertexai-demo-maps-embed"

project=""
dry_run=false
reuse_existing=false
env_file=""
referrers=()

usage() {
  cat <<'EOF'
Create or reuse a restricted Google Maps Embed API key for the demo.

Usage:
  tools/scripts/create-maps-embed-key.sh --project PROJECT --referrer ORIGIN [options]

Options:
  --project PROJECT       Google Cloud project ID.
  --referrer REFERRER     Allowed HTTP referrer. Repeat for each local or hosted origin.
  --dry-run               Print the gcloud commands without creating or updating a key.
  --env-file PATH         Append MAPS_ENABLE_EMBED and GOOGLE_MAPS_EMBED_API_KEY exports.
  --reuse-existing        Reuse and update the demo key if one already exists.
  -h, --help              Show this help.

Examples:
  tools/scripts/create-maps-embed-key.sh \
    --project my-project \
    --referrer "http://localhost:8000/*" \
    --referrer "https://coffee.example.com/*" \
    --reuse-existing
EOF
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

require_arg_value() {
  local flag="$1"
  local value="${2:-}"
  [[ -n "${value}" ]] || die "${flag} requires a value"
}

join_by_comma() {
  local joined=""
  local value
  for value in "$@"; do
    if [[ -z "${joined}" ]]; then
      joined="${value}"
    else
      joined="${joined},${value}"
    fi
  done
  printf '%s' "${joined}"
}

print_cmd() {
  local arg
  printf '  '
  for arg in "$@"; do
    printf '%s ' "${arg}"
  done
  printf '\n'
}

run_or_print() {
  if [[ "${dry_run}" == "true" ]]; then
    print_cmd "$@"
  else
    "$@"
  fi
}

parse_args() {
  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --project)
        require_arg_value "$1" "${2:-}"
        project="$2"
        shift 2
        ;;
      --referrer)
        require_arg_value "$1" "${2:-}"
        referrers+=("$2")
        shift 2
        ;;
      --dry-run)
        dry_run=true
        shift
        ;;
      --env-file)
        require_arg_value "$1" "${2:-}"
        env_file="$2"
        shift 2
        ;;
      --reuse-existing)
        reuse_existing=true
        shift
        ;;
      -h | --help)
        usage
        exit 0
        ;;
      *)
        die "Unknown argument: $1"
        ;;
    esac
  done
}

validate_referrers() {
  [[ "${#referrers[@]}" -gt 0 ]] || die "At least one --referrer is required to avoid unrestricted key creation"

  local referrer
  for referrer in "${referrers[@]}"; do
    case "${referrer}" in
      http://* | https://*) ;;
      *) die "--referrer must start with http:// or https://: ${referrer}" ;;
    esac
  done
}

is_tracked_file() {
  local path="$1"
  local repo_root

  repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  [[ -n "${repo_root}" ]] || return 1

  local absolute_path
  if [[ "${path}" = /* ]]; then
    absolute_path="${path}"
  else
    absolute_path="${PWD}/${path}"
  fi

  case "${absolute_path}" in
    "${repo_root}"/*) ;;
    *) return 1 ;;
  esac

  local relative_path="${absolute_path#"${repo_root}/"}"
  git -C "${repo_root}" ls-files --error-unmatch "${relative_path}" >/dev/null 2>&1
}

validate_env_file() {
  [[ -z "${env_file}" ]] && return
  if is_tracked_file "${env_file}"; then
    die "Refusing to write secrets to tracked env file: ${env_file}"
  fi
}

find_existing_key_resource() {
  gcloud services api-keys list \
    "--project=${project}" \
    "--filter=displayName=${KEY_DISPLAY_NAME}" \
    "--format=value(name)" \
    --limit=1
}

append_env_exports() {
  local key_string="$1"
  [[ -n "${env_file}" ]] || return 0

  if [[ "${dry_run}" == "true" ]]; then
    printf 'Would append MAPS_ENABLE_EMBED and GOOGLE_MAPS_EMBED_API_KEY exports to %s\n' "${env_file}"
    return
  fi

  {
    printf '\n# Google Maps Embed configuration for Cymbal Coffee\n'
    printf 'MAPS_ENABLE_EMBED="true"\n'
    printf 'GOOGLE_MAPS_EMBED_API_KEY="%s"\n' "${key_string}"
  } >>"${env_file}"
}

print_exports() {
  local key_string="$1"
  printf '\nSet these environment variables for optional embed mode:\n'
  printf 'export MAPS_ENABLE_EMBED="true"\n'
  printf 'export GOOGLE_MAPS_EMBED_API_KEY="%s"\n' "${key_string}"
}

create_or_update_key() {
  local allowed_referrers
  allowed_referrers="$(join_by_comma "${referrers[@]}")"

  if [[ "${dry_run}" == "true" ]]; then
    printf 'Would run:\n'
  fi

  run_or_print gcloud services enable "${API_SERVICE}" "--project=${project}"

  local key_resource=""
  if [[ "${reuse_existing}" == "true" ]]; then
    if [[ "${dry_run}" == "true" ]]; then
      print_cmd gcloud services api-keys list "--project=${project}" "--filter=displayName=${KEY_DISPLAY_NAME}" "--format=value(name)" --limit=1
    else
      key_resource="$(find_existing_key_resource || true)"
    fi
  fi

  if [[ -n "${key_resource}" ]]; then
    run_or_print gcloud services api-keys update "${key_resource}" \
      "--project=${project}" \
      --location=global \
      "--allowed-referrers=${allowed_referrers}" \
      "--api-target=service=${API_SERVICE}"
  else
    run_or_print gcloud services api-keys create \
      "--project=${project}" \
      "--display-name=${KEY_DISPLAY_NAME}" \
      "--allowed-referrers=${allowed_referrers}" \
      "--api-target=service=${API_SERVICE}"
    if [[ "${dry_run}" != "true" ]]; then
      key_resource="$(find_existing_key_resource || true)"
    fi
  fi

  local key_string="DRY_RUN_KEY_STRING"
  if [[ "${dry_run}" != "true" ]]; then
    [[ -n "${key_resource}" ]] || die "Could not resolve the created or reused API key resource"
    key_string="$(gcloud services api-keys get-key-string "${key_resource}" "--project=${project}" --location=global "--format=value(keyString)")"
    [[ -n "${key_string}" ]] || die "Could not read the API key string from ${key_resource}"
  fi

  append_env_exports "${key_string}"
  print_exports "${key_string}"
}

main() {
  parse_args "$@"
  [[ -n "${project}" ]] || die "--project is required"
  validate_referrers
  validate_env_file
  create_or_update_key
}

main "$@"
