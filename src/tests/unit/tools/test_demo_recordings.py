# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the deterministic VHS terminal demo recorder and tracked `.tape` scripts."""

from __future__ import annotations

import os
import stat
import subprocess  # ruff: ignore[suspicious-subprocess-import]
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from tools.demos.shell import (
    VHSRecorderConfig,
    VHSRecorderError,
    VHSRecordResult,
    list_default_tapes,
    parse_tape_outputs,
    record_all_tapes,
    record_vhs_tape,
    resolve_chromium_binary,
    verify_vhs_prerequisites,
)

from tests.support.paths import PROJECT_ROOT

LIVE_SCRIPT_PATH = PROJECT_ROOT / "tools" / "scripts" / "record-live-demos.sh"


def _make_executable(path: Path, content: str = "#!/usr/bin/env bash\nexit 0\n") -> Path:
    """Create a small executable file on disk for binary resolution tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_resolve_chromium_binary_precedence_and_missing_guidance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify resolve_chromium_binary checks ROD_BROWSER_BIN, PATH, Playwright cache, and raises actionable errors."""
    explicit_bin = _make_executable(tmp_path / "custom" / "chrome")
    monkeypatch.setenv("ROD_BROWSER_BIN", str(explicit_bin))
    monkeypatch.setattr("tools.demos.shell.shutil.which", lambda _name: None)
    assert resolve_chromium_binary(playwright_cache_dir=tmp_path / "empty-cache") == explicit_bin

    monkeypatch.delenv("ROD_BROWSER_BIN", raising=False)
    path_chrome = _make_executable(tmp_path / "bin" / "chromium")
    monkeypatch.setattr("tools.demos.shell.shutil.which", lambda name: str(path_chrome) if name == "chromium" else None)
    assert resolve_chromium_binary(playwright_cache_dir=tmp_path / "empty-cache") == path_chrome

    monkeypatch.setattr("tools.demos.shell.shutil.which", lambda _name: None)
    cache_dir = tmp_path / "ms-playwright"
    older = _make_executable(cache_dir / "chromium-1140" / "chrome-linux" / "chrome")
    newer = _make_executable(cache_dir / "chromium-1161" / "chrome-linux" / "chrome")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))
    assert resolve_chromium_binary(playwright_cache_dir=cache_dir) == newer

    with pytest.raises(VHSRecorderError, match="uv run --group demos playwright install chromium"):
        resolve_chromium_binary(playwright_cache_dir=tmp_path / "missing-cache")


