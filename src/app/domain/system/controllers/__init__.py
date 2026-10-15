# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""System domain controllers."""

from litestar_security import PublicController

from app.domain.system.controllers._metrics import MetricsController
from app.domain.system.controllers._system import SystemController

controllers: list[type[PublicController]] = [MetricsController, SystemController]

__all__ = ("MetricsController", "SystemController", "controllers")
