# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Vertex AI, Google GenAI, and chat-workflow configuration settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from app.lib.settings._env import _env_float, _env_int

__all__ = ("PLACEHOLDER_VALUES", "AISettings", "ChatSettings")

PLACEHOLDER_VALUES: frozenset[str] = frozenset({
    "",
    "demo-project",
    "your-project-id",
    "your-gcp-project-id",
    "placeholder",
    "your-api-key",
})


@dataclass(frozen=True, slots=True)
class AISettings:
    """Vertex AI / Google GenAI configuration settings."""

    project_id: str = field(
        default_factory=lambda: (
            os.getenv("VERTEX_AI_PROJECT_ID")
            or os.getenv("GOOGLE_CLOUD_PROJECT")
            or os.getenv("GOOGLE_PROJECT_ID")
            or ""
        )
    )
    """Google Cloud Project ID for Vertex AI."""
    location: str = field(
        default_factory=lambda: (
            os.getenv("VERTEX_AI_LOCATION")
            or os.getenv("GOOGLE_CLOUD_LOCATION")
            or os.getenv("GOOGLE_LOCATION")
            or "global"
        )
    )
    """Vertex AI location/region (defaults to ``global`` for Gemini 3.8 preview models)."""
    gcp_region: str = field(default_factory=lambda: os.getenv("GCP_REGION") or "us-central1")
    """Primary GCP deployment region."""
    api_key: str | None = field(default_factory=lambda: os.getenv("VERTEX_AI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    """Optional API key for Google AI clients."""
    chat_model: str = field(default_factory=lambda: os.getenv("VERTEX_AI_CHAT_MODEL", "gemini-3.8-flash"))
    """Vertex AI chat model."""
    intent_model_override: str | None = field(default_factory=lambda: os.getenv("VERTEX_AI_INTENT_MODEL"))
    """Optional override for the single-call intent-classification model."""
    embedding_model: str = field(default_factory=lambda: os.getenv("VERTEX_AI_EMBEDDING_MODEL", "gemini-embedding-2"))
    """Vertex AI embedding model."""
    embedding_dimensions: int = 3072
    """Embedding vector dimensions (gemini-embedding-2 native output)."""

    @property
    def intent_model(self) -> str:
        """Intent-classification model, falling back to the chat model."""
        return self.intent_model_override or self.chat_model

    def has_valid_project_id(self) -> bool:
        """Return ``True`` when ``project_id`` is non-empty and not a placeholder."""
        cleaned = (self.project_id or "").strip()
        return bool(cleaned and cleaned.lower() not in PLACEHOLDER_VALUES)

    def has_valid_api_key(self) -> bool:
        """Return ``True`` when ``api_key`` is non-empty and not a placeholder."""
        cleaned = (self.api_key or "").strip()
        return bool(cleaned and cleaned.lower() not in PLACEHOLDER_VALUES)

    def resolve_location(self, gcp_region: str | None = None) -> str:
        """Resolve the effective Vertex AI endpoint location.

        Gemini 3.8 preview models are served on the ``global`` Vertex AI
        endpoint unless an explicit location override is configured.
        """
        del gcp_region
        if self.location and self.location.strip():
            return self.location.strip()
        return "global"


@dataclass(frozen=True, slots=True)
class ChatSettings:
    """Chat-workflow runtime constants."""

    session_app_name: str = field(default_factory=lambda: os.getenv("CHAT_SESSION_APP_NAME", "coffee_assistant"))
    """App name used for session lookups."""
    response_cache_version: str = field(
        default_factory=lambda: os.getenv("CHAT_RESPONSE_CACHE_VERSION", "menu-grounded-v2")
    )
    """Cache-key namespace bumped to invalidate stale grounded responses."""
    response_cache_ttl_minutes: int = field(default_factory=lambda: _env_int("CHAT_RESPONSE_CACHE_TTL_MINUTES", 60))
    """Response-cache time-to-live in minutes."""
    product_search_limit: int = field(default_factory=lambda: _env_int("CHAT_PRODUCT_SEARCH_LIMIT", 5))
    """Default product vector-search result limit."""
    product_search_threshold: float = field(default_factory=lambda: _env_float("CHAT_PRODUCT_SEARCH_THRESHOLD", 0.7))
    """Default product vector-search similarity threshold."""
    grounded_answer_timeout_seconds: float = field(
        default_factory=lambda: _env_float("CHAT_GROUNDED_ANSWER_TIMEOUT_SECONDS", 2.5)
    )
    """Maximum time allowed for Product RAG structured selection before falling back."""
    display_history_limit: int = field(default_factory=lambda: _env_int("CHAT_DISPLAY_HISTORY_LIMIT", 40))
    """Maximum number of display-history messages retained per session."""
