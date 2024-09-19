# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from typing import Any, Literal, TypedDict

from app.lib.schema import CamelizedBaseStruct


class CoffeeChatMessage(CamelizedBaseStruct):
    message: str


class PointsOfInterest(TypedDict):
    id: int
    name: str
    address: str
    latitude: float
    longitude: float


class ChatMessage(TypedDict):
    message: str
    source: Literal["human", "ai", "system"]


class CoffeeChatReply(TypedDict):
    message: str
    messages: list[ChatMessage]
    answer: str
    points_of_interest: list[PointsOfInterest]
    llm_response: Any


class HistoryMeta(TypedDict):
    conversation_id: str
    user_id: str
