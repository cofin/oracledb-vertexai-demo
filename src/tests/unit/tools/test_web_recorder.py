# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the headless Playwright browser demo recorder and ``manage.py demos`` CLI."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self

import manage
import pytest
from click.testing import CliRunner
from tools.demos.web import (
    HUD_INIT_SCRIPT,
    WebDemoConfig,
    WebDemoError,
    WebDemoResult,
    WebDemoScenario,
    build_ffmpeg_gif_filter,
    build_ffmpeg_mp4_args,
    record_all_web_scenarios,
    record_web_scenario,
    transcode_webm_to_mp4_and_gif,
    verify_web_prerequisites,
)


@dataclass(slots=True)
class _FakeVideo:
    """Fake Playwright Video handle enforcing context.close() before path() resolution."""

    raw_webm_path: Path
    owner_context: _FakeBrowserContext

    def path(self) -> str:
        """Return the finalized WebM path only after the owning BrowserContext has closed."""
        if not self.owner_context.closed:
            msg = "BrowserContext must be closed before reading page.video.path()"
            raise AssertionError(msg)
        return str(self.raw_webm_path)


@dataclass(slots=True)
class _FakeLocator:
    """Fake Playwright Locator recording interactions for scenario verification."""

    selector: str
    page: _FakePage

    @property
    def first(self) -> _FakeLocator:
        """First matching locator handle."""
        return self

    def wait_for(self, **_kwargs: Any) -> None:
        """Simulate waiting for element visibility."""
        self.page.events.append(("wait_for", self.selector))

    def fill(self, value: str) -> None:
        """Record an input fill operation."""
        self.page.events.append(("fill", f"{self.selector}={len(value)}"))

    def click(self, **_kwargs: Any) -> None:
        """Record a click interaction."""
        self.page.events.append(("click", self.selector))


@dataclass(slots=True)
class _FakePage:
    """Fake Playwright Page recording navigation, locator calls, and HUD captions."""

    owner_context: _FakeBrowserContext
    video: _FakeVideo
    visited_urls: list[str] = field(default_factory=list)
    captions: list[str] = field(default_factory=list)
    events: list[tuple[str, str]] = field(default_factory=list)

    def goto(self, url: str, **_kwargs: Any) -> None:
        """Record page navigation."""
        self.visited_urls.append(url)

    def locator(self, selector: str) -> _FakeLocator:
        """Build a fake CSS/ID locator."""
        return _FakeLocator(selector=selector, page=self)

    def get_by_role(self, role: str, *, name: str, **_kwargs: Any) -> _FakeLocator:
        """Build a fake ARIA role locator."""
        return _FakeLocator(selector=f"role={role}[{name}]", page=self)

    def get_by_label(self, label: str, **_kwargs: Any) -> _FakeLocator:
        """Build a fake form-label locator."""
        return _FakeLocator(selector=f"label={label}", page=self)

    def evaluate(self, script: str, arg: Any = None) -> Any:
        """Capture HUD step captions passed into the browser context."""
        if isinstance(arg, str) and "__cymbalSetCaption" in script:
            self.captions.append(arg)
        elif isinstance(arg, dict) and isinstance(arg.get("caption"), str):
            self.captions.append(arg["caption"])
        return None

    def wait_for_load_state(self, state: str = "networkidle", **_kwargs: Any) -> None:
        """Simulate load-state synchronization."""
        self.events.append(("load_state", state))

    def wait_for_timeout(self, timeout_ms: int) -> None:
        """Record pacing pauses without sleeping in unit tests."""
        self.events.append(("pause_ms", str(timeout_ms)))


