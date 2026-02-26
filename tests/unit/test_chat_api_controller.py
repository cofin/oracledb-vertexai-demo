from __future__ import annotations

from typing import Any

import pytest

from app import schemas
from app.domain.chat.controllers._chat import CoffeeChatController


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def process_request(
        self,
        query: str,
        user_id: str,
        session_id: str,
        persona: str,
        cache_service: object,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "query": query,
                "user_id": user_id,
                "session_id": session_id,
                "persona": persona,
                "cache_service": cache_service,
            }
        )
        return {
            "answer": "Try the Guatemala single origin.",
            "from_cache": True,
            "embedding_cache_hit": False,
            "intent_detected": "PRODUCT_SEARCH",
            "response_time_ms": 42.0,
            "agent_processing_ms": 12.0,
            "session_id": session_id,
        }


@pytest.mark.anyio
async def test_send_chat_message_uses_header_session_id_and_returns_reply() -> None:
    controller = object.__new__(CoffeeChatController)
    runner = FakeRunner()
    cache_service = object()
    request = type("Req", (), {"headers": {"x-session-id": "session-123"}})()

    reply = await CoffeeChatController.send_chat_message.fn(
        controller,
        data=schemas.CoffeeChatMessage(message="Need a fruity roast", persona="novice"),
        adk_runner=runner,  # type: ignore[arg-type]
        cache_service=cache_service,  # type: ignore[arg-type]
        request=request,  # type: ignore[arg-type]
    )

    assert runner.calls[0]["session_id"] == "session-123"
    assert runner.calls[0]["persona"] == "novice"
    assert reply.answer == "Try the Guatemala single origin."
    assert reply.from_cache is True
    assert reply.intent_detected == "PRODUCT_SEARCH"
    assert reply.messages[0].source == "human"
    assert reply.messages[1].source == "ai"


@pytest.mark.anyio
async def test_send_chat_message_normalizes_invalid_persona() -> None:
    controller = object.__new__(CoffeeChatController)
    runner = FakeRunner()
    request = type("Req", (), {"headers": {}})()

    await CoffeeChatController.send_chat_message.fn(
        controller,
        data=schemas.CoffeeChatMessage(message="Suggest espresso beans", persona="not-a-persona"),
        adk_runner=runner,  # type: ignore[arg-type]
        cache_service=object(),  # type: ignore[arg-type]
        request=request,  # type: ignore[arg-type]
    )

    assert runner.calls[0]["persona"] == "enthusiast"
    assert isinstance(runner.calls[0]["session_id"], str)
    assert runner.calls[0]["session_id"] != ""
