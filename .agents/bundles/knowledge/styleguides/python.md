---
type: Guide
title: Python Styleguide
description: Python 3.12+ style, PEP 585/604 typing, msgspec structs, Dishka DI, SQLSpec services, and AST hygiene rules
tags:
  - styleguide
  - python
  - typing
---

# Python Style Guide

Python 3.12+ conventions for Litestar 2, SQLSpec (`oracledb` async), Dishka DI, `msgspec`, and repository tooling across `src/app/`, `src/tests/`, `tools/`, and `manage.py`.

## License and Copyright Headers

Every source-owned file begins with the concise SPDX license header enforced by `tools/license_headers.py`:

```python
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Module docstring describing domain responsibility."""
```

Comment syntax by file type (`tools/license_headers.py`):

| Extension / file | Comment form |
| :--- | :--- |
| `.py`, `.pyi`, `.sh`, `.toml`, `.yaml`, `.yml` | `# SPDX-FileCopyrightText: 2026 Google LLC` |
| `.pre-commit-config.yaml`, `Makefile`, `Dockerfile*`, `manage.py` | `# SPDX-FileCopyrightText: 2026 Google LLC` |
| `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs` | `// SPDX-FileCopyrightText: 2026 Google LLC` |
| `.sql` | `-- SPDX-FileCopyrightText: 2026 Google LLC` |
| `.css` | `/* SPDX-FileCopyrightText: 2026 Google LLC */` (multiline block) |
| `.html.j2` | `{# SPDX-FileCopyrightText: 2026 Google LLC #}` (multiline block) |

Header placement and enforcement:

- Place the SPDX lines at the top of the file before module docstrings and imports.
- When line 1 is a shebang (`#!/usr/bin/env ...`) or Dockerfile parser directive (`# syntax=...`), place the SPDX lines immediately after line 1.
- Generated or vendored directories (`src/resources/public/`, `dist/`, `.venv/`, `src/resources/node_modules/`) are skipped automatically.
- Ruff `CPY001` checks headers during `make lint`, and `uv run python tools/license_headers.py --fix` inserts missing headers across supported targets.

## Module Layout and AST Hygiene

`tools/ci/check_code_hygiene.py` (`src/app/`, `tools/`, `manage.py`), `src/tests/unit/test_test_suite_guards.py` (`src/app/`, `src/tests/`), and Ruff `RUF022` enforce strict AST layout rules:

1. **Zero Narrative Inline `#` Comments**: Never write narrative inline or block `#` comments inside Python files (`src/app/`, `src/tests/`, `tools/`, `manage.py`). Only leading `#!` shebangs, SPDX header lines, and tool/doc directive pragmas (`# noqa`, `# type: ignore`, `# pyright:`, `# pragma:`, `# fmt:`, `# docs-start:`, `# docs-end:`) are permitted; document intent, invariants, and edge cases in Google-style docstrings.
2. **Module Order**: SPDX header -> module docstring -> grouped top-level imports (`stdlib` -> third-party -> `app.*`) -> sorted explicit `__all__` tuple (required across `src/app/`) -> public constants/classes/functions -> private `_...` helpers at the bottom.
3. **Top-Level Imports Only**: Never place `import` or `from ... import` inside `def` or `async def` bodies. The sole repository exception is lazy CLI subcommand dispatch in `src/app/cli/main.py` and `src/app/cli/commands.py`.
4. **Private Implementation Modules**: Domain subpackages (`controllers/`, `services/`, `schemas/`, `runtime/`, `protocols/`) store implementation code in private `_*` modules (such as `_products.py`, `_stores.py`, `_apex_ai.py`) and re-export public symbols exclusively from the subpackage `__init__.py` via `__all__`.
5. **Class Member Ordering**: Order members inside every class as:
   - Class attributes (`__slots__`, `ClassVar`, schema fields)
   - `__init__` / `__post_init__`
   - `@property` accessors
   - Public methods (`@classmethod`, `@staticmethod`, instance methods)
   - Private `_...` helper methods strictly below public methods

```python
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Oracle Text query escaping and proximity builder utilities."""

from __future__ import annotations

from typing import Final

__all__ = ("DEFAULT_MAX_TOKENS", "format_token_clause")

DEFAULT_MAX_TOKENS: Final[int] = 8


def format_token_clause(raw_query: str, *, max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    """Normalize whitespace-delimited search input into braced Oracle Text tokens."""
    tokens = _tokenize(raw_query)[:max_tokens]
    return " ACCUM ".join(f"{{{token}}}" for token in tokens)


def _tokenize(raw_query: str) -> list[str]:
    """Split and strip non-empty tokens from raw user input."""
    return [part for part in raw_query.strip().split() if part]
```

