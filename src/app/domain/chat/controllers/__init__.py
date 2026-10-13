# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Chat domain controllers."""

from litestar_security import PublicController

from app.domain.chat.controllers._chat import CoffeeChatController

controllers: list[type[PublicController]] = [CoffeeChatController]

__all__ = ("CoffeeChatController", "controllers")
