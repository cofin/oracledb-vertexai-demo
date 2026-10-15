# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Base msgspec Struct classes for application schemas."""

import msgspec

__all__ = ("BaseStruct", "CamelizedBaseStruct")


class BaseStruct(msgspec.Struct):
    """Base msgspec struct."""


class CamelizedBaseStruct(BaseStruct, rename="camel"):
    """Camelized Base Struct"""
