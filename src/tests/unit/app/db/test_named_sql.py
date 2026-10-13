# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from app.config import db_manager
from tests.support.paths import APP_ROOT, SRC_ROOT

if TYPE_CHECKING:
    from pathlib import Path

SQL_DIR = APP_ROOT / "db" / "sql"
DOMAIN_DIR = APP_ROOT / "domain"

EXPECTED_FILES = ("ai-runtime.sql", "hybrid.sql", "inventory.sql", "products.sql", "stores.sql", "system.sql")

_NAME_DIRECTIVE = re.compile(r"^--\s*name:\s*([a-zA-Z0-9_-]+)", flags=re.MULTILINE)


def _discover_named_keys() -> tuple[str, ...]:
    keys: set[str] = set()
    for sql_file in sorted(SQL_DIR.glob("*.sql")):
        keys.update(_NAME_DIRECTIVE.findall(sql_file.read_text()))
    return tuple(sorted(keys))


def _discover_service_files() -> tuple[Path, ...]:
    files = [p for p in sorted(DOMAIN_DIR.glob("*/services/*.py")) if p.name != "__init__.py"]
    ai_store = DOMAIN_DIR / "ai" / "runtime" / "_store.py"
    if ai_store.exists():
        files.append(ai_store)
    return tuple(files)


EXPECTED_KEYS = _discover_named_keys()

INLINE_SQL_PATTERN = re.compile(r'(?:"|\')\s*(SELECT|INSERT|UPDATE|DELETE|MERGE)(?=[ \t\n])')

SERVICE_FILES = _discover_service_files()


def test_sql_directory_and_files_exist() -> None:
    assert SQL_DIR.is_dir(), f"{SQL_DIR} must exist"
    for name in EXPECTED_FILES:
        path = SQL_DIR / name
        assert path.is_file(), f"{path} must exist with named-query directives"


@pytest.mark.parametrize("key", EXPECTED_KEYS)
def test_expected_named_query_loads(key: str) -> None:
    assert db_manager.has_sql_query(key), (
        f"db_manager has no named query '{key}' — check src/app/db/sql/*.sql for `-- name: {key}`"
    )


def test_named_query_registry_matches_get_sql_call_sites() -> None:
    referenced: set[str] = set()
    call_pattern = re.compile(r'get_sql\(\s*["\']([a-zA-Z0-9_-]+)["\']')
    for py_file in sorted(APP_ROOT.rglob("*.py")):
        text = py_file.read_text()
        referenced.update(call_pattern.findall(text))

    assert referenced, "expected at least one db_manager.get_sql('<key>') call in src/app"

    missing = [key for key in sorted(referenced) if not db_manager.has_sql_query(key)]
    assert not missing, f"get_sql() references with no matching .sql definition: {missing}"

    unreferenced = sorted(set(EXPECTED_KEYS) - referenced)
    assert not unreferenced, f"Named SQL queries with no get_sql() reference in src/app: {unreferenced}"


@pytest.mark.parametrize("service_file", SERVICE_FILES, ids=lambda p: p.relative_to(SRC_ROOT).as_posix())
def test_no_inline_sql_strings_in_domain_services(service_file: Path) -> None:
    text = service_file.read_text()
    matches = INLINE_SQL_PATTERN.findall(text)
    assert not matches, (
        f"{service_file.relative_to(SRC_ROOT)} still contains inline SQL keywords: "
        f"{matches}. Use db_manager.get_sql('<key>') or sql.update/insert/delete builders."
    )
