---
type: Task
id: task-2
flow_id: litestar-mcp-agent-adoption
state: open
title: Implement CoffeeSkillController and Centralize Tool Declarations
description: Implement CoffeeSkillController subclassing litestar_mcp.SkillController, migrate coffee tools, register on LitestarMCP, and delete hand-rolled _tools.py.
verification_strategy: behavior_tdd
depends_on:
  - task-1
commit: null
tags:
  - task
  - mcp
  - skill-controller
  - tools
---

# Task task-2: Implement CoffeeSkillController and Centralize Tool Declarations

## Objective
Consolidate coffee product search, inventory lookup, and store recommendations into a dedicated `CoffeeSkillController` subclassing `litestar_mcp.SkillController`, register it on `LitestarMCP`, remove route-level `mcp_tool` annotations from HTTP controllers, and delete the custom `src/app/domain/ai/runtime/_tools.py` runner.

## Itemized Checklist
- [ ] Create `src/app/domain/ai/services/skill_controller.py`:
  - Define `CoffeeSkillController(SkillController)`:
    ```python
    from typing import Any
    from litestar_mcp import SkillController, tool
    from litestar_mcp.agent import ToolContext
    from app.domain.products.services import ProductService, StoreService

    class CoffeeSkillController(SkillController):
        """Cymbal Coffee operations skill unifying menu search and store inventory."""

        name = "coffee_shop"
        description = "Cymbal Coffee menu discovery, inventory lookup, and store recommendations."
        instructions = "Always check store inventory before confirming product availability."

        @tool
        async def search_coffee_products(
            self,
            query: str,
            limit: int = 5,
            ctx: ToolContext | None = None,
        ) -> dict[str, Any]:
            """Search Cymbal Coffee products using semantic vector search."""
            context = ctx or ToolContext()
            product_service: ProductService = context.state["product_service"]
            results = await product_service.search_by_vector(...)
            return {"items": [p.to_dict() for p in results]}

        @tool
        async def find_nearby_stores(
            self,
            query: str,
            limit: int = 3,
            ctx: ToolContext | None = None,
        ) -> dict[str, Any]:
            """Find nearby store locations and operating hours."""
            context = ctx or ToolContext()
            store_service: StoreService = context.state["store_service"]
            stores = await store_service.find_nearby(query, limit=limit)
            return {"stores": [s.to_dict() for s in stores]}
    ```
- [ ] Update `src/app/server/plugins.py`:
  - Register `CoffeeSkillController` in `MCPConfig(skill_controllers=[CoffeeSkillController])`.
- [ ] Clean up `src/app/domain/products/controllers/`:
  - Remove `mcp_tool="search_coffee_products"` and `mcp_tool="find_nearby_stores"` parameters from `ProductController` and `StoreController`.
- [ ] Delete `src/app/domain/ai/runtime/_tools.py`.
- [ ] Update `src/app/domain/ai/runtime/__init__.py` to export upstream `Tool`, `tool`, `execute_parallel`, and `ToolContext` from `litestar_mcp`.
- [ ] Update MCP unit tests in `src/tests/unit/app/domain/ai/mcp/test_mcp.py` to verify tool dispatch through `CoffeeSkillController` and `tools/list` response.
- [ ] Run targeted verification (`uv run pytest src/tests/unit/app/domain/ai/mcp/test_mcp.py` and `make lint`).

## Verification
- Strategy: `behavior_tdd`
- Initial Evidence: Run `uv run pytest src/tests/unit/app/domain/ai/mcp/test_mcp.py -k test_coffee_skill_controller`
  - Expected: Fails with `ImportError` or `AttributeError` because `CoffeeSkillController` does not exist yet.
- Final Evidence: Run `uv run pytest src/tests/unit/app/domain/ai/mcp/test_mcp.py && make lint`
  - Expected: All MCP tests pass and tools are cleanly registered via `CoffeeSkillController`.
