# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Repository AST and token code-hygiene gate for Cymbal Coffee."""

from __future__ import annotations

import ast
import sys
import tokenize
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
APP_DIR = ROOT_DIR / "src" / "app"
TOOLS_DIR = ROOT_DIR / "tools"
MANAGE_PY = ROOT_DIR / "manage.py"

__all__ = (
    "ALLOWED_COMMENT_PREFIXES",
    "ALLOWED_LAZY_IMPORT_FILES",
    "APP_DIR",
    "MANAGE_PY",
    "ROOT_DIR",
    "TOOLS_DIR",
    "check_ast_rules",
    "check_inline_comments",
    "main",
)

ALLOWED_COMMENT_PREFIXES: tuple[str, ...] = (
    "# noqa",
    "# ruff: ignore",
    "# type: ignore",
    "# pyright:",
    "# pragma:",
    "# fmt:",
    "# SPDX-FileCopyrightText:",
    "# SPDX-License-Identifier:",
    "# docs-start:",
    "# docs-end:",
    "#!",
)

ALLOWED_LAZY_IMPORT_FILES: frozenset[Path] = frozenset({APP_DIR / "cli" / "commands.py", APP_DIR / "cli" / "main.py"})


def check_inline_comments(paths: list[Path]) -> list[str]:
    """Verify that Python source files contain no non-directive inline comments."""
    errors: list[str] = []
    for path in paths:
        rel = _display_path(path)
        with path.open("rb") as handle:
            for tok in tokenize.tokenize(handle.readline):
                if tok.type == tokenize.COMMENT:
                    text = tok.string.strip()
                    if not any(text.startswith(prefix) for prefix in ALLOWED_COMMENT_PREFIXES):
                        errors.append(f"{rel}:{tok.start[0]}: disallowed inline comment: {text[:60]}")
    return errors


def check_ast_rules(paths: list[Path]) -> list[str]:
    """Verify module docstrings, ordering, top-level imports, Dishka annotations, and dataclass slots."""
    errors: list[str] = []
    for path in paths:
        rel = _display_path(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)

        if ast.get_docstring(tree) is None:
            errors.append(f"{rel}:1: module is missing a top-level docstring")

        if _is_ioc_provider_path(path):
            errors.extend(
                f"{rel}:{node.lineno}: Dishka provider modules in src/app/ioc/ must not use "
                "from __future__ import annotations"
                for node in tree.body
                if isinstance(node, ast.ImportFrom) and node.module == "__future__"
            )

        for node in ast.walk(tree):
            if path not in ALLOWED_LAZY_IMPORT_FILES and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                errors.extend(
                    f"{rel}:{child.lineno}: function-scoped import inside '{node.name}' "
                    "(place imports at module top-level)"
                    for child in ast.walk(node)
                    if isinstance(child, (ast.Import, ast.ImportFrom))
                )
            if isinstance(node, ast.ClassDef) and _is_unslotted_dataclass(node):
                errors.append(f"{rel}:{node.lineno}: @dataclass class '{node.name}' must specify slots=True")

        seen_private = False
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                is_private = node.name.startswith("_") and not node.name.startswith("__")
                if is_private:
                    seen_private = True
                elif seen_private:
                    errors.append(f"{rel}:{node.lineno}: public symbol '{node.name}' defined after private helper")
    return errors


def main() -> int:
    """Run all code-hygiene checks across src/app, tools, and manage.py."""
    target_files = sorted({*APP_DIR.rglob("*.py"), *TOOLS_DIR.rglob("*.py"), MANAGE_PY})
    violations = [*check_inline_comments(target_files), *check_ast_rules(target_files)]
    if violations:
        for violation in violations:
            sys.stderr.write(f"{violation}\n")
        return 1
    sys.stdout.write(f"Code hygiene OK ({len(target_files)} files checked).\n")
    return 0


def _display_path(path: Path) -> str:
    """Format a path relative to the repository root when possible."""
    if path.is_relative_to(ROOT_DIR):
        return str(path.relative_to(ROOT_DIR))
    return str(path)


def _is_ioc_provider_path(path: Path) -> bool:
    """Return whether a path targets a Dishka provider module under src/app/ioc/."""
    if path.is_relative_to(APP_DIR / "ioc"):
        return True
    return path.parts[-4:-1] == ("src", "app", "ioc")


def _is_unslotted_dataclass(node: ast.ClassDef) -> bool:
    """Return True when ``node`` carries a ``@dataclass`` decorator without ``slots=True``."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "dataclass":
            return True
        if isinstance(dec, ast.Attribute) and dec.attr == "dataclass":
            return True
        if isinstance(dec, ast.Call):
            func_name = (
                dec.func.id
                if isinstance(dec.func, ast.Name)
                else (dec.func.attr if isinstance(dec.func, ast.Attribute) else "")
            )
            if func_name == "dataclass":
                slots_kw = next((kw.value for kw in dec.keywords if kw.arg == "slots"), None)
                if not (isinstance(slots_kw, ast.Constant) and slots_kw.value is True):
                    return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
