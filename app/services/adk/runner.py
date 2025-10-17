"""ADK Agent Runner for the modern Coffee Assistant System.

This module provides the main runner class that manages the ADK agent system
using the proper ADK Runner pattern with our custom session service.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import structlog
from google.adk import Runner
from google.genai import types
from sqlspec.adapters.oracledb.adk.store import OracleAsyncADKStore
from sqlspec.extensions.adk import SQLSpecSessionService

from app.config import db
from app.services.adk.agent import CoffeeAssistantAgent

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from google.adk.sessions import Session

logger = structlog.get_logger()


class ADKRunner:
    """Main runner for the ADK-based coffee assistant system."""

    def __init__(self) -> None:
        """Initialize the ADK runner with SQLSpec session service."""
        store = OracleAsyncADKStore(config=db)
        self.session_service = SQLSpecSessionService(store)
        self.runner = Runner(
            agent=CoffeeAssistantAgent,
            app_name="coffee-assistant",
            session_service=self.session_service,
        )
        logger.debug("ADKRunner initialized with SQLSpec session service")

    async def process_request(
        self, query: str, user_id: str = "default", session_id: str | None = None
    ) -> dict[str, Any]:
        """Process user request through the ADK agent system."""
        start_time = time.time()
        logger.debug("Processing request via ADKRunner...", query=query)

        session = await self._ensure_session(user_id, session_id)
        content = types.Content(role="user", parts=[types.Part(text=query)])

        events = self.runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        )

        final_response_text = await self._process_events(events)

        total_time_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "answer": final_response_text,
            "session_id": session.id,
            "response_time_ms": total_time_ms,
        }

    async def _ensure_session(self, user_id: str, session_id: str | None) -> Session:
        """Ensure session exists using get-or-create pattern."""
        if session_id:
            existing = await self.session_service.get_session(
                app_name="coffee-assistant",
                user_id=user_id,
                session_id=session_id,
            )
            if existing:
                return existing

        return await self.session_service.create_session(
            app_name="coffee-assistant",
            user_id=user_id,
            session_id=session_id,
            state={},
        )

    async def _process_events(self, events: AsyncGenerator) -> str:
        """Process ADK events to extract the final response."""
        final_response_text = ""
        async for event in events:
            if event.is_final_response() and event.content and event.content.parts:
                final_response_text = "".join(part.text for part in event.content.parts if part.text)
        return final_response_text
