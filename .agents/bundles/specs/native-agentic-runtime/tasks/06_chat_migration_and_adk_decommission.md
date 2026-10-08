---
type: Task
id: task-6
flow_id: native-agentic-runtime
state: closed
title: Migrate Chat Controller to Domain AI, Wire Dishka DI, and Decommission Google ADK
description: Update chat controller to consume AgentOrchestrationService, configure Dishka providers in ioc.py, delete legacy ADK services, remove google-adk dependency, and validate integration suite.
verification_strategy: integration_acceptance
depends_on:
  - task-1
  - task-2
  - task-3
  - task-4
  - task-5
commit: null
tags:
  - task
  - chat-migration
  - dishka-di
  - adk-decommission
  - integration
---

# Task task-6: Migrate Chat Controller to Domain AI, Wire Dishka DI, and Decommission Google ADK

## Objective
Migrate `src/app/domain/chat/controllers/_chat.py` and `src/app/domain/web/controllers/_pages.py` to consume `AgentOrchestrationService` and `AgentStreamService` from `src/app/domain/ai/`, wire `SecurityPlugin` (`litestar-security>=0.6.0`) with hardened headers, wire `OpenTelemetryPlugin` (`litestar[opentelemetry]`) enabled by default, adopt `PublicController` across controllers, wire all native runtime providers into `src/app/ioc.py`, remove the `adk` extra from `sqlspec` in `pyproject.toml`, decommission legacy ADK modules, and verify the entire end-to-end integration and test suite.

## Itemized Checklist
- [x] Add `"litestar-security>=0.6.0"` and `"litestar[cryptography,jinja,jwt,opentelemetry,structlog]"` to `dependencies` in `pyproject.toml` and remove `adk` extra from `sqlspec[mypyc,oracledb,performance]`. Run `uv sync`.
- [x] Mount `OpenTelemetryPlugin` (enabled by default) and `SecurityPlugin` in `src/app/server/plugins.py`:
  - Configure `OpenTelemetryConfig(exclude=settings.otel.EXCLUDE_PATHS)`.
  - Configure `SecurityConfig(headers=SecurityHeadersConfig.hardened(), exclude=[r"^/static", r"^/favicon\.ico"])`.
  - Add `"security"` and `"opentelemetry"` to `lazy_names`.
- [x] Update `src/app/server/core.py`:
  - Extend `app_config.plugins` with `plugins.security` and `plugins.opentelemetry`.
  - Remove manual `app_config.middleware.append(config.session_config.middleware)`.
  - Remove manual `app_config.csrf_config = config.csrf`.
- [x] Subclass `PublicController` across domain controllers:
  - `src/app/domain/chat/controllers/_chat.py` (`CoffeeChatController(PublicController)`).
  - `src/app/domain/web/controllers/_pages.py` (`PageController(PublicController)`), removing `exclude_from_auth=True`.
  - `src/app/domain/products/controllers/_products.py` (`ProductController(PublicController)`, `StoreController(PublicController)`).
  - `src/app/domain/products/controllers/_vector.py` (`VectorSearchController(PublicController)`).
  - `src/app/domain/system/controllers/_system.py` (`SystemController(PublicController)`).
  - `src/app/domain/system/controllers/_metrics.py` (`MetricsController(PublicController)`).
- [x] Update `src/app/ioc.py` to remove ADK providers (`provide_adk_store`, `provide_session_service`, `provide_adk_runner`) and register `GeminiModelClient`, `AgentRuntime`, `SpecTree`, `OracleSessionStore`, `OracleEventStore` (`Scope.APP`), and `AgentOrchestrationService`, `AgentStreamService` (`Scope.REQUEST`).
- [x] Refactor `src/app/domain/chat/controllers/_chat.py` to inject `orchestrator: Inject[AgentOrchestrationService]` and stream normalized SSE frames.
- [x] Update `src/app/domain/web/controllers/_pages.py` to inject `orchestrator: Inject[AgentOrchestrationService]` and retrieve chat history via `orchestrator.get_display_history()`.
- [x] Update `src/app/domain/chat/services/__init__.py` to remove ADK exports and retain `FlashLiteIntentClassifier`.
- [x] Delete legacy ADK implementation modules:
  - `src/app/domain/chat/services/adk.py`
  - `src/app/domain/chat/services/workflow.py`
  - `src/app/domain/chat/services/_adk_grounding.py`
  - `src/app/domain/chat/services/_adk_support.py`
