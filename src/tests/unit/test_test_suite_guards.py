# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Automated meta-guards enforcing `src/tests/AGENTS.md`, canonical test layout, and `src/app/` code hygiene."""

from __future__ import annotations

import ast
import io
import tokenize
import tomllib
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = TESTS_ROOT.parents[1]
APP_ROOT = REPO_ROOT / "src" / "app"

DEFAULT_TESTPATHS = ("src/tests",)
ALLOWED_CONFTESTS = frozenset({"conftest.py", "unit/conftest.py", "integration/conftest.py"})
CONFTEST_COUNT_HIGH_WATER = len(ALLOWED_CONFTESTS)

ALLOWED_PRAGMAS = (
    "# noqa",
    "# ruff: ignore",
    "# type: ignore",
    "# pyright:",
    "# pragma:",
    "# fmt:",
    "# docs-start:",
    "# docs-end:",
)

ALLOW_NESTED_IMPORTS = frozenset({
    "src/app/cli/commands.py",
    "src/app/cli/main.py",
    "src/app/config.py",
    "src/app/server/plugins.py",
})

KEEP_LIST_PATHS = (
    "unit/domain/chat/services/test_hybrid_router.py",
    "unit/domain/chat/services/test_grounded_routes.py",
    "unit/domain/ai/runtime/test_loop_stream.py",
    "unit/domain/ai/runtime/test_model_store.py",
    "unit/domain/ai/test_agent_orchestration.py",
    "unit/db/test_named_sql.py",
    "unit/lib/test_settings.py",
    "integration/db/test_sqlspec_connection.py",
    "integration/domain/products/services/test_vector_search.py",
)

DELETED_LEGACY_PATHS = (
    "src/app/ioc.py",
    "src/app/lib/settings.py",
    "src/app/domain/chat/services/classifier.py",
    "src/app/db/migrations/__init__.py",
    "src/app/db/migrations/0002_native_ai_and_hybrid_rrf.sql",
    "src/app/db/migrations/0003_drop_intent_exemplar.sql",
    "src/tests/api",
    "src/tests/unit/app",
    "src/tests/integration/app",
    "src/tests/unit/domain/ai/test_store.py",
    "src/tests/unit/tools/cli",
    "src/tests/unit/tools/oracle",
    "src/tests/unit/tools/scripts",
    "src/tests/unit/tools/slides/conftest.py",
)


def _iter_test_python_files() -> list[Path]:
    """Return all Python files under `src/tests/` in deterministic order."""
    return sorted(TESTS_ROOT.rglob("*.py"))


def _iter_app_python_files() -> list[Path]:
    """Return all Python files under `src/app/` in deterministic order."""
    return sorted(APP_ROOT.rglob("*.py"))


def _imports_unittest_mock(tree: ast.Module) -> bool:
    """Return True if an AST module imports `unittest.mock`."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(alias.name.startswith("unittest.mock") for alias in node.names):
            return True
        if isinstance(node, ast.ImportFrom):
            if node.module == "unittest" and any(alias.name == "mock" for alias in node.names):
                return True
            if node.module is not None and node.module.startswith("unittest.mock"):
                return True
    return False


def _is_allowed_comment(comment_text: str) -> bool:
    """Return True if a comment token is an SPDX header, shebang, or allowed linter pragma."""
    stripped = comment_text.strip()
    if stripped.startswith(("#!", "# SPDX-")):
        return True
    return any(stripped.startswith(pragma) for pragma in ALLOWED_PRAGMAS)


def _method_category(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Classify a class method into ordering categories (0: `__init__`, 1: property, 2: public, 3: private)."""
    if node.name in {"__init__", "__new__", "__post_init__"}:
        return 0
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "property":
            return 1
        if isinstance(dec, ast.Attribute) and dec.attr in {"setter", "deleter", "getter"}:
            return 1
    if node.name.startswith("_") and not (node.name.startswith("__") and node.name.endswith("__")):
        return 3
    return 2


def test_only_authorized_conftest_files_exist() -> None:
    """Verify no domain-level or ad-hoc `conftest.py` files exist outside the 3 layer roots."""
    actual = {p.relative_to(TESTS_ROOT).as_posix() for p in TESTS_ROOT.rglob("conftest.py")}
    assert actual == ALLOWED_CONFTESTS


def test_conftest_count_ratchet() -> None:
    """Verify total `conftest.py` count never exceeds the 3-layer-root ratchet."""
    count = sum(1 for _ in TESTS_ROOT.rglob("conftest.py"))
    assert count <= CONFTEST_COUNT_HIGH_WATER


def test_default_testpaths_configured() -> None:
    """Verify `pyproject.toml` default pytest `testpaths` matches `DEFAULT_TESTPATHS`."""
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    found = tuple(config["tool"]["pytest"]["ini_options"]["testpaths"])
    assert found == DEFAULT_TESTPATHS


