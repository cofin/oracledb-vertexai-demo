# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Vertex AI embedding and Oracle vector search orchestration services."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any

from google.genai.types import EmbedContentConfig, GenerateContentConfig

from app.config import db_manager
from app.domain.products.schemas import ExplainPlan, ExplainPlanRow, ProductMatch

if TYPE_CHECKING:
    from google.genai import Client

    from app.domain.products.services._products import ProductService

__all__ = (
    "EMBEDDING_PURPOSE_INSTRUCTIONS",
    "GEMINI_EMBEDDING_2_MODEL",
    "EmbeddingService",
    "OracleVectorSearchService",
    "VertexAIService",
)

GEMINI_EMBEDDING_2_MODEL = "gemini-embedding-2"
EMBEDDING_PURPOSE_INSTRUCTIONS = {
    "query": (
        "Task: Generate an embedding for a search query to retrieve relevant "
        "Cymbal Coffee menu and store availability documents."
    ),
    "document": (
        "Task: Generate an embedding for a document that can be retrieved by Cymbal Coffee customer search queries."
    ),
}


class VertexAIService:
    """Service for interacting with Google Vertex AI."""

    def __init__(
        self, client: Client, model: str, embedding_model: str, embedding_dimensions: int, cache_service: Any
    ) -> None:
        self.client = client
        self.model = model
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.cache_service = cache_service

    async def get_text_embedding(
        self, text: str, *, embedding_purpose: str = "document", return_cache_status: bool = False
    ) -> Any:
        """Compute or retrieve a cached text embedding vector."""
        cached = await self.cache_service.get_embedding(text, self.embedding_model)
        if cached:
            return (cached, True) if return_cache_status else cached

        content = _embedding_content(self.embedding_model, text, embedding_purpose)
        config_kwargs: dict[str, Any] = {"output_dimensionality": self.embedding_dimensions}

        response = await self.client.aio.models.embed_content(
            model=self.embedding_model, contents=content, config=EmbedContentConfig(**config_kwargs)
        )
        embedding_list = response.embeddings
        if not embedding_list or not embedding_list[0].values:
            return None
        embedding = embedding_list[0].values
        await self.cache_service.save_embedding(text, embedding, self.embedding_model)
        return (embedding, False) if return_cache_status else embedding

    async def generate_structured_content(self, *, model: str, contents: str, config: GenerateContentConfig) -> Any:
        """Generate structured content through the shared Vertex AI client."""
        return await self.client.aio.models.generate_content(model=model, contents=contents, config=config)


EmbeddingService = VertexAIService


class OracleVectorSearchService:
    """Orchestrator for Oracle + Vertex AI vector search operations."""

    def __init__(self, vertex_ai_service: VertexAIService, product_service: ProductService) -> None:
        self.vertex_ai_service = vertex_ai_service
        self.product_service = product_service

    async def similarity_search(
        self, query: str, k: int = 5, threshold: float = 0.5, *, store_id: int | None = None
    ) -> tuple[list[ProductMatch], bool, dict[str, float]]:
        """Embed a query and execute Oracle vector similarity search."""
        start_time = time.time()
        embedding, cache_hit = await self.vertex_ai_service.get_text_embedding(
            query, embedding_purpose="query", return_cache_status=True
        )
        embedding_ms = (time.time() - start_time) * 1000

        oracle_start = time.time()
        results = await self.product_service.search_by_vector(
            embedding, similarity_threshold=threshold, limit=k, store_id=store_id
        )
        oracle_ms = (time.time() - oracle_start) * 1000

        return results, cache_hit, {"embedding_ms": embedding_ms, "oracle_ms": oracle_ms}

    @staticmethod
    def parse_plan_rows(plan_lines: list[str]) -> list[ExplainPlanRow]:
        """Parse the operation table rows from ``DBMS_XPLAN.DISPLAY`` output."""

        def cell(cells: list[str], index: int) -> str:
            try:
                return cells[index]
            except IndexError:
                return ""

        rows: list[ExplainPlanRow] = []
        for line in plan_lines:
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells[0].lower() == "id":
                continue
            operation_cell = cell(cells, 1)
            if not operation_cell:
                continue
            plan_id = re.sub(r"[^0-9]", "", cells[0])
            if not plan_id:
                continue
            operation = re.sub(r"\s+", " ", operation_cell).strip()
            rows.append(
                ExplainPlanRow(
                    id=plan_id,
                    operation=operation,
                    name=cell(cells, 2),
                    rows=cell(cells, 3),
                    bytes=cell(cells, 4),
                    cost=cell(cells, 5),
                    time=cell(cells, 6),
                    raw_line=line,
                    is_vector="VECTOR" in line.upper(),
                )
            )
        return rows

    async def explain_search_plan(self, query: str) -> ExplainPlan:
        """Run EXPLAIN PLAN against the vector-search SQL and pull the plan."""
        embedding, _ = await self.vertex_ai_service.get_text_embedding(
            query, embedding_purpose="query", return_cache_status=True
        )
        await self.product_service.driver.execute(
            db_manager.get_sql("explain-plan-vector-search"), query_vector=embedding, threshold=0.5, limit=5
        )
        rows = await self.product_service.driver.select(db_manager.get_sql("explain-plan-display"))
        plan_lines = [str(row["plan_table_output"]) for row in rows]
        plan_rows = self.parse_plan_rows(plan_lines)
        plan_summary = next(
            (f"{row.operation} {row.name}".strip() for row in plan_rows if row.is_vector),
            plan_rows[0].operation if plan_rows else (plan_lines[0].strip() if plan_lines else ""),
        )
        return ExplainPlan(plan_lines=plan_lines, plan_summary=plan_summary, plan_rows=plan_rows)


def _embedding_content(model: str, text: str, embedding_purpose: str) -> str:
    if GEMINI_EMBEDDING_2_MODEL not in model:
        return text
    instruction = EMBEDDING_PURPOSE_INSTRUCTIONS.get(embedding_purpose)
    if instruction is None:
        return text
    return f"{instruction}\n\n{text}"
