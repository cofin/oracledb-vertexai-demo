# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""OpenAI-compatible Chat Completions and Models wire schemas for the APEX Vertex AI gateway."""

from typing import Literal

import msgspec

from app.lib.schema import FrozenBaseStruct

__all__ = (
    "OpenAIChatChoice",
    "OpenAIChatCompletionChunk",
    "OpenAIChatCompletionRequest",
    "OpenAIChatCompletionResponse",
    "OpenAIChatMessage",
    "OpenAIChatResponseMessage",
    "OpenAIChatStreamChoice",
    "OpenAIChatStreamDelta",
    "OpenAIModelCard",
    "OpenAIModelList",
    "OpenAITextContentPart",
    "OpenAIUsage",
)


class OpenAITextContentPart(FrozenBaseStruct, frozen=True, kw_only=True):
    """Structured text content segment inside an OpenAI chat message."""

    type: str = "text"
    text: str = ""


class OpenAIChatMessage(FrozenBaseStruct, frozen=True, kw_only=True):
    """Role-tagged message accepted in an OpenAI Chat Completions request."""

    role: Literal["system", "developer", "user", "assistant"]
    content: str | list[OpenAITextContentPart] | None = None

    def text_content(self) -> str:
        """Return plain text from string content or joined structured text parts."""
        if self.content is None:
            return ""
        if isinstance(self.content, str):
            return self.content
        return "\n".join(part.text for part in self.content if part.text)


class OpenAIChatCompletionRequest(FrozenBaseStruct, frozen=True, kw_only=True):
    """Request payload for ``POST /api/apex/ai/v1/chat/completions``."""

    messages: list[OpenAIChatMessage] = msgspec.field(default_factory=list)
    model: str = "gemini-3.8-flash"
    temperature: float = 0.2
    max_tokens: int | None = None
    max_completion_tokens: int | None = None
    stream: bool = False


class OpenAIChatResponseMessage(FrozenBaseStruct, frozen=True, kw_only=True, omit_defaults=False):
    """Assistant message returned in a non-streaming OpenAI completion choice."""

    role: Literal["assistant"] = "assistant"
    content: str = ""


class OpenAIChatChoice(FrozenBaseStruct, frozen=True, kw_only=True, omit_defaults=False):
    """Single completion choice inside an OpenAI Chat Completions response."""

    index: int = 0
    message: OpenAIChatResponseMessage
    finish_reason: str | None = "stop"


class OpenAIChatStreamDelta(FrozenBaseStruct, frozen=True, kw_only=True, omit_defaults=True):
    """Incremental delta emitted inside an OpenAI SSE completion chunk."""

    role: Literal["assistant"] | None = None
    content: str | None = None


class OpenAIChatStreamChoice(FrozenBaseStruct, frozen=True, kw_only=True, omit_defaults=False):
    """Single streaming choice inside an OpenAI SSE completion chunk."""

    index: int = 0
    delta: OpenAIChatStreamDelta
    finish_reason: str | None = None


class OpenAIChatCompletionChunk(FrozenBaseStruct, frozen=True, kw_only=True, omit_defaults=False):
    """SSE event payload emitted when ``stream=True``."""

    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: list[OpenAIChatStreamChoice]


class OpenAIUsage(FrozenBaseStruct, frozen=True, kw_only=True, omit_defaults=False):
    """Token accounting metadata in OpenAI Chat Completions format."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class OpenAIChatCompletionResponse(FrozenBaseStruct, frozen=True, kw_only=True, omit_defaults=False):
    """Non-streaming response payload for ``POST /api/apex/ai/v1/chat/completions``."""

    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[OpenAIChatChoice]
    usage: OpenAIUsage


class OpenAIModelCard(FrozenBaseStruct, frozen=True, kw_only=True, omit_defaults=False):
    """Model metadata card returned by ``GET /api/apex/ai/v1/models``."""

    id: str
    object: Literal["model"] = "model"
    created: int = 1767225600
    owned_by: str = "google-vertex-ai"


class OpenAIModelList(FrozenBaseStruct, frozen=True, kw_only=True, omit_defaults=False):
    """OpenAI model list envelope returned by ``GET /api/apex/ai/v1/models``."""

    object: Literal["list"] = "list"
    data: list[OpenAIModelCard]
