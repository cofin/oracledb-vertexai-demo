# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Convention guard for msgspec Struct names in `app/domain/*/schemas/`.

Project rule (declared 2026-04-29): Structs are named after the *entity*,
with optional `Create` / `Update` suffixes for mutating inputs and
entity-first qualifiers for projections (e.g., `ProductMatch`,
`MetricsChart`). Names must NOT end in `Result`, `Response`, `Read`,
`Request`, `Data`, or `DTO` — those are role-of-the-shape markers, not
entity names. Strip them.

Examples of allowed forms:
- `Product`, `Store`, `EmbeddingCache`         (entity)
- `ProductCreate`, `ProductUpdate`            (mutating input)
- `ProductMatch`, `MetricsChart`, `MetricsSummary`  (entity-first qualifier)

Examples of forbidden forms:
- `IntentResult`, `MetricsSummaryResponse`, `UserSessionRead`,
  `VectorDemoRequest`, `ChartDataResponse`, `TimeSeriesData`, `ProductDTO`

This test walks the AST of every `_*.py` under each domain's schemas
package and asserts that no `class X(<Camelized|msgspec.Struct>...)`
declaration ends in a banned suffix.
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

import pytest

from tests.support.paths import APP_ROOT, SRC_ROOT

if TYPE_CHECKING:
    from pathlib import Path

DOMAIN_DIR = APP_ROOT / "domain"

# Suffixes that signal "role of the shape in a request/response cycle"
# rather than "what entity this is". Must be applied as suffix, not
# substring: `ResponseCache` is fine (it's a *cache* of responses, with
# 'Cache' as the entity-tail), but `ChartDataResponse` is not.
BANNED_SUFFIXES: tuple[str, ...] = (
    "Result",
    "Response",
    "Read",
    "Request",
    "Data",
    "DTO",
)

# Bases that mark a class as a wire-format Struct that we want to govern.
# We match by the base class's *name* in source (we can't always import it
# at AST time without executing the module).
STRUCT_BASE_NAMES: frozenset[str] = frozenset(
    {"CamelizedBaseStruct", "Struct"}
)


def _schema_files() -> list[Path]:
    """Every domain schema source file (excluding __init__ and dunders)."""
    files: list[Path] = []
    for schemas_dir in DOMAIN_DIR.glob("*/schemas"):
        for path in schemas_dir.glob("_*.py"):
            if path.name.startswith("__"):
                continue
            files.append(path)
    return sorted(files)


def _struct_class_names(path: Path) -> list[str]:
    """Return the names of every class in `path` that subclasses a Struct base."""
    tree = ast.parse(path.read_text())
    names: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            base_name: str | None = None
            if isinstance(base, ast.Name):
                base_name = base.id
            elif isinstance(base, ast.Attribute):
                base_name = base.attr
            if base_name in STRUCT_BASE_NAMES:
                names.append(node.name)
                break
    return names


def test_schema_files_are_discoverable() -> None:
    files = _schema_files()
    assert files, (
        f"expected at least one domain schema file under {DOMAIN_DIR}/*/schemas/_*.py"
    )


@pytest.mark.parametrize(
    "schema_file",
    _schema_files(),
    ids=lambda p: p.relative_to(SRC_ROOT).as_posix(),
)
def test_no_banned_suffixes_in_struct_names(schema_file: Path) -> None:
    """Every Struct subclass name must avoid the role-of-shape suffixes."""
    offenders: list[tuple[str, str]] = []
    for class_name in _struct_class_names(schema_file):
        for suffix in BANNED_SUFFIXES:
            if class_name.endswith(suffix) and class_name != suffix:
                offenders.append((class_name, suffix))
                break

    assert not offenders, (
        f"{schema_file.relative_to(SRC_ROOT)} declares Structs with banned suffixes: "
        f"{offenders}. Rename to entity-first form (e.g., 'MetricsSummaryResponse' "
        "→ 'MetricsSummary', 'ChartDataResponse' → 'MetricsChart', "
        "'UserSessionRead' → 'UserSession')."
    )


def test_dto_wording_absent_from_schema_docstrings() -> None:
    """Schema docstrings must not call themselves "DTO" — the project doesn't use Litestar DTOs."""
    pattern = re.compile(r"\bDTO\b", flags=re.IGNORECASE)
    offenders: list[tuple[str, str]] = []
    for path in _schema_files():
        text = path.read_text()
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            offenders.append((path.relative_to(SRC_ROOT).as_posix(), f"line {line_no}"))

    assert not offenders, (
        "schema files mention 'DTO' in docstrings/comments — the project uses msgspec "
        f"Structs as the wire format, not Litestar DTOs. Offenders: {offenders}"
    )
