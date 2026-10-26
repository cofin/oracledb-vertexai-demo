# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests enforcing factual path, Make-target, symbol, and privacy accuracy across public documentation."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MAKEFILE_PATH = REPO_ROOT / "Makefile"

REPO_PATH_RE = re.compile(r"`((?:src|tools|docs)/[A-Za-z0-9_./-]+)`")
MAKE_CMD_RE = re.compile(r"(?:^|[\s`$])make\s+([a-z][a-z0-9_-]*)\b")
MAKEFILE_TARGET_RE = re.compile(r"^([a-zA-Z0-9_-]+)\s*:(?!=)", re.MULTILINE)
INTERNAL_SHORTLINK_RE = re.compile(r"(?<![A-Za-z0-9_./-])go/[a-z0-9][a-z0-9_-]{2,}", re.IGNORECASE)
INTERNAL_APP_RE = re.compile(r"\b(?:db-skus|beekeeper|dma_classic)\b", re.IGNORECASE)

IGNORED_GENERATED_PREFIXES: tuple[str, ...] = (
    "docs/_build",
    "docs/_static/demos/",
    "src/app/domain/web/static",
    "src/resources/generated",
    "src/resources/public",
    "tools/oracle/downloads",
)

RETIRED_DOC_TOKENS: tuple[str, ...] = (
    "enable_AutoLob",
    "OrdsSidecar",
    "apex_install.py",
    "apex_media.py",
    "manage.py infra ords",
    "manage.py infra apex install",
    "LITESTAR_PORT=5006",
    "localhost:5006",
    "ADK_SESSION_TABLE",
    "make_container",
    "ResponseCacheService",
    "SystemService",
    "InventoryService",
    "EmbeddingService",
    "MapsService",
    "LitestarPersistenceProvider",
    "IntegrationsProvider",
    "tools/deploy/gcp/configure-apex-cdn.sql",
)

FORBIDDEN_PATH_PREFIXES: tuple[str, ...] = ("/usr/local/google/home/", "/google/src/")


def _public_doc_files() -> list[Path]:
    """Collect all tracked public Markdown documentation files in deterministic order."""
    explicit = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "CONTRIBUTING.md",
        REPO_ROOT / "SLIDES.md",
        REPO_ROOT / "src" / "app" / "db" / "migrations" / "README.md",
        REPO_ROOT / "src" / "apex" / "README.md",
    ]
    sphinx_docs = sorted((REPO_ROOT / "docs").rglob("*.md"))
    return [path for path in [*explicit, *sphinx_docs] if path.is_file()]


def _makefile_targets() -> set[str]:
    """Parse all target names declared in the root ``Makefile``."""
    raw = MAKEFILE_PATH.read_text(encoding="utf-8")
    targets = set(MAKEFILE_TARGET_RE.findall(raw))
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith(".PHONY:"):
            targets.update(stripped.removeprefix(".PHONY:").split())
    return targets


def _extract_make_invocations(markdown_text: str) -> list[str]:
    """Extract ``make <target>`` invocations from inline code spans and shell code blocks."""
    found: list[str] = []
    for inline_span in re.findall(r"`([^`\n]+)`", markdown_text):
        found.extend(MAKE_CMD_RE.findall(inline_span))
    for fence in re.findall(r"```(?:bash|sh|shell|console)?\n(.*?)```", markdown_text, flags=re.DOTALL):
        for raw_line in fence.splitlines():
            stripped = raw_line.strip()
            if stripped.startswith("#"):
                continue
            found.extend(MAKE_CMD_RE.findall(stripped))
    return found


def test_public_docs_repository_file_references_exist() -> None:
    """Verify every backtick-quoted ``src/...``, ``tools/...``, and ``docs/...`` path exists on disk."""
    missing: list[str] = []
    for doc_path in _public_doc_files():
        rel_doc = doc_path.relative_to(REPO_ROOT).as_posix()
        text = doc_path.read_text(encoding="utf-8")
        for match in REPO_PATH_RE.finditer(text):
            candidate = match.group(1).rstrip(".,;:")
            if "..." in candidate or any(candidate.startswith(prefix) for prefix in IGNORED_GENERATED_PREFIXES):
                continue
            if not (REPO_ROOT / candidate).exists():
                missing.append(f"{rel_doc}: {candidate}")
    assert missing == []


def test_public_docs_referenced_make_targets_exist_in_makefile() -> None:
    """Verify every ``make <target>`` command documented in code spans or fences exists in ``Makefile``."""
    valid_targets = _makefile_targets()
    non_target_words = {"sure", "it", "this", "a", "an", "the", "changes", "requests", "sense"}
    unknown: list[str] = []
    for doc_path in _public_doc_files():
        rel_doc = doc_path.relative_to(REPO_ROOT).as_posix()
        for target in _extract_make_invocations(doc_path.read_text(encoding="utf-8")):
            if target in non_target_words:
                continue
            if target not in valid_targets:
                unknown.append(f"{rel_doc}: make {target}")
    assert unknown == []


def test_public_docs_contain_no_retired_symbols_or_legacy_ports() -> None:
    """Verify active public documentation contains zero retired symbols, legacy CLI commands, or stale ports."""
    violations: list[str] = []
    for doc_path in _public_doc_files():
        rel_doc = doc_path.relative_to(REPO_ROOT).as_posix()
        text = doc_path.read_text(encoding="utf-8")
        violations.extend(
            f"{rel_doc}: contains retired token {token!r}" for token in RETIRED_DOC_TOKENS if token in text
        )
    assert violations == []


def test_public_docs_contain_no_private_paths_or_internal_identifiers() -> None:
    """Verify tracked public documentation leaks zero local workstation paths or internal identifiers."""
    leaks: list[str] = []
    for doc_path in _public_doc_files():
        rel_doc = doc_path.relative_to(REPO_ROOT).as_posix()
        text = doc_path.read_text(encoding="utf-8")
        leaks.extend(
            f"{rel_doc}: contains private workstation path {prefix!r}"
            for prefix in FORBIDDEN_PATH_PREFIXES
            if prefix in text
        )
        leaks.extend(
            f"{rel_doc}: contains internal shortlink {shortlink!r}" for shortlink in INTERNAL_SHORTLINK_RE.findall(text)
        )
        leaks.extend(
            f"{rel_doc}: contains internal identifier {app_name!r}" for app_name in INTERNAL_APP_RE.findall(text)
        )
    assert leaks == []
