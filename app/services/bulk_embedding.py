"""Bulk embedding service for Oracle Database integration with Vertex AI."""

from __future__ import annotations

import array
import asyncio
import json
import uuid
from typing import TYPE_CHECKING, Any, Final

import structlog
from google.cloud import aiplatform, storage  # type: ignore[attr-defined]

from app.lib.settings import get_settings

if TYPE_CHECKING:
    from google.cloud.aiplatform import BatchPredictionJob

    from app.services.product import ProductService
    from app.services.vertex_ai import VertexAIService

logger = structlog.get_logger()

# Constants
RECOMMENDED_BATCH_SIZE: Final[int] = 25000


def convert_to_oracle_vector(embedding: list[float]) -> array.array:
    """Convert a Python list of floats to Oracle VECTOR format."""
    return array.array("f", embedding)


class BulkEmbeddingService:
    """Service for bulk embedding operations using Vertex AI Batch Prediction."""

    def __init__(self, product_service: ProductService) -> None:
        """Initialize the bulk embedding service."""
        self.product_service = product_service
        settings = get_settings()

        # Initialize AI Platform
        aiplatform.init(
            project=settings.app.GOOGLE_PROJECT_ID,
            location="us-central1",
        )

        # Initialize Cloud Storage client
        self.storage_client = storage.Client(project=settings.app.GOOGLE_PROJECT_ID)
        self.bucket_name = f"{settings.app.GOOGLE_PROJECT_ID}-bulk-embeddings"
        self.embedding_model = "text-embedding-004"

    async def create_storage_bucket_if_not_exists(self) -> None:
        """Create storage bucket for batch processing if it doesn't exist."""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            if not bucket.exists():
                bucket = self.storage_client.create_bucket(self.bucket_name, location="us-central1")
                await logger.ainfo(f"Created storage bucket: {self.bucket_name}")
            else:
                await logger.ainfo(f"Using existing storage bucket: {self.bucket_name}")
        except Exception:
            await logger.aerror("Failed to create/access storage bucket", exc_info=True)
            raise

    async def export_products_to_jsonl(self, output_path: str) -> int:
        """Export products without embeddings to JSONL format for batch processing."""

        # Get products that need embeddings (where embedding is NULL)
        async with self.product_service.get_cursor() as cursor:
            await cursor.execute("""
                SELECT id, name, description
                FROM product
                WHERE embedding IS NULL
            """)

            batch_data = []
            async for row in cursor:
                product_id, name, description = row
                # Combine product name and description for embedding
                text_content = f"{name}: {description}"

                # Format for Vertex AI batch prediction
                request_data = {
                    "content": text_content,
                    "task_type": "RETRIEVAL_DOCUMENT",
                    "title": name,
                    # Include product ID for mapping results back
                    "metadata": {"product_id": str(product_id)},
                }
                batch_data.append(request_data)

        # Write to JSONL file
        bucket = self.storage_client.bucket(self.bucket_name)
        blob = bucket.blob(output_path)

        jsonl_content = "\n".join(json.dumps(item) for item in batch_data)
        blob.upload_from_string(jsonl_content, content_type="application/jsonl")

        await logger.ainfo(f"Exported {len(batch_data)} products to {output_path}")
        return len(batch_data)

    async def submit_batch_embedding_job(
        self, input_path: str, output_path: str, job_display_name: str | None = None
    ) -> BatchPredictionJob:
        """Submit a batch prediction job for embeddings."""
        if job_display_name is None:
            job_display_name = f"bulk-embeddings-{uuid.uuid4().hex[:8]}"

        # Input and output URIs
        input_uri = f"gs://{self.bucket_name}/{input_path}"
        output_uri = f"gs://{self.bucket_name}/{output_path}"

        await logger.ainfo(f"Submitting batch job: {job_display_name}")
        await logger.ainfo(f"Input URI: {input_uri}")
        await logger.ainfo(f"Output URI: {output_uri}")

        # Create batch prediction job
        job = aiplatform.BatchPredictionJob.create(
            job_display_name=job_display_name,
            model_name=f"publishers/google/models/{self.embedding_model}",
            instances_format="jsonl",
            predictions_format="jsonl",
            gcs_source=input_uri,
            gcs_destination_prefix=output_uri,
        )

        await logger.ainfo(f"Batch job submitted with ID: {job.resource_name}")
        return job

    async def wait_for_job_completion(self, job: BatchPredictionJob, check_interval: int = 60) -> None:
        """Wait for batch job to complete with periodic status checks."""
        await logger.ainfo(f"Waiting for job completion: {job.display_name}")

        while True:
            # Get current job state - BatchPredictionJob doesn't have refresh method
            # Instead, we need to fetch the job again
            job = aiplatform.BatchPredictionJob.get(job.resource_name)  # type: ignore[attr-defined]
            state = job.state.name

            await logger.ainfo(f"Job state: {state}")

            if state == "JOB_STATE_SUCCEEDED":
                await logger.ainfo("Batch job completed successfully!")
                break
            if state in ["JOB_STATE_FAILED", "JOB_STATE_CANCELLED"]:
                error_msg = f"Batch job failed with state: {state}"
                if hasattr(job, "error"):
                    error_msg += f" Error: {job.error}"
                await logger.aerror(error_msg)
                raise RuntimeError(error_msg)

            # Wait before next check
            await asyncio.sleep(check_interval)

    async def process_embedding_results(self, output_path: str) -> int:
        """Process embedding results and update Oracle database."""
        bucket = self.storage_client.bucket(self.bucket_name)

        # List all result files (batch jobs may create multiple output files)
        blobs = bucket.list_blobs(prefix=output_path)

        total_processed = 0
        for blob in blobs:
            if blob.name.endswith(".jsonl"):
                await logger.ainfo(f"Processing results from: {blob.name}")

                # Download and process results
                content = blob.download_as_text()
                lines = content.strip().split("\n")

                for line in lines:
                    if line.strip():
                        result = json.loads(line)
                        await self._update_product_embedding(result)
                        total_processed += 1

        await logger.ainfo(f"Processed {total_processed} embedding results")
        return total_processed

    async def _update_product_embedding(self, result: dict[str, Any]) -> None:
        """Update a single product with its embedding."""
        product_id: str | None = None

        # Extract product ID from metadata
        product_id = result.get("metadata", {}).get("product_id")
        if not product_id:
            await logger.awarn("No product_id found in result metadata")
            return

        # Extract embedding vector
        embedding = result.get("embeddings", {}).get("values", [])
        if not embedding:
            await logger.awarn(f"No embedding found for product {product_id}")
            return

        # Update product in database
        # Convert to Oracle VECTOR format
        oracle_vector = convert_to_oracle_vector(embedding)

        # Use raw SQL to update product
        async with self.product_service.get_cursor() as cursor:
            await cursor.execute(
                """
                UPDATE product
                SET embedding = :embedding
                WHERE id = :id
                """,
                {"embedding": oracle_vector, "id": int(product_id)},
            )
            await self.product_service.connection.commit()

        await logger.adebug(f"Updated embedding for product {product_id}")

    async def run_bulk_embedding_job(self) -> dict[str, Any]:
        """Run a complete bulk embedding job from start to finish."""
        job_id = uuid.uuid4().hex[:8]
        input_path = f"batch-jobs/input_{job_id}.jsonl"
        output_path = f"batch-jobs/output_{job_id}/"

        try:
            # Step 1: Create storage bucket if needed
            await self.create_storage_bucket_if_not_exists()

            # Step 2: Export products to JSONL
            product_count = await self.export_products_to_jsonl(input_path)

            if product_count == 0:
                await logger.ainfo("No products need embeddings")
                return {"status": "skipped", "reason": "no_products_to_process"}

            # Check minimum batch size recommendation
            if product_count < RECOMMENDED_BATCH_SIZE:
                await logger.awarn(
                    "Product count is below recommended minimum for batch processing",
                    product_count=product_count,
                    recommended_minimum=RECOMMENDED_BATCH_SIZE,
                    suggestion="Consider using online API for smaller batches",
                )

            # Step 3: Submit batch job
            job = await self.submit_batch_embedding_job(input_path, output_path, f"bulk-embeddings-{job_id}")

            # Step 4: Wait for completion
            await self.wait_for_job_completion(job)

            # Step 5: Process results
            processed_count = await self.process_embedding_results(output_path)

        except Exception as e:  # noqa: BLE001
            await logger.aerror("Bulk embedding job failed", job_id=job_id, exc_info=True)
            return {"status": "failed", "job_id": job_id, "error": str(e)}

        else:
            return {
                "status": "completed",
                "job_id": job_id,
                "products_exported": product_count,
                "embeddings_processed": processed_count,
                "job_resource_name": job.resource_name,
            }


