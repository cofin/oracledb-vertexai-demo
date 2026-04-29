# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Chat domain controllers."""

from litestar import Controller

from app.domain.chat.controllers._chat import CoffeeChatController

controllers: list[type[Controller]] = [CoffeeChatController]

__all__ = ("CoffeeChatController", "controllers")
