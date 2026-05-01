# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Frontend chat behavior regression checks."""

from tests.support.paths import RESOURCES_ROOT


def test_chat_stream_form_data_is_captured_before_disabling_input() -> None:
    source = (RESOURCES_ROOT / "main.js").read_text()

    form_data_index = source.index("const formData = new FormData(form)")
    busy_index = source.index("setFormBusy(form, true)")

    assert form_data_index < busy_index
    assert "body: formData" in source
    assert "body: new FormData(form)" not in source


def test_chat_stream_renders_message_level_telemetry() -> None:
    source = (RESOURCES_ROOT / "main.js").read_text()

    assert 'id="pending-reply-meta"' in source
    assert "const renderMessageTelemetry = (payload) =>" in source
    assert "Vector query" in source
    assert "Embedding phase" in source
    assert "Oracle vector phase" in source
    assert "payload.embedding_cache_hit" in source
    assert "payload.from_cache" in source
    assert "renderMessageTelemetry(payload)" in source
    assert "data-telemetry-detail" in source
    assert "showTelemetryPopover" in source
    assert "payload.sql_phases" in source
    assert "SQL" in source


def test_chat_stream_final_payload_replaces_speculative_delta_text() -> None:
    source = (RESOURCES_ROOT / "main.js").read_text()

    final_branch = source[source.index('if (eventName === "final")') : source.index('if (eventName === "error")')]
    assert 'setPendingText(payload.answer ?? "")' in final_branch
    assert "currentText.trim()" not in final_branch
