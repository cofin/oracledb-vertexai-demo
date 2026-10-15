---
type: Guide
title: Unit & Integration Test Catalog
description: Flattened test tree layout, AnyIO async rules, AST/tokenize meta-guards, and Oracle 26ai integration fixtures
tags:
  - testing
  - pytest
  - anyio
  - oracle-26ai
---

# Unit & Integration Test Catalog

## 1. Flattened Directory Layout (`src/tests/`)

The test suite mirrors `src/app/` directly under `src/tests/unit/` and `src/tests/integration/` without redundant `/app/` nesting:

```text
src/tests/
├── AGENTS.md
├── conftest.py                # Shared fixtures + pytest_plugins = ["tests.fixtures.slides"]
├── fixtures/
│   └── slides.py              # Slide builder test fixtures
├── support/
│   └── paths.py
├── unit/
│   ├── AGENTS.md
│   ├── conftest.py
│   ├── test_test_suite_guards.py  # AST/tokenize meta-guards
│   ├── test_okf_layout.py         # OKF v0.2 & AGENTIC_REVIEW layout tests
│   ├── cli/
│   ├── db/
│   ├── domain/
│   ├── ioc/
│   ├── lib/
│   ├── server/
│   ├── tools/slides/
│   └── utils/
└── integration/
    ├── AGENTS.md
    ├── conftest.py
    ├── db/
    ├── domain/
    └── server/
```

## 2. AST & Tokenize Meta-Guards (`src/tests/unit/test_test_suite_guards.py`)

`test_test_suite_guards.py` runs in under 1 second as part of `make test-unit` and enforces:
1. No unexpected root files (`src/tests/*.py`) or top-level directories (`src/tests/*/`).
2. No `unittest.mock` imports anywhere inside `src/tests/integration/**/*.py`.
3. No `class Test*` grouping wrappers in any test file.
4. No function-scoped imports or inline `#` comments across `src/tests/**/*.py`.
5. No duplicate `def test_*` names within any test file.
6. Every test function has a docstring.
7. Only approved top-level meta-test files exist directly in `src/tests/unit/*.py` (`conftest.py`, `test_okf_layout.py`, `test_test_suite_guards.py`).

## 3. Running the Suite

- **`make test-unit`**: Runs `uv run pytest src/tests/unit` with zero external database or Vertex AI dependencies.
- **`make test-integration`**: Runs `uv run pytest src/tests/integration` against the live Oracle 26ai container (`make start-infra && uv run coffee upgrade`).
- **`make test`**: Runs the complete unit and integration suite.
