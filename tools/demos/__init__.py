# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Deterministic VHS terminal and headless Playwright browser demo recorders."""

from __future__ import annotations

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
