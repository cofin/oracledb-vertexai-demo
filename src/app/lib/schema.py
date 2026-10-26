# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Immutable, GC-exempt msgspec Struct base classes for application schemas."""

from __future__ import annotations

from typing import Any, cast

import msgspec

__all__ = ("CamelizedFrozenStruct", "FrozenBaseStruct", "Message")


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