@dataclass(slots=True)
class _FakeBrowserContext:
    """Fake Playwright BrowserContext tracking init scripts, options, and close lifecycle."""

    options: dict[str, Any]
    raw_webm_path: Path
    init_scripts: list[str] = field(default_factory=list)
    pages: list[_FakePage] = field(default_factory=list)
    closed: bool = False

    def add_init_script(self, script: str) -> None:
        """Record injected initialization JavaScript."""
        self.init_scripts.append(script)

    def new_page(self) -> _FakePage:
        """Create and register a fake Page with an attached Video handle."""
        video = _FakeVideo(raw_webm_path=self.raw_webm_path, owner_context=self)
        page = _FakePage(owner_context=self, video=video)
        self.pages.append(page)
        return page

    def close(self) -> None:
        """Flush the fake WebM video artifact and mark the context closed."""
        self.raw_webm_path.parent.mkdir(parents=True, exist_ok=True)
        self.raw_webm_path.write_bytes(b"\x1a\x45\xdf\xa3fake-webm-stream")
        self.closed = True


@dataclass(slots=True)
class _FakeBrowser:
    """Fake Chromium Browser tracking created contexts and shutdown."""

    tmp_dir: Path
    launch_kwargs: dict[str, Any]
    contexts: list[_FakeBrowserContext] = field(default_factory=list)
    closed: bool = False

    def new_context(self, **kwargs: Any) -> _FakeBrowserContext:
        """Create a fake BrowserContext writing its raw WebM file into record_video_dir."""
        video_dir = Path(kwargs["record_video_dir"])
        raw_webm = video_dir / f"recording-{len(self.contexts)}.webm"
        ctx = _FakeBrowserContext(options=kwargs, raw_webm_path=raw_webm)
        self.contexts.append(ctx)
        return ctx

    def close(self) -> None:
        """Mark the browser closed."""
        self.closed = True


@dataclass(slots=True)
class _FakePlaywrightDriver:
    """Fake sync_playwright() context manager providing a Chromium launcher."""

    tmp_dir: Path
    browsers: list[_FakeBrowser] = field(default_factory=list)

    @property
    def chromium(self) -> Any:
        """Fake Chromium browser launcher."""
        return SimpleNamespace(launch=self._launch)

    def __enter__(self) -> Self:
        """Enter sync_playwright context."""
        return self

    def __exit__(self, *_exc: object) -> None:
        """Exit sync_playwright context."""

    def _launch(self, **kwargs: Any) -> _FakeBrowser:
        browser = _FakeBrowser(tmp_dir=self.tmp_dir, launch_kwargs=kwargs)
        self.browsers.append(browser)
        return browser


