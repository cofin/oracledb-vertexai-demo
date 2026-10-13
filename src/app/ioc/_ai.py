# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Dishka provider for Google GenAI and native agent runtime singletons."""

import shutil
import ssl
import subprocess  # ruff: ignore[suspicious-subprocess-import]
from datetime import UTC, datetime, timedelta
from typing import Any

import google.auth
import httpx
from dishka import Provider, Scope, provide
from google.auth.credentials import Credentials
from google.auth.exceptions import GoogleAuthError, RefreshError
from google.auth.transport import mtls
from google.genai import Client, types

import app.ioc as _ioc_pkg
from app.domain.ai.runtime import AgentRuntime, GeminiModelClient, OracleEventStore, OracleSessionStore, SpecTree
from app.domain.ai.services import get_coffee_spec_tree
from app.domain.chat.exceptions import AIServiceUnconfigured
from app.domain.system.services import PersonaManager

__all__ = ("DEFAULT_RETRY", "AIProvider", "IntegrationsProvider")

_PLACEHOLDER_VALUES = frozenset({"", "demo-project", "your-project-id", "placeholder", "your-api-key"})
_CLOUD_PLATFORM_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

DEFAULT_RETRY = types.HttpRetryOptions(
    attempts=4,
    initial_delay=1.0,
    max_delay=8.0,
    exp_base=2.0,
    jitter=0.2,
    http_status_codes=[408, 429, 500, 502, 503, 504],
)


class AIProvider(Provider):
    """APP-scoped singletons for external AI integrations and native runtime stores."""

    @provide(scope=Scope.APP)
    def provide_genai_client(self) -> Client:
        """Provide a configured Google GenAI client or raise 503 AIServiceUnconfigured."""
        settings = _ioc_pkg.get_settings()
        project_id = (settings.ai.project_id or "").strip()
        api_key = (settings.ai.api_key or "").strip()
        if project_id and project_id.lower() not in _PLACEHOLDER_VALUES:
            location = settings.ai.resolve_location(settings.ai.gcp_region)
            credentials = _VertexFallbackCredentials(quota_project_id=project_id)
            http_options = _build_vertex_http_options(location)
            return Client(
                vertexai=True, project=project_id, location=location, credentials=credentials, http_options=http_options
            )
        if api_key and api_key.lower() not in _PLACEHOLDER_VALUES:
            http_options = types.HttpOptions(
                client_args={"transport": httpx.HTTPTransport()},
                async_client_args={"transport": httpx.AsyncHTTPTransport()},
                retry_options=DEFAULT_RETRY,
            )
            return Client(api_key=api_key, http_options=http_options)
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


class _VertexFallbackCredentials(Credentials):
    """Credentials adapter that falls back to ``gcloud`` ADC token minting on mTLS workstations."""

    def __init__(self, wrapped: Credentials | None = None, *, quota_project_id: str | None = None) -> None:
        super().__init__()  # type: ignore[no-untyped-call]
        self._wrapped = wrapped
        self._quota_project_id = quota_project_id or (wrapped.quota_project_id if wrapped is not None else None)
        self._prefer_gcloud = False
        if wrapped is not None:
            self.token = wrapped.token
            self.expiry = wrapped.expiry

    def refresh(self, request: Any) -> None:
        """Refresh the access token via ``google-auth`` or fall back to ``gcloud`` CLI."""
        if not self._prefer_gcloud:
            try:
                if self._wrapped is None:
                    creds, _ = google.auth.default(
                        scopes=_CLOUD_PLATFORM_SCOPES, quota_project_id=self._quota_project_id
                    )
                    self._wrapped = creds
                self._wrapped.refresh(request)  # type: ignore[no-untyped-call]
            except GoogleAuthError:
                self._prefer_gcloud = True
            else:
                self.token = self._wrapped.token
                self.expiry = self._wrapped.expiry
                if self.token:
                    return
                self._prefer_gcloud = True

        self.token = _mint_gcloud_adc_access_token()
        self.expiry = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=50)


def _mint_gcloud_adc_access_token() -> str:
    """Mint an ADC access token via ``gcloud auth application-default print-access-token``."""
    gcloud_bin = shutil.which("gcloud")
    if not gcloud_bin:
        msg = "Unable to refresh Google Cloud credentials and 'gcloud' CLI is not installed."
        raise RefreshError(msg)  # type: ignore[no-untyped-call]
    try:
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [gcloud_bin, "auth", "application-default", "print-access-token"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        msg = f"Failed to refresh Google Cloud ADC token via gcloud: {exc}"
        raise RefreshError(msg) from exc  # type: ignore[no-untyped-call]
    token = completed.stdout.strip()
    if not token:
        msg = "gcloud auth application-default print-access-token returned an empty token."
        raise RefreshError(msg)  # type: ignore[no-untyped-call]
    return token


def _resolve_vertex_mtls_ssl_context() -> ssl.SSLContext | None:
    """Return a client-certificate SSLContext when Context-Aware Access mTLS is active."""
    try:
        if not mtls.should_use_client_cert() or not mtls.has_default_client_cert_source():  # type: ignore[no-untyped-call]
            return None
        ctx = mtls.get_default_ssl_context()
    except Exception:
        return None
    return ctx if isinstance(ctx, ssl.SSLContext) else None


def _build_vertex_http_options(location: str) -> types.HttpOptions:
    """Construct httpx transport and retry options, routing to mTLS endpoints when required."""
    mtls_ctx = _resolve_vertex_mtls_ssl_context()
    if mtls_ctx is not None:
        base_url = (
            "https://aiplatform.mtls.googleapis.com/"
            if location in {"global", "us", "eu"}
            else f"https://{location}-aiplatform.mtls.googleapis.com/"
        )
        return types.HttpOptions(
            base_url=base_url,
            client_args={"transport": httpx.HTTPTransport(verify=mtls_ctx)},
            async_client_args={"transport": httpx.AsyncHTTPTransport(verify=mtls_ctx)},
            retry_options=DEFAULT_RETRY,
        )
    return types.HttpOptions(
        client_args={"transport": httpx.HTTPTransport()},
        async_client_args={"transport": httpx.AsyncHTTPTransport()},
        retry_options=DEFAULT_RETRY,
    )
