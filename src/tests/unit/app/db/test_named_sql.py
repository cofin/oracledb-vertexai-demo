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

_NAME_DIRECTIVE = re.compile(r"^--\s*name:\s*([a-zA-Z0-9_-]+)", flags=re.MULTILINE)


def _discover_named_keys() -> tuple[str, ...]:
    keys: set[str] = set()
    for sql_file in sorted(SQL_DIR.glob("*.sql")):
        keys.update(_NAME_DIRECTIVE.findall(sql_file.read_text()))
    return tuple(sorted(keys))


def _discover_service_files() -> tuple[Path, ...]:
    files = sorted(DOMAIN_DIR.glob("*/services/services.py"))
    files.append(DOMAIN_DIR / "chat" / "services" / "adk.py")
    return tuple(files)


# Every `-- name: <key>` directive declared across db/sql/*.sql.
EXPECTED_KEYS = _discover_named_keys()

# Match a SQL keyword inside a Python string literal *only* when followed by whitespace
# (real SQL: `SELECT id`, `UPDATE foo`). Excludes false positives like the named-query
# key string `"update-product-embedding"` (hyphen after the keyword) and method calls
# like `sql.update("table")` (keyword not inside the string).
INLINE_SQL_PATTERN = re.compile(
    r'(?:"|\')\s*(SELECT|INSERT|UPDATE|DELETE|MERGE)(?=[ \t\n])',
)

# Domain services that must source SQL from db_manager, never inline strings.
SERVICE_FILES = _discover_service_files()


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
