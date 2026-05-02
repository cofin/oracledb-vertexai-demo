# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Insert and check concise license headers for source-owned files."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Sequence

COPYRIGHT_LINE: Final = "SPDX-FileCopyrightText: 2026 Google LLC"
LICENSE_LINE: Final = "SPDX-License-Identifier: Apache-2.0"

HEADER_SCAN_BYTES: Final = 4096

COPYRIGHT_RE: Final = re.compile(
    r"(?i)(?:Copyright|SPDX-FileCopyrightText:)\s+"
    r"(?:Copyright\s+)?(?:\(C\)\s+)?\d{4}(?:[-,]\s*\d{4})*\s+Google LLC",
)
LICENSE_RE: Final = re.compile(r"SPDX-License-Identifier:\s+Apache-2\.0")
CODING_RE: Final = re.compile(r"coding[:=]\s*[-\w.]+")
DOCKERFILE_DIRECTIVE_RE: Final = re.compile(r"#\s*(?:syntax|escape|check)=")

LINE_PREFIX_BY_SUFFIX: Final = {
    ".py": "#",
    ".pyi": "#",
    ".sh": "#",
    ".toml": "#",
    ".yaml": "#",
    ".yml": "#",
}
LINE_PREFIX_BY_NAME: Final = {
    ".pre-commit-config.yaml": "#",
    "Makefile": "#",
}
SLASH_SUFFIXES: Final = frozenset({".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"})
SQL_SUFFIXES: Final = frozenset({".sql"})
CSS_SUFFIXES: Final = frozenset({".css"})
JINJA_SUFFIXES: Final = (".html.j2",)

DEFAULT_TARGETS: Final = (
    ".pre-commit-config.yaml",
    "Makefile",
    "manage.py",
    "vite.config.ts",
    "src/app",
    "src/tests",
    "src/resources",
    "tools",
)
SKIP_PARTS: Final = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "dist",
        "node_modules",
    }
)
SKIP_PART_WINDOWS: Final = (
    ("src", "resources", "generated"),
    ("src", "resources", "public"),
)


@dataclass(frozen=True, slots=True)
class HeaderResult:
    """Result for a single license-header check."""

    path: Path
    supported: bool
    missing: bool = False
    changed: bool = False
    reason: str = ""


def ensure_header(path: Path, *, fix: bool = False) -> HeaderResult:
    """Ensure that a supported file has the project license header."""
    style = _header_for(path)
    if style is None:
        return HeaderResult(path=path, supported=False, reason="unsupported")

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return HeaderResult(path=path, supported=False, reason="non-utf8")

    if _has_header(text):
        return HeaderResult(path=path, supported=True)

    if not fix:
        return HeaderResult(path=path, supported=True, missing=True)

    path.write_text(_insert_header(text, style), encoding="utf-8")
    return HeaderResult(path=path, supported=True, missing=True, changed=True)


def collect_results(paths: Sequence[str], *, fix: bool = False) -> list[HeaderResult]:
    """Check or update every candidate file under the supplied paths."""
    return [ensure_header(path, fix=fix) for path in _candidate_files(paths)]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the license header checker."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix", action="store_true", help="insert missing headers in supported files")
    parser.add_argument("paths", nargs="*", help="files or directories to check")
    args = parser.parse_args(argv)

    results = collect_results(args.paths, fix=args.fix)
    missing = [result for result in results if result.supported and result.missing]
    changed = [result for result in missing if result.changed]
    unchanged_missing = [result for result in missing if not result.changed]

    if changed:
        sys.stderr.write("license headers added:\n")
        for result in changed:
            sys.stderr.write(f"  {_display_path(result.path)}\n")
        return 1

    if unchanged_missing:
        sys.stderr.write("license headers missing:\n")
        for result in unchanged_missing:
            sys.stderr.write(f"  {_display_path(result.path)}\n")
        sys.stderr.write("Run `uv run python tools/license_headers.py --fix` to update them.\n")
        return 1

    return 0


def _candidate_files(paths: Sequence[str]) -> list[Path]:
    target_paths = tuple(paths) if paths else DEFAULT_TARGETS
    candidates: list[Path] = []
    seen: set[Path] = set()

    for raw_path in target_paths:
        path = Path(raw_path)
        iterable = path.rglob("*") if path.is_dir() else (path,)
        for candidate in iterable:
            if not candidate.is_file() or _should_skip(candidate):
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            candidates.append(candidate)

    return candidates


def _should_skip(path: Path) -> bool:
    if set(path.parts) & SKIP_PARTS:
        return True
    return any(_contains_part_window(path, window) for window in SKIP_PART_WINDOWS)


def _contains_part_window(path: Path, window: tuple[str, ...]) -> bool:
    parts = path.parts
    width = len(window)
    return any(parts[index : index + width] == window for index in range(len(parts) - width + 1))


def _header_for(path: Path) -> str | None:
    if _should_skip(path):
        return None

    prefix = _line_prefix_for(path)
    if prefix is not None:
        return _line_header(prefix)
    if path.suffix in CSS_SUFFIXES:
        return f"/*\n * {COPYRIGHT_LINE}\n * {LICENSE_LINE}\n */\n"
    if path.name.endswith(JINJA_SUFFIXES):
        return f"{{#\n{COPYRIGHT_LINE}\n{LICENSE_LINE}\n#}}\n"

    return None


def _line_prefix_for(path: Path) -> str | None:
    if path.name in LINE_PREFIX_BY_NAME:
        return LINE_PREFIX_BY_NAME[path.name]
    if path.name.startswith("Dockerfile"):
        return "#"
    if path.suffix in LINE_PREFIX_BY_SUFFIX:
        return LINE_PREFIX_BY_SUFFIX[path.suffix]
    if path.suffix in SLASH_SUFFIXES:
        return "//"
    if path.suffix in SQL_SUFFIXES:
        return "--"
    return None


def _line_header(prefix: str) -> str:
    return f"{prefix} {COPYRIGHT_LINE}\n{prefix} {LICENSE_LINE}\n"


def _has_header(text: str) -> bool:
    head = text[:HEADER_SCAN_BYTES]
    return COPYRIGHT_RE.search(head) is not None and LICENSE_RE.search(head) is not None


def _insert_header(text: str, header: str) -> str:
    lines = text.splitlines(keepends=True)
    insert_at = _insertion_index(lines)
    before = "".join(lines[:insert_at])
    after = "".join(lines[insert_at:])
    separator = "" if not after or after.startswith(("\n", "\r\n")) else "\n"
    return f"{before}{header}{separator}{after}"


def _insertion_index(lines: Sequence[str]) -> int:
    index = 0
    if lines and (lines[0].startswith("#!") or DOCKERFILE_DIRECTIVE_RE.match(lines[0]) is not None):
        index = 1
    if len(lines) > index and CODING_RE.search(lines[index]) is not None:
        index += 1
    return index


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
