# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Deterministic VHS terminal and headless Playwright browser demo recorders."""

from __future__ import annotations

from tools.demos.cli import demos_group
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

__all__ = (
    "HUD_INIT_SCRIPT",
    "VHSRecordResult",
    "VHSRecorderConfig",
    "VHSRecorderError",
    "WebDemoConfig",
    "WebDemoError",
    "WebDemoResult",
    "WebDemoScenario",
    "build_ffmpeg_gif_filter",
    "build_ffmpeg_mp4_args",
    "demos_group",
    "list_default_tapes",
    "parse_tape_outputs",
    "record_all_tapes",
    "record_all_web_scenarios",
    "record_vhs_tape",
    "record_web_scenario",
    "resolve_chromium_binary",
    "transcode_webm_to_mp4_and_gif",
    "verify_vhs_prerequisites",
    "verify_web_prerequisites",
)
