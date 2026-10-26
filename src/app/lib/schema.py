# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Base msgspec Struct classes for application schemas."""

from __future__ import annotations

from typing import Any, cast

import msgspec

__all__ = ("BaseStruct", "CamelizedBaseStruct", "CamelizedFrozenStruct", "FrozenBaseStruct", "Message")


class BaseStruct(msgspec.Struct):
    """Legacy mutable msgspec struct base retained during incremental domain migration."""


class CamelizedBaseStruct(BaseStruct, rename="camel"):
    """Legacy mutable camelCase msgspec struct base retained during incremental domain migration."""


class FrozenBaseStruct(msgspec.Struct, frozen=True, gc=False, omit_defaults=True):
    """Immutable, GC-exempt msgspec Struct base for domain and wire models."""

    def to_dict(self) -> dict[str, Any]:
        """Convert struct fields into a built-in dictionary."""
        return cast("dict[str, Any]", msgspec.to_builtins(self))


class CamelizedFrozenStruct(FrozenBaseStruct, rename="camel", frozen=True, gc=False, omit_defaults=True):
    """Immutable, GC-exempt msgspec Struct with camelCase wire field names."""


class Message(CamelizedFrozenStruct, frozen=True, gc=False):
    """Standard API status message payload."""

    message: str
