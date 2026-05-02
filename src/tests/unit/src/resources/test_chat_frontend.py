# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Frontend chat behavior regression checks."""

from tests.support.paths import APP_ROOT, RESOURCES_ROOT


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


def test_chat_frontend_exposes_clear_chat_button_handler() -> None:
    source = (RESOURCES_ROOT / "main.js").read_text()

    assert "[data-clear-chat]" in source
    assert 'fetch("/api/chat/session/clear"' in source
    assert "resetChatMessages()" in source
    assert "welcomeMessageHtml" in source
    assert "chat-avatar" in source
    assert 'data-chat-avatar="ai"' in source
    assert 'data-chat-avatar="human"' in source
    assert "initPersonaPicker" in source
    assert "Alpine" not in source
    assert "Tell me what sounds good and I'll check the Cymbal Coffee menu." in source
    assert "Welcome back. Tell me what sounds good" not in source


def test_chat_frontend_requires_explicit_location_opt_in() -> None:
    source = (RESOURCES_ROOT / "main.js").read_text()
    template = (APP_ROOT / "domain/web/templates/pages/chat.html.j2").read_text()

    assert "data-use-location" in template
    assert 'name="location_consent" value="false"' in template
    assert 'name="latitude"' in template
    assert 'name="longitude"' in template
    assert 'name="city"' in template
    assert 'name="zip_code"' in template
    assert "navigator.geolocation.getCurrentPosition" in source
    assert "enableHighAccuracy: false" in source
    assert "timeout: 8000" in source
    assert "maximumAge: 300000" in source
    assert "Location denied" in source
    assert "Location timed out" in source
    assert "Location unsupported" in source


def test_chat_frontend_renders_store_cards_and_no_key_maps_links() -> None:
    source = (RESOURCES_ROOT / "main.js").read_text()

    assert "renderStructuredResults(payload)" in source
    assert "payload.store_results" in source
    assert "payload.inventory_results" in source
    assert "payload.map_actions" in source
    assert "Open in Google Maps" in source
    assert 'https:" && parsed.hostname === "www.google.com"' in source
    assert 'parsed.pathname.startsWith("/maps/")' in source
    assert "pending-reply-results" in source
    assert "<iframe" not in source
