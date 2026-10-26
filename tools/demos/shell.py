# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Deterministic VHS terminal and SQLcl video recorder for Cymbal Coffee demos."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

__all__ = (
    "VHSRecordResult",
    "VHSRecorderConfig",
    "VHSRecorderError",
    "list_default_tapes",
    "parse_tape_outputs",
    "record_all_tapes",
    "record_vhs_tape",
    "resolve_chromium_binary",
    "verify_vhs_prerequisites",
)

DEFAULT_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
CHROME_PATH_CANDIDATES: Final[tuple[str, ...]] = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
)
PLAYWRIGHT_CHROME_PATTERNS: Final[tuple[str, ...]] = (
    "chromium-*/chrome-linux/chrome",
    "chromium-*/chrome-linux64/chrome",
    "chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium",
)


class VHSRecorderError(RuntimeError):
    """Raised when VHS prerequisites, execution, or output artifacts fail validation."""


@dataclass(frozen=True, slots=True)
class VHSRecorderConfig:
    """Configuration for executing VHS terminal demo tapes."""

    repo_root: Path = DEFAULT_REPO_ROOT
    chromium_binary: Path | None = None
    no_sandbox: bool = True
    timeout_seconds: int = 300


@dataclass(frozen=True, slots=True)
class VHSRecordResult:
    """Verified output summary for a completed VHS tape execution."""

    tape_path: Path
    outputs: tuple[Path, ...]
    stdout: str


def resolve_chromium_binary(*, playwright_cache_dir: Path | None = None) -> Path:
    """Locate an executable headless Chromium binary for Go Rod / VHS."""
    explicit_env = os.environ.get("ROD_BROWSER_BIN", "").strip()
    if explicit_env:
        explicit_path = Path(explicit_env).expanduser()
        if explicit_path.is_file() and os.access(explicit_path, os.X_OK):
            return explicit_path
        raise VHSRecorderError(f"ROD_BROWSER_BIN does not point to an executable binary: {explicit_path}")

    for binary_name in CHROME_PATH_CANDIDATES:
        resolved = shutil.which(binary_name)
        if resolved:
            return Path(resolved)

    cache_root = (
        playwright_cache_dir if playwright_cache_dir is not None else (Path.home() / ".cache" / "ms-playwright")
    )
    if cache_root.is_dir():
        candidates: list[Path] = []
        for pattern in PLAYWRIGHT_CHROME_PATTERNS:
            candidates.extend(
                candidate
                for candidate in cache_root.glob(pattern)
                if candidate.is_file() and os.access(candidate, os.X_OK)
            )
        if candidates:
            candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
            return candidates[0]

    raise VHSRecorderError(
        "No headless Chromium binary found for VHS. Set ROD_BROWSER_BIN or install Playwright Chromium with: "
        "uv run --group demos playwright install chromium"
    )


def verify_vhs_prerequisites(*, playwright_cache_dir: Path | None = None) -> dict[str, Path]:
    """Verify that ``vhs``, ``ttyd``, ``ffmpeg``, and headless Chromium are available."""
    resolved = _resolve_host_binaries(("vhs", "ttyd", "ffmpeg"))
    resolved["chromium"] = resolve_chromium_binary(playwright_cache_dir=playwright_cache_dir)
    return resolved


def list_default_tapes(*, repo_root: Path | None = None) -> tuple[Path, ...]:
    """Return all tracked ``.tape`` files under ``docs/_tapes/`` in deterministic order."""
    root = repo_root if repo_root is not None else DEFAULT_REPO_ROOT
    tapes_dir = root / "docs" / "_tapes"
    return tuple(sorted(tapes_dir.glob("*.tape")))


def parse_tape_outputs(tape_path: Path, *, repo_root: Path | None = None) -> tuple[Path, ...]:
    """Extract all ``Output`` artifact paths declared in a VHS ``.tape`` file."""
    if not tape_path.is_file():
        raise VHSRecorderError(f"VHS tape file does not exist: {tape_path}")

    root = repo_root if repo_root is not None else DEFAULT_REPO_ROOT
    outputs: list[Path] = []
    for raw_line in tape_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("Output "):
            target = stripped[len("Output ") :].strip().strip("\"'")
            if target:
                candidate = Path(target)
                outputs.append(candidate if candidate.is_absolute() else (root / candidate))

    if not outputs:
        raise VHSRecorderError(f"VHS tape does not declare any Output directives: {tape_path}")
    return tuple(outputs)


def record_vhs_tape(tape_path: Path, *, config: VHSRecorderConfig | None = None) -> VHSRecordResult:
    """Execute a VHS ``.tape`` script and verify that every declared output exists and is non-empty."""
    cfg = config if config is not None else VHSRecorderConfig()
    host_bins = _resolve_host_binaries(("vhs", "ttyd", "ffmpeg"))
    if cfg.chromium_binary is not None:
        if not cfg.chromium_binary.is_file() or not os.access(cfg.chromium_binary, os.X_OK):
            raise VHSRecorderError(f"Configured chromium_binary is missing or not executable: {cfg.chromium_binary}")
        chrome_bin = cfg.chromium_binary
    else:
        chrome_bin = resolve_chromium_binary()

    outputs = parse_tape_outputs(tape_path, repo_root=cfg.repo_root)
    for output_path in outputs:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env["ROD_BROWSER_BIN"] = str(chrome_bin)
    if cfg.no_sandbox:
        env["VHS_NO_SANDBOX"] = "true"

    try:
        completed = subprocess.run(
            [str(host_bins["vhs"]), str(tape_path)],
            cwd=cfg.repo_root,
            env=env,
            text=True,
            capture_output=True,
            timeout=cfg.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise VHSRecorderError(f"VHS timed out after {cfg.timeout_seconds}s for {tape_path.name}") from exc
    except OSError as exc:
        raise VHSRecorderError(f"Failed to execute VHS for {tape_path.name}: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or f"exit code {completed.returncode}").strip()
        raise VHSRecorderError(f"VHS failed for {tape_path.name}: {detail}")

    for output_path in outputs:
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise VHSRecorderError(f"VHS produced missing or zero-byte output artifact: {output_path}")

    return VHSRecordResult(tape_path=tape_path, outputs=outputs, stdout=completed.stdout)


def record_all_tapes(
    *, config: VHSRecorderConfig | None = None, tapes: Sequence[Path] | None = None
) -> tuple[VHSRecordResult, ...]:
    """Execute every requested VHS ``.tape`` script in deterministic order."""
    cfg = config if config is not None else VHSRecorderConfig()
    target_tapes = tuple(tapes) if tapes is not None else list_default_tapes(repo_root=cfg.repo_root)
    return tuple(record_vhs_tape(tape, config=cfg) for tape in target_tapes)


def _resolve_host_binaries(names: tuple[str, ...]) -> dict[str, Path]:
    """Resolve required CLI binaries on ``PATH`` or raise ``VHSRecorderError``."""
    resolved: dict[str, Path] = {}
    for name in names:
        found = shutil.which(name)
        if not found:
            raise VHSRecorderError(f"Required binary '{name}' was not found on PATH.")
        resolved[name] = Path(found)
    return resolved
