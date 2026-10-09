---
type: Task
id: task-1
flow_id: litestar-mcp-agent-adoption
state: open
title: Upgrade litestar-mcp Dependency and Adopt Upstream GoogleGenAIClient
description: Upgrade pyproject.toml to litestar-mcp[a2a]>=0.15.0, replace GeminiModelClient with litestar_mcp.GoogleGenAIClient in src/app/ioc.py, and delete _model.py.
verification_strategy: characterization
depends_on: []
commit: null
tags:
  - task
  - dependencies
  - model-client
  - google-genai
---

# Task task-1: Upgrade litestar-mcp Dependency and Adopt Upstream GoogleGenAIClient

## Objective
Upgrade `pyproject.toml` to consume `litestar-mcp[a2a]>=0.15.0`, update `IntegrationsProvider` in `src/app/ioc.py` to provide `litestar_mcp.GoogleGenAIClient`, and remove the hand-rolled `src/app/domain/ai/runtime/_model.py` module and its redundant streaming chunk parser.

## Itemized Checklist
- [ ] Update `pyproject.toml` dependencies:
  - Update `"litestar-mcp[a2a]>=0.15.0"`.
  - Run `uv sync` to update `uv.lock`.
- [ ] Update `src/app/ioc.py`:
  - Import `GoogleGenAIClient` from `litestar_mcp.agent.models` (or `litestar_mcp`).
  - Replace `provide_model_client` to instantiate and return `GoogleGenAIClient`:
    ```python
    @provide(scope=Scope.APP)
    def provide_model_client(self) -> GoogleGenAIClient:
        settings = get_settings()
        return GoogleGenAIClient(
            model=settings.ai.chat_model,
            vertexai=bool(settings.ai.project_id),
            project=settings.ai.project_id,
            location=settings.ai.location,
            api_key=settings.ai.api_key,
        )
    ```
- [ ] Remove `src/app/domain/ai/runtime/_model.py`.
- [ ] Update `src/app/domain/ai/runtime/__init__.py` to export `GoogleGenAIClient` and `ModelClient` from `litestar_mcp`.
- [ ] Update unit tests in `src/tests/unit/app/domain/ai/runtime/test_model_store.py` to assert against `GoogleGenAIClient` and upstream `ModelDelta`.
- [ ] Run targeted verification (`uv run pytest src/tests/unit/app/domain/ai/runtime/test_model_store.py` and `make lint`).

## Verification
- Strategy: `characterization`
- Initial Evidence: Run `uv run pytest src/tests/unit/app/domain/ai/runtime/test_model_store.py`
  - Expected: Current unit tests pass using local `GeminiModelClient`.
- Final Evidence: Run `uv run pytest src/tests/unit/app/domain/ai/runtime/test_model_store.py && make lint`
  - Expected: All tests pass using upstream `GoogleGenAIClient` and `make lint` passes with 0 errors.
