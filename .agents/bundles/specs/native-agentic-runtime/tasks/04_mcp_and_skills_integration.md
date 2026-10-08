---
type: Task
id: task-4
flow_id: native-agentic-runtime
state: closed
title: Configure LitestarMCP Plugin, Skills Catalog, and Route-Level Tool Exposure
description: Mount LitestarMCP with MCPSkillsConfig, annotate product/store route handlers with mcp_tool, and verify stateless JSON-RPC /mcp transport.
verification_strategy: behavior_tdd
depends_on:
  - task-1
commit: null
tags:
  - task
  - mcp
  - litestar-mcp
  - skills
  - json-rpc
---

# Task task-4: Configure LitestarMCP Plugin, Skills Catalog, and Route-Level Tool Exposure

## Objective
Mount and configure `LitestarMCP` in `src/app/server/plugins.py`, configure the `MCPSkillsConfig` catalog to serve skills over `io.modelcontextprotocol/skills`, annotate product and store route handlers with `mcp_tool="name"`, and verify stateless POST `/mcp` JSON-RPC execution.

## Itemized Checklist
- [x] Update `src/app/server/plugins.py`:
  - Add `mcp: LitestarMCP` to global plugin annotations.
  - In `_initialize()`, instantiate `_LitestarMCP` with `_MCPConfig(name="Cymbal Coffee MCP", skills=..., route_opt={"auth": public()})` and assign to `g["mcp"]`.
  - In `_reset()`, include `"mcp"` in `lazy_names`.
- [x] Annotate `src/app/domain/products/controllers/_products.py`:
  - Subclass `PublicController` for `ProductController` and `StoreController`.
  - Add `mcp_tool="get_product"` to `get_product`.
  - Add `mcp_tool="get_store_inventory"` to `get_store_inventory`.
- [x] Annotate `src/app/domain/products/controllers/_vector.py`:
  - Subclass `PublicController` for `VectorController`.
  - Add `mcp_tool="search_products"` to `vector_search`.
- [x] Create `src/app/domain/ai/mcp/__init__.py` exporting prompt and resource registrations.
- [x] Author test suite `src/tests/unit/app/domain/ai/mcp/test_mcp.py` testing JSON-RPC `server/discover`, `tools/list`, `tools/call`, and `skills/list`.

## Implementation Details & Code Samples

### 1. `src/app/server/plugins.py` (Line 43 & Line 80)
```python
# Add to imports in _initialize():
from pathlib import Path
from litestar_mcp import LitestarMCP as _LitestarMCP
from litestar_mcp import MCPConfig as _MCPConfig
from litestar_mcp import MCPSkillsConfig as _MCPSkillsConfig
from litestar_security import public as _public

# In _initialize():
skills_config = _MCPSkillsConfig(
    paths=[Path(".agents/skills"), Path("skills")],
    directory_read=True,
)
g["mcp"] = _LitestarMCP(
    _MCPConfig(
        name="Cymbal Coffee MCP",
        instructions="Exposes coffee product catalog, vector search, store inventory, and skills.",
        skills=skills_config,
        route_opt={"auth": _public()},
    )
)
```

### 2. `src/app/domain/products/controllers/_products.py` (Line 15 & Line 65)
```python
from litestar_security import PublicController

# In ProductController:
class ProductController(PublicController):
    ...
    @get(path="/{product_id:str}", mcp_tool="get_product")
    async def get_product(
        self,
        product_id: str,
        product_service: Inject[ProductService],
    ) -> ProductDetail:
        """Fetch product details by ID."""
        return await product_service.get_detail(product_id)
```

### 3. `src/app/domain/products/controllers/_vector.py` (Line 25 & Line 38)
```python
from litestar_security import PublicController

# In VectorSearchController:
class VectorSearchController(PublicController):
    ...
    @get(path="/search", mcp_tool="search_products")
    async def vector_search(
        self,
        product_service: Inject[ProductService],
        query: str,
        limit: int = 5,
    ) -> list[ProductMatch]:
        """Perform semantic vector search for coffee products."""
        return await product_service.search_by_text(query=query, limit=limit)
```

### 4. `src/tests/unit/app/domain/ai/mcp/test_mcp.py`
```python
"""Unit tests for stateless MCP server dispatching."""

import pytest
from litestar.testing import AsyncTestClient

from app.server.asgi import create_app


@pytest.mark.anyio
async def test_mcp_server_discover() -> None:
    """Verify POST /mcp responds to server/discover with skills capability."""
    app = create_app()
    async with AsyncTestClient(app=app) as client:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "server/discover",
            "params": {"protocolVersion": "2026-07-28"},
        }
        res = await client.post("/mcp", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert body["jsonrpc"] == "2.0"
        assert body["id"] == 1
        assert "capabilities" in body["result"]
```

## Verification
- Strategy: `behavior_tdd`
- Initial Evidence: Run `uv run pytest src/tests/unit/app/domain/ai/mcp/test_mcp.py`
  - Expected: Fails because test file does not exist yet.
- Final Evidence: Run `uv run pytest src/tests/unit/app/domain/ai/mcp/test_mcp.py && make lint`
  - Expected: All unit tests pass, route handlers are discovered by LitestarMCP, and `make lint` is clean.