def test_web_demo_config_from_env_defaults_and_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify WebDemoConfig.from_env populates APEX 26.1 defaults and respects environment overrides."""
    for key in ("APEX_BASE_URL", "APEX_WORKSPACE", "APEX_APP_USER", "APEX_PASSWORD", "ORACLE_APP_PASSWORD"):
        monkeypatch.delenv(key, raising=False)

    cfg = WebDemoConfig.from_env()
    assert hasattr(cfg, "__slots__")
    assert cfg.apex_base_url == "https://localhost:8443/ords/apex"
    assert cfg.ords_base_url == "https://localhost:8443/ords"
    assert cfg.workspace == "COFFEE"
    assert cfg.username == "APP"
    assert cfg.width == 1280
    assert cfg.height == 720
    assert cfg.output_dir == Path("docs/_static/demos")

    monkeypatch.setenv("APEX_BASE_URL", "https://localhost:9443/ords/apex/")
    monkeypatch.setenv("APEX_WORKSPACE", "ROASTERY")
    monkeypatch.setenv("APEX_APP_USER", "BARISTA")
    monkeypatch.setenv("ORACLE_APP_PASSWORD", "CustomPass_123")
    overridden = WebDemoConfig.from_env()
    assert overridden.apex_base_url == "https://localhost:9443/ords/apex"
    assert overridden.ords_base_url == "https://localhost:9443/ords"
    assert overridden.workspace == "ROASTERY"
    assert overridden.username == "BARISTA"
    assert overridden.password == "CustomPass_123"


def test_ffmpeg_mp4_and_two_pass_palette_gif_builders_and_transcoding(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify FFmpeg H.264 MP4 args, two-pass Bayer palette GIF filter, and fail-fast transcoding."""
    webm_path = tmp_path / "raw" / "capture.webm"
    webm_path.parent.mkdir(parents=True, exist_ok=True)
    webm_path.write_bytes(b"\x1a\x45\xdf\xa3webm")
    mp4_target = tmp_path / "out" / "demo.mp4"

    mp4_args = build_ffmpeg_mp4_args(webm_path, mp4_target, ffmpeg_binary=Path("/usr/bin/ffmpeg"))
    assert mp4_args[:3] == ["/usr/bin/ffmpeg", "-y", "-i"]
    assert "-c:v" in mp4_args
    assert "libx264" in mp4_args
    assert "-pix_fmt" in mp4_args
    assert "yuv420p" in mp4_args
    assert "-movflags" in mp4_args
    assert "+faststart" in mp4_args

    gif_filter = build_ffmpeg_gif_filter(width=1280, fps=15)
    assert "palettegen=stats_mode=diff" in gif_filter
    assert "paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" in gif_filter

    monkeypatch.setattr("tools.demos.web.shutil.which", lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None)
    commands_run: list[list[str]] = []

    def fake_ffmpeg_ok(cmd: list[str], **_kwargs: Any) -> SimpleNamespace:
        commands_run.append(cmd)
        target = Path(cmd[-1])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"non-empty-media-bytes")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("tools.demos.web.subprocess.run", fake_ffmpeg_ok)
    mp4_out, gif_out = transcode_webm_to_mp4_and_gif(webm_path, output_dir=tmp_path / "demos", stem="apex-demo")
    assert len(commands_run) == 2
    assert mp4_out == tmp_path / "demos" / "apex-demo.mp4"
    assert gif_out == tmp_path / "demos" / "apex-demo.gif"
    assert mp4_out.stat().st_size > 0
    assert gif_out.stat().st_size > 0

    def fake_ffmpeg_empty(cmd: list[str], **_kwargs: Any) -> SimpleNamespace:
        target = Path(cmd[-1])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("tools.demos.web.subprocess.run", fake_ffmpeg_empty)
    with pytest.raises(WebDemoError, match="zero-byte"):
        transcode_webm_to_mp4_and_gif(webm_path, output_dir=tmp_path / "demos", stem="broken-demo")

    def fake_ffmpeg_fail(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(returncode=1, stdout="", stderr="encoder libx264 error")

    monkeypatch.setattr("tools.demos.web.subprocess.run", fake_ffmpeg_fail)
    with pytest.raises(WebDemoError, match="encoder libx264 error"):
        transcode_webm_to_mp4_and_gif(webm_path, output_dir=tmp_path / "demos", stem="failed-demo")


def test_record_web_scenarios_configure_context_inject_hud_flush_video_and_redact_secrets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify both web scenarios set ignore_https_errors, 1280x720 video, HUD init script, context flush, and safe captions."""
    fake_driver = _FakePlaywrightDriver(tmp_dir=tmp_path)
    fake_sync_api = SimpleNamespace(sync_playwright=lambda: fake_driver)
    real_import_module = importlib.import_module
    monkeypatch.setattr(
        "tools.demos.web.importlib.import_module",
        lambda name, package=None: (
            fake_sync_api if name == "playwright.sync_api" else real_import_module(name, package)
        ),
    )
    monkeypatch.setattr("tools.demos.web.shutil.which", lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None)

    def fake_ffmpeg_transcode(cmd: list[str], **_kwargs: Any) -> SimpleNamespace:
        out_file = Path(cmd[-1])
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_bytes(b"encoded-video-payload")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("tools.demos.web.subprocess.run", fake_ffmpeg_transcode)

    secret_pw = "SuperSecretDemoPw_987"
    cfg = WebDemoConfig(
        apex_base_url="https://localhost:8443/ords/apex",
        workspace="COFFEE",
        username="APP",
        password=secret_pw,
        project_id="demo-gcp-project",
        location="global",
        output_dir=tmp_path / "out",
    )

    prereqs = verify_web_prerequisites()
    assert prereqs["ffmpeg"] == Path("/usr/bin/ffmpeg")
    assert prereqs["playwright"] == "playwright.sync_api"

    results = record_all_web_scenarios(config=cfg)
    assert [res.scenario for res in results] == [
        WebDemoScenario.APEX_CONFIGURE_VERTEX_AI,
        WebDemoScenario.APEX_CREATE_VERTEX_APP,
    ]
    assert len(fake_driver.browsers) == 2

    token_pairs = (("ya", "29."), ("AI", "za"), ("AK", "IA"), ("gh", "p_"))
    forbidden_fragments = (secret_pw, "Bearer ", *(left + right for left, right in token_pairs))

    for idx, result in enumerate(results):
        assert isinstance(result, WebDemoResult)
        assert hasattr(result, "__slots__")
        assert result.mp4_path.is_file()
        assert result.gif_path.is_file()

        browser = fake_driver.browsers[idx]
        assert browser.launch_kwargs.get("headless") is True
        assert browser.closed is True

        ctx = browser.contexts[0]
        assert ctx.closed is True
        assert ctx.options["ignore_https_errors"] is True
        assert ctx.options["viewport"] == {"width": 1280, "height": 720}
        assert ctx.options["record_video_size"] == {"width": 1280, "height": 720}
        assert HUD_INIT_SCRIPT in ctx.init_scripts

        page = ctx.pages[0]
        assert page.visited_urls
        assert page.captions
        for caption in page.captions:
            for forbidden in forbidden_fragments:
                assert forbidden not in caption

    single = record_web_scenario(WebDemoScenario.APEX_CREATE_VERTEX_APP, config=cfg)
    assert single.mp4_path.name == "apex-create-vertex-app.mp4"
    assert single.gif_path.name == "apex-create-vertex-app.gif"


def test_manage_demos_cli_help_check_and_subcommand_dispatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify manage.py demos --help, check, shell, web, and all subcommands execute cleanly via CliRunner."""
    runner = CliRunner()
    help_res = runner.invoke(manage.cli, ["demos", "--help"])
    assert help_res.exit_code == 0, help_res.output
    for subcmd in ("check", "shell", "web", "all"):
        assert subcmd in help_res.output

    monkeypatch.setattr(
        "tools.demos.cli.verify_vhs_prerequisites",
        lambda: {
            "vhs": Path("/usr/bin/vhs"),
            "ttyd": Path("/usr/bin/ttyd"),
            "ffmpeg": Path("/usr/bin/ffmpeg"),
            "chromium": Path("/opt/chrome"),
        },
    )
    monkeypatch.setattr(
        "tools.demos.cli.verify_web_prerequisites",
        lambda: {"ffmpeg": Path("/usr/bin/ffmpeg"), "playwright": "playwright.sync_api"},
    )
    check_res = runner.invoke(manage.cli, ["demos", "check"])
    assert check_res.exit_code == 0, check_res.output
    assert "vhs" in check_res.output.lower()
    assert "playwright" in check_res.output.lower()

    fake_tape = tmp_path / "sample.tape"
    fake_tape.write_text("Output docs/_static/demos/sample.mp4\n", encoding="utf-8")
    monkeypatch.setattr(
        "tools.demos.cli.record_all_tapes",
        lambda **_kwargs: (
            SimpleNamespace(tape_path=fake_tape, outputs=(tmp_path / "sample.mp4", tmp_path / "sample.gif"), stdout=""),
        ),
    )
    monkeypatch.setattr(
        "tools.demos.cli.record_all_web_scenarios",
        lambda **_kwargs: (
            WebDemoResult(
                scenario=WebDemoScenario.APEX_CONFIGURE_VERTEX_AI,
                mp4_path=tmp_path / "apex-configure-vertex-ai.mp4",
                gif_path=tmp_path / "apex-configure-vertex-ai.gif",
            ),
        ),
    )

    all_res = runner.invoke(manage.cli, ["demos", "all", "--output-dir", str(tmp_path)])
    assert all_res.exit_code == 0, all_res.output
    assert "sample.mp4" in all_res.output
    assert "apex-configure-vertex-ai.mp4" in all_res.output
