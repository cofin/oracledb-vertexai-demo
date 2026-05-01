# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""System domain controllers."""

from litestar import Controller

from app.domain.system.controllers._explore import ExploreController
from app.domain.system.controllers._metrics import MetricsController
from app.domain.system.controllers._system import SystemController

controllers: list[type[Controller]] = [ExploreController, MetricsController, SystemController]

__all__ = ("ExploreController", "MetricsController", "SystemController", "controllers")
