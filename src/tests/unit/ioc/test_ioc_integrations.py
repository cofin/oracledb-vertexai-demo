# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for `AIProvider` and `DomainServiceProvider` runtime wiring."""

from __future__ import annotations

import ssl
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from google.auth.exceptions import RefreshError

from app.domain.ai.runtime import AgentRuntime, AgentStreamService, GeminiModelClient, SpecTree
from app.domain.chat.services import GroundedRouteService
from app.domain.system.services import PersonaManager
from app.ioc import AIProvider, DomainServiceProvider
from app.ioc._ai import CredentialProtocol, _build_vertex_http_options, _VertexFallbackCredentials
from app.lib.settings import AISettings


def test_ai_provider_builds_model_client_from_injected_client_and_settings() -> None:
    """Verify AIProvider constructs a GeminiModelClient from Client and AISettings."""
    provider = AIProvider()
    sentinel_client = MagicMock()
    ai_settings = AISettings(chat_model="gemini-3.8-flash")

    model_client = provider.provide_model_client(sentinel_client, ai_settings)

    assert isinstance(model_client, GeminiModelClient)
    assert model_client._client is sentinel_client
    assert model_client._default_model == "gemini-3.8-flash"


def test_ai_provider_builds_agent_runtime_and_stream_service() -> None:
    """Verify AIProvider constructs AgentRuntime and APP-scoped AgentStreamService."""
    provider = AIProvider()
    sentinel_model_client = MagicMock(spec=GeminiModelClient)

    runtime = provider.provide_agent_runtime(sentinel_model_client)
    stream_service = provider.provide_agent_stream_service()

    assert isinstance(runtime, AgentRuntime)
    assert runtime._model_client is sentinel_model_client
    assert isinstance(stream_service, AgentStreamService)


def test_ai_provider_builds_spec_tree_with_grounded_tools() -> None:
    """Verify AIProvider provides a SpecTree with 5 grounded coffee tools."""
    provider = AIProvider()
    spec_tree = provider.provide_spec_tree()

    assert isinstance(spec_tree, SpecTree)
    assert spec_tree.root.name == "coffee_barista"
    assert len(spec_tree.root.tools) == 5


def test_ai_provider_builds_persona_manager() -> None:
    """Verify AIProvider provides PersonaManager."""
    provider = AIProvider()
    persona_manager = provider.provide_persona_manager()

    assert isinstance(persona_manager, PersonaManager)


def test_domain_service_provider_builds_grounded_route_service() -> None:
    """Verify DomainServiceProvider constructs GroundedRouteService from request services."""
    provider = DomainServiceProvider()
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


def test_vertex_fallback_credentials_satisfies_protocol_and_prefers_google_auth() -> None:
    """Verify _VertexFallbackCredentials satisfies CredentialProtocol and prefers wrapped google-auth credentials."""
    wrapped = MagicMock()
    wrapped.quota_project_id = "cymbal-coffee-test"
    wrapped.token = "initial-access-value"
    wrapped.expiry = None

    def _refresh(_request: object) -> None:
        wrapped.token = "refreshed-via-google-auth"

    wrapped.refresh.side_effect = _refresh
    creds = _VertexFallbackCredentials(wrapped, quota_project_id="cymbal-coffee-test")
    assert isinstance(creds, CredentialProtocol)
    creds.refresh(object())

    assert creds.token == "refreshed-via-google-auth"
    assert creds.quota_project_id == "cymbal-coffee-test"
    assert creds._prefer_gcloud is False


def test_vertex_fallback_credentials_falls_back_to_gcloud_on_refresh_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify _VertexFallbackCredentials falls back to gcloud ADC token minting when google-auth refresh fails."""
    wrapped = MagicMock()
    wrapped.quota_project_id = "cymbal-coffee-test"
    wrapped.token = None
    wrapped.expiry = None
    wrapped.refresh.side_effect = RefreshError("access_denied: Account restricted")  # type: ignore[no-untyped-call]

    monkeypatch.setattr("app.ioc._ai.shutil.which", lambda _cmd: "/usr/bin/gcloud")
    monkeypatch.setattr(
        "app.ioc._ai.subprocess.run", lambda *_args, **_kwargs: SimpleNamespace(stdout="gcloud-minted-value\n")
    )

    creds = _VertexFallbackCredentials(wrapped, quota_project_id="cymbal-coffee-test")
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
