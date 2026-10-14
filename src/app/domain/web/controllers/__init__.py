# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Web domain controllers — page-level Jinja renderers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.web.controllers._pages import PageController

if TYPE_CHECKING:
    from litestar_security import PublicController

__all__ = ("PageController", "controllers")

controllers: list[type[PublicController]] = [PageController]
