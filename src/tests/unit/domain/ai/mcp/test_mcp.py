# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for stateless MCP server dispatching and tool discovery."""

from __future__ import annotations

import pytest
from litestar.stores.memory import MemoryStore
from litestar.testing import AsyncTestClient
from litestar_autowire import clear_autowire_cache

from app.server.asgi import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def clean_cache() -> None:
    """Clear autowire cache between test executions."""
    clear_autowire_cache()


def _mcp_headers(method: str, name: str | None = None) -> dict[str, str]:
    """Build standard MCP protocol transport headers.

    Args:
        method: MCP RPC method name.
        name: Optional tool or resource name.

    Returns:
        Mapping of HTTP headers.
    """
    headers = {"MCP-Protocol-Version": "2026-07-28", "Mcp-Method": method}
    if name is not None:
        headers["Mcp-Name"] = name
    return headers


def _mcp_params(extra_params: dict[str, object] | None = None) -> dict[str, object]:
    """Build standard MCP RPC params dictionary with required _meta envelope.

    Args:
        extra_params: Optional additional parameters to merge.

    Returns:
        Structured params dictionary including _meta protocol envelope.
    """
    params: dict[str, object] = {
        "_meta": {
            "io.modelcontextprotocol/protocolVersion": "2026-07-28",
            "io.modelcontextprotocol/clientCapabilities": {},
        }
    }
    if extra_params:
        params.update(extra_params)
    return params


async def test_mcp_tools_list(clean_cache: None) -> None:
    """Verify POST /mcp tools/list includes route-annotated MCP tools."""
    del clean_cache
    app = create_app()
    app.stores._stores["sessions"] = MemoryStore()

    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": _mcp_params()}

    async with AsyncTestClient(app=app) as client:
        res = await client.post("/mcp", json=payload, headers=_mcp_headers("tools/list"))
        assert res.status_code == 200
        body = res.json()
        assert body["jsonrpc"] == "2.0"
        assert body["id"] == 1
        tools = body["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "get_product" in tool_names
        assert "get_store_inventory" in tool_names
        assert "search_products" in tool_names


async def test_mcp_skills_list(clean_cache: None) -> None:
    """Verify POST /mcp skills/list returns discovered skill manifests."""
    del clean_cache
    app = create_app()
    app.stores._stores["sessions"] = MemoryStore()

    payload = {"jsonrpc": "2.0", "id": 2, "method": "skills/list", "params": _mcp_params()}

    async with AsyncTestClient(app=app) as client:
        res = await client.post("/mcp", json=payload, headers=_mcp_headers("skills/list"))
        assert res.status_code == 200
        body = res.json()
        assert body["jsonrpc"] == "2.0"
        assert body["id"] == 2
        skills = body["result"]["skills"]
        assert len(skills) >= 1
        skill_uris = [s["uri"] for s in skills]
        assert any("SKILL.md" in uri for uri in skill_uris)


async def test_mcp_header_mismatch_validation(clean_cache: None) -> None:
    """Verify POST /mcp rejects requests with mismatched protocol headers."""
    del clean_cache
    app = create_app()
    app.stores._stores["sessions"] = MemoryStore()

    payload = {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": _mcp_params()}
    mismatched_headers = {"MCP-Protocol-Version": "2026-07-28", "Mcp-Method": "wrong/method"}

    async with AsyncTestClient(app=app) as client:
        res = await client.post("/mcp", json=payload, headers=mismatched_headers)
        assert res.status_code == 400
        body = res.json()
        assert body["jsonrpc"] == "2.0"
        assert "error" in body
        assert "header does not match" in body["error"]["message"].lower()
