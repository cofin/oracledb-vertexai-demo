# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Dishka provider for Google GenAI and native agent runtime singletons."""

from dishka import Provider, Scope, provide
from google.genai import Client

import app.ioc as _ioc_pkg
from app.domain.ai.runtime import AgentRuntime, GeminiModelClient, OracleEventStore, OracleSessionStore, SpecTree
from app.domain.ai.services import get_coffee_spec_tree
from app.domain.chat.exceptions import AIServiceUnconfigured
from app.domain.system.services import PersonaManager

__all__ = (
    "AIProvider",
    "IntegrationsProvider",
)

_PLACEHOLDER_VALUES = frozenset({"", "demo-project", "your-project-id", "placeholder", "your-api-key"})


class AIProvider(Provider):
    """APP-scoped singletons for external AI integrations and native runtime stores."""

    @provide(scope=Scope.APP)
    def provide_genai_client(self) -> Client:
        """Provide a configured Google GenAI client or raise 503 AIServiceUnconfigured."""
        settings = _ioc_pkg.get_settings()
        project_id = (settings.ai.project_id or "").strip()
        api_key = (settings.ai.api_key or "").strip()
        if project_id and project_id.lower() not in _PLACEHOLDER_VALUES:
            return Client(vertexai=True, project=project_id, location=settings.ai.location)
        if api_key and api_key.lower() not in _PLACEHOLDER_VALUES:
            return Client(api_key=api_key)
        msg = "Vertex AI or Google GenAI credentials are not configured."
        raise AIServiceUnconfigured(msg)

    @provide(scope=Scope.APP)
    def provide_model_client(self, client: Client) -> GeminiModelClient:
        """Provide a GeminiModelClient bound to the configured chat model."""
        settings = _ioc_pkg.get_settings()
        return GeminiModelClient(client=client, default_model=settings.ai.chat_model)

    @provide(scope=Scope.APP)
    def provide_agent_runtime(self, model_client: GeminiModelClient) -> AgentRuntime:
        """Provide the re-entrant native AgentRuntime."""
        return AgentRuntime(model_client=model_client)

    @provide(scope=Scope.APP)
    def provide_spec_tree(self) -> SpecTree:
        """Provide the Cymbal Coffee agent SpecTree with grounded tools."""
        return get_coffee_spec_tree()

    @provide(scope=Scope.APP)
    def provide_persona_manager(self) -> PersonaManager:
        """Provide the chat PersonaManager singleton."""
        return PersonaManager()

    @provide(scope=Scope.APP)
    def provide_session_store(self) -> OracleSessionStore:
        """Provide the Oracle-backed agent session store."""
        return OracleSessionStore()

    @provide(scope=Scope.APP)
    def provide_event_store(self) -> OracleEventStore:
        """Provide the Oracle-backed agent event store."""
        return OracleEventStore()


IntegrationsProvider = AIProvider