- [x] Delete legacy ADK unit tests:
  - `src/tests/unit/app/domain/chat/services/test_adk.py`
  - `src/tests/unit/app/domain/chat/services/test_adk_grounding.py`
  - `src/tests/unit/app/domain/chat/services/test_workflow.py`
- [x] Rewrite `src/tests/integration/app/domain/chat/controllers/test_chat_http.py` to verify SSE streaming, session reset, and error handling against `AgentOrchestrationService` with `SecurityPlugin` and `OpenTelemetryPlugin` active.
- [x] Run full verification suite (`uv run pytest src/tests/unit`, `uv run pytest src/tests/integration/app/domain/chat/`, and `make lint`).

## Implementation Details & Code Samples

### 1. `src/app/ioc.py`
Replace ADK imports and providers in `src/app/ioc.py`:
```python
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Dishka container configuration for Litestar.

Three providers:
- LitestarPersistenceProvider: APP-scoped Oracle config + REQUEST-scoped driver.
- IntegrationsProvider: APP-scoped external integrations (genai client, AI runtime, stores).
- DomainServiceProvider: REQUEST-scoped domain services that depend on the per-request driver.

NOTE: Dishka introspects @provide method annotations at runtime; this module must NOT use
`from __future__ import annotations`.
"""

import sys
from collections.abc import AsyncIterator

from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from google.genai import Client
from sqlspec.adapters.oracledb import OracleAsyncConfig, OracleAsyncDriver

from app.domain.ai.runtime import (
    AgentRuntime,
    AgentStreamService,
    GeminiModelClient,
    OracleEventStore,
    OracleSessionStore,
    SpecTree,
)
from app.domain.ai.services import AgentOrchestrationService, get_coffee_spec_tree
from app.domain.chat.services.classifier import FlashLiteIntentClassifier
from app.domain.products.services.services import (
    OracleVectorSearchService,
    ProductService,
    StoreService,
    VertexAIService,
)
from app.domain.system.services.services import CacheService, MetricsService, PersonaManager
from app.lib.settings import get_settings


class LitestarPersistenceProvider(Provider):
    """Oracle config (APP) + per-request driver (REQUEST)."""

    @provide(scope=Scope.APP)
    def provide_config(self) -> OracleAsyncConfig:
        from app import config

        return config.db

    @provide(scope=Scope.REQUEST)
    async def provide_driver(self) -> AsyncIterator[OracleAsyncDriver]:
        """Provide per-request OracleAsyncDriver."""
        from app import config

        session_context = config.db_manager.provide_session(config.db)
        driver = await session_context.__aenter__()
        try:
            yield driver
        except BaseException:
            await session_context.__aexit__(*sys.exc_info())
            raise
        else:
            await session_context.__aexit__(None, None, None)


class IntegrationsProvider(Provider):
    """APP-scoped singletons for external integrations."""

    @provide(scope=Scope.APP)
    def provide_genai_client(self) -> Client:
        settings = get_settings()
        if settings.ai.project_id:
            return Client(vertexai=True, project=settings.ai.project_id, location=settings.ai.location)
        return Client(api_key=settings.ai.api_key)

    @provide(scope=Scope.APP)
    def provide_model_client(self, client: Client) -> GeminiModelClient:
        settings = get_settings()
        return GeminiModelClient(client=client, default_model=settings.ai.chat_model)

    @provide(scope=Scope.APP)
    def provide_agent_runtime(self, model_client: GeminiModelClient) -> AgentRuntime:
        return AgentRuntime(model_client=model_client)

    @provide(scope=Scope.APP)
    def provide_spec_tree(self) -> SpecTree:
        return get_coffee_spec_tree()

    @provide(scope=Scope.APP)
    def provide_oracle_stores(self, config: OracleAsyncConfig) -> tuple[OracleSessionStore, OracleEventStore]:
        return OracleSessionStore(config=config), OracleEventStore(config=config)

    @provide(scope=Scope.APP)
    def provide_session_store(self, stores: tuple[OracleSessionStore, OracleEventStore]) -> OracleSessionStore:
        return stores[0]

    @provide(scope=Scope.APP)
    def provide_event_store(self, stores: tuple[OracleSessionStore, OracleEventStore]) -> OracleEventStore:
        return stores[1]

    @provide(scope=Scope.APP)
    def provide_intent_classifier(self, client: Client) -> FlashLiteIntentClassifier:
        return FlashLiteIntentClassifier(client, model=get_settings().ai.intent_model)

    @provide(scope=Scope.APP)
    def provide_persona_manager(self) -> PersonaManager:
        return PersonaManager()


class DomainServiceProvider(Provider):
    """REQUEST-scoped domain services."""

    scope = Scope.REQUEST

    product_service = provide(ProductService)
    store_service = provide(StoreService)
    cache_service = provide(CacheService)
    metrics_service = provide(MetricsService)

    agent_stream_service = provide(AgentStreamService)
    agent_orchestration_service = provide(AgentOrchestrationService)

    @provide
    def provide_vertex_ai_service(self, client: Client, cache_service: CacheService) -> VertexAIService:
        settings = get_settings()
        return VertexAIService(
            client=client,
            model=settings.ai.chat_model,
            embedding_model=settings.ai.embedding_model,
            embedding_dimensions=settings.ai.embedding_dimensions,
            cache_service=cache_service,
        )

    @provide
    def provide_vector_search_service(
        self, vertex_ai_service: VertexAIService, product_service: ProductService
    ) -> OracleVectorSearchService:
        return OracleVectorSearchService(vertex_ai_service=vertex_ai_service, product_service=product_service)


PROVIDERS: tuple[type[Provider], ...] = (LitestarPersistenceProvider, IntegrationsProvider, DomainServiceProvider)


def make_container(*extra_providers: Provider) -> AsyncContainer:
    """Build the Dishka container with the three user providers plus any extras."""
    return make_async_container(*extra_providers, *(P() for P in PROVIDERS))


__all__ = (
    "PROVIDERS",
    "DomainServiceProvider",
    "IntegrationsProvider",
    "LitestarPersistenceProvider",
    "make_container",
)
```

