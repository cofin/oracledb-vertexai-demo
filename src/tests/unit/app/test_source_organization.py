# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Public-first source organization guardrails."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tests.support.paths import PROJECT_ROOT

if TYPE_CHECKING:
    from pathlib import Path

SOURCE_ROOTS = (PROJECT_ROOT / "src" / "app", PROJECT_ROOT / "tools")
MIN_SOURCE_FILE_COUNT = 89
PUBLIC_UNDERSCORE_MODULES = frozenset(
    {
        "src/app/domain/chat/controllers/_chat.py",
        "src/app/domain/chat/schemas/_chat.py",
        "src/app/domain/products/controllers/_products.py",
        "src/app/domain/products/controllers/_vector.py",
        "src/app/domain/products/schemas/_products.py",
        "src/app/domain/system/controllers/_metrics.py",
        "src/app/domain/system/controllers/_system.py",
        "src/app/domain/system/schemas/_cache.py",
        "src/app/domain/system/schemas/_metrics.py",
        "src/app/domain/system/schemas/_session.py",
        "src/app/domain/web/controllers/_pages.py",
    }
)
PRIVATE_HELPER_PACKAGES = frozenset({"_helpers"})
MODULE_INFRASTRUCTURE_FILES = frozenset({"__init__.py", "__main__.py", "__metadata__.py"})
DOMAIN_CONTROLLER_ENTRYPOINTS = {
    "src/app/domain/chat/controllers/_chat.py": "CoffeeChatController",
    "src/app/domain/products/controllers/_products.py": "ProductController",
    "src/app/domain/products/controllers/_vector.py": "VectorController",
    "src/app/domain/system/controllers/_metrics.py": "MetricsController",
    "src/app/domain/system/controllers/_system.py": "SystemController",
    "src/app/domain/web/controllers/_pages.py": "PageController",
}
TEMPORARY_HOTSPOT_ALLOWLIST: dict[str, str] = {}


@dataclass(frozen=True)
class TopLevelDefinition:
    """Top-level public or private definition in a Python module."""

    name: str
    line: int

    @property
    def is_private_helper(self) -> bool:
        return self.name.startswith("_") and not self.name.startswith("__")


def _project_path(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _source_files() -> list[Path]:
    return sorted(path for root in SOURCE_ROOTS for path in root.rglob("*.py"))


def _is_public_module(path: Path) -> bool:
    project_path = _project_path(path)
    if path.name in MODULE_INFRASTRUCTURE_FILES:
        return False
    if any(part in PRIVATE_HELPER_PACKAGES for part in path.parts):
        return False
    return not path.name.startswith("_") or project_path in PUBLIC_UNDERSCORE_MODULES


def _top_level_definitions(path: Path) -> list[TopLevelDefinition]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        TopLevelDefinition(name=node.name, line=node.lineno)
        for node in tree.body
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
    ]


def _private_definition_prefix(definitions: list[TopLevelDefinition]) -> list[TopLevelDefinition]:
    prefix: list[TopLevelDefinition] = []
    for definition in definitions:
        if not definition.is_private_helper:
            break
        prefix.append(definition)
    return prefix


def test_source_audit_scans_app_and_tools_python_files() -> None:
    source_files = {_project_path(path) for path in _source_files()}

    assert len(source_files) >= MIN_SOURCE_FILE_COUNT
    assert "src/app/domain/chat/services/adk.py" in source_files
    assert "tools/oracle/database.py" in source_files


def test_temporary_hotspot_allowlist_entries_are_actionable() -> None:
    source_files = {_project_path(path): path for path in _source_files()}

    for project_path, reason in TEMPORARY_HOTSPOT_ALLOWLIST.items():
        assert reason.strip(), f"{project_path} needs a reason for its temporary source organization exception"
        assert project_path in source_files, f"{project_path} is allowlisted but no longer exists"

        private_prefix = _private_definition_prefix(_top_level_definitions(source_files[project_path]))
        assert len(private_prefix) > 1, f"{project_path} is allowlisted but no longer starts with private helpers"


def test_public_modules_do_not_start_with_private_helper_runs() -> None:
    offenders: dict[str, list[str]] = {}
    for path in _source_files():
        project_path = _project_path(path)
        if not _is_public_module(path) or project_path in TEMPORARY_HOTSPOT_ALLOWLIST:
            continue

        private_prefix = _private_definition_prefix(_top_level_definitions(path))
        if len(private_prefix) > 1:
            offenders[project_path] = [f"{definition.name}:{definition.line}" for definition in private_prefix]

    assert offenders == {}


def test_domain_controller_modules_start_with_controller_classes() -> None:
    source_files = {_project_path(path): path for path in _source_files()}

    for project_path, expected_controller in DOMAIN_CONTROLLER_ENTRYPOINTS.items():
        definitions = _top_level_definitions(source_files[project_path])
        assert definitions, f"{project_path} has no public controller definition"
        assert definitions[0].name == expected_controller, (
            f"{project_path} should lead with {expected_controller}, got {definitions[0].name}"
        )
