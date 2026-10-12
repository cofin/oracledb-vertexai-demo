# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for ``IntegrationsProvider`` and ``DomainServiceProvider`` runtime wiring."""

from __future__ import annotations

from unittest.mock import MagicMock

import app.ioc as ioc_module
from app.domain.ai.runtime import AgentRuntime, GeminiModelClient, SpecTree
from app.domain.chat.services import GroundedRouteService
from app.domain.system.services import PersonaManager


def test_integrations_provider_builds_model_client_from_injected_client() -> None:
    """Verify IntegrationsProvider constructs a GeminiModelClient from Client."""
    provider = ioc_module.IntegrationsProvider()
    sentinel_client = MagicMock()

    model_client = provider.provide_model_client(sentinel_client)

    assert isinstance(model_client, GeminiModelClient)
    assert model_client._client is sentinel_client


def test_integrations_provider_builds_agent_runtime_from_model_client() -> None:
    """Verify IntegrationsProvider constructs AgentRuntime with the model client."""
    provider = ioc_module.IntegrationsProvider()
    sentinel_model_client = MagicMock(spec=GeminiModelClient)

    runtime = provider.provide_agent_runtime(sentinel_model_client)

    assert isinstance(runtime, AgentRuntime)
    assert runtime._model_client is sentinel_model_client


def test_integrations_provider_builds_spec_tree_with_grounded_tools() -> None:
    """Verify IntegrationsProvider provides a SpecTree with 5 grounded coffee tools."""
    provider = ioc_module.IntegrationsProvider()
    spec_tree = provider.provide_spec_tree()

    assert isinstance(spec_tree, SpecTree)
    assert spec_tree.root.name == "coffee_barista"
    assert len(spec_tree.root.tools) == 5


def test_integrations_provider_builds_persona_manager() -> None:
    """Verify IntegrationsProvider provides PersonaManager."""
    provider = ioc_module.IntegrationsProvider()
    persona_manager = provider.provide_persona_manager()

    assert isinstance(persona_manager, PersonaManager)


def test_domain_service_provider_builds_grounded_route_service() -> None:
    """Verify DomainServiceProvider constructs GroundedRouteService from request services."""
    provider = ioc_module.DomainServiceProvider()
    product_service = MagicMock()
    store_service = MagicMock()
    vertex_ai_service = MagicMock()

    grounded = provider.provide_grounded_route_service(
        product_service=product_service,
        store_service=store_service,
        vertex_ai_service=vertex_ai_service,
    )

    assert isinstance(grounded, GroundedRouteService)
    assert grounded.product_service is product_service
    assert grounded.store_service is store_service
    assert grounded.vertex_ai_service is vertex_ai_service