### 2. `src/app/domain/chat/controllers/_chat.py`
Refactor `CoffeeChatController` to consume `AgentOrchestrationService` and inherit from `PublicController`:
```python
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Coffee chat controller for streaming agent conversations and session resets."""

import re
from collections.abc import AsyncIterator

import structlog
from litestar import post
from litestar.exceptions import ValidationException
from litestar.response import ServerSentEvent
from litestar_htmx import HTMXRequest
from litestar_security import PublicController

from app.domain.ai.services import AgentOrchestrationService
from app.domain.chat.controllers._helpers import chat_form_from_request, location_context_from_form
from app.domain.chat.session import adk_session_identity, clear_adk_session_identity
from app.lib.di import Inject
from app.utils.serialization import to_json

logger = structlog.get_logger()
_STREAM_ERROR_MESSAGE = "Chat failed while streaming. Please try again."


class CoffeeChatController(PublicController):
    """Coffee chat API controller — JSON for SPA clients, HTML partials for HTMX."""

    @staticmethod
    def validate_message(message: str) -> str:
        """Validate and sanitize user message input."""
        message = re.sub(r"<[^>]+>", "", message)
        max_length = 500
        if len(message) > max_length:
            message = message[:max_length]
        message = message.replace("\x00", "").strip()

        if not message:
            raise ValidationException(detail="Message cannot be empty")

        return message

    @staticmethod
    def validate_persona(persona: str) -> str:
        """Validate persona input."""
        if persona not in {"barista", "snob", "scientist", "wellness"}:
            return "barista"
        return persona

    @post(path="/api/chat/stream", name="chat.api.stream")
    async def stream_chat_message(
        self,
        orchestrator: Inject[AgentOrchestrationService],
        request: HTMXRequest,
    ) -> ServerSentEvent:
        """Stream chat response events for the browser chat UI."""
        data = await chat_form_from_request(request)
        clean_message = self.validate_message(data.message)
        validated_persona = self.validate_persona(data.persona)
        location_context = location_context_from_form(data)
        user_id, session_id = adk_session_identity(request)

        dynamic_context = (
            f"Persona: {validated_persona}\nLocation Context: {location_context}"
            if location_context
            else f"Persona: {validated_persona}"
        )

        async def stream_events() -> AsyncIterator[dict[str, str]]:
            try:
                async for frame in orchestrator.stream_conversation_turn(
                    session_id=session_id,
                    user_id=user_id,
                    message=clean_message,
                    services=request,
                    dynamic_context=dynamic_context,
                ):
                    frame_type = str(frame.get("type", "message"))
                    yield {"event": frame_type, "data": to_json(frame, as_bytes=False)}
            except Exception as exc:
                await logger.aexception(
                    "Chat stream failed after response started",
                    error_type=type(exc).__name__,
                    detail=str(exc),
                )
                yield {
                    "event": "error",
                    "data": to_json({"type": "error", "message": _STREAM_ERROR_MESSAGE}, as_bytes=False),
                }

        return ServerSentEvent(stream_events(), status_code=200)

    @post(path="/api/chat/session/clear", name="chat.api.clear_session", status_code=200)
    async def clear_chat_session(
        self,
        orchestrator: Inject[AgentOrchestrationService],
        request: HTMXRequest,
    ) -> dict[str, str]:
        """Clear the anonymous browser's agent chat session."""
        user_id, session_id = adk_session_identity(request)
        await orchestrator.clear_session(session_id=session_id, user_id=user_id)
        clear_adk_session_identity(request)
        return {"status": "cleared"}
```

