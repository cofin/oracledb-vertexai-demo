"""Monkey patches for ADK library issues.

This module contains patches for known issues in google-adk and google-genai dependencies.
"""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from google.genai.client import Client

logger = structlog.get_logger()


def apply_genai_client_patch() -> None:
    """Patch both google-genai Client cleanup and google-adk Gemini.api_client caching.

    This patch addresses two related issues:

    1. Google GenAI Client cleanup AttributeError:
       The google.genai.Client class has a __del__ method that tries to close
       _api_client and _async_httpx_client attributes that may not exist if the
       client is garbage collected before full initialization.

    2. Google ADK repeated Client creation:
       The Gemini.api_client property creates a new Client on every access instead
       of caching it, causing many short-lived Client instances to be created and
       garbage collected, triggering issue #1 repeatedly.

    References:
    - https://github.com/google/genai-python/issues
    - https://github.com/googleapis/python-aiplatform/issues
    """
    _patch_genai_client_cleanup()
    _patch_genai_base_api_client_cleanup()
    _patch_adk_client_caching()
    logger.info("Applied all Google GenAI/ADK patches")


def _patch_genai_client_cleanup() -> None:
    """Patch google.genai.Client.__del__ to handle missing attributes gracefully."""
    try:
        from google.genai.client import Client

        original_del = Client.__del__

        def safe_del(self: Client) -> None:
            """Safe cleanup that handles missing attributes."""
            try:
                # Only call close() if _api_client exists
                if hasattr(self, "_api_client"):
                    original_del(self)
            except AttributeError:
                # Silently ignore AttributeError during cleanup
                pass
            except Exception:  # noqa: BLE001
                # Log other exceptions but don't crash
                logger.debug("Error during Client cleanup", exc_info=True)

        Client.__del__ = safe_del

    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to apply GenAI Client cleanup patch", error=str(e))


def _patch_genai_base_api_client_cleanup() -> None:
    """Patch google.genai._api_client.BaseApiClient.aclose to handle missing attributes."""
    try:
        from google.genai._api_client import BaseApiClient

        original_aclose = BaseApiClient.aclose

        async def safe_aclose(self: Any) -> None:
            """Safe async cleanup that handles missing attributes."""
            try:
                # Only close if _async_httpx_client exists
                if hasattr(self, "_async_httpx_client"):
                    await original_aclose(self)
            except AttributeError:
                pass
            except Exception:  # noqa: BLE001
                logger.debug("Error during BaseApiClient cleanup", exc_info=True)

        BaseApiClient.aclose = safe_aclose  # type: ignore[method-assign]

    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to apply BaseApiClient aclose patch", error=str(e))


def _patch_adk_client_caching() -> None:
    """Patch google-adk Gemini.api_client to use @cached_property."""
    try:
        from google.adk.models.google_llm import Gemini

        # Check if already patched (cached_property is already applied)
        if isinstance(getattr(Gemini, "api_client", None), cached_property):
            return

        # Get the original property - need to check if it's a property first
        api_client_attr = getattr(Gemini, "api_client", None)
        if not isinstance(api_client_attr, property):
            logger.warning("api_client is not a property, skipping patch")
            return

        # Save original property getter
        original_getter = api_client_attr.fget
        if original_getter is None:
            logger.warning("api_client property has no getter, skipping patch")
            return

        # Create cached version
        def cached_api_client(self: Any) -> Client:
            """Cached GenAI client instance."""
            return original_getter(self)

        # Replace property with cached_property
        setattr(Gemini, "api_client", cached_property(cached_api_client))

    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to apply ADK client caching patch", error=str(e))
