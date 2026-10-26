# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Headless Playwright and FFmpeg browser video recorder for Oracle APEX 26.1 + Vertex AI demos."""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from tools.oracle.database import DatabaseConfig

__all__ = (
    "HUD_INIT_SCRIPT",
    "WebDemoConfig",
    "WebDemoError",
    "WebDemoResult",
    "WebDemoScenario",
    "build_ffmpeg_gif_filter",
    "build_ffmpeg_mp4_args",
    "record_all_web_scenarios",
    "record_web_scenario",
    "transcode_webm_to_mp4_and_gif",
    "verify_web_prerequisites",
)

HUD_INIT_SCRIPT: Final[str] = """
(() => {
  const mountHud = () => {
    if (document.getElementById("__cymbal_hud_root")) {
      return;
    }
    const root = document.createElement("div");
    root.id = "__cymbal_hud_root";
    root.style.cssText = "position:fixed;inset:0;pointer-events:none;z-index:2147483647;font-family:system-ui,-apple-system,sans-serif;";

    const cursor = document.createElement("div");
    cursor.id = "__cymbal_cursor";
    cursor.style.cssText = "position:fixed;width:18px;height:18px;border-radius:50%;background:rgba(26,115,232,0.85);border:2px solid #ffffff;box-shadow:0 2px 8px rgba(0,0,0,0.35);transform:translate(-50%,-50%);transition:left 90ms linear,top 90ms linear;";

    const caption = document.createElement("div");
    caption.id = "__cymbal_caption";
    caption.style.cssText = "position:fixed;right:24px;bottom:20px;max-width:560px;padding:10px 16px;border-radius:10px;background:rgba(15,23,42,0.88);color:#f8fafc;font-size:14px;font-weight:600;letter-spacing:0.01em;box-shadow:0 8px 24px rgba(0,0,0,0.35);display:none;";

    root.appendChild(cursor);
    root.appendChild(caption);
    document.documentElement.appendChild(root);

    document.addEventListener("mousemove", (evt) => {
      cursor.style.left = `${evt.clientX}px`;
      cursor.style.top = `${evt.clientY}px`;
    }, { passive: true });

    document.addEventListener("mousedown", (evt) => {
      const ripple = document.createElement("div");
      ripple.style.cssText = `position:fixed;left:${evt.clientX}px;top:${evt.clientY}px;width:36px;height:36px;border-radius:50%;border:2px solid #1a73e8;transform:translate(-50%,-50%) scale(0.4);opacity:0.95;transition:transform 320ms ease-out,opacity 320ms ease-out;`;
      root.appendChild(ripple);
      requestAnimationFrame(() => {
        ripple.style.transform = "translate(-50%,-50%) scale(1.35)";
        ripple.style.opacity = "0";
      });
      setTimeout(() => ripple.remove(), 360);
    }, { passive: true });
  };

  window.__cymbalSetCaption = (text) => {
    mountHud();
    const badge = document.getElementById("__cymbal_caption");
    if (!badge) {
      return;
    }
    if (!text) {
      badge.style.display = "none";
      badge.textContent = "";
      return;
    }
    badge.textContent = String(text);
    badge.style.display = "block";
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountHud, { once: true });
  } else {
    mountHud();
  }
})();
"""


class WebDemoError(RuntimeError):
    """Raised when Playwright browser recording or FFmpeg transcoding fails."""


class WebDemoScenario(StrEnum):
    """Scripted Oracle APEX 26.1 + Vertex AI browser walkthrough scenarios."""

    APEX_CONFIGURE_VERTEX_AI = "apex-configure-vertex-ai"
    APEX_CREATE_VERTEX_APP = "apex-create-vertex-app"


