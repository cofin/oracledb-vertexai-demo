# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Pin Ch 2 architectural patterns in .agents/patterns.md."""

from __future__ import annotations

from tests.support.paths import PROJECT_ROOT

PATTERNS = (PROJECT_ROOT / ".agents" / "patterns.md").read_text()


def test_patterns_drops_false_query_builder_claim() -> None:
    """Project uses named SQL files exclusively — no query builder."""
    assert "query builder" not in PATTERNS.lower(), (
        "patterns.md must not advertise the query builder; the project uses named SQL files only."
    )


def test_patterns_documents_three_providers_with_scopes() -> None:
    for name in ("LitestarPersistenceProvider", "IntegrationsProvider", "DomainServiceProvider"):
        assert name in PATTERNS, f"{name} must be documented in patterns.md"


def test_patterns_documents_named_sql_pattern() -> None:
    assert "db_manager.get_sql" in PATTERNS, (
        "Named SQL pattern (db_manager.get_sql('name')) must be documented"
    )


def test_patterns_documents_filter_dependencies_pattern() -> None:
    assert "create_filter_dependencies" in PATTERNS, (
        "create_filter_dependencies pattern for list endpoints must be documented"
    )
    assert "list_with_count" in PATTERNS, (
        "list_with_count(*filters) service signature must be documented"
    )


def test_patterns_documents_sqlspec_async_service_base() -> None:
    assert "SQLSpecAsyncService" in PATTERNS, (
        "SQLSpecAsyncService base class must be documented as the canonical service base"
    )


def test_patterns_documents_domain_package_layout() -> None:
    """Domain modules use controllers/services/schemas sub-packages."""
    text = PATTERNS.lower()
    assert "controllers/" in text or "controllers," in text, "controllers package must be mentioned"
    assert "services/" in text or "services," in text, "services package must be mentioned"
    assert "schemas/" in text or "schemas," in text, "schemas package must be mentioned"
