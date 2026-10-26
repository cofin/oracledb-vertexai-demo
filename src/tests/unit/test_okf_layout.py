# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests validating the OKF v0.2 `.agents/bundles/` knowledge layout and `AGENTIC_REVIEW` configuration."""

from __future__ import annotations

import re
from pathlib import Path

from tests.support.paths import PROJECT_ROOT

AGENTS_DIR = PROJECT_ROOT / ".agents"
BUNDLES_DIR = AGENTS_DIR / "bundles"
PRODUCT_DIR = BUNDLES_DIR / "product"
KNOWLEDGE_DIR = BUNDLES_DIR / "knowledge"
SPECS_DIR = BUNDLES_DIR / "specs"
RESEARCH_DIR = BUNDLES_DIR / "research"
OKF_BUNDLE_DIRS = (PRODUCT_DIR, KNOWLEDGE_DIR, SPECS_DIR, RESEARCH_DIR)

REQUIRED_OKF_KNOWLEDGE_PATHS = (
    "AGENTS.md",
    ".agents/AGENTS.md",
    "src/tests/AGENTS.md",
    "src/tests/unit/AGENTS.md",
    "src/tests/integration/AGENTS.md",
    ".agents/bundles/index.md",
    ".agents/bundles/knowledge/index.md",
    ".agents/bundles/knowledge/workflow.md",
    ".agents/bundles/knowledge/architecture/index.md",
    ".agents/bundles/knowledge/architecture/system-architecture.md",
    ".agents/bundles/knowledge/architecture/native-ai-runtime.md",
    ".agents/bundles/knowledge/architecture/oracle-26ai-hybrid-rrf.md",
    ".agents/bundles/knowledge/domains/index.md",
    ".agents/bundles/knowledge/domains/core-lib-ioc-server-cli.md",
    ".agents/bundles/knowledge/domains/ai-and-protocols.md",
    ".agents/bundles/knowledge/domains/chat-products-stores-system.md",
    ".agents/bundles/knowledge/testing/index.md",
    ".agents/bundles/knowledge/testing/unit-and-integration-catalog.md",
    ".agents/bundles/knowledge/patterns/index.md",
    ".agents/bundles/knowledge/gotchas/index.md",
    ".agents/bundles/knowledge/gotchas/oracle-sqlspec-and-queues.md",
    ".agents/bundles/knowledge/gotchas/litestar-security-and-vertex.md",
)

RETIRED_KNOWLEDGE_DIRS = (".agents/bundles/knowledge/guides", ".agents/bundles/knowledge/plans")

REQUIRED_REVIEW_SKILLS = (
    ".agents/skills/review-python-backend/SKILL.md",
    ".agents/skills/review-python-backend/references/false-positive-suppressions.md",
    ".agents/skills/review-oracle-sqlspec/SKILL.md",
    ".agents/skills/review-oracle-sqlspec/references/false-positive-suppressions.md",
    ".agents/skills/review-ai-and-mcp/SKILL.md",
    ".agents/skills/review-ai-and-mcp/references/false-positive-suppressions.md",
    ".agents/skills/review-web-htmx/SKILL.md",
    ".agents/skills/review-web-htmx/references/false-positive-suppressions.md",
    ".agents/skills/ghop-review-manager/SKILL.md",
    ".agents/skills/ghop-review-manager/scripts/validate_agentic_review.py",
)