@dataclass(frozen=True, slots=True)
class WebDemoConfig:
    """Configuration for headless Playwright APEX 26.1 demo video capture."""

    apex_base_url: str = "https://localhost:8443/ords/apex"
    workspace: str = "COFFEE"
    username: str = "APP"
    password: str = ""
    project_id: str = "your-gcp-project-id"
    location: str = "global"
    model: str = "google/gemini-3.8-flash"
    app_alias: str = "cymbal-coffee-ops"
    width: int = 1280
    height: int = 720
    fps: int = 15
    output_dir: Path = Path("docs/_static/demos")
    headless: bool = True
    timeout_seconds: int = 300

    @property
    def ords_base_url(self) -> str:
        """Derive the root ORDS URL (e.g. ``https://localhost:8443/ords``) from ``apex_base_url``."""
        normalized = self.apex_base_url.rstrip("/")
        if normalized.endswith("/apex"):
            return normalized[: -len("/apex")]
        return normalized

    @property
    def vertex_openapi_url(self) -> str:
        """Build the Direct Vertex AI OpenAI-compatible ``/endpoints/openapi`` base URL."""
        host = (
            "aiplatform.googleapis.com" if self.location == "global" else f"{self.location}-aiplatform.googleapis.com"
        )
        return f"https://{host}/v1/projects/{self.project_id}/locations/{self.location}/endpoints/openapi"

    @classmethod
    def from_env(cls, *, output_dir: Path | None = None) -> WebDemoConfig:
        """Load browser demo settings from environment variables with local ``adb-free`` defaults."""
        db_cfg = DatabaseConfig.from_env()
        default_apex_url = f"https://localhost:{db_cfg.https_port}/ords/apex"
        raw_base = os.environ.get("APEX_BASE_URL", default_apex_url).strip().rstrip("/")
        workspace = os.environ.get("APEX_WORKSPACE", db_cfg.workspace_name).strip() or "COFFEE"
        username = (
            (os.environ.get("APEX_APP_USER") or os.environ.get("ORACLE_APP_USER") or db_cfg.app_user or "APP")
            .strip()
            .upper()
        )
        password = (
            os.environ.get("APEX_PASSWORD") or os.environ.get("ORACLE_APP_PASSWORD") or db_cfg.app_user_password
        ).strip()
        project_id = (
            os.environ.get("VERTEX_AI_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT") or "your-gcp-project-id"
        ).strip()
        location = os.environ.get("VERTEX_AI_LOCATION", "global").strip() or "global"
        resolved_out = output_dir if output_dir is not None else Path("docs/_static/demos")
        return cls(
            apex_base_url=raw_base,
            workspace=workspace,
            username=username,
            password=password,
            project_id=project_id,
            location=location,
            output_dir=resolved_out,
        )


@dataclass(frozen=True, slots=True)
class WebDemoResult:
    """Verified `.mp4` and `.gif` artifacts produced for a web demo scenario."""

    scenario: WebDemoScenario
    mp4_path: Path
    gif_path: Path


def verify_web_prerequisites() -> dict[str, Path | str]:
    """Verify that ``ffmpeg`` and ``playwright.sync_api`` are available."""
    ffmpeg_bin = _resolve_ffmpeg_binary()
    _load_playwright_sync_api()
    return {"ffmpeg": ffmpeg_bin, "playwright": "playwright.sync_api"}


def build_ffmpeg_mp4_args(
    webm_path: Path, mp4_path: Path, *, ffmpeg_binary: Path | None = None, fps: int = 15
) -> list[str]:
    """Construct FFmpeg arguments for H.264 ``yuv420p`` ``+faststart`` MP4 transcoding."""
    ffmpeg_bin = ffmpeg_binary if ffmpeg_binary is not None else _resolve_ffmpeg_binary()
    return [
        str(ffmpeg_bin),
        "-y",
        "-i",
        str(webm_path),
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        "22",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-an",
        str(mp4_path),
    ]


def build_ffmpeg_gif_filter(*, width: int = 1280, fps: int = 15) -> str:
    """Build the two-pass Lanczos ``palettegen`` / ``paletteuse`` filtergraph for crisp GIF previews."""
    return (
        f"fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];"
        "[s0]palettegen=stats_mode=diff[p];"
        "[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle"
    )


