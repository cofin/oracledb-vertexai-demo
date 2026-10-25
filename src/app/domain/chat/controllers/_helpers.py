# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Private request parsing helpers for chat controllers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.exceptions import ValidationException

from app.domain.chat.schemas import CoffeeChatForm

if TYPE_CHECKING:
    from litestar_htmx import HTMXRequest

__all__ = (
    "chat_form_from_request",
    "location_context_from_form",
    "location_text",
    "payload_bool",
    "payload_float",
    "payload_raw",
    "payload_value",
)

_MIN_LATITUDE = -90.0
_MAX_LATITUDE = 90.0
_MIN_LONGITUDE = -180.0
_MAX_LONGITUDE = 180.0
_MISSING = object()


def payload_raw(payload: Any, *keys: str, default: Any = "") -> Any:
    """Extract the first present raw field value from a form or JSON mapping."""
    getter = getattr(payload, "get", None)
    if not callable(getter):
        return default
    value = _MISSING
    for key in keys:
        value = getter(key, _MISSING)
        if value is not _MISSING:
            break
    if value is _MISSING:
        value = default
    if isinstance(value, list | tuple):
        value = value[0] if value else default
    return default if value is None else value


def payload_value(payload: Any, *keys: str, default: str = "") -> str:
    """Extract a string field value from a form or JSON mapping."""
    value = payload_raw(payload, *keys, default=default)
    return str(value or default)


def payload_bool(payload: Any, *keys: str, default: bool = False) -> bool:
    """Coerce a boolean field value from a form or JSON mapping."""
    value = payload_raw(payload, *keys, default=default)
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return bool(value)
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "on"}
    return default


def payload_float(payload: Any, *keys: str) -> float | None:
    """Coerce an optional floating-point coordinate field from a form or JSON mapping."""
    value = payload_raw(payload, *keys, default=None)
    if value is None or (isinstance(value, str) and not value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationException(detail="Location coordinates must be numbers") from exc


def location_context_from_form(data: CoffeeChatForm) -> dict[str, Any]:
    """Build a validated request-scoped location context from parsed chat form fields."""
    context: dict[str, Any] = {}
    for key, value in (
        ("city", data.city),
        ("state", data.state),
        ("zip_code", data.zip_code),
        ("store_name", data.store_name),
    ):
        cleaned = location_text(value)
        if cleaned:
            context[key] = cleaned

    if not data.location_consent:
        return context

    if data.latitude is None and data.longitude is None:
        return context
    if data.latitude is None or data.longitude is None:
        raise ValidationException(detail="Location coordinates require latitude and longitude")
    if not _MIN_LATITUDE <= data.latitude <= _MAX_LATITUDE or not (_MIN_LONGITUDE <= data.longitude <= _MAX_LONGITUDE):
        raise ValidationException(detail="Invalid location coordinates")

    coordinates = {"latitude": data.latitude, "longitude": data.longitude}
    if data.accuracy is not None:
        coordinates["accuracy_meters"] = max(data.accuracy, 0.0)
    context["coordinates"] = coordinates
    return context


async def chat_form_from_request(request: HTMXRequest) -> CoffeeChatForm:
    """Parse either JSON API payloads or HTMX form submissions into a frozen CoffeeChatForm."""
    content_type = request.headers.get("content-type", "")
    payload = await request.json() if "application/json" in content_type else await request.form()
    return CoffeeChatForm(
        message=payload_value(payload, "message"),
        persona=payload_value(payload, "persona", default="barista"),
        location_consent=payload_bool(payload, "locationConsent", "location_consent"),
        latitude=payload_float(payload, "latitude", "lat"),
        longitude=payload_float(payload, "longitude", "lng", "lon"),
        accuracy=payload_float(payload, "accuracy", "accuracyMeters", "accuracy_meters"),
        city=payload_value(payload, "city"),
        state=payload_value(payload, "state"),
        zip_code=payload_value(payload, "zipCode", "zip_code", "zip"),
        store_name=payload_value(payload, "storeName", "store_name"),
    )


def location_text(value: str) -> str:
    """Strip null bytes and bound user-supplied location hint text."""
    return value.replace("\x00", "").strip()[:100]
