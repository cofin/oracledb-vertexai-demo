# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for `IntegrationsProvider` and `DomainServiceProvider` runtime wiring."""

from __future__ import annotations

import ssl
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from google.auth.exceptions import RefreshError

import app.ioc as ioc_module
from app.domain.ai.runtime import AgentRuntime, GeminiModelClient, SpecTree
from app.domain.chat.services import GroundedRouteService
from app.domain.system.services import PersonaManager
from app.ioc._ai import _build_vertex_http_options, _VertexFallbackCredentials


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
        product_service=product_service, store_service=store_service, vertex_ai_service=vertex_ai_service
    )

    assert isinstance(grounded, GroundedRouteService)
    assert grounded.product_service is product_service
    assert grounded.store_service is store_service
    assert grounded.vertex_ai_service is vertex_ai_service


def test_vertex_fallback_credentials_prefers_standard_google_auth() -> None:
    """Verify _VertexFallbackCredentials uses wrapped google-auth credentials when refresh succeeds."""
    wrapped = MagicMock()
    wrapped.quota_project_id = "db-black-belts-playground-01"
    wrapped.token = "initial-access-value"
    wrapped.expiry = None

    def _refresh(_request: object) -> None:
        wrapped.token = "refreshed-via-google-auth"

    wrapped.refresh.side_effect = _refresh
    creds = _VertexFallbackCredentials(wrapped, quota_project_id="db-black-belts-playground-01")
    creds.refresh(object())

    assert creds.token == "refreshed-via-google-auth"
    assert creds.quota_project_id == "db-black-belts-playground-01"
    assert creds._prefer_gcloud is False


def test_vertex_fallback_credentials_falls_back_to_gcloud_on_refresh_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify _VertexFallbackCredentials falls back to gcloud ADC token minting when google-auth refresh fails."""
    wrapped = MagicMock()
    wrapped.quota_project_id = "db-black-belts-playground-01"
    wrapped.token = None
    wrapped.expiry = None
    wrapped.refresh.side_effect = RefreshError("access_denied: Account restricted")  # type: ignore[no-untyped-call]

    monkeypatch.setattr("app.ioc._ai.shutil.which", lambda _cmd: "/usr/bin/gcloud")
    monkeypatch.setattr(
        "app.ioc._ai.subprocess.run", lambda *_args, **_kwargs: SimpleNamespace(stdout="gcloud-minted-value\n")
    )

    creds = _VertexFallbackCredentials(wrapped, quota_project_id="db-black-belts-playground-01")
    creds.refresh(object())

    assert creds.token == "gcloud-minted-value"
    assert creds.expiry is not None
    assert creds._prefer_gcloud is True
    assert creds.valid is True


def test_build_vertex_http_options_uses_mtls_endpoint_when_client_cert_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify _build_vertex_http_options configures mTLS base_url when client certs are active."""
    ctx = ssl.create_default_context()
    monkeypatch.setattr("app.ioc._ai._resolve_vertex_mtls_ssl_context", lambda: ctx)

    global_opts = _build_vertex_http_options("global")
    regional_opts = _build_vertex_http_options("us-central1")

    assert global_opts.base_url == "https://aiplatform.mtls.googleapis.com/"
    assert regional_opts.base_url == "https://us-central1-aiplatform.mtls.googleapis.com/"

    monkeypatch.setattr("app.ioc._ai._resolve_vertex_mtls_ssl_context", lambda: None)
    standard_opts = _build_vertex_http_options("global")
    assert standard_opts.base_url is None