LEGACY_BEADS_RE = re.compile(r"\bbd\s+(?:ready|create|close|update|list|show|sync)\b", re.IGNORECASE)
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]+`")
MARKDOWN_LINK_RE = re.compile(r"(?<!\!)\[[^\]]+\]\(([^)]+)\)")
INTERNAL_SHORTLINK_RE = re.compile(r"(?<![A-Za-z0-9_./-])go/[a-z0-9][a-z0-9_-]{2,}", re.IGNORECASE)
INTERNAL_APP_RE = re.compile(r"\b(?:db-skus|beekeeper|dma_classic)\b", re.IGNORECASE)
DRIVE_DOC_URL_RE = re.compile(
    r"(?:docs|drive)\.google\.com/(?:presentation|document|spreadsheets|file)/d/[A-Za-z0-9_-]+", re.IGNORECASE
)
CREDENTIAL_TOKEN_RE = re.compile(
    r"(?:"
    + "|".join((
        "ya" + r"29\.[A-Za-z0-9_.-]{10,}",
        "AI" + r"za[0-9A-Za-z_-]{20,}",
        "AK" + r"IA[0-9A-Z]{12,}",
        "gh" + r"p_[0-9A-Za-z]{20,}",
    ))
    + r")"
)

RETIRED_AGENT_DOC_TOKENS: tuple[str, ...] = (
    "enable_AutoLob",
    "OrdsSidecar",
    "apex_install.py",
    "apex_media.py",
    "ResponseCacheService",
    "SystemService",
    "InventoryService",
    "EmbeddingService",
    "MapsService",
    "make_container",
    "LitestarPersistenceProvider",
    "IntegrationsProvider",
    "tools/deploy/gcp/configure-apex-cdn.sql",
)

FORBIDDEN_AGENT_PATH_PREFIXES: tuple[str, ...] = ("/usr/local/google/home/", "/google/src/")


def _strip_code_spans(markdown_text: str) -> str:
    """Remove fenced code blocks and inline code spans before scanning markdown links."""
    without_fences = FENCED_CODE_RE.sub("", markdown_text)
    return INLINE_CODE_RE.sub("", without_fences)


def _validate_okf_frontmatter(md_file: Path) -> str | None:
    """Validate opening/closing YAML frontmatter and required OKF keys for a bundle file."""
    rel = md_file.relative_to(PROJECT_ROOT).as_posix()
    text = md_file.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return f"{rel}: missing opening --- frontmatter"
    closing_idx = text.find("\n---\n", 4)
    if closing_idx == -1:
        return f"{rel}: missing closing --- frontmatter"
    frontmatter = text[4:closing_idx]
    missing_keys = [key for key in ("type:", "title:", "description:") if key not in frontmatter]
    if missing_keys:
        return f"{rel}: missing frontmatter keys {missing_keys}"
    return None


def _active_agent_doc_files() -> list[Path]:
    """Collect active agent rule, test-guide, OKF product/knowledge, and skill Markdown files."""
    explicit = [
        PROJECT_ROOT / "AGENTS.md",
        AGENTS_DIR / "AGENTS.md",
        PROJECT_ROOT / "src" / "tests" / "README.md",
        PROJECT_ROOT / "src" / "tests" / "AGENTS.md",
        PROJECT_ROOT / "src" / "tests" / "unit" / "AGENTS.md",
        PROJECT_ROOT / "src" / "tests" / "integration" / "AGENTS.md",
        BUNDLES_DIR / "index.md",
    ]
    product_files = sorted(PRODUCT_DIR.rglob("*.md")) if PRODUCT_DIR.exists() else []
    knowledge_files = sorted(KNOWLEDGE_DIR.rglob("*.md")) if KNOWLEDGE_DIR.exists() else []
    skill_files = sorted((AGENTS_DIR / "skills").rglob("*.md")) if (AGENTS_DIR / "skills").exists() else []
    return [path for path in [*explicit, *product_files, *knowledge_files, *skill_files] if path.is_file()]


def test_required_okf_knowledge_files_exist() -> None:
    """Verify all required OKF v0.2 knowledge bundle and `AGENTS.md` files exist."""
    missing = [rel for rel in REQUIRED_OKF_KNOWLEDGE_PATHS if not (PROJECT_ROOT / rel).is_file()]
    assert missing == []


def test_retired_knowledge_directories_are_removed() -> None:
    """Verify legacy `guides/` and `plans/` directories under `.agents/bundles/knowledge/` are removed."""
    present = [rel for rel in RETIRED_KNOWLEDGE_DIRS if (PROJECT_ROOT / rel).exists()]
    assert present == []


def test_knowledge_markdown_files_have_yaml_frontmatter() -> None:
    """Verify every markdown file under `.agents/bundles/product/` and `.agents/bundles/knowledge/` has OKF frontmatter."""
    invalid_frontmatter: list[str] = []
    for bundle_dir in (PRODUCT_DIR, KNOWLEDGE_DIR):
        for md_file in sorted(bundle_dir.rglob("*.md")):
            problem = _validate_okf_frontmatter(md_file)
            if problem is not None:
                invalid_frontmatter.append(problem)
    assert invalid_frontmatter == []


def test_no_legacy_beads_commands_in_agents_docs() -> None:
    """Verify active `AGENTS.md` and `.agents/bundles/knowledge/` files contain no legacy `bd` CLI invocations."""
    violations: list[str] = []
    targets = [PROJECT_ROOT / "AGENTS.md", AGENTS_DIR / "AGENTS.md", *sorted(KNOWLEDGE_DIR.rglob("*.md"))]
    for path in targets:
        if not path.is_file():
            continue
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        if LEGACY_BEADS_RE.search(path.read_text(encoding="utf-8")):
            violations.append(rel)
    assert violations == []


def test_agentic_review_and_skills_exist_and_validate() -> None:
    """Verify root `AGENTIC_REVIEW` and all GHOP review skills exist and pass structural validation."""
    agentic_review = PROJECT_ROOT / "AGENTIC_REVIEW"
    assert agentic_review.is_file()

    missing = [rel for rel in REQUIRED_REVIEW_SKILLS if not (PROJECT_ROOT / rel).is_file()]
    assert missing == []

    lines = agentic_review.read_text(encoding="utf-8").splitlines()
    skill_lines = [line.strip() for line in lines if "review_capability_skills" in line]
    assert len(skill_lines) == 4
    for line in skill_lines:
        assert not line.startswith("#"), "Comment lines must never contain review_capability_skills"
        assert line.startswith('review_capability_skills: "')


def test_knowledge_and_spec_relative_markdown_links_resolve() -> None:
    """Verify relative markdown links across PRODUCT_DIR, KNOWLEDGE_DIR, SPECS_DIR, and RESEARCH_DIR resolve."""
    broken_links: list[str] = []
    markdown_files = [
        md_file for bundle_dir in OKF_BUNDLE_DIRS if bundle_dir.exists() for md_file in sorted(bundle_dir.rglob("*.md"))
    ]
    for md_file in markdown_files:
        rel_source = md_file.relative_to(PROJECT_ROOT).as_posix()
        cleaned = _strip_code_spans(md_file.read_text(encoding="utf-8"))
        for match in MARKDOWN_LINK_RE.finditer(cleaned):
            raw_target = match.group(1).strip()
            if not raw_target:
                continue
            target_part = raw_target.split()[0].split("#", 1)[0].strip()
            if not target_part or "://" in target_part or target_part.startswith(("mailto:", "/")):
                continue
            resolved = (md_file.parent / target_part).resolve()
            if not resolved.exists():
                broken_links.append(f"{rel_source} -> {raw_target}")
    assert broken_links == []


def test_no_retired_symbols_or_private_paths_in_agents_knowledge_and_skills() -> None:
    """Verify active rules, test guides, OKF chapters, and skills contain zero retired symbols or leaked identifiers."""
    violations: list[str] = []
    for doc_path in _active_agent_doc_files():
        rel_doc = doc_path.relative_to(PROJECT_ROOT).as_posix()
        text = doc_path.read_text(encoding="utf-8")
        violations.extend(
            f"{rel_doc}: contains retired token {token!r}" for token in RETIRED_AGENT_DOC_TOKENS if token in text
        )
        violations.extend(
            f"{rel_doc}: contains private workstation path {prefix!r}"
            for prefix in FORBIDDEN_AGENT_PATH_PREFIXES
            if prefix in text
        )
        violations.extend(
            f"{rel_doc}: contains internal shortlink {shortlink!r}" for shortlink in INTERNAL_SHORTLINK_RE.findall(text)
        )
        violations.extend(
            f"{rel_doc}: contains internal identifier {app_name!r}" for app_name in INTERNAL_APP_RE.findall(text)
        )
        violations.extend(
            f"{rel_doc}: contains Drive/Slides document URL {drive_url!r}"
            for drive_url in DRIVE_DOC_URL_RE.findall(text)
        )
        violations.extend(
            f"{rel_doc}: contains credential token {token[:6]!r}..." for token in CREDENTIAL_TOKEN_RE.findall(text)
        )
    assert violations == []
