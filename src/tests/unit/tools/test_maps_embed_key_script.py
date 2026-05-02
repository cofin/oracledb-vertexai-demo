# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import subprocess  # noqa: S404

from tests.support.paths import PROJECT_ROOT

SCRIPT = PROJECT_ROOT / "tools/scripts/create-maps-embed-key.sh"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["/usr/bin/env", "bash", str(SCRIPT), *args],
        cwd=PROJECT_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


def test_maps_embed_key_script_dry_run_uses_restricted_key_commands() -> None:
    result = run_script(
        "--project",
        "demo-project",
        "--referrer",
        "http://localhost:5006/*",
        "--referrer",
        "https://demo.example.com/*",
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    assert "gcloud services enable maps-embed-backend.googleapis.com --project=demo-project" in result.stdout
    assert "gcloud services api-keys create" in result.stdout
    assert "--allowed-referrers=http://localhost:5006/*,https://demo.example.com/*" in result.stdout
    assert "--api-target=service=maps-embed-backend.googleapis.com" in result.stdout
    assert 'export GOOGLE_MAPS_EMBED_API_KEY="DRY_RUN_KEY_STRING"' in result.stdout
    assert 'export MAPS_ENABLE_EMBED="true"' in result.stdout
    assert "VERTEX" not in result.stdout
    assert "GEMINI" not in result.stdout


def test_maps_embed_key_script_refuses_unrestricted_key_creation() -> None:
    result = run_script("--project", "demo-project", "--dry-run")

    assert result.returncode != 0
    assert "At least one --referrer is required" in result.stderr


def test_maps_embed_key_script_refuses_tracked_env_file() -> None:
    result = run_script(
        "--project",
        "demo-project",
        "--referrer",
        "http://localhost:5006/*",
        "--dry-run",
        "--env-file",
        "README.md",
    )

    assert result.returncode != 0
    assert "Refusing to write secrets to tracked env file" in result.stderr
