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

from functools import lru_cache
from typing import TYPE_CHECKING

from langchain_community.vectorstores.oraclevs import OracleVS
from langchain_core.vectorstores import VectorStore
from langchain_google_vertexai import ChatVertexAI

from app.config import get_settings

if TYPE_CHECKING:
    import oracledb
    from langchain_core.embeddings import Embeddings
    from langchain_core.vectorstores import VectorStore


@lru_cache
def get_llm() -> ChatVertexAI:
    return ChatVertexAI(
        model="gemini-1.5-flash-001",
        temperature=0,
        max_tokens=None,
        max_retries=6,
        stop=None,
        # other params...
    )


@lru_cache
def get_embeddings_service(model_type: str) -> Embeddings:
    settings = get_settings()
    match model_type:
        case "textembedding-gecko@003":
            from langchain_google_vertexai import VertexAIEmbeddings

            return VertexAIEmbeddings(
                google_api_key=settings.app.GOOGLE_API_KEY,
                model=model_type,
            )
        case _:
            msg = "Model is not supported"
            raise ValueError(msg)


def get_embedding(query: str) -> list[float]:
    return get_embeddings_service("textembedding-gecko@003").embed_query(query)


def get_vector_store(connection: oracledb.Connection, embeddings: Embeddings, table_name: str) -> VectorStore:
    return OracleVS(client=connection, embedding_function=embeddings, table_name=table_name, query=None)
