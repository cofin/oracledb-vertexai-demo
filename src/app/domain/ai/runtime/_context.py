# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Request-scoped invocation context and typed tool context for agent tool execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domain.chat.schemas import HybridTurnContext
    from app.domain.products.services import ProductService, StoreService, VertexAIService
    from app.domain.system.services import MetricsService

__all__ = ("CallContext", "CoffeeToolContext")


@dataclass(slots=True)
class CoffeeToolContext:
    """Typed request-scoped services and hybrid turn context bound for agent tools."""

    product_service: ProductService | None = None
    store_service: StoreService | None = None
    vertex_ai_service: VertexAIService | None = None
    metrics_service: MetricsService | None = None
    turn_context: HybridTurnContext | None = None


@dataclass(slots=True)
class CallContext:
    """Execution context passed into tool invocations."""

    session_id: str
    invocation_id: str
    turn: int
    state: dict[str, Any] = field(default_factory=dict)
    services: Any = None

    @property
    def tool_context(self) -> CoffeeToolContext:
        """Typed CoffeeToolContext bound on this CallContext."""
        if isinstance(self.services, CoffeeToolContext):
            return self.services
        return CoffeeToolContext()