class OnlineEmbeddingService:
    """Service for real-time embedding operations for new/updated products."""

    def __init__(self, vertex_ai_service: VertexAIService) -> None:
        """Initialize with existing Vertex AI service."""
        self.vertex_ai_service = vertex_ai_service

    async def embed_single_product(self, product_id: str, text_content: str) -> list[float]:
        """Generate embedding for a single product using online API."""
        try:
            # Use the correct vertex AI service method
            return await self.vertex_ai_service.create_embedding(text_content)

        except Exception:
            logger.exception("Failed to generate embedding for product", product_id=product_id)
            raise

    async def process_new_products(self, product_service: ProductService, limit: int = 200) -> int:
        """Process products that need embeddings using online API."""

        # Get products without embeddings (limit to reasonable batch size)
        async with product_service.get_cursor() as cursor:
            await cursor.execute(
                """
                SELECT id, name, description
                FROM product
                WHERE embedding IS NULL
                FETCH FIRST :limit ROWS ONLY
            """,
                {"limit": limit},
            )

            products = [{"id": row[0], "name": row[1], "description": row[2]} async for row in cursor]

        # Use semaphore to limit concurrent requests (avoid rate limiting)
        semaphore = asyncio.Semaphore(16)  # Limit to 16 concurrent requests

        async def process_product(product: dict) -> int:
            async with semaphore:
                text_content = f"{product['name']}: {product['description']}"
                embedding = await self.embed_single_product(str(product["id"]), text_content)

                if embedding:
                    oracle_vector = convert_to_oracle_vector(embedding)
                    # Update product with embedding
                    async with product_service.get_cursor() as cursor:
                        await cursor.execute(
                            """
                            UPDATE product
                            SET embedding = :embedding
                            WHERE id = :id
                            """,
                            {"embedding": oracle_vector, "id": product["id"]},
                        )
                        await product_service.connection.commit()
                        return 1
                return 0

        # Process all products concurrently
        tasks = [process_product(product) for product in products]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful updates
        success_count = sum(1 for result in results if result == 1)

        await logger.ainfo(f"Processed {success_count} products with online embedding API")
        return success_count
