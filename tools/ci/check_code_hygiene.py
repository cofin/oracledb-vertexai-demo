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
MANAGE_PY = ROOT_DIR / "manage.py"

ALLOWED_COMMENT_PREFIXES: tuple[str, ...] = (
    "# noqa",
    "# ruff: ignore",
    "# type: ignore",
    "# pyright:",
    "# pragma:",
    "# SPDX-FileCopyrightText:",
    "# SPDX-License-Identifier:",
    "# docs-start:",
    "# docs-end:",
    "#!",
)

ALLOWED_LAZY_IMPORT_FILES: frozenset[Path] = frozenset({
    APP_DIR / "cli" / "main.py",
    APP_DIR / "config.py",
    APP_DIR / "server" / "plugins.py",
})

ALLOWED_CONTROLLER_BASES: frozenset[str] = frozenset({
    "PublicController",
    "SecureController",
    "SkillController",
    "PromptController",
})


def check_inline_comments(paths: list[Path]) -> list[str]:
    """Verify that Python source files contain no non-directive inline comments."""
    errors: list[str] = []
    for path in paths:
        rel = path.relative_to(ROOT_DIR)
        with path.open("rb") as handle:
            for tok in tokenize.tokenize(handle.readline):
                if tok.type == tokenize.COMMENT:
                    text = tok.string.strip()
                    if not any(text.startswith(prefix) for prefix in ALLOWED_COMMENT_PREFIXES):
                        errors.append(f"{rel}:{tok.start[0]}: disallowed inline comment: {text[:60]}")
    return errors


def check_ast_rules(paths: list[Path]) -> list[str]:
    """Verify module ordering, top-level imports, Dishka annotations, and controller base classes."""
    errors: list[str] = []
    for path in paths:
        rel = path.relative_to(ROOT_DIR)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(rel))

        if path.is_relative_to(APP_DIR / "ioc"):
            errors.extend(
                f"{rel}:{node.lineno}: Dishka provider modules in src/app/ioc/ must not use "
                "from __future__ import annotations"
                for node in tree.body
                if isinstance(node, ast.ImportFrom) and node.module == "__future__"
            )

        if path not in ALLOWED_LAZY_IMPORT_FILES:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    errors.extend(
                        f"{rel}:{child.lineno}: function-scoped import inside '{node.name}' "
                        "(place imports at module top-level)"
                        for child in ast.walk(node)
                        if isinstance(child, (ast.Import, ast.ImportFrom))
                    )

        seen_private = False
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                is_private = node.name.startswith("_") and not node.name.startswith("__")
                if is_private:
                    seen_private = True
                elif seen_private:
                    errors.append(f"{rel}:{node.lineno}: public symbol '{node.name}' defined after private helper")
            if isinstance(node, ast.ClassDef) and "controllers" in path.parts:
                base_names = {_extract_base_name(base) for base in node.bases}
                if node.name.endswith("Controller") and not (base_names & ALLOWED_CONTROLLER_BASES):
                    errors.append(
                        f"{rel}:{node.lineno}: controller '{node.name}' must inherit from "
                        f"one of {sorted(ALLOWED_CONTROLLER_BASES)}"
                    )
    return errors


def main() -> int:
    """Run all code-hygiene checks across src/app and manage.py."""
    app_files = sorted(APP_DIR.rglob("*.py"))
    target_files = [*app_files, MANAGE_PY]
    violations = [*check_inline_comments(target_files), *check_ast_rules(app_files)]
    if violations:
        for violation in violations:
            sys.stderr.write(f"{violation}\n")
        return 1
    sys.stdout.write(f"Code hygiene OK ({len(target_files)} files checked).\n")
    return 0


def _extract_base_name(node: ast.expr) -> str:
    """Return the simple class name for a base-class AST expression."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _extract_base_name(node.value)
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
