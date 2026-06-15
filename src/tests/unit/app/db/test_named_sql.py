# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from tests.support.paths import APP_ROOT, SRC_ROOT

if TYPE_CHECKING:
    from pathlib import Path

SQL_DIR = APP_ROOT / "db" / "sql"
DOMAIN_DIR = APP_ROOT / "domain"

EXPECTED_FILES = ("inventory.sql", "products.sql", "stores.sql", "system.sql")

EXPECTED_KEYS = (
    "get-product",
    "list-products-for-embedding",
    "vector-search-products",
    "get-store-by-id",
    "list-stores",
    "find-stores-by-location",
    "rank-stores-by-distance",
    "find-stores-with-product-inventory",
    "find-product-availability-by-query",
    "get-cached-response",
    "get-cached-embedding",
    "get-cache-stats",
    "get-performance-stats",
    "metrics-breakdown",
    "metrics-scatter-points",
    "metrics-time-series",
)

# Match a SQL keyword inside a Python string literal *only* when followed by whitespace
# (real SQL: `SELECT id`, `UPDATE foo`). Excludes false positives like the named-query
# key string `"update-product-embedding"` (hyphen after the keyword) and method calls
# like `sql.update("table")` (keyword not inside the string).
INLINE_SQL_PATTERN = re.compile(
    r'(?:"|\')\s*(SELECT|INSERT|UPDATE|DELETE|MERGE)(?=[ \t\n])',
)

SERVICE_FILES = (
    DOMAIN_DIR / "products" / "services" / "services.py",
    DOMAIN_DIR / "system" / "services" / "services.py",
    DOMAIN_DIR / "chat" / "services" / "adk.py",
)


def test_sql_directory_and_files_exist() -> None:
    assert SQL_DIR.is_dir(), f"{SQL_DIR} must exist"
    for name in EXPECTED_FILES:
        path = SQL_DIR / name
        assert path.is_file(), f"{path} must exist with named-query directives"


@pytest.mark.parametrize("key", EXPECTED_KEYS)
def test_expected_named_query_loads(key: str) -> None:
    from app.config import db_manager

    assert db_manager.has_sql_query(key), (
        f"db_manager has no named query '{key}' — check src/py/app/db/sql/*.sql for `-- name: {key}`"
    )


def test_named_query_registry_matches_get_sql_call_sites() -> None:
    from app.config import db_manager

    referenced: set[str] = set()
    call_pattern = re.compile(r'get_sql\(\s*["\']([a-zA-Z0-9_-]+)["\']')
    for service_file in SERVICE_FILES:
        text = service_file.read_text()
        referenced.update(call_pattern.findall(text))

    assert referenced, "expected at least one db_manager.get_sql('<key>') call in domain services"

    missing = [key for key in referenced if not db_manager.has_sql_query(key)]
    assert not missing, f"get_sql() references with no matching .sql definition: {missing}"


@pytest.mark.parametrize("service_file", SERVICE_FILES, ids=lambda p: p.relative_to(SRC_ROOT).as_posix())
def test_no_inline_sql_strings_in_domain_services(service_file: Path) -> None:
    text = service_file.read_text()
    matches = INLINE_SQL_PATTERN.findall(text)
    assert not matches, (
        f"{service_file.relative_to(SRC_ROOT)} still contains inline SQL keywords: "
        f"{matches}. Use db_manager.get_sql('<key>') or sql.update/insert/delete builders."
    )