def test_unittest_mock_is_banned_under_integration_and_fixtures() -> None:
    """Verify `unittest.mock` is never imported under `integration/` or `fixtures/`."""
    violations: list[str] = []
    for path in _iter_test_python_files():
        rel = path.relative_to(TESTS_ROOT).as_posix()
        if not rel.startswith(("integration/", "fixtures/")):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        if _imports_unittest_mock(tree):
            violations.append(rel)
    assert violations == []


def test_no_test_classes_in_test_suite() -> None:
    """Verify test modules use top-level `test_*` functions rather than `class Test*`."""
    violations: list[str] = []
    for path in _iter_test_python_files():
        rel = path.relative_to(TESTS_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        violations.extend(
            f"{rel}:{node.lineno}:{node.name}"
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name.startswith("Test")
        )
    assert violations == []


def test_no_inline_comments_across_app_and_tests() -> None:
    """Verify zero non-pragma inline `#` comments exist across `src/app/` and `src/tests/`."""
    violations: list[str] = []
    for path in [*_iter_app_python_files(), *_iter_test_python_files()]:
        rel = path.relative_to(REPO_ROOT).as_posix()
        source = path.read_text(encoding="utf-8")
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        violations.extend(
            f"{rel}:{tok.start[0]}:{tok.string.strip()}"
            for tok in tokens
            if tok.type == tokenize.COMMENT and not _is_allowed_comment(tok.string)
        )
    assert violations == []


def test_no_nested_imports_across_app_and_tests() -> None:
    """Verify zero function-scoped imports exist across `src/app/` and `src/tests/`."""
    violations: list[str] = []
    for path in [*_iter_app_python_files(), *_iter_test_python_files()]:
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in ALLOW_NESTED_IMPORTS:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                violations.extend(
                    f"{rel}:{child.lineno}:{node.name}"
                    for child in ast.walk(node)
                    if isinstance(child, (ast.Import, ast.ImportFrom))
                )
    assert violations == []


def test_all_production_modules_define_docstring_and_all() -> None:
    """Verify every non-`__init__.py` module under `src/app/` has a module docstring and `__all__`."""
    missing_doc: list[str] = []
    missing_all: list[str] = []
    for path in _iter_app_python_files():
        if path.name == "__init__.py":
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        if not ast.get_docstring(tree):
            missing_doc.append(rel)
        has_all = any(
            (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets))
            or (isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id == "__all__")
            for n in tree.body
        )
        if not has_all:
            missing_all.append(rel)
    assert missing_doc == []
    assert missing_all == []


def test_all_test_modules_define_docstring() -> None:
    """Verify every non-`__init__.py` module under `src/tests/` has a module docstring."""
    missing_doc: list[str] = []
    for path in _iter_test_python_files():
        if path.name == "__init__.py":
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        if not ast.get_docstring(tree):
            missing_doc.append(rel)
    assert missing_doc == []


def test_all_test_functions_define_docstring() -> None:
    """Verify every `def test_*` and `async def test_*` function across `src/tests/` has a docstring."""
    missing_doc: list[str] = []
    for path in _iter_test_python_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        missing_doc.extend(
            f"{rel}:{node.lineno}:{node.name}"
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            and not ast.get_docstring(node)
        )
    assert missing_doc == []


def test_test_module_helper_ordering_and_no_nested_classes() -> None:
    """Verify test modules define private `_...` helpers before `def test_*` and never nest classes inside tests."""
    violations: list[str] = []
    for path in _iter_test_python_files():
        if not path.name.startswith("test_"):
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        seen_test = False
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                seen_test = True
            elif (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and node.name.startswith("_")
                and not node.name.startswith("__")
                and seen_test
            ):
                violations.append(f"{rel}:{node.lineno}:{node.name} defined after test_* function")
        for item in ast.walk(tree):
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test_"):
                violations.extend(
                    f"{rel}:{child.lineno}:nested class {child.name} inside {item.name}"
                    for child in ast.walk(item)
                    if isinstance(child, ast.ClassDef)
                )
    assert violations == []


def test_production_class_method_ordering() -> None:
    """Verify production classes place `__init__` -> properties -> public methods -> private `_...` methods."""
    violations: list[str] = []
    for path in _iter_app_python_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            max_cat = -1
            max_name = ""
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    cat = _method_category(item)
                    if cat < max_cat:
                        violations.append(f"{rel}:{item.lineno}:{node.name}.{item.name} after {max_name}")
                    else:
                        max_cat = cat
                        max_name = item.name
    assert violations == []


def test_deleted_legacy_paths_do_not_return() -> None:
    """Verify retired shims, squashed migrations, and nested `app/` test directories stay deleted."""
    existing = [rel for rel in DELETED_LEGACY_PATHS if (REPO_ROOT / rel).exists()]
    assert existing == []


def test_keep_list_files_exist() -> None:
    """Verify every reference test module on the `src/tests/AGENTS.md` keep-list exists."""
    missing = [rel for rel in KEEP_LIST_PATHS if not (TESTS_ROOT / rel).is_file()]
    assert missing == []
