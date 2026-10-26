---
type: Pattern
title: Code Style Patterns
description: Conventions for Python code style, FrozenBaseStruct schemas, Dishka DI, private module boundaries, and AST code hygiene
tags:
  - code-style
  - python
  - typing
---

# Code Style Patterns

<!-- truth: start -->
- Use SPDX headers on every source-owned file: `SPDX-FileCopyrightText: 2026 Google LLC` plus `SPDX-License-Identifier: Apache-2.0`. Ruff's `CPY001` rule enforces presence; the `license-headers` prek hook (running `tools/license_headers.py`) inserts them on commit. See styleguides for per-language comment forms.
- Use PEP 585 built-in generics (`list[str]`, `dict[str, Any]`) and PEP 604 unions (`str | None`) across typed boundaries.
- Enforce repository code hygiene via `tools/ci/check_code_hygiene.py` (`src/app/`, `tools/`, `manage.py`), `src/tests/unit/test_test_suite_guards.py` (`src/app/` and `src/tests/`), and Ruff `RUF022`: zero non-directive inline `#` comments (explain intent exclusively in Google-style docstrings), module-top-level imports only (except lazy CLI subcommand dispatch in `src/app/cli/main.py` and `src/app/cli/commands.py`), top-level module docstrings, public classes and functions defined before private `_...` helpers, `@dataclass(..., slots=True)` on every dataclass, and (across `src/app/`) sorted explicit `__all__` plus class member ordering (class attributes -> `__init__` -> `@property` -> public methods -> private `_...` methods).
- Place domain implementation details in private `_*` modules inside `controllers/`, `services/`, and `schemas/` subpackages (for example `_products.py`, `_stores.py`, `_apex_ai.py`) and re-export public symbols exclusively through each subpackage's `__init__.py` (`__all__`). Never leave backward-compatibility aliases, re-export shims, or facade modules around.
- Define domain, DTO, and wire schemas as subclasses of `FrozenBaseStruct` or `CamelizedFrozenStruct` in `src/app/lib/schema.py` (`msgspec.Struct(..., frozen=True, gc=False, omit_defaults=True)`) so instances remain immutable and omit CPython cyclic GC tracking overhead (`pydantic` is banned by Ruff `TID251`).
- Assemble Dishka containers through `create_container()` and `get_providers()` in `src/app/ioc/__init__.py` (`ConfigProvider`, `DBProvider`, `AIProvider`, `DomainServiceProvider`). Provider modules in `src/app/ioc/_*.py` (`_config.py`, `_database.py`, `_ai.py`, `_domain.py`) must never use `from __future__ import annotations` because Dishka introspects `@provide` annotations at runtime.
- Prefer handler-argument `Inject[T]` (`from app.lib.di import Inject`) over route-level `@inject` decorators, and inherit HTTP controllers from `PublicController` or `SecureController` (`litestar_security`, enforced by `tools/ci/check_litestar_security.py`).
- Use `@async_inject` (`src/app/cli/utils.py`) for async Click commands; command modules should not call `sqlspec.utils.sync_tools.run_` directly or define nested async runners.
- Inherit domain database services from `OracleLoaderService` (`self.get_sql("<name>")` backed by `default_sql_loader()`) or `OracleAsyncService` in `src/app/lib/service.py`, pass `schema_type=` whenever a typed `FrozenBaseStruct` / `CamelizedFrozenStruct` schema exists, and sanitize Oracle Text queries through `build_oracle_text_query` and `build_oracle_proximity_query` in `src/app/lib/text_search.py`.
- Use SQLSpec builders (`sql.insert`, `sql.update`, `sql.delete`) for simple CRUD and named SQL (`self.get_sql("<name>")` / `db_manager.get_sql("<name>")` / `sql_loader.get_sql("<name>")`) from `src/app/db/sql/*.sql` for static reads and complex queries.
- Route JSON encoding and decoding through centralized `msgspec` utilities in `src/app/utils/serialization.py` (`encode_json`, `encode_json_bytes`, `format_json`, `decode_json`, `from_json`, `to_json`, `to_schema`, `sanitize_for_json`) rather than calling `msgspec.json` or `json.loads` / `json.dumps` directly (`orjson` is banned by Ruff `TID251`).
- Use `schema_dump(..., wire_format=False)` from `src/app/utils/serialization.py` when dumping `msgspec` schemas into database writes that require Python or Oracle `snake_case` column names instead of camelized wire names.
- Push aggregate null handling into SQL with `COALESCE`, not Python `value or 0`.
- For `gemini-embedding-2`, encode query and document purpose in the embedding input text (`embedding_purpose="query"` / `"document"`). Do not send legacy embedding `task_type` parameters.
- Keep placeholder Vertex AI project checks on the typed `AIServiceUnconfigured` path (`PLACEHOLDER_VALUES` in `src/app/lib/settings/_ai.py`) so unconfigured environments return a clean HTTP 503.
- Keep settings `@dataclass(frozen=True, slots=True)` under `src/app/lib/settings/`, accessed via `Settings.from_env()` or Dishka-injected sub-settings; Ruff `TID251` bans importing `app.config` or `app.lib.settings.get_settings` inside domain, IoC, and library modules.
<!-- truth: end -->