### 3. `src/app/domain/web/controllers/_pages.py`
Update `PageController` to inherit from `PublicController` and eliminate `exclude_from_auth=True`:
```python
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Page-level routes for the HTMX frontend."""

from typing import Annotated

import structlog
from litestar import get
from litestar.params import QueryParameter
from litestar.response import Template
from litestar_htmx import HTMXRequest
from litestar_security import PublicController

from app.domain.ai.services import AgentOrchestrationService
from app.domain.chat.session import adk_session_identity
from app.domain.products.services import StoreService
from app.lib.di import Inject

logger = structlog.get_logger()


class PageController(PublicController):
    """Server-rendered page routes for chat and explore."""

    @get(path="/", name="pages.chat", include_in_schema=False)
    async def chat_page(
        self,
        request: HTMXRequest,
        orchestrator: Inject[AgentOrchestrationService],
    ) -> Template:
        """Render the primary coffee chat landing page with session history."""
        user_id, session_id = adk_session_identity(request)
        history_messages = await orchestrator.get_display_history(session_id=session_id, user_id=user_id)
        return Template(template_name="pages/chat.html.j2", context={"history_messages": history_messages})

    @get(path="/explore", name="pages.explore", include_in_schema=False)
    async def explore_page(
        self,
        stores_service: Inject[StoreService],
        search_query: Annotated[str | None, QueryParameter(name="query")] = None,
    ) -> Template:
        """Render the explore and vector search page."""
        try:
            stores = await stores_service.get_all_stores()
        except Exception as exc:
            await logger.awarning("Store inventory selector unavailable", error_type=type(exc).__name__)
            stores = []
        return Template(template_name="pages/explore.html.j2", context={"query": search_query or "", "stores": stores})
```

### 4. `src/app/server/plugins.py` & `src/app/server/core.py`
### 4. `src/app/server/plugins.py` & `src/app/server/core.py`
Register `SecurityPlugin` with hardened headers and `OpenTelemetryPlugin` enabled by default:
```python
# In src/app/server/plugins.py:
from litestar.plugins.opentelemetry import OpenTelemetryConfig as _OpenTelemetryConfig
from litestar.plugins.opentelemetry import OpenTelemetryPlugin as _OpenTelemetryPlugin
from litestar_security import SecurityConfig as _SecurityConfig
from litestar_security import SecurityHeadersConfig as _SecurityHeadersConfig
from litestar_security import SecurityPlugin as _SecurityPlugin

# In _initialize():
g["security"] = _SecurityPlugin(
    config=_SecurityConfig(
        headers=_SecurityHeadersConfig.hardened(),
        exclude=[r"^/static", r"^/favicon\.ico"],
    )
)
if settings.otel.ENABLED:
    g["opentelemetry"] = _OpenTelemetryPlugin(
        config=_OpenTelemetryConfig(
            exclude=settings.otel.EXCLUDE_PATHS,
        )
    )

# In src/app/server/core.py:
app_plugins = [
    plugins.granian,
    plugins.db,
    plugins.structlog,
    plugins.problem_details,
    plugins.security,
    plugins.vite,
    plugins.htmx,
    plugins.flash,
    plugins.autowire,
]
if settings.otel.ENABLED:
    app_plugins.append(plugins.opentelemetry)
app_config.plugins.extend(app_plugins)
```

### 5. `src/app/domain/chat/services/__init__.py`
Update `src/app/domain/chat/services/__init__.py` to remove retired ADK exports:
```python
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Chat domain service package."""

from .classifier import INTENT_VALUES, FlashLiteIntentClassifier, IntentLabel

__all__ = (
    "INTENT_VALUES",
    "FlashLiteIntentClassifier",
    "IntentLabel",
)
```