def test_verify_vhs_prerequisites_validates_required_binaries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify verify_vhs_prerequisites checks vhs, ttyd, ffmpeg, and Chromium availability."""
    fake_chrome = _make_executable(tmp_path / "chrome")
    monkeypatch.setenv("ROD_BROWSER_BIN", str(fake_chrome))
    monkeypatch.setattr(
        "tools.demos.shell.shutil.which", lambda name: f"/usr/bin/{name}" if name in {"vhs", "ttyd", "ffmpeg"} else None
    )
    prereqs = verify_vhs_prerequisites()
    assert prereqs["vhs"] == Path("/usr/bin/vhs")
    assert prereqs["ttyd"] == Path("/usr/bin/ttyd")
    assert prereqs["ffmpeg"] == Path("/usr/bin/ffmpeg")
    assert prereqs["chromium"] == fake_chrome

    monkeypatch.setattr("tools.demos.shell.shutil.which", lambda name: None if name == "ttyd" else f"/usr/bin/{name}")
    with pytest.raises(VHSRecorderError, match="ttyd"):
        verify_vhs_prerequisites()


def test_tracked_tapes_declare_mp4_and_gif_outputs_dimensions_hide_show_and_no_secrets() -> None:
    """Verify tracked VHS tapes configure 1200x675 MP4/GIF outputs, Hide/Show blocks, Wait+Screen, and zero secrets."""
    tapes = list_default_tapes(repo_root=PROJECT_ROOT)
    assert [tape.name for tape in tapes] == ["apex-vertex-ai-setup.tape", "apexlang-workflow.tape"]
    assert (PROJECT_ROOT / "docs" / "_static" / "demos" / ".gitkeep").is_file()

    token_pairs = (("ya", "29."), ("AI", "za"), ("AK", "IA"), ("gh", "p_"))
    forbidden_tokens = (
        "Bearer ",
        "WALLET_PASSWORD=",
        "ORACLE_ADMIN_PASSWORD=",
        *(left + right for left, right in token_pairs),
    )
    for tape_path in tapes:
        raw = tape_path.read_text(encoding="utf-8")
        outputs = parse_tape_outputs(tape_path, repo_root=PROJECT_ROOT)
        suffixes = {output.suffix for output in outputs}
        assert suffixes == {".mp4", ".gif"}
        for output in outputs:
            rel = output.relative_to(PROJECT_ROOT).as_posix()
            assert rel.startswith("docs/_static/demos/")

        assert "Set Width 1200" in raw
        assert "Set Height 675" in raw
        assert "Hide" in raw
        assert "Show" in raw
        assert "Wait+Screen" in raw
        for token in forbidden_tokens:
            assert token not in raw


def test_record_vhs_tape_injects_rod_env_and_fails_fast_on_errors_or_empty_outputs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify record_vhs_tape sets ROD_BROWSER_BIN and VHS_NO_SANDBOX and validates non-empty .mp4/.gif outputs."""
    fake_chrome = _make_executable(tmp_path / "bin" / "chrome")
    tape_file = tmp_path / "docs" / "_tapes" / "sample.tape"
    tape_file.parent.mkdir(parents=True, exist_ok=True)
    tape_file.write_text(
        'Output docs/_static/demos/sample.mp4\nOutput "docs/_static/demos/sample.gif"\nSet Width 1200\nSet Height 675\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "tools.demos.shell.shutil.which", lambda name: f"/usr/bin/{name}" if name in {"vhs", "ttyd", "ffmpeg"} else None
    )
    recorded_invocations: list[tuple[list[str], dict[str, str], Path]] = []

    def fake_run_success(cmd: list[str], *, cwd: Path, env: dict[str, str], **_kwargs: Any) -> SimpleNamespace:
        recorded_invocations.append((cmd, env, cwd))
        out_dir = cwd / "docs" / "_static" / "demos"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "sample.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
        (out_dir / "sample.gif").write_bytes(b"GIF89a\x01\x00\x01\x00")
        return SimpleNamespace(returncode=0, stdout="Created sample.mp4\n", stderr="")

    monkeypatch.setattr("tools.demos.shell.subprocess.run", fake_run_success)
    cfg = VHSRecorderConfig(repo_root=tmp_path, chromium_binary=fake_chrome)
    assert hasattr(cfg, "__slots__")
    results = record_all_tapes(config=cfg, tapes=[tape_file])
    assert len(results) == 1
    result = results[0]
    assert isinstance(result, VHSRecordResult)
    assert hasattr(result, "__slots__")
    assert len(result.outputs) == 2
    cmd, env, cwd = recorded_invocations[0]
    assert cmd == ["/usr/bin/vhs", str(tape_file)]
    assert cwd == tmp_path
    assert env["ROD_BROWSER_BIN"] == str(fake_chrome)
    assert env["VHS_NO_SANDBOX"] == "true"

    def fake_run_nonzero(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(returncode=1, stdout="", stderr="vhs failed to connect to ttyd")

    monkeypatch.setattr("tools.demos.shell.subprocess.run", fake_run_nonzero)
    with pytest.raises(VHSRecorderError, match="vhs failed to connect to ttyd"):
        record_vhs_tape(tape_file, config=cfg)

    def fake_run_zero_byte(*_args: Any, cwd: Path, **_kwargs: Any) -> SimpleNamespace:
        out_dir = cwd / "docs" / "_static" / "demos"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "sample.mp4").write_bytes(b"")
        (out_dir / "sample.gif").write_bytes(b"GIF89a")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("tools.demos.shell.subprocess.run", fake_run_zero_byte)
    with pytest.raises(VHSRecorderError, match=r"sample\.mp4"):
        record_vhs_tape(tape_file, config=cfg)

    def fake_run_timeout(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
        raise subprocess.TimeoutExpired(cmd="vhs", timeout=300)

    monkeypatch.setattr("tools.demos.shell.subprocess.run", fake_run_timeout)
    with pytest.raises(VHSRecorderError, match="timed out"):
        record_vhs_tape(tape_file, config=cfg)


def test_record_live_demos_script_requires_exact_confirmation_phrase(tmp_path: Path) -> None:
    """Verify tools/scripts/record-live-demos.sh aborts without RECORD LIVE DEMOS and dispatches manage.py demos all."""
    assert LIVE_SCRIPT_PATH.is_file()
    assert os.access(LIVE_SCRIPT_PATH, os.X_OK)

    aborted = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [str(LIVE_SCRIPT_PATH)], input="no\n", text=True, capture_output=True, check=False
    )
    assert aborted.returncode != 0
    assert "RECORD LIVE DEMOS" in (aborted.stdout + aborted.stderr)

    marker_file = tmp_path / "uv_args.txt"
    fake_bin = tmp_path / "bin"
    _make_executable(fake_bin / "uv", f'#!/usr/bin/env bash\nprintf "%s\\n" "$*" > "{marker_file}"\nexit 0\n')
    env = dict(os.environ)
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
    confirmed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [str(LIVE_SCRIPT_PATH)], input="RECORD LIVE DEMOS\n", text=True, capture_output=True, env=env, check=False
    )
    assert confirmed.returncode == 0, confirmed.stderr
    assert marker_file.read_text(encoding="utf-8").strip() == "run --group demos python manage.py demos all"
