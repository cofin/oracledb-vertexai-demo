# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for security configuration, MCP/A2A API key auth, CSRF opt-in, and health routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from litestar.stores.memory import MemoryStore
from litestar.testing import AsyncTestClient
from litestar_autowire import clear_autowire_cache
from litestar_security import exclude

import app.config as app_config
from app.domain.chat.controllers import CoffeeChatController
from app.domain.products.controllers import VectorController
from app.lib import settings as app_settings
from app.server.asgi import create_app

if TYPE_CHECKING:
    from litestar import Litestar
    from pytest import MonkeyPatch

pytestmark = pytest.mark.anyio


def _mcp_headers(method: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"MCP-Protocol-Version": "2026-07-28", "Mcp-Method": method}
    if extra:
        headers.update(extra)
    return headers


def _mcp_params() -> dict[str, object]:
    return {
        "_meta": {
            "io.modelcontextprotocol/protocolVersion": "2026-07-28",
            "io.modelcontextprotocol/clientCapabilities": {},
        }
    }


async def test_health_endpoints_and_permissions_policy_header(test_settings: app_settings.Settings) -> None:
    """Verify GET /health and GET /api/system/health return 200 and Permissions-Policy header."""
    del test_settings
    clear_autowire_cache()
    litestar_app = create_app()
    litestar_app.stores._stores["sessions"] = MemoryStore()
    async with AsyncTestClient(app=litestar_app) as client:
        for path in ("/health", "/api/system/health"):
            response = await client.get(path)
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
            assert response.headers.get("permissions-policy") == "geolocation=(self)"


async def test_mcp_and_agent_card_public_when_mcp_api_key_unset(test_settings: app_settings.Settings) -> None:
    """Verify /mcp and /.well-known/agent-card.json are publicly accessible when MCP_API_KEY is unset."""
    del test_settings
    clear_autowire_cache()
    litestar_app = create_app()
    litestar_app.stores._stores["sessions"] = MemoryStore()
    async with AsyncTestClient(app=litestar_app) as client:
        card_resp = await client.get("/.well-known/agent-card.json")
        assert card_resp.status_code == 200
        assert card_resp.json()["name"] == "Cymbal Coffee Barista Agent"

        mcp_resp = await client.post(
            "/mcp",
            headers=_mcp_headers("prompts/list"),
            json={"jsonrpc": "2.0", "id": 1, "method": "prompts/list", "params": _mcp_params()},
        )
        assert mcp_resp.status_code == 200
        prompts = mcp_resp.json()["result"]["prompts"]
        assert any(p["name"] == "coffee/barista-recommendation" for p in prompts)


async def test_mcp_and_a2a_enforce_api_key_when_configured(
    monkeypatch: MonkeyPatch, test_settings: app_settings.Settings
) -> None:
    """Verify /mcp and /a2a reject missing/invalid X-API-Key and accept valid X-API-Key."""
    del test_settings
    clear_autowire_cache()
    monkeypatch.setenv("MCP_API_KEY", "super-secret-mcp-token")
    app_settings.Settings.from_env.cache_clear()
    fresh_settings = app_settings.Settings.from_env()
    monkeypatch.setattr(app_settings, "get_settings", lambda *_a, **_kw: fresh_settings)
    app_config._reset()

    secured_app: Litestar = create_app()
    secured_app.stores._stores["sessions"] = MemoryStore()
    async with AsyncTestClient(app=secured_app, raise_server_exceptions=False) as secured_client:
        unauth_mcp = await secured_client.post(
            "/mcp",
            headers=_mcp_headers("prompts/list"),
            json={"jsonrpc": "2.0", "id": 1, "method": "prompts/list", "params": _mcp_params()},
        )
        assert unauth_mcp.status_code in {401, 403}

        wrong_key_mcp = await secured_client.post(
            "/mcp",
            headers=_mcp_headers("prompts/list", {"X-API-Key": "wrong-token"}),
            json={"jsonrpc": "2.0", "id": 1, "method": "prompts/list", "params": _mcp_params()},
        )
        assert wrong_key_mcp.status_code in {401, 403}

        valid_mcp = await secured_client.post(
            "/mcp",
            headers=_mcp_headers("prompts/list", {"X-API-Key": "super-secret-mcp-token"}),
            json={"jsonrpc": "2.0", "id": 1, "method": "prompts/list", "params": _mcp_params()},
        )
        assert valid_mcp.status_code == 200
        prompts = valid_mcp.json()["result"]["prompts"]
        assert any(p["name"] == "coffee/barista-recommendation" for p in prompts)

        unauth_a2a = await secured_client.post(
            "/a2a", json={"jsonrpc": "2.0", "id": 1, "method": "tasks/get", "params": {"id": "t1"}}
        )
        assert unauth_a2a.status_code in {401, 403}

        card_resp = await secured_client.get("/.well-known/agent-card.json")
        assert card_resp.status_code == 200


async def test_chat_post_routes_enforce_csrf_when_debug_disabled(
    monkeypatch: MonkeyPatch, test_settings: app_settings.Settings
) -> None:
    """Verify CoffeeChatController POST handlers opt into CSRF and reject un-tokened POSTs when DEBUG=False."""
    del test_settings
    clear_autowire_cache()
    assert VectorController.auth == exclude()
    for handler in (
        CoffeeChatController.stream_chat_message,
        CoffeeChatController.clear_chat_session,
        VectorController.vector_search_demo,
    ):
        assert handler.opt.get("exclude_from_csrf") is False

    monkeypatch.setenv("LITESTAR_DEBUG", "false")
    app_settings.Settings.from_env.cache_clear()
    prod_settings = app_settings.Settings.from_env()
    monkeypatch.setattr(app_settings, "get_settings", lambda *_a, **_kw: prod_settings)
    app_config._reset()

    prod_app: Litestar = create_app()
    prod_app.stores._stores["sessions"] = MemoryStore()
    async with AsyncTestClient(app=prod_app, raise_server_exceptions=False) as prod_client:
        csrf_rejected = await prod_client.post("/api/chat/session/clear")
        assert csrf_rejected.status_code == 403
        vector_demo_rejected = await prod_client.post("/api/vector-demo", json={"query": "espresso"})
        assert vector_demo_rejected.status_code == 403
