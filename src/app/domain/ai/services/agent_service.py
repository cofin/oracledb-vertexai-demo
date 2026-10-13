# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""High-level agent orchestration service coordinating hybrid RRF routing, sessions, runtime, and persistence."""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator, AsyncIterator
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

import msgspec

from app.domain.ai.runtime._context import CallContext, CoffeeToolContext
from app.domain.ai.runtime._spec import AgentSpec, GenerationConfig, SpecTree
from app.domain.ai.runtime._types import AgentEvent, Content, Part
from app.domain.ai.services._tools import build_coffee_tools
from app.domain.chat.schemas import ChatMessage
from app.domain.chat.services._telemetry import (
    SQLPhase,
    build_hybrid_sql_phases,
    build_response_cache_phase,
    build_search_metrics,
    safe_location_context,
)
from app.domain.products.services import InventoryService, MapsService
from app.domain.system.schemas import SearchMetricsCreate
from app.domain.system.services import BASE_SYSTEM_INSTRUCTION, PersonaManager
from app.lib.settings import get_settings

if TYPE_CHECKING:
    from app.domain.ai.runtime._loop import AgentRuntime
    from app.domain.ai.runtime._store import OracleEventStore, OracleSessionStore
    from app.domain.ai.runtime._stream import AgentStreamService
    from app.domain.chat.schemas import HybridTurnContext
    from app.domain.chat.services._grounded import GroundedRouteService, GroundedTurnResult
    from app.domain.chat.services._router import HybridRouteResolver
    from app.domain.products.services import ProductService, StoreService, VertexAIService
    from app.domain.system.services import CacheService, MetricsService

__all__ = ("AgentOrchestrationService", "get_coffee_spec_tree", "make_response_cache_key")


def get_coffee_spec_tree() -> SpecTree:
    """Construct the coffee agent specification tree with coordinator and grounded tools.

    Returns:
        Configured SpecTree with coffee barista root coordinator and 5 grounded tools.
    """
    settings = get_settings()
    coordinator = AgentSpec(
        name="coffee_barista",
        description="Friendly, knowledgeable Cymbal Coffee barista guiding recommendations and recipes.",
        model=settings.ai.chat_model,
        static_instruction=BASE_SYSTEM_INSTRUCTION,
        tools=list(build_coffee_tools()),
        generation=GenerationConfig(temperature=0.2, max_output_tokens=4096),
    )
    return SpecTree(root=coordinator)


def make_response_cache_key(query: str, persona: str, *, model: str = "gemini-3.8-flash") -> str:
    """Build a deterministic SHA-256 response cache key for location-independent queries."""
    normalized = " ".join(query.casefold().split())
    version = get_settings().chat.response_cache_version
    digest = sha256(f"{version}:{model}:{persona}:{normalized}".encode()).hexdigest()
    return f"chat:{digest}"


