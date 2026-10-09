---
type: Task
id: task-5
flow_id: litestar-mcp-agent-adoption
state: open
title: Multi-Protocol End-to-End Verification and Repository Cleanup
description: Validate end-to-end A2A discovery and execution, MCP tool invocation via CoffeeSkillController, chat SSE streaming, and run aggregate verification gates.
verification_strategy: integration_acceptance
depends_on:
  - task-4
commit: null
tags:
  - task
  - verification
  - integration
  - mcp
  - a2a
---

# Task task-5: Multi-Protocol End-to-End Verification and Repository Cleanup

## Objective
Execute comprehensive multi-protocol verification covering A2A agent discovery, MCP tool execution through `CoffeeSkillController`, browser HTMX chat SSE streaming, and run the full aggregate test and linting gates across the repository.

## Itemized Checklist
- [ ] Verify A2A protocol surface:
  - Run `src/tests/unit/app/domain/ai/a2a/test_a2a.py` ensuring `GET /.well-known/agent-card.json` advertises `coffee_shop` skills and `POST /a2a` dispatches turns.
- [ ] Verify MCP protocol surface:
  - Run `src/tests/unit/app/domain/ai/mcp/test_mcp.py` asserting `tools/list` contains `search_coffee_products` and `find_nearby_stores` from `CoffeeSkillController` with clean input schemas.
- [ ] Verify Chat HTTP & Web surfaces:
  - Run `src/tests/integration/app/domain/chat/controllers/test_chat_http.py` and `src/tests/integration/app/domain/web/controllers/test_pages.py`.
- [ ] Verify Vector search & Oracle persistence:
  - Run `src/tests/integration/app/domain/products/controllers/test_vector_http.py`.
- [ ] Run full project gates:
  - `make lint` (all 12 `prek` pre-commit hooks, mypy, pyright, markdownlint).
  - `uv run pytest src/tests/unit` (full unit test suite).
  - Integration suite against Oracle DB container.
- [ ] Audit repository for dead code, legacy imports, and orphaned custom runtime files.

## Verification
- Strategy: `integration_acceptance`
- Initial Evidence: Run `grep -rn "src/app/domain/ai/runtime/_loop.py" src/`
  - Expected: Confirms old custom runtime modules are completely deleted and unreferenced.
- Final Evidence: Run `make lint && uv run pytest src/tests/unit && uv run pytest src/tests/integration/app/domain/chat/`
  - Expected: Full linting and test suites pass 100% green with zero errors.