def transcode_webm_to_mp4_and_gif(
    webm_path: Path, *, output_dir: Path, stem: str, width: int = 1280, fps: int = 15, timeout_seconds: int = 300
) -> tuple[Path, Path]:
    """Transcode a Playwright ``.webm`` recording to both ``.mp4`` and palette-optimized ``.gif``."""
    if not webm_path.is_file() or webm_path.stat().st_size == 0:
        raise WebDemoError(f"Playwright WebM source is missing or zero-byte: {webm_path}")

    ffmpeg_bin = _resolve_ffmpeg_binary()
    output_dir.mkdir(parents=True, exist_ok=True)
    mp4_path = output_dir / f"{stem}.mp4"
    gif_path = output_dir / f"{stem}.gif"

    mp4_cmd = build_ffmpeg_mp4_args(webm_path, mp4_path, ffmpeg_binary=ffmpeg_bin, fps=fps)
    _run_ffmpeg(mp4_cmd, label=f"{stem}.mp4", timeout_seconds=timeout_seconds)

    gif_cmd = [
        str(ffmpeg_bin),
        "-y",
        "-i",
        str(webm_path),
        "-vf",
        build_ffmpeg_gif_filter(width=width, fps=fps),
        "-loop",
        "0",
        str(gif_path),
    ]
    _run_ffmpeg(gif_cmd, label=f"{stem}.gif", timeout_seconds=timeout_seconds)

    for artifact in (mp4_path, gif_path):
        if not artifact.is_file() or artifact.stat().st_size == 0:
            raise WebDemoError(f"FFmpeg produced missing or zero-byte output artifact: {artifact}")

    return (mp4_path, gif_path)


def record_web_scenario(scenario: WebDemoScenario, *, config: WebDemoConfig | None = None) -> WebDemoResult:
    """Execute a headless Playwright APEX 26.1 walkthrough and transcode it to `.mp4` and `.gif`."""
    cfg = config if config is not None else WebDemoConfig.from_env()
    sync_api = _load_playwright_sync_api()
    pw_errors = _playwright_error_types(sync_api)

    with tempfile.TemporaryDirectory(prefix="cymbal-web-demo-") as raw_tmp:
        raw_dir = Path(raw_tmp)
        try:
            raw_webm = _capture_scenario_webm(sync_api, scenario=scenario, cfg=cfg, raw_dir=raw_dir)
        except pw_errors as exc:
            raise WebDemoError(f"Playwright failed while recording {scenario.value}: {exc}") from exc

        mp4_path, gif_path = transcode_webm_to_mp4_and_gif(
            raw_webm,
            output_dir=cfg.output_dir,
            stem=scenario.value,
            width=cfg.width,
            fps=cfg.fps,
            timeout_seconds=cfg.timeout_seconds,
        )
    return WebDemoResult(scenario=scenario, mp4_path=mp4_path, gif_path=gif_path)


def record_all_web_scenarios(
    *, config: WebDemoConfig | None = None, scenarios: Sequence[WebDemoScenario] | None = None
) -> tuple[WebDemoResult, ...]:
    """Record every configured APEX 26.1 browser demo scenario in deterministic order."""
    cfg = config if config is not None else WebDemoConfig.from_env()
    target_scenarios = (
        tuple(scenarios)
        if scenarios is not None
        else (WebDemoScenario.APEX_CONFIGURE_VERTEX_AI, WebDemoScenario.APEX_CREATE_VERTEX_APP)
    )
    return tuple(record_web_scenario(scenario, config=cfg) for scenario in target_scenarios)


def _playwright_error_types(sync_api: Any) -> tuple[type[Exception], ...]:
    """Return Playwright's runtime ``Error`` exception tuple when exposed by ``sync_api``."""
    err_cls = getattr(sync_api, "Error", None)
    if isinstance(err_cls, type) and issubclass(err_cls, Exception):
        return (err_cls,)
    return ()


def _capture_scenario_webm(sync_api: Any, *, scenario: WebDemoScenario, cfg: WebDemoConfig, raw_dir: Path) -> Path:
    """Launch headless Chromium, run the scenario inside an isolated context, and guarantee browser cleanup."""
    with sync_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=cfg.headless)
        try:
            return _run_context_capture(browser, scenario=scenario, cfg=cfg, raw_dir=raw_dir)
        finally:
            browser.close()


