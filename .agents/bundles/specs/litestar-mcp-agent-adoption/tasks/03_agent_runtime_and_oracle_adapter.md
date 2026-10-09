---
type: Task
id: task-3
flow_id: litestar-mcp-agent-adoption
state: open
title: Wire Upstream AgentRuntime with TurnBudget and Adapt Oracle Stores
description: Wire upstream litestar_mcp.AgentRuntime with TurnBudget in ioc.py, adapt OracleSessionStore and OracleEventStore to AgentMessage, and delete _loop.py and _spec.py.
verification_strategy: behavior_tdd
depends_on:
  - task-2
commit: null
tags:
  - task
  - agent-runtime
  - turn-budget
  - oracle-26ai
  - sqlspec
---

# Task task-3: Wire Upstream AgentRuntime with TurnBudget and Adapt Oracle Stores

## Objective
Replace the custom `AgentRuntime` execution loop and `SpecTree` prompt fencer with upstream `litestar_mcp.AgentRuntime`, `AgentGroup`, and `TurnBudget`. Adapt `OracleSessionStore` and `OracleEventStore` to persist upstream `AgentMessage` instances while preserving all Oracle 26ai SQLSpec named queries in `src/app/db/sql/ai-runtime.sql`.

## Itemized Checklist
- [ ] Update `src/app/domain/ai/runtime/_store.py`:
  - Import `AgentMessage` from `litestar_mcp.agent.spec`.
  - Update `OracleEventStore.append_event` and `list_events` to serialize and deserialize `AgentMessage` dictionaries cleanly.
  - Keep all Oracle SQL statements intact: `save-agent-session`, `get-agent-session`, `delete-agent-session`, `append-agent-event`, `list-agent-events`, `delete-agent-events`.
- [ ] Update `src/app/ioc.py`:
  - Import `AgentRuntime`, `TurnBudget`, and `AgentGroup` from `litestar_mcp`.
  - Replace `provide_agent_runtime` in `IntegrationsProvider`:
    ```python
    @provide(scope=Scope.APP)
    def provide_agent_runtime(self, model_client: GoogleGenAIClient) -> AgentRuntime:
        return AgentRuntime(
            model_client=model_client,
            budget=TurnBudget(max_tool_calls=10, max_tokens=8192),
        )
    ```
- [ ] Delete hand-rolled runtime files:
  - `src/app/domain/ai/runtime/_loop.py`
  - `src/app/domain/ai/runtime/_spec.py`
- [ ] Update `src/app/domain/ai/runtime/__init__.py` to export upstream `AgentRuntime`, `TurnBudget`, `BudgetExceededError`, `AgentMessage`, and `AgentGroup`.
- [ ] Update unit tests in `src/tests/unit/app/domain/ai/runtime/test_loop_stream.py` to assert budget enforcement (`BudgetExceededError`) and `AgentRuntime.stream_turn()`.
- [ ] Run targeted verification (`uv run pytest src/tests/unit/app/domain/ai/runtime/test_loop_stream.py` and `make lint`).

## Verification
- Strategy: `behavior_tdd`
- Initial Evidence: Run `uv run pytest src/tests/unit/app/domain/ai/runtime/test_loop_stream.py -k test_budget_exceeded`
  - Expected: Fails because `TurnBudget` enforcement is not yet wired to the runtime.
- Final Evidence: Run `uv run pytest src/tests/unit/app/domain/ai/runtime/test_loop_stream.py && make lint`
  - Expected: All runtime loop and store tests pass cleanly.
