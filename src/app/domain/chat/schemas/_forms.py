# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Chat form request schema representations."""

from __future__ import annotations

from app.lib.schema import FrozenBaseStruct

__all__ = ("CoffeeChatForm",)


class CoffeeChatForm(FrozenBaseStruct, frozen=True, gc=False):
    """Parsed chat submission payload from JSON API or HTMX form requests."""

    message: str
    persona: str = "barista"
    location_consent: bool = False
    latitude: float | None = None
    longitude: float | None = None
    accuracy: float | None = None
    city: str = ""
    state: str = ""
    zip_code: str = ""
    store_name: str = ""