## Type Annotations (PEP 585 & PEP 604)

- Use built-in generic collections (`list[str]`, `dict[str, Any]`, `tuple[int, ...]`, `set[str]`) and `collections.abc` protocols (`Sequence`, `Mapping`, `Callable`, `AsyncGenerator`, `AsyncIterator`) rather than `typing.List`, `typing.Dict`, or `typing.Optional`.
- Use PEP 604 union syntax (`Product | None`, `str | int`).
- `from __future__ import annotations` and `if TYPE_CHECKING:` blocks are standard across application, test, and tooling modules to keep runtime import graphs light.
- **Dishka Provider Exception**: Never include `from __future__ import annotations` in Dishka provider modules under `src/app/ioc/` (`src/app/ioc/_config.py`, `src/app/ioc/_database.py`, `src/app/ioc/_ai.py`, `src/app/ioc/_domain.py`), because Dishka inspects concrete runtime type annotations when building the container graph.

## Schemas, Dataclasses, and Serialization

### Immutable `msgspec` Schemas (`src/app/lib/schema.py`)

Domain payloads, wire DTOs, telemetry snapshots, and tool outputs inherit from `FrozenBaseStruct` (snake_case) or `CamelizedFrozenStruct` (camelCase wire payloads). Both set `frozen=True, gc=False, omit_defaults=True` so instances omit cyclic garbage-collector tracking overhead:

```python
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Store search request and response schemas."""

from __future__ import annotations

from app.lib.schema import CamelizedFrozenStruct, FrozenBaseStruct

__all__ = ("StoreCoordinates", "StoreSummary")


class StoreCoordinates(FrozenBaseStruct, frozen=True, gc=False):
    """Request-scoped browser coordinates for proximity search."""

    latitude: float
    longitude: float
    radius_miles: float = 25.0


class StoreSummary(CamelizedFrozenStruct, frozen=True, gc=False):
    """Public camelCase store payload returned to API callers."""

    store_id: int
    store_name: str
    distance_miles: float | None = None
```

### Slotted Dataclasses (`make slotscheck`)

Environment-backed settings (`src/app/lib/settings/`) and CLI/infrastructure value objects (`tools/`) use `@dataclass(frozen=True, slots=True)`. Non-struct service and runtime classes declare explicit `__slots__ = (...)` so `make slotscheck` passes across `app`.

### Centralized JSON Serialization (`src/app/utils/serialization.py`)

Never import `orjson` or `pydantic` (banned via Ruff `TID251` in `pyproject.toml`), and do not scatter direct `json.dumps` / `json.loads` calls across domain modules. Route JSON encoding, decoding, and struct conversion through `src/app/utils/serialization.py` (`encode_json`, `encode_json_bytes`, `format_json`, `decode_json`, `from_json`, `to_json`, `schema_dump`, `to_schema`, `sanitize_for_json`).

## Dependency Injection, Controllers, and Services

### Dishka Providers (`src/app/ioc/`)

Container providers live in `src/app/ioc/` (`ConfigProvider`, `DBProvider`, `AIProvider`, `DomainServiceProvider`) and are assembled via `create_container()` and `get_providers()` in `src/app/ioc/__init__.py`.

- HTTP handlers inject dependencies with `Inject[ServiceType]` (`FromDishka` alias from `src/app/lib/di.py`).
- Async Click CLI commands inject dependencies with `@async_inject` (`src/app/cli/utils.py`).
- Never import `app.config` inside `src/app/domain/`, `src/app/ioc/`, or `src/app/lib/`; read settings through `Settings.from_env()` (`src/app/lib/settings/`).

```python
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Dishka provider example without postponed annotations."""

from dishka import Provider, Scope, provide
from sqlspec.adapters.oracledb import OracleAsyncDriver
from sqlspec.loader import SQLFileLoader

from app.domain.products.services import ProductService

__all__ = ("CatalogProvider",)


class CatalogProvider(Provider):
    """Request-scoped catalog service provider."""

    @provide(scope=Scope.REQUEST)
    def provide_product_service(
        self,
        driver: OracleAsyncDriver,
        loader: SQLFileLoader,
    ) -> ProductService:
        """Construct a request-scoped ProductService."""
        return ProductService(driver, loader)
```