### 6. `pyproject.toml`
Update dependency definition in `pyproject.toml`:
```toml
dependencies = [
    "litestar[cryptography,jinja,jwt,opentelemetry,structlog]",
    "litestar-granian[uvloop]",
    "litestar-mcp[a2a]>=0.14.0",
    "litestar-security>=0.6.0",
    "sqlspec[mypyc,oracledb,performance]",
    "numpy",
    "python-dotenv",
    "dishka",
    "litestar-vite",
    "litestar-autowire[dishka]>=0.2.0",
    "litestar-htmx>=0.5.0",
]
```
Followed by executing `uv sync` to refresh `uv.lock`.

### 7. Decommissioned Legacy ADK Files
Safely remove the following modules from Git and the filesystem:
```bash
git rm src/app/domain/chat/services/adk.py
git rm src/app/domain/chat/services/workflow.py
git rm src/app/domain/chat/services/_adk_grounding.py
git rm src/app/domain/chat/services/_adk_support.py
git rm src/tests/unit/app/domain/chat/services/test_adk.py
git rm src/tests/unit/app/domain/chat/services/test_adk_grounding.py
git rm src/tests/unit/app/domain/chat/services/test_workflow.py
```

### 8. `src/tests/integration/app/domain/chat/controllers/test_chat_http.py`
Rewrite integration acceptance tests against `AgentOrchestrationService`:
```python
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""The chat surface routes: POST /api/chat/stream and POST /api/chat/session/clear."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from litestar.testing import AsyncTestClient

pytestmark = [pytest.mark.anyio, pytest.mark.usefixtures("stub_orchestrator")]


@pytest.fixture
def stub_orchestrator(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub AgentOrchestrationService streaming and clearing for HTTP testing."""
    from app.domain.ai.services import AgentOrchestrationService

    async def _mock_stream(self: Any, *args: Any, **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        del self, args, kwargs
        yield {"type": "session", "session_id": "test-session-id"}
        yield {"type": "delta", "text": "A pour-over Ethiopian Yirgacheffe brews bright and floral."}
        yield {
            "type": "final",
            "session_id": "test-session-id",
            "search_metrics": {"prompt_tokens": 12, "output_tokens": 42, "total_tokens": 54},
        }

    async def _mock_clear(self: Any, *args: Any, **kwargs: Any) -> None:
        del self, args, kwargs

    monkeypatch.setattr(AgentOrchestrationService, "stream_conversation_turn", _mock_stream)
    monkeypatch.setattr(AgentOrchestrationService, "clear_session", _mock_clear)


async def test_stream_returns_sse_events(client: AsyncTestClient) -> None:
    """Verify that POST /api/chat/stream returns normalized SSE frames."""
    response = await client.post("/api/chat/stream", data={"message": "recommend an ethiopian", "persona": "barista"})

    assert response.status_code == 200, response.text[:500]
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: session" in response.text
    assert "event: delta" in response.text
    assert "event: final" in response.text
    assert "Ethiopian Yirgacheffe" in response.text


async def test_stream_handles_runtime_exception(
    client: AsyncTestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that stream errors yield an error SSE frame rather than HTTP 500."""
    from app.domain.ai.services import AgentOrchestrationService

    async def _failing_stream(self: Any, *args: Any, **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        del self, args, kwargs
        yield {"type": "delta", "text": "Starting"}
        raise RuntimeError("simulated model failure")

    monkeypatch.setattr(AgentOrchestrationService, "stream_conversation_turn", _failing_stream)

    response = await client.post("/api/chat/stream", data={"message": "recommend an ethiopian", "persona": "barista"})

    assert response.status_code == 200, response.text[:500]
    assert "event: delta" in response.text
    assert "event: error" in response.text
    assert "Chat failed while streaming. Please try again." in response.text


async def test_clear_chat_session(client: AsyncTestClient) -> None:
    """Verify POST /api/chat/session/clear succeeds and clears session identity."""
    response = await client.post("/api/chat/session/clear")
    assert response.status_code == 200
    assert response.json() == {"status": "cleared"}
```

## Verification
- Strategy: `integration_acceptance`
- Initial Evidence: Run `grep -rn "google\.adk" src/`
  - Expected: Returns occurrences of `google.adk` imports in `src/app/domain/chat/services/adk.py` and `src/app/domain/chat/services/workflow.py`.
- Final Evidence: Run `uv run pytest src/tests/integration/app/domain/chat/controllers/test_chat_http.py && uv run pytest src/tests/unit && make lint`
  - Expected: All integration and unit tests pass, `grep -rn "google\.adk" src/` returns 0 occurrences, and `make lint` is 100% clean.
