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

from langchain_community.vectorstores import oraclevs
from langchain_community.vectorstores.oraclevs import OracleVS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.documents import Document
from rich import get_console

from app.config import oracle
from app.domain.coffee.llm import get_embeddings_service
from app.lib.settings import get_settings

console = get_console()


def _convert_to_documents(results: list[dict]) -> list[Document]:
    return [
        Document(page_content=result["DESCRIPTION"], metadata={"id": result["ID"], "name": result["NAME"]})
        for result in results
    ]


def generate_embeddings(create_index: bool = True) -> None:
    settings = get_settings()
    model = get_embeddings_service(settings.app.EMBEDDING_MODEL_TYPE)
    with oracle.get_connection() as db_connection, db_connection.cursor() as cursor:
        cursor.execute("select to_char(id) as id, name, description from product order by id")
        columns = [col[0] for col in cursor.description]
        cursor.rowfactory = lambda *args: dict(zip(columns, args, strict=False))
        table_name = "PRODUCT_DESCRIPTION_VS"
        records = cursor.fetchall()
        console.print(f"Creating and loading vectors to {table_name}")
        vs = OracleVS.from_documents(
            _convert_to_documents(results=records),
            model,
            client=db_connection,
            table_name=table_name,
            distance_strategy=DistanceStrategy.DOT_PRODUCT,
        )
        if create_index:
            console.print(f"Creating HNSW Index for {table_name}")
            oraclevs.create_index(
                client=db_connection,
                vector_store=vs,
                params={"idx_name": f"IDX_{table_name}_HNSW".upper(), "idx_type": "HNSW"},
            )
        else:
            console.print(f"Skipping HNSW Index for {table_name}")
