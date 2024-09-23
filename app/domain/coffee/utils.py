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
from typing import TYPE_CHECKING

import structlog
from langchain.schema import SystemMessage
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_community.vectorstores.oraclevs import OracleVS
from langchain_core.vectorstores import VectorStore
from langchain_google_vertexai import ChatVertexAI
from sqlalchemy.ext.asyncio import create_async_engine

from app.lib.settings import get_settings

if TYPE_CHECKING:
    import oracledb
    from langchain_core.embeddings import Embeddings
    from langchain_core.vectorstores import VectorStore


settings = get_settings()
logger = structlog.get_logger()

_chat_engine = create_async_engine(url="sqlite+aiosqlite:///.memory.db")


def get_llm() -> ChatVertexAI:
    return ChatVertexAI(
        model_name="gemini-1.5-flash-001",
        project=settings.app.GOOGLE_PROJECT_ID,
        temperature=0,
        max_tokens=None,
        max_retries=6,
        stop=None,
        # other params...
    )


def get_embeddings_service(model_type: str) -> Embeddings:
    match model_type:
        case "textembedding-gecko@003":
            from langchain_google_vertexai import VertexAIEmbeddings

            return VertexAIEmbeddings(model_name=model_type, project=settings.app.GOOGLE_PROJECT_ID)
        case _:
            msg = "Model is not supported"
            raise ValueError(msg)


def get_vector_store(connection: oracledb.Connection, embeddings: Embeddings, table_name: str) -> VectorStore:
    return OracleVS(client=connection, embedding_function=embeddings, table_name=table_name, query=None)


def get_chat_history_manager(user_id: str, conversation_id: str) -> SQLChatMessageHistory:
    return SQLChatMessageHistory(session_id=f"{user_id}--{conversation_id}", connection=_chat_engine)


def setup_system_message(message: str | None = None) -> SystemMessage:
    """Set up the system message"""
    setup = dedent("""
        You are a helpful AI assistant specializing in coffee recommendations.
        Given a user's chat history and the latest user query and a list of matching coffees from a database, provide an engaging and informative response.
        If the user is asking about coffee recommendations and locations, provide the information and finish the response with "the map below displays the locations where you can find the coffee."
        If the user is asking a general question or making a statement, respond appropriately without using the database.
        Your responses should be as concise as possible.

        {context}
    """)
    system_message = message or dedent(setup).strip()
    return SystemMessage(content=system_message)
