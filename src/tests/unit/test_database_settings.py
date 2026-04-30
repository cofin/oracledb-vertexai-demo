# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Database settings contracts for SQLSpec Oracle integrations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def test_oracle_adk_and_litestar_session_flags_wire_to_sqlspec_config(monkeypatch: MonkeyPatch) -> None:
    from app.lib.settings import DatabaseSettings

    monkeypatch.setenv("ORACLE_ADK_IN_MEMORY", "true")
    monkeypatch.setenv("ORACLE_LITESTAR_SESSION_IN_MEMORY", "true")
    monkeypatch.setenv("ADK_ENABLE_MEMORY", "false")

    config = DatabaseSettings().create_config()

    assert config.extension_config["adk"]["in_memory"] is True
    assert config.extension_config["adk"]["include_memory_migration"] is False
    assert config.extension_config["adk"]["memory_table"] == "adk_memory_entries"
    assert config.extension_config["litestar"]["in_memory"] is True
