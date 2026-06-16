# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import msgspec


class BaseStruct(msgspec.Struct):
    """Base msgspec struct."""


class CamelizedBaseStruct(BaseStruct, rename="camel"):
    """Camelized Base Struct"""
