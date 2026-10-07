---
type: Pattern
title: Code Style Patterns
description: Conventions for Python code style, typing, licensing, and clean organization
tags:
  - code-style
  - python
  - typing
---

# Code Style Patterns

<!-- truth: start -->
- Use SPDX headers on source files: `SPDX-FileCopyrightText: 2026 Google LLC` plus `SPDX-License-Identifier: Apache-2.0`. Ruff's `CPY001` rule enforces presence; the `license-headers` prek hook (running `tools/license_headers.py`) inserts them on commit. See styleguides for per-language comment forms.
- Use PEP 604 unions (`str | None`) and typed public boundaries.
- Keep demo-facing public Python modules public-first: exported controllers, services, settings, commands, and lifecycle entry points should appear before private mechanics. Move substantial helper runs into focused private sibling modules or below the public API; avoid compatibility shim or facade modules.
- `src/app/ioc.py` must not use `from __future__ import annotations`; Dishka introspects provider annotations at runtime.
- Prefer handler-argument `Inject[T]` over route-level `@inject` decorators.
- Use `@async_inject` for async Click commands; command modules should not call `sqlspec.utils.sync_tools.run_` directly or define nested async runners.
- SQLSpec reads should pass `schema_type=` whenever a typed row/schema exists.
- Use `SQLSpecAsyncService` from `app.lib.service` as the domain service base.
- Use SQLSpec builders for dynamic writes (`sql.update`, `sql.insert_into`) and named SQL for static reads.
- Use `from_json` / `to_json` from `app.utils.serialization`, not ad hoc `json.loads` / `json.dumps`, in app code.
- Use `schema_dump(..., wire_format=False)` from `app.utils.serialization` when dumping msgspec schemas into database writes that require Python/Oracle column names instead of camelized wire names.
- Push aggregate null handling into SQL with `COALESCE`, not Python `value or 0`.
- For `gemini-embedding-2`, encode query/document purpose in the embedding input text. Do not send the old embedding `task_type` API parameter.
- Keep placeholder Vertex project checks on the typed `AIServiceUnconfigured` path so local misconfiguration returns a clean 503.
- Settings stay dataclass/cached, quiet, and effectively immutable; remove future knobs until source behavior wires them.
<!-- truth: end -->
