# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Frontend chat behavior regression checks."""

from pathlib import Path


def test_chat_stream_form_data_is_captured_before_disabling_input() -> None:
    source = (Path(__file__).parents[2] / "resources" / "main.js").read_text()

    form_data_index = source.index("const formData = new FormData(form)")
    busy_index = source.index("setFormBusy(form, true)")

    assert form_data_index < busy_index
    assert "body: formData" in source
    assert "body: new FormData(form)" not in source
