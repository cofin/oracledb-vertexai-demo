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

from textwrap import dedent
from typing import TYPE_CHECKING, Any

import structlog
from langchain.chat_models.base import BaseChatModel
from langchain.schema import SystemMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import (
    ConfigurableFieldSpec,
    Runnable,
)
from langchain_core.runnables.history import RunnableWithMessageHistory

from app.config import get_settings
from app.domain.coffee.utils import InMemoryHistory

if TYPE_CHECKING:
    from langchain.chat_models.base import BaseChatModel
    from langchain_core.chat_history import BaseChatMessageHistory
    from langchain_core.runnables import Runnable

settings = get_settings()
logger = structlog.get_logger()
conversation_history = InMemoryHistory()

store = {}


def get_session_history(
    user_id: str,
    conversation_id: str,
) -> BaseChatMessageHistory:
    if (user_id, conversation_id) not in store:
        store[(user_id, conversation_id)] = ChatMessageHistory()
    return store[(user_id, conversation_id)]


def setup_system_message(message: str | None = None) -> SystemMessage:
    """Set up the system message"""
    setup = dedent("""
        You are a helpful AI assistant specializing in coffee recommendations.
        Given a user's chat history and the latest user query and a list of matching coffees from a database, provide an engaging and informative response.
        If the user is asking about coffee recommendations and locations, provide the information and finish the response with "the map below displays the locations where you can find the coffee."
        If the user is asking a general question or making a statement, respond appropriately without using the database.
        Your responses should be as concise as possible.

        **Response:**
    """)
    system_message = message or dedent(setup).strip()
    return SystemMessage(content=system_message)


def get_retrieval_chain(model: BaseChatModel, system_message: SystemMessage | None = None) -> Runnable[Any, Any]:
    system_message = system_message if system_message is not None else setup_system_message()

    prompt = ChatPromptTemplate.from_messages(
        [system_message, MessagesPlaceholder("chat_history"), ("human", "{input}")],
    )
    runnable = prompt | model

    return RunnableWithMessageHistory(
        runnable,  # type: ignore[arg-type] # pyright: ignore[reportArgumentType]
        get_session_history,
        history_factory_config=[
            ConfigurableFieldSpec(
                id="user_id",
                annotation=str,
                name="User ID",
                description="Unique identifier for the user.",
                default="",
                is_shared=True,
            ),
            ConfigurableFieldSpec(
                id="conversation_id",
                annotation=str,
                name="Conversation ID",
                description="Unique identifier for the conversation.",
                default="",
                is_shared=True,
            ),
        ],
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )
