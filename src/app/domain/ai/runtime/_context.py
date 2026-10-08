# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Request-scoped invocation context and registry for tool execution."""

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

__all__ = ("CallContext", "RunContextRegistry")


@dataclass(slots=True)
class CallContext:
    """Execution context passed into tool invocations."""

    session_id: str
    invocation_id: str
    turn: int
    state: dict[str, Any] = field(default_factory=dict)
    services: Any = None


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