class AgentOrchestrationService:
    """Orchestrates single-query hybrid RRF routing, grounded composers, dynamic agent turns, and persistence."""

    def __init__(
        self,
        runtime: AgentRuntime,
        stream_service: AgentStreamService,
        spec_tree: SpecTree,
        session_store: OracleSessionStore,
        event_store: OracleEventStore,
        route_resolver: HybridRouteResolver | None = None,
        grounded_service: GroundedRouteService | None = None,
        product_service: ProductService | None = None,
        store_service: StoreService | None = None,
        vertex_ai_service: VertexAIService | None = None,
        cache_service: CacheService | None = None,
        metrics_service: MetricsService | None = None,
        persona_manager: PersonaManager | None = None,
    ) -> None:
        self._runtime = runtime
        self._stream_service = stream_service
        self._spec_tree = spec_tree
        self._session_store = session_store
        self._event_store = event_store
        self._route_resolver = route_resolver
        self._grounded_service = grounded_service
        self._product_service = product_service
        self._store_service = store_service
        self._vertex_ai_service = vertex_ai_service
        self._cache_service = cache_service
        self._metrics_service = metrics_service
        self._persona_manager = persona_manager or PersonaManager()

    async def run_conversation_turn(
        self,
        *,
        session_id: str,
        user_id: str,
        message: str,
        services: Any = None,
        dynamic_context: str | None = None,
        persona: str = "barista",
        location_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a full conversation turn and return the final event frame dictionary."""
        final_frame: dict[str, Any] = {"type": "final", "session_id": session_id, "answer": ""}
        async for frame in self.stream_conversation_turn(
            session_id=session_id,
            user_id=user_id,
            message=message,
            services=services,
            dynamic_context=dynamic_context,
            persona=persona,
            location_context=location_context,
        ):
            if frame.get("type") == "final":
                final_frame = frame
        return final_frame

    async def stream_conversation_turn(
        self,
        *,
        session_id: str,
        user_id: str,
        message: str,
        services: Any = None,
        dynamic_context: str | None = None,
        persona: str = "barista",
        location_context: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute a conversation turn and stream normalized SSE frames."""
        turn_started = time.perf_counter()
        invocation_id = uuid4().hex
        history, turn_num, next_seq, session_state = await self._prepare_session_and_user_event(
            session_id=session_id, user_id=user_id, invocation_id=invocation_id, message=message
        )

        cache_key, cached_payload, cache_phase = await self._lookup_response_cache(
            message=message, persona=persona, safe_loc=safe_location_context(location_context)
        )
        if cached_payload is not None and cache_phase is not None:
            async for frame in self._emit_cached_turn(
                session_id=session_id,
                user_id=user_id,
                invocation_id=invocation_id,
                turn_num=turn_num,
                next_seq=next_seq,
                turn_started=turn_started,
                cached_payload=cached_payload,
                cache_phase=cache_phase,
                safe_loc=safe_location_context(location_context),
                session_state=session_state,
            ):
                yield frame
            return

        turn_context, query_embedding, embed_hit, embed_ms, oracle_ms = await self._resolve_hybrid_context(message)
        if turn_context is not None and self._grounded_service is not None and turn_context.is_deterministic:
            grounded = await self._grounded_service.dispatch(
                message,
                turn_context,
                location_context=location_context,
                persona=persona,
                last_products=_extract_last_products(session_state),
                embedding_ms=embed_ms,
                oracle_ms=oracle_ms,
                embedding_cache_hit=embed_hit,
                query_embedding=query_embedding,
            )
            if grounded is not None:
                async for frame in self._emit_grounded_turn(
                    session_id=session_id,
                    user_id=user_id,
                    invocation_id=invocation_id,
                    turn_num=turn_num,
                    next_seq=next_seq,
                    turn_started=turn_started,
                    grounded=grounded,
                    cache_key=cache_key,
                    cache_phase=cache_phase,
                    session_state=session_state,
                ):
                    yield frame
                return

        async for frame in self._stream_agent_runtime_turn(
            session_id=session_id,
            invocation_id=invocation_id,
            turn_num=turn_num,
            next_seq=next_seq,
            turn_started=turn_started,
            message=message,
            history=history,
            services=services,
            dynamic_context=dynamic_context,
            persona=persona,
            location_context=location_context,
            turn_context=turn_context,
            query_embedding=query_embedding,
            embed_hit=embed_hit,
            embed_ms=embed_ms,
            oracle_ms=oracle_ms,
            cache_key=cache_key,
            cache_phase=cache_phase,
        ):
            yield frame

    async def get_display_history(self, session_id: str, user_id: str) -> list[ChatMessage]:
        """Retrieve recent conversation history formatted for HTML display templates."""
        del user_id
        events = await self._event_store.list_events(session_id=session_id)
        display_messages: list[ChatMessage] = []
        for event in events:
            text = event.text()
            if not text:
                continue
            source: Literal["human", "ai"] = "human" if event.agent == "user" else "ai"
            display_messages.append(ChatMessage(message=text, source=source))
        return display_messages

    async def clear_session(self, session_id: str, user_id: str) -> None:
        """Clear session state and associated event rows."""
        await self._session_store.clear_session(session_id=session_id, user_id=user_id)

    async def _prepare_session_and_user_event(
        self, *, session_id: str, user_id: str, invocation_id: str, message: str
    ) -> tuple[list[AgentEvent], int, int, dict[str, Any]]:
        existing = await self._session_store.get_session(session_id=session_id, user_id=user_id)
        session_state = _extract_session_state(existing)
        if existing is None:
            await self._session_store.save_session(
                session_id=session_id, user_id=user_id, app_name="cymbal_coffee", state=session_state
            )
        history = await self._event_store.list_events(session_id=session_id)
        turn_num = len(history) // 2 + 1
        next_seq = (
            await self._event_store.get_next_seq(session_id)
            if hasattr(self._event_store, "get_next_seq")
            else len(history) + 1
        )
        user_event = AgentEvent(
            session_id=session_id,
            invocation_id=invocation_id,
            agent="user",
            seq=next_seq,
            turn=turn_num,
            content=Content(role="user", parts=[Part(text=message)]),
        )
        await self._event_store.append_event(user_event)
        return history, turn_num, next_seq + 1, session_state

    async def _lookup_response_cache(
        self, *, message: str, persona: str, safe_loc: dict[str, Any]
    ) -> tuple[str | None, dict[str, Any] | None, SQLPhase | None]:
        if self._cache_service is None or safe_loc:
            return None, None, None
        cache_key = make_response_cache_key(message, persona, model=self._spec_tree.root.model)
        started = time.perf_counter()
        cached = await self._cache_service.get_cached_response(cache_key)
        runtime_ms = (time.perf_counter() - started) * 1000
        payload = cached.response_data if cached is not None and isinstance(cached.response_data, dict) else None
        phase = build_response_cache_phase(cache_key, hit=payload is not None, runtime_ms=runtime_ms)
        return cache_key, payload, phase

    async def _resolve_hybrid_context(
        self, message: str
    ) -> tuple[HybridTurnContext | None, list[float] | None, bool, float, float]:
        if self._route_resolver is None or self._vertex_ai_service is None:
            return None, None, False, 0.0, 0.0
        embed_started = time.perf_counter()
        embedding_res = await self._vertex_ai_service.get_text_embedding(
            message, embedding_purpose="query", return_cache_status=True
        )
        embed_ms = (time.perf_counter() - embed_started) * 1000
        if isinstance(embedding_res, tuple):
            query_embedding, embed_hit = embedding_res
        else:
            query_embedding, embed_hit = embedding_res, False
        if not query_embedding:
            return None, None, False, embed_ms, 0.0

        turn_context = await self._route_resolver.resolve_turn(user_message=message, query_embedding=query_embedding)
        oracle_ms = turn_context.oracle_time_ms
        if self._metrics_service is not None:
            top_sim = turn_context.products[0].vector_similarity if turn_context.products else None
            await self._metrics_service.record_search(
                SearchMetricsCreate(
                    query_id=uuid4().hex,
                    user_id="chat",
                    search_time_ms=embed_ms + oracle_ms,
                    embedding_time_ms=embed_ms,
                    oracle_time_ms=oracle_ms,
                    similarity_score=top_sim,
                    result_count=len(turn_context.products),
                )
            )
        return turn_context, query_embedding, bool(embed_hit), embed_ms, oracle_ms

    async def _emit_cached_turn(
        self,
        *,
        session_id: str,
        user_id: str,
        invocation_id: str,
        turn_num: int,
        next_seq: int,
        turn_started: float,
        cached_payload: dict[str, Any],
        cache_phase: SQLPhase,
        safe_loc: dict[str, Any],
        session_state: dict[str, Any],
    ) -> AsyncGenerator[dict[str, Any], None]:
        answer = str(cached_payload.get("answer") or "")
        await self._append_assistant_event(
            session_id=session_id, invocation_id=invocation_id, turn_num=turn_num, seq=next_seq, answer=answer
        )
        cached_last_products = cached_payload.get("last_products")
        if isinstance(cached_last_products, list) and cached_last_products:
            session_state["last_products"] = [str(item) for item in cached_last_products if str(item).strip()]
            await self._session_store.save_session(
                session_id=session_id, user_id=user_id, app_name="cymbal_coffee", state=session_state
            )
        elapsed_ms = round((time.perf_counter() - turn_started) * 1000, 2)
        metrics = dict(cached_payload.get("search_metrics") or {})
        metrics["total_ms"] = round(elapsed_ms)
        cached_phases = list(cached_payload.get("sql_phases") or [])
        yield {"type": "session", "session_id": session_id}
        if answer:
            yield {"type": "delta", "text": answer}
        yield {
            "type": "final",
            "answer": answer,
            "session_id": session_id,
            "response_time_ms": elapsed_ms,
            "intent_detected": str(cached_payload.get("intent_detected") or "GENERAL_CONVERSATION"),
            "search_metrics": metrics,
            "sql_phases": [cache_phase.to_dict(), *cached_phases],
            "from_cache": True,
            "embedding_cache_hit": bool(cached_payload.get("embedding_cache_hit")),
            "store_results": list(cached_payload.get("store_results") or []),
            "inventory_results": list(cached_payload.get("inventory_results") or []),
            "map_actions": list(cached_payload.get("map_actions") or []),
            "location_context": safe_loc,
        }

    async def _emit_grounded_turn(
        self,
        *,
        session_id: str,
        user_id: str,
        invocation_id: str,
        turn_num: int,
        next_seq: int,
        turn_started: float,
        grounded: GroundedTurnResult,
        cache_key: str | None,
        cache_phase: SQLPhase | None,
        session_state: dict[str, Any],
    ) -> AsyncGenerator[dict[str, Any], None]:
        await self._append_assistant_event(
            session_id=session_id, invocation_id=invocation_id, turn_num=turn_num, seq=next_seq, answer=grounded.answer
        )
        if grounded.last_products:
            session_state["last_products"] = list(grounded.last_products)
            await self._session_store.save_session(
                session_id=session_id, user_id=user_id, app_name="cymbal_coffee", state=session_state
            )
        elapsed_ms = round((time.perf_counter() - turn_started) * 1000, 2)
        metrics_dict = grounded.search_metrics.to_dict()
        metrics_dict["total_ms"] = round(elapsed_ms)
        grounded_phases = [phase.to_dict() for phase in grounded.sql_phases]
        all_phases = ([cache_phase.to_dict()] if cache_phase is not None else []) + grounded_phases

        if cache_key is not None and self._cache_service is not None and grounded.answer:
            await self._cache_service.set_cached_response(
                cache_key,
                {
                    "answer": grounded.answer,
                    "intent_detected": grounded.intent_detected,
                    "search_metrics": metrics_dict,
                    "embedding_cache_hit": grounded.embedding_cache_hit,
                    "sql_phases": grounded_phases,
                    "store_results": grounded.store_results,
                    "inventory_results": grounded.inventory_results,
                    "map_actions": grounded.map_actions,
                    "last_products": grounded.last_products,
                },
                ttl_minutes=get_settings().chat.response_cache_ttl_minutes,
            )

        yield {"type": "session", "session_id": session_id}
        if grounded.answer:
            yield {"type": "delta", "text": grounded.answer}
        yield {
            "type": "final",
            "answer": grounded.answer,
            "session_id": session_id,
            "response_time_ms": elapsed_ms,
            "intent_detected": grounded.intent_detected,
            "search_metrics": metrics_dict,
            "sql_phases": all_phases,
            "from_cache": False,
            "embedding_cache_hit": grounded.embedding_cache_hit,
            "store_results": grounded.store_results,
            "inventory_results": grounded.inventory_results,
            "map_actions": grounded.map_actions,
            "location_context": grounded.location_context,
        }

    async def _stream_agent_runtime_turn(
        self,
        *,
        session_id: str,
        invocation_id: str,
        turn_num: int,
        next_seq: int,
        turn_started: float,
        message: str,
        history: list[AgentEvent],
        services: Any,
        dynamic_context: str | None,
        persona: str,
        location_context: dict[str, Any] | None,
        turn_context: HybridTurnContext | None,
        query_embedding: list[float] | None,
        embed_hit: bool,
        embed_ms: float,
        oracle_ms: float,
        cache_key: str | None,
        cache_phase: SQLPhase | None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        tool_services = self._build_tool_services(services, turn_context=turn_context)
        safe_loc = safe_location_context(location_context)
        ctx = CallContext(
            session_id=session_id,
            invocation_id=invocation_id,
            turn=turn_num,
            state={
                "location_context": location_context,
                "embedding_cache_hit": embed_hit,
                "sql_phases": [],
                "search_metrics": {},
                "store_results": [],
                "inventory_results": [],
                "map_actions": [],
            },
            services=tool_services,
        )
        effective_dynamic = self._build_dynamic_context(
            dynamic_context=dynamic_context, persona=persona, safe_loc=safe_loc, turn_context=turn_context
        )
        raw_stream = self._runtime.execute_turn(
            spec_tree=self._spec_tree,
            session_id=session_id,
            invocation_id=invocation_id,
            user_message=message,
            ctx=ctx,
            history=history,
            dynamic_context=effective_dynamic,
        )

        async def _persisting_stream() -> AsyncIterator[AgentEvent]:
            nonlocal next_seq
            async for event in raw_stream:
                if not event.partial and event.content:
                    event.seq = next_seq
                    next_seq += 1
                    await self._event_store.append_event(event)
                yield event

        async for frame in self._stream_service.adapt(_persisting_stream(), session_id=session_id):
            if frame.get("type") == "final":
                yield await self._enrich_runtime_final_frame(
                    frame=frame,
                    message=message,
                    turn_started=turn_started,
                    ctx=ctx,
                    turn_context=turn_context,
                    query_embedding=query_embedding,
                    embed_hit=embed_hit,
                    embed_ms=embed_ms,
                    oracle_ms=oracle_ms,
                    safe_loc=safe_loc,
                    cache_key=cache_key,
                    cache_phase=cache_phase,
                )
            else:
                yield frame

    async def _enrich_runtime_final_frame(
        self,
        *,
        frame: dict[str, Any],
        message: str,
        turn_started: float,
        ctx: CallContext,
        turn_context: HybridTurnContext | None,
        query_embedding: list[float] | None,
        embed_hit: bool,
        embed_ms: float,
        oracle_ms: float,
        safe_loc: dict[str, Any],
        cache_key: str | None,
        cache_phase: SQLPhase | None,
    ) -> dict[str, Any]:
        elapsed_ms = round((time.perf_counter() - turn_started) * 1000, 2)
        base_phases = (
            [
                phase.to_dict()
                for phase in build_hybrid_sql_phases(
                    query=message,
                    turn_context=turn_context,
                    query_embedding=query_embedding,
                    embedding_ms=embed_ms,
                    oracle_ms=oracle_ms,
                    embedding_cache_hit=embed_hit,
                )
            ]
            if turn_context is not None
            else []
        )
        tool_phases = list(ctx.state.get("sql_phases") or [])
        all_phases = ([cache_phase.to_dict()] if cache_phase is not None else []) + base_phases + tool_phases

        merged_metrics: dict[str, Any] = dict(frame.get("search_metrics") or {})
        if turn_context is not None:
            merged_metrics.update(
                build_search_metrics(
                    query=message,
                    turn_context=turn_context,
                    total_ms=elapsed_ms,
                    embedding_ms=embed_ms,
                    oracle_ms=oracle_ms,
                ).to_dict()
            )
        merged_metrics.update(dict(ctx.state.get("search_metrics") or {}))
        merged_metrics["total_ms"] = round(elapsed_ms)

        intent_detected = turn_context.intent_detected if turn_context is not None else "GENERAL_CONVERSATION"
        answer = str(frame.get("answer") or "")
        embedding_cache_hit = bool(ctx.state.get("embedding_cache_hit", embed_hit))
        store_results = list(ctx.state.get("store_results") or [])
        inventory_results = list(ctx.state.get("inventory_results") or [])
        map_actions = list(ctx.state.get("map_actions") or [])

        if cache_key is not None and self._cache_service is not None and answer:
            await self._cache_service.set_cached_response(
                cache_key,
                {
                    "answer": answer,
                    "intent_detected": intent_detected,
                    "search_metrics": merged_metrics,
                    "embedding_cache_hit": embedding_cache_hit,
                    "sql_phases": base_phases + tool_phases,
                    "store_results": store_results,
                    "inventory_results": inventory_results,
                    "map_actions": map_actions,
                },
                ttl_minutes=get_settings().chat.response_cache_ttl_minutes,
            )

        return {
            **frame,
            "answer": answer,
            "response_time_ms": elapsed_ms,
            "intent_detected": intent_detected,
            "search_metrics": merged_metrics,
            "sql_phases": all_phases,
            "from_cache": False,
            "embedding_cache_hit": embedding_cache_hit,
            "store_results": store_results,
            "inventory_results": inventory_results,
            "map_actions": map_actions,
            "location_context": safe_loc,
        }

    def _build_tool_services(self, fallback_services: Any, *, turn_context: HybridTurnContext | None = None) -> Any:
        if isinstance(fallback_services, CoffeeToolContext):
            if turn_context is not None and fallback_services.turn_context is None:
                fallback_services.turn_context = turn_context
            return fallback_services
        if any((self._product_service, self._store_service, self._vertex_ai_service, self._metrics_service)):
            inv_svc = self._store_service if isinstance(self._store_service, InventoryService) else None
            return CoffeeToolContext(
                product_service=self._product_service,
                store_service=self._store_service,
                inventory_service=inv_svc,
                maps_service=MapsService(),
                embedding_service=self._vertex_ai_service,
                vertex_ai_service=self._vertex_ai_service,
                metrics_service=self._metrics_service,
                turn_context=turn_context,
            )
        return fallback_services

    def _build_dynamic_context(
        self,
        *,
        dynamic_context: str | None,
        persona: str,
        safe_loc: dict[str, Any],
        turn_context: HybridTurnContext | None,
    ) -> str:
        persona_cfg = self._persona_manager.PERSONAS.get(persona, self._persona_manager.PERSONAS["barista"])
        parts: list[str] = [f"Persona: {persona_cfg.name}\n{persona_cfg.system_prompt_addon}"]
        if dynamic_context:
            parts.append(dynamic_context)
        if safe_loc and (not dynamic_context or "Location Context:" not in dynamic_context):
            parts.append(f"Location Context: {safe_loc}")
        if turn_context is not None and turn_context.products:
            candidate_lines = [f"- {p.name} (${p.price:.2f}): {p.description}" for p in turn_context.products[:3]]
            parts.append("Pre-fetched Catalog Candidates:\n" + "\n".join(candidate_lines))
        return "\n\n".join(parts)

    async def _append_assistant_event(
        self, *, session_id: str, invocation_id: str, turn_num: int, seq: int, answer: str
    ) -> None:
        if not answer:
            return
        await self._event_store.append_event(
            AgentEvent(
                session_id=session_id,
                invocation_id=invocation_id,
                agent=self._spec_tree.root.name,
                seq=seq,
                turn=turn_num,
                partial=False,
                content=Content(role="model", parts=[Part(text=answer)]),
            )
        )


def _extract_session_state(existing: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(existing, dict):
        return {}
    raw_state = existing.get("state")
    if isinstance(raw_state, dict):
        return dict(raw_state)
    if isinstance(raw_state, str) and raw_state.strip():
        try:
            decoded = msgspec.json.decode(raw_state.encode("utf-8"))
        except msgspec.DecodeError:
            return {}
        return dict(decoded) if isinstance(decoded, dict) else {}
    return {}


def _extract_last_products(session_state: dict[str, Any]) -> list[str] | None:
    raw = session_state.get("last_products")
    if not isinstance(raw, list):
        return None
    return [str(item) for item in raw if str(item).strip()] or None