def _run_context_capture(browser: Any, *, scenario: WebDemoScenario, cfg: WebDemoConfig, raw_dir: Path) -> Path:
    """Record one scenario inside a video-enabled ``BrowserContext`` and flush the ``.webm`` file."""
    context = browser.new_context(
        ignore_https_errors=True,
        viewport={"width": cfg.width, "height": cfg.height},
        record_video_dir=str(raw_dir),
        record_video_size={"width": cfg.width, "height": cfg.height},
    )
    context_closed = False
    try:
        context.add_init_script(HUD_INIT_SCRIPT)
        page = context.new_page()
        if scenario == WebDemoScenario.APEX_CONFIGURE_VERTEX_AI:
            _run_configure_vertex_ai_scenario(page, cfg)
        elif scenario == WebDemoScenario.APEX_CREATE_VERTEX_APP:
            _run_create_vertex_app_scenario(page, cfg)
        else:
            raise WebDemoError(f"Unsupported web demo scenario: {scenario}")
        context.close()
        context_closed = True
        if page.video is None:
            raise WebDemoError(f"Playwright page did not attach a video recorder for {scenario.value}")
        return Path(page.video.path())
    finally:
        if not context_closed:
            context.close()


def _resolve_ffmpeg_binary() -> Path:
    """Resolve ``ffmpeg`` on ``PATH`` or raise ``WebDemoError``."""
    found = shutil.which("ffmpeg")
    if not found:
        raise WebDemoError("Required binary 'ffmpeg' was not found on PATH.")
    return Path(found)


def _load_playwright_sync_api() -> Any:
    """Import ``playwright.sync_api`` lazily so base installs do not require Playwright."""
    try:
        return importlib.import_module("playwright.sync_api")
    except ModuleNotFoundError as exc:
        raise WebDemoError(
            "Playwright is not installed. Install the demos dependency group with: "
            "uv sync --group demos && uv run --group demos playwright install chromium"
        ) from exc


