# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Direct Google GenAI client targeting Gemini 3.8 Flash with streaming."""

from collections.abc import AsyncIterator
from typing import Any

from google.genai import Client, types
from google.genai.errors import APIError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.domain.ai.runtime._tools import ToolDeclaration
from app.domain.ai.runtime._types import AgentEvent, Content, FunctionCall, Part, Usage

__all__ = ("HTTP_429_TOO_MANY_REQUESTS", "GeminiModelClient")

HTTP_429_TOO_MANY_REQUESTS = 429


def _is_rate_limit_error(exc: BaseException) -> bool:
    """Return True if an APIError indicates rate limiting.

    Args:
        exc: Exception instance raised during model invocation.

    Returns:
        Boolean indicating whether HTTP status code is 429.
    """
    return isinstance(exc, APIError) and getattr(exc, "code", None) == HTTP_429_TOO_MANY_REQUESTS


class GeminiModelClient:
    """Model client managing direct streaming generation with Gemini 3.8 Flash."""

    def __init__(self, client: Client, default_model: str = "gemini-3.8-flash") -> None:
        """Initialize the Gemini model client.

        Args:
            client: Configured google.genai Client instance.
            default_model: Default Gemini model identifier.
        """
        self._client = client
        self._default_model = default_model

    async def generate_stream(
        self,
        contents: list[Content],
        *,
        tools: list[ToolDeclaration] | None = None,
        system_instruction: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> AsyncIterator[AgentEvent]:
        """Stream generation chunks from Gemini 3.8 Flash, yielding normalized AgentEvents.

        Args:
            contents: Multi-turn conversation history.
            tools: Optional runtime tool declarations.
            system_instruction: System prompt instruction.
            model: Optional model override.
            temperature: Sampling temperature.

        Yields:
            Normalized AgentEvent instances containing content or usage.
        """
        active_model = model or self._default_model
        genai_tools = self._convert_tool_declarations(tools) if tools else None

        config = types.GenerateContentConfig(
            temperature=temperature, system_instruction=system_instruction, tools=genai_tools
        )
        genai_contents = self._convert_contents(contents)
        stream_response = await self._call_stream(model=active_model, contents=genai_contents, config=config)

        async for chunk in stream_response:
            usage = self._extract_usage(chunk)
            extracted_parts = self._extract_chunk_parts(chunk)
            if extracted_parts or usage:
                yield AgentEvent(
                    session_id="",
                    invocation_id="",
                    content=Content(role="model", parts=extracted_parts) if extracted_parts else None,
                    partial=True,
                    usage=usage,
                )

    def _convert_contents(self, contents: list[Content]) -> list[types.Content]:
        """Convert runtime Content items to google.genai types.Content objects."""
        genai_contents: list[types.Content] = []
        for c in contents:
            parts: list[types.Part] = []
            for p in c.parts:
                if p.function_call:
                    parts.append(
                        types.Part(
                            function_call=types.FunctionCall(
                                id=p.function_call.id or None,
                                name=p.function_call.name,
                                args=p.function_call.args,
                            ),
                            thought_signature=p.thought_signature,
                        )
                    )
                elif p.function_response:
                    parts.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                id=p.function_response.id or None,
                                name=p.function_response.name,
                                response=p.function_response.response,
                            )
                        )
                    )
                elif p.text is not None:
                    parts.append(
                        types.Part(
                            text=p.text,
                            thought=p.thought or None,
                            thought_signature=p.thought_signature,
                        )
                    )
                elif p.thought_signature is not None:
                    parts.append(
                        types.Part(
                            thought=p.thought or None,
                            thought_signature=p.thought_signature,
                        )
                    )
            genai_contents.append(types.Content(role=c.role, parts=parts))
        return genai_contents

    def _extract_usage(self, chunk: Any) -> Usage | None:
        """Extract token usage metrics from a streaming response chunk."""
        if chunk.usage_metadata is None:
            return None
        return Usage(
            prompt_tokens=int(chunk.usage_metadata.prompt_token_count or 0),
            output_tokens=int(chunk.usage_metadata.candidates_token_count or 0),
            total_tokens=int(chunk.usage_metadata.total_token_count or 0),
            cached_tokens=int(chunk.usage_metadata.cached_content_token_count or 0),
        )

    def _extract_chunk_parts(self, chunk: Any) -> list[Part]:
        """Extract valid text, thought signature, or function call parts from chunk candidate."""
        if not chunk.candidates:
            return []
        candidate = chunk.candidates[0]
        if not candidate.content or not candidate.content.parts:
            return []
        extracted: list[Part] = []
        for part in candidate.content.parts:
            raw_sig = getattr(part, "thought_signature", None)
            sig_bytes = bytes(raw_sig) if isinstance(raw_sig, (bytes, bytearray)) else None
            if getattr(part, "thought", False):
                if sig_bytes is not None:
                    extracted.append(Part(thought=True, thought_signature=sig_bytes))
                continue
            if part.function_call:
                call = FunctionCall(
                    id=part.function_call.id or "",
                    name=part.function_call.name or "",
                    args=part.function_call.args or {},
                )
                extracted.append(Part(function_call=call, thought_signature=sig_bytes))
            elif part.text:
                extracted.append(Part(text=part.text, thought_signature=sig_bytes))
            elif sig_bytes is not None:
                extracted.append(Part(thought_signature=sig_bytes))
        return extracted

    def _convert_tool_declarations(self, tools: list[ToolDeclaration]) -> list[Any]:
        """Convert runtime ToolDeclarations into google.genai types.Tool.

        Args:
            tools: List of runtime ToolDeclaration objects.

        Returns:
            List of google.genai Tool instances containing FunctionDeclarations.
        """
        decls = [
            types.FunctionDeclaration(
                name=t.name, description=t.description, parameters_json_schema=t.parameters_json_schema
            )
            for t in tools
        ]
        return [types.Tool(function_declarations=decls)]

    @retry(
        retry=retry_if_exception(_is_rate_limit_error),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.1, min=0.1, max=10),
        reraise=True,
    )
    async def _call_stream(self, model: str, contents: list[types.Content], config: types.GenerateContentConfig) -> Any:
        """Call Google GenAI streaming generation API with rate limit retry.

        Args:
            model: Gemini model identifier.
            contents: GenAI Content items.
            config: GenAI GenerateContentConfig options.

        Returns:
            GenAI streaming response iterator.
        """
        return await self._client.aio.models.generate_content_stream(model=model, contents=contents, config=config)
