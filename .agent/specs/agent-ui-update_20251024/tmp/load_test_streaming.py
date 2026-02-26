#!/usr/bin/env python3
"""Load test script for SSE streaming endpoint.

Tests concurrent SSE connections to validate streaming performance
and detect memory leaks or connection issues.

Usage:
    python load_test_streaming.py --concurrent 50 --duration 60
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass

import aiohttp
import structlog

logger = structlog.get_logger()


@dataclass
class TestResult:
    """Results from a single SSE streaming test."""

    success: bool
    duration_ms: float
    first_chunk_ms: float
    chunks_received: int
    error: str | None = None


class StreamingLoadTester:
    """Load tester for SSE streaming endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize load tester.

        Args:
            base_url: Base URL of the application
        """
        self.base_url = base_url
        self.results: list[TestResult] = []
        self.stats = defaultdict(int)

    async def test_single_stream(self, session: aiohttp.ClientSession, test_query: str) -> TestResult:
        """Test a single SSE streaming connection.

        Args:
            session: aiohttp client session
            test_query: Query to send

        Returns:
            Test result with timing and success info
        """
        start_time = time.time()
        first_chunk_time = None
        chunks_received = 0

        try:
            # 1. Submit query to get streaming response
            async with session.post(
                f"{self.base_url}/",
                data={"message": test_query, "persona": "enthusiast"},
                headers={"HX-Request": "true"},
            ) as response:
                html = await response.text()

                # Extract query_id from response
                import re

                match = re.search(r'id="ai-response-([a-f0-9\-]+)"', html)
                if not match:
                    return TestResult(
                        success=False,
                        duration_ms=0,
                        first_chunk_ms=0,
                        chunks_received=0,
                        error="Could not extract query_id",
                    )

                query_id = match.group(1)

            # 2. Connect to SSE stream
            async with session.get(
                f"{self.base_url}/chat/stream/{query_id}",
                headers={"Accept": "text/event-stream"},
            ) as response:
                async for line in response.content:
                    line_str = line.decode("utf-8").strip()

                    # Parse SSE events
                    if line_str.startswith("event:"):
                        event_type = line_str.split(":", 1)[1].strip()
                    elif line_str.startswith("data:"):
                        chunks_received += 1
                        if first_chunk_time is None:
                            first_chunk_time = time.time()

                        # Check for completion
                        if "done" in line_str and "true" in line_str:
                            break

            duration_ms = (time.time() - start_time) * 1000
            first_chunk_ms = (first_chunk_time - start_time) * 1000 if first_chunk_time else 0

            return TestResult(
                success=True,
                duration_ms=duration_ms,
                first_chunk_ms=first_chunk_ms,
                chunks_received=chunks_received,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                success=False,
                duration_ms=duration_ms,
                first_chunk_ms=0,
                chunks_received=chunks_received,
                error=str(e),
            )

    async def run_concurrent_tests(self, num_concurrent: int, test_duration_seconds: int):
        """Run concurrent SSE streaming tests.

        Args:
            num_concurrent: Number of concurrent connections
            test_duration_seconds: Duration to run tests
        """
        logger.info("Starting load test", concurrent=num_concurrent, duration=test_duration_seconds)

        test_queries = [
            "Tell me about light roast coffee",
            "What brewing methods do you recommend?",
            "I want a strong espresso blend",
            "What's the difference between arabica and robusta?",
            "Recommend a coffee for cold brew",
        ]

        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            test_count = 0

            while (time.time() - start_time) < test_duration_seconds:
                # Create batch of concurrent requests
                tasks = []
                for i in range(num_concurrent):
                    query = test_queries[test_count % len(test_queries)]
                    tasks.append(self.test_single_stream(session, query))
                    test_count += 1

                # Run batch concurrently
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                for result in batch_results:
                    if isinstance(result, TestResult):
                        self.results.append(result)
                        if result.success:
                            self.stats["success"] += 1
                        else:
                            self.stats["error"] += 1
                            logger.warning("Test failed", error=result.error)
                    else:
                        self.stats["exception"] += 1
                        logger.error("Test exception", exc=result)

                # Small delay between batches
                await asyncio.sleep(1)

        logger.info("Load test complete", total_tests=test_count)

    def print_report(self):
        """Print performance report."""
        if not self.results:
            print("No results to report")
            return

        successful = [r for r in self.results if r.success]

        print("\n" + "=" * 60)
        print("STREAMING LOAD TEST REPORT")
        print("=" * 60)

        print(f"\nTotal Tests: {len(self.results)}")
        print(f"Successful: {self.stats['success']}")
        print(f"Failed: {self.stats['error']}")
        print(f"Exceptions: {self.stats['exception']}")
        print(f"Success Rate: {self.stats['success'] / len(self.results) * 100:.1f}%")

        if successful:
            durations = [r.duration_ms for r in successful]
            first_chunks = [r.first_chunk_ms for r in successful if r.first_chunk_ms > 0]
            chunks = [r.chunks_received for r in successful]

            print("\nDuration Metrics (ms):")
            print(f"  Min: {min(durations):.0f}")
            print(f"  Max: {max(durations):.0f}")
            print(f"  Avg: {sum(durations) / len(durations):.0f}")
            print(f"  P50: {sorted(durations)[len(durations) // 2]:.0f}")
            print(f"  P95: {sorted(durations)[int(len(durations) * 0.95)]:.0f}")

            if first_chunks:
                print("\nTime to First Chunk (ms):")
                print(f"  Min: {min(first_chunks):.0f}")
                print(f"  Max: {max(first_chunks):.0f}")
                print(f"  Avg: {sum(first_chunks) / len(first_chunks):.0f}")
                print(f"  P95: {sorted(first_chunks)[int(len(first_chunks) * 0.95)]:.0f}")

            print("\nChunks Received:")
            print(f"  Min: {min(chunks)}")
            print(f"  Max: {max(chunks)}")
            print(f"  Avg: {sum(chunks) / len(chunks):.1f}")

        print("=" * 60 + "\n")


async def main():
    """Run load test."""
    import argparse

    parser = argparse.ArgumentParser(description="SSE Streaming Load Test")
    parser.add_argument("--concurrent", type=int, default=10, help="Number of concurrent connections")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")

    args = parser.parse_args()

    tester = StreamingLoadTester(base_url=args.url)
    await tester.run_concurrent_tests(args.concurrent, args.duration)
    tester.print_report()


if __name__ == "__main__":
    asyncio.run(main())