def _run_ffmpeg(cmd: list[str], *, label: str, timeout_seconds: int) -> None:
    """Execute an FFmpeg command and raise ``WebDemoError`` on timeout, OS error, or non-zero exit status."""
    try:
        completed = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout_seconds, check=False)
    except subprocess.TimeoutExpired as exc:
        raise WebDemoError(f"FFmpeg timed out after {timeout_seconds}s while generating {label}") from exc
    except OSError as exc:
        raise WebDemoError(f"Failed to execute FFmpeg while generating {label}: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or f"exit code {completed.returncode}").strip()
        raise WebDemoError(f"FFmpeg failed while generating {label}: {detail}")


def _set_caption(page: Any, text: str, *, pause_ms: int = 1200) -> None:
    """Update the in-page HUD step caption banner and hold briefly for viewer legibility."""
    page.evaluate("text => window.__cymbalSetCaption && window.__cymbalSetCaption(text)", text)
    page.wait_for_timeout(pause_ms)


def _run_configure_vertex_ai_scenario(page: Any, cfg: WebDemoConfig) -> None:
    """Record signing into APEX 26.1 Builder, inspecting VERTEX_AI_CRED and COFFEE_VERTEX_AI, and testing Vertex AI."""
    page.goto(cfg.apex_base_url, wait_until="domcontentloaded")
    _set_caption(page, f"Step 1: Sign in to Oracle APEX 26.1 Builder (Workspace {cfg.workspace})")

    workspace_input = page.locator("#F4550_P1_COMPANY").first
    workspace_input.wait_for(state="visible", timeout=30_000)
    workspace_input.fill(cfg.workspace)
    page.locator("#F4550_P1_USERNAME").first.fill(cfg.username)
    page.locator("#F4550_P1_PASSWORD").first.fill(cfg.password)
    page.get_by_role("button", name="Sign In").first.click()
    page.wait_for_load_state("networkidle")

    _set_caption(page, "Step 2: Open App Builder -> Workspace Utilities -> Web Credentials (VERTEX_AI_CRED)")
    app_builder_link = page.get_by_role("link", name="App Builder").first
    app_builder_link.wait_for(state="visible", timeout=30_000)
    app_builder_link.click()
    page.wait_for_load_state("networkidle")

    utilities_link = page.get_by_role("link", name="Workspace Utilities").first
    utilities_link.wait_for(state="visible", timeout=30_000)
    utilities_link.click()
    page.wait_for_load_state("networkidle")

    web_creds_link = page.get_by_role("link", name="Web Credentials").first
    web_creds_link.wait_for(state="visible", timeout=30_000)
    web_creds_link.click()
    page.wait_for_load_state("networkidle")

    cred_detail_link = page.get_by_role("link", name="VERTEX_AI_CRED").first
    cred_detail_link.wait_for(state="visible", timeout=30_000)
    cred_detail_link.click()
    page.wait_for_load_state("networkidle")

    utilities_breadcrumb = page.get_by_role("link", name="Workspace Utilities").first
    utilities_breadcrumb.wait_for(state="visible", timeout=30_000)
    utilities_breadcrumb.click()
    page.wait_for_load_state("networkidle")

    _set_caption(
        page, f"Step 3: Generative AI Service COFFEE_VERTEX_AI -> {cfg.vertex_openapi_url} ({cfg.model})", pause_ms=1800
    )
    genai_link = page.get_by_role("link", name="Generative AI").first
    genai_link.wait_for(state="visible", timeout=30_000)
    genai_link.click()
    page.wait_for_load_state("networkidle")

    service_link = page.get_by_role("link", name="COFFEE_VERTEX_AI").first
    service_link.wait_for(state="visible", timeout=30_000)
    service_link.click()
    page.wait_for_load_state("networkidle")

    _set_caption(page, "Step 4: Verify COFFEE_VERTEX_AI (Used by App Builder = Yes) & Test Connection", pause_ms=1800)
    test_button = page.get_by_role("button", name="Test Connection").first
    test_button.wait_for(state="visible", timeout=30_000)
    test_button.click()
    page.wait_for_load_state("networkidle")
    _set_caption(page, f"Direct Vertex AI Connection Verified ({cfg.model})", pause_ms=2200)


def _run_create_vertex_app_scenario(page: Any, cfg: WebDemoConfig) -> None:
    """Record opening the Cymbal Coffee APEX 26.1 app and invoking APEX_AI.GENERATE on Page 6."""
    workspace_slug = cfg.workspace.lower()
    login_url = f"{cfg.ords_base_url}/r/{workspace_slug}/{cfg.app_alias}/login"
    concierge_url = f"{cfg.ords_base_url}/r/{workspace_slug}/{cfg.app_alias}/vector-recommendations"

    page.goto(login_url, wait_until="domcontentloaded")
    _set_caption(page, f"Step 1: Launch Cymbal Coffee APEX 26.1 App ({cfg.app_alias})")

    user_input = page.locator("#P9999_USERNAME").first
    user_input.wait_for(state="visible", timeout=30_000)
    user_input.fill(cfg.username)
    page.locator("#P9999_PASSWORD").first.fill(cfg.password)
    page.get_by_role("button", name="Sign In").first.click()
    page.wait_for_load_state("networkidle")

    _set_caption(page, "Step 2: Review Oracle 26ai Catalog, VECTOR(3072, FLOAT32) & ANNOTATIONS KPIs", pause_ms=1800)

    page.goto(concierge_url, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    _set_caption(page, "Step 3: Open Page 6 — Vertex AI Coffee Concierge (APEX_AI.GENERATE)")

    prompt_field = page.locator("#P6_PROMPT").first
    prompt_field.wait_for(state="visible", timeout=30_000)
    prompt_field.fill("Recommend a bright floral pour-over and a pastry pairing from our in-stock menu")
    _set_caption(page, f"Step 4: Invoke COFFEE_VERTEX_AI ({cfg.model}) Grounded on Live PRODUCT Rows")

    ask_button = page.get_by_role("button", name="Ask Vertex AI").first
    ask_button.click()
    page.wait_for_load_state("networkidle")
    page.locator("#P6_AI_RESPONSE").first.wait_for(state="visible", timeout=60_000)
    _set_caption(page, "Grounded Vertex AI Recommendation Rendered via APEX_AI.GENERATE", pause_ms=2600)