### Controllers (`src/app/lib/security.py`)

Every HTTP controller must inherit from `PublicController` or `SecureController` (`litestar_security`), enforced by `tools/ci/check_litestar_security.py`. Direct inheritance from `litestar.Controller` is banned.

### SQLSpec Services (`src/app/lib/service.py`)

Database services inherit from `OracleLoaderService` (when executing named SQL from `src/app/db/sql/*.sql` via `self.get_sql("<query_name>")`) or `OracleAsyncService` (when using SQLSpec `sql.select`, `sql.insert`, `sql.update`, or `sql.delete` builders):

```python
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Catalog lookup service backed by SQLSpec named queries."""

from __future__ import annotations

from app.domain.products.schemas import Product
from app.lib.service import OracleLoaderService

__all__ = ("CatalogLookupService",)


class CatalogLookupService(OracleLoaderService):
    """Read-only product lookup operations on Oracle 26ai."""

    __slots__ = ()

    async def get_product(self, product_id: int) -> Product | None:
        """Fetch a single product by primary key."""
        return await self.driver.select_one_or_none(
            self.get_sql("get-product").where("id = :id"),
            id=product_id,
            schema_type=Product,
        )
```

## Docstrings and Error Handling

Use Google-style docstrings on modules, classes, and public functions. Catch specific exception types rather than bare `except:` clauses, and raise domain-appropriate or Litestar HTTP exceptions at controller boundaries:

```python
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Input validation helper with Google-style docstring."""

from __future__ import annotations

__all__ = ("validate_radius_miles",)


def validate_radius_miles(radius_miles: float) -> float:
    """Validate a store-locator search radius in miles.

    Args:
        radius_miles: Requested search radius in miles.

    Returns:
        Validated radius clamped to a positive float.

    Raises:
        ValueError: If ``radius_miles`` is zero, negative, or exceeds 500 miles.
    """
    if radius_miles <= 0 or radius_miles > 500:
        msg = f"radius_miles must be between 0 and 500, got {radius_miles}"
        raise ValueError(msg)
    return radius_miles
```

## CLI Scripts and Repository Tooling (`tools/`)

Repository automation and CI gates live under `tools/` and `manage.py` and run via `uv run`:

- Write terminal output with `sys.stdout.write(...)` and `sys.stderr.write(...)` instead of `print(...)` (Ruff `T20` flags `print` calls outside explicit CLI exceptions).
- Return integer exit codes from `main(argv: Sequence[str] | None = None) -> int` and invoke `raise SystemExit(main())` under `if __name__ == "__main__":`.
- Do not add unnecessary executable permission bits or `#!/usr/bin/env python3` shebangs to non-executable modules invoked via `uv run python tools/...`.

```python
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Minimal CLI check template for repository tooling."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ("main",)


def main(argv: Sequence[str] | None = None) -> int:
    """Verify that every supplied path exists on disk."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="files to verify")
    args = parser.parse_args(argv)

    missing = [raw for raw in args.paths if not Path(raw).exists()]
    if missing:
        for item in missing:
            sys.stderr.write(f"missing file: {item}\n")
        return 1
    sys.stdout.write(f"verified {len(args.paths)} file(s)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Testing Conventions (`src/tests/AGENTS.md`)

- Write plain `def test_*` and `async def test_*` functions (never `class Test*:` groupings).
- Mark async tests with `@pytest.mark.anyio` (never `@pytest.mark.asyncio`).
- Place unit tests under `src/tests/unit/` (zero live database or Vertex AI dependencies) and live Oracle 26ai tests under `src/tests/integration/` (`pytestmark = pytest.mark.integration`).

```python
# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for Oracle Text query formatting."""

from __future__ import annotations

import pytest

from app.lib.text_search import build_oracle_text_query


@pytest.mark.parametrize(
    ("raw_query", "expected"),
    [
        ("dark roast", "{dark} ACCUM {roast}"),
        ("   ", None),
    ],
)
def test_build_oracle_text_query_formats_tokens(raw_query: str, expected: str | None) -> None:
    """Verify whitespace tokenization and Oracle Text bracing."""
    assert build_oracle_text_query(raw_query) == expected
```

## Verification Commands

```bash
make format
make lint
make py-check
make slotscheck
make test-unit
make test-integration
```
