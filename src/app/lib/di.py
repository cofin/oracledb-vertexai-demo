# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Dependency injection re-exports."""

from dishka.integrations.litestar import DishkaRouter as LitestarRouter
from dishka.integrations.litestar import FromDishka as Inject
from dishka.integrations.litestar import LitestarProvider, setup_dishka

__all__ = ("Inject", "LitestarProvider", "LitestarRouter", "setup_dishka")
