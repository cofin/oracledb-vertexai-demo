# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Request-scoped invocation context, typed tool context, and registry for tool execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from app.domain.chat.schemas import HybridTurnContext
    from app.domain.products.services import (
        EmbeddingService,
        InventoryService,
        MapsService,
        ProductService,
        StoreService,
        VertexAIService,
    )
    from app.domain.system.services import MetricsService

__all__ = (
    "CallContext",
    "CoffeeToolContext",
    "RunContextRegistry",
)


@dataclass(slots=True)
class CoffeeToolContext:
    """Typed request-scoped services and hybrid turn context bound for agent tools."""

    product_service: ProductService | None = None
    store_service: StoreService | None = None
    inventory_service: InventoryService | None = None
    maps_service: MapsService | None = None
    embedding_service: EmbeddingService | None = None
    vertex_ai_service: VertexAIService | None = None
    metrics_service: MetricsService | None = None
    turn_context: HybridTurnContext | None = None

    def __post_init__(self) -> None:
        if self.embedding_service is not None and self.vertex_ai_service is None:
            self.vertex_ai_service = self.embedding_service
        elif self.vertex_ai_service is not None and self.embedding_service is None:
            self.embedding_service = self.vertex_ai_service


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


class RunContextRegistry:
    """Token-based registry mapping single-turn tokens to CallContext."""

    def __init__(self) -> None:
        self._contexts: dict[str, CallContext] = {}

    def bind(self, context: CallContext) -> str:
        """Bind a CallContext and return an opaque token.

        Args:
            context: The CallContext to register.

        Returns:
            Opaque string token for subsequent retrieval.
        """
        token = uuid4().hex
        self._contexts[token] = context
        return token

    def resolve(self, token: str) -> CallContext:
        """Resolve a CallContext from an opaque token.

        Args:
            token: The token previously returned by bind.

        Returns:
            The associated CallContext.

        Raises:
            RuntimeError: If the token is missing or expired.
        """
        ctx = self._contexts.get(token)
        if ctx is None:
            msg = "Tool CallContext expired or missing"
            raise RuntimeError(msg)
        return ctx

    def release(self, token: str) -> None:
        """Release a bound token when the turn completes.

        Args:
            token: The token to remove.
        """
        self._contexts.pop(token, None)
