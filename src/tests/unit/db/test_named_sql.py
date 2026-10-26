# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Verify named SQL query files, SQLFileLoader registry loading, and absence of inline SQL in domain services."""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

import pytest

from app.lib.service import default_sql_loader
from tests.support.paths import APP_ROOT, SRC_ROOT

if TYPE_CHECKING:
    from pathlib import Path

SQL_DIR = APP_ROOT / "db" / "sql"
DOMAIN_DIR = APP_ROOT / "domain"

EXPECTED_FILES = ("ai-runtime.sql", "hybrid.sql", "inventory.sql", "products.sql", "stores.sql", "system.sql")

_NAME_DIRECTIVE = re.compile(r"^--\s*name:\s*([a-zA-Z0-9_-]+)", flags=re.MULTILINE)
INLINE_SQL_PATTERN = re.compile(r'(?:"|\')\s*(SELECT|INSERT|UPDATE|DELETE|MERGE)(?=[ \t\n])')


def _discover_named_keys() -> tuple[str, ...]:
    """Discover all `-- name:` query keys across `src/app/db/sql/*.sql`."""
    keys: set[str] = set()
    for sql_file in sorted(SQL_DIR.glob("*.sql")):
        keys.update(_NAME_DIRECTIVE.findall(sql_file.read_text(encoding="utf-8")))
    return tuple(sorted(keys))


def _discover_service_files() -> tuple[Path, ...]:
    """Discover all domain service and runtime store Python files."""
    files = [p for p in sorted(DOMAIN_DIR.glob("*/services/*.py")) if p.name != "__init__.py"]
    ai_store = DOMAIN_DIR / "ai" / "runtime" / "_store.py"
    if ai_store.exists():
        files.append(ai_store)
    return tuple(files)


def _extract_get_sql_key(node: ast.AST) -> str | None:
    """Return the string query key when ``node`` is a ``<target>.get_sql('<key>')`` call."""
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return None
    if node.func.attr != "get_sql" or not node.args:
        return None
    first_arg = node.args[0]
    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
        return first_arg.value
    return None


def _discover_get_sql_references() -> set[str]:
    """Discover all string-literal `.get_sql('<name>')` call-site references across `src/app/`."""
    referenced: set[str] = set()
    for py_file in sorted(APP_ROOT.rglob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            key = _extract_get_sql_key(node)
            if key is not None:
                referenced.add(key)
    return referenced


EXPECTED_KEYS = _discover_named_keys()
SERVICE_FILES = _discover_service_files()


def test_sql_directory_and_files_exist() -> None:
    """Verify `src/app/db/sql/` contains the expected named-query `.sql` files."""
    assert SQL_DIR.is_dir(), f"{SQL_DIR} must exist"
    for name in EXPECTED_FILES:
        path = SQL_DIR / name
        assert path.is_file(), f"{path} must exist with named-query directives"


@pytest.mark.parametrize("key", EXPECTED_KEYS)
def test_expected_named_query_loads(key: str) -> None:
    """Verify every discovered named query key is registered in `default_sql_loader()`."""
    default_sql_loader.cache_clear()
    loader = default_sql_loader()
    assert loader.has_query(key), (
        f"SQLFileLoader has no named query '{key}' — check src/app/db/sql/*.sql for `-- name: {key}`"
    )
    assert str(loader.get_sql(key)).strip()


def test_named_query_registry_matches_get_sql_call_sites() -> None:
    """Verify every `.get_sql(...)` call references an existing named query and no named query is dead."""
    default_sql_loader.cache_clear()
    loader = default_sql_loader()
    referenced = _discover_get_sql_references()

    assert referenced, "expected at least one .get_sql('<key>') call in src/app"

    missing = [key for key in sorted(referenced) if not loader.has_query(key)]
    assert not missing, f"get_sql() references with no matching .sql definition: {missing}"

    unreferenced = sorted(set(_discover_named_keys()) - referenced)
    assert not unreferenced, f"Named SQL queries with no get_sql() reference in src/app: {unreferenced}"


def test_system_sql_uses_atomic_merge_and_disjoint_windows() -> None:
    """Verify `system.sql` defines atomic `MERGE INTO` cache upserts and disjoint window bounds."""
    default_sql_loader.cache_clear()
    loader = default_sql_loader()

    assert loader.has_query("upsert-response-cache")
    assert "MERGE INTO response_cache" in str(loader.get_sql("upsert-response-cache"))

    assert loader.has_query("upsert-embedding-cache")
    assert "MERGE INTO embedding_cache" in str(loader.get_sql("upsert-embedding-cache"))

    perf_sql = str(loader.get_sql("get-performance-stats"))
    assert ":window_start_hours" in perf_sql
    assert ":window_end_hours" in perf_sql


@pytest.mark.parametrize("service_file", SERVICE_FILES, ids=lambda p: p.relative_to(SRC_ROOT).as_posix())
def test_no_inline_sql_strings_in_domain_services(service_file: Path) -> None:
    """Verify domain services use named SQL queries or SQLSpec builders rather than inline SQL strings."""
    text = service_file.read_text(encoding="utf-8")
    matches = INLINE_SQL_PATTERN.findall(text)
    assert not matches, (
        f"{service_file.relative_to(SRC_ROOT)} still contains inline SQL keywords: "
        f"{matches}. Use self.get_sql('<key>') or sql.update/insert/delete builders."
    )
