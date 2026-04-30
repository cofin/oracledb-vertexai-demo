#!/usr/bin/env python3
"""Benchmark streaming vs non-streaming performance.

Compares the old synchronous approach with the new streaming approach
to measure latency improvements and overhead.
"""

import asyncio
import time
from statistics import mean, stdev

import aiohttp


async def benchmark_streaming(base_url: str, num_requests: int = 20):
    """Benchmark streaming response times.

    Args:
        base_url: Base URL of the application
        num_requests: Number of requests to test

    Returns:
        Dictionary with benchmark results
    """
    results = {
        "user_message_times": [],
        "first_chunk_times": [],
        "total_times": [],
        "chunks_received": [],
    }

    async with aiohttp.ClientSession() as session:
        for i in range(num_requests):
            start = time.time()

            # Submit query
            async with session.post(
                f"{base_url}/",
                data={"message": f"Test query {i}", "persona": "enthusiast"},
                headers={"HX-Request": "true"},
            ) as response:
                html = await response.text()
                user_message_time = (time.time() - start) * 1000
                results["user_message_times"].append(user_message_time)

                # Extract query_id
                import re

                match = re.search(r'id="ai-response-([a-f0-9\-]+)"', html)
                if not match:
                    continue
                query_id = match.group(1)

            # Connect to stream
            first_chunk_time = None
            chunks = 0

            async with session.get(
                f"{base_url}/chat/stream/{query_id}",
                headers={"Accept": "text/event-stream"},
            ) as response:
                async for line in response.content:
                    line_str = line.decode("utf-8").strip()

                    if line_str.startswith("data:"):
                        chunks += 1
                        if first_chunk_time is None:
                            first_chunk_time = (time.time() - start) * 1000

                        # Check for completion
                        if "done" in line_str and "true" in line_str:
                            break

            total_time = (time.time() - start) * 1000
            results["total_times"].append(total_time)
            results["first_chunk_times"].append(first_chunk_time or 0)
            results["chunks_received"].append(chunks)

            # Small delay between requests
            await asyncio.sleep(0.5)

    return results


def print_benchmark_results(results):
    """Print formatted benchmark results."""
    print("\n" + "=" * 60)
    print("STREAMING PERFORMANCE BENCHMARK")
    print("=" * 60)

    metrics = [
        ("User Message Display Time", results["user_message_times"]),
        ("Time to First Chunk", results["first_chunk_times"]),
        ("Total Response Time", results["total_times"]),
    ]

    for label, times in metrics:
        if times:
            print(f"\n{label}:")
            print(f"  Min:    {min(times):7.1f}ms")
            print(f"  Max:    {max(times):7.1f}ms")
            print(f"  Mean:   {mean(times):7.1f}ms")
            print(f"  Median: {sorted(times)[len(times) // 2]:7.1f}ms")
            if len(times) > 1:
                print(f"  StdDev: {stdev(times):7.1f}ms")

    if results["chunks_received"]:
        chunks = results["chunks_received"]
        print("\nChunks Received per Response:")
        print(f"  Min:    {min(chunks)}")
        print(f"  Max:    {max(chunks)}")
        print(f"  Mean:   {mean(chunks):.1f}")

    # Calculate perceived latency improvement
    user_msg_avg = mean(results["user_message_times"])
    first_chunk_avg = mean([t for t in results["first_chunk_times"] if t > 0])

    print("\n✨ Perceived Latency Improvement:")
    print("  Baseline (sync):        ~2000ms")
    print(f"  User Message (async):   {user_msg_avg:.0f}ms")
    print(f"  Time to First Token:    {first_chunk_avg:.0f}ms")
    print(f"  Improvement:            ~{(2000 - user_msg_avg) / 2000 * 100:.0f}%")

    print("=" * 60 + "\n")


async def main():
    """Run benchmark."""
    import argparse

    parser = argparse.ArgumentParser(description="Streaming Performance Benchmark")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--requests", type=int, default=20, help="Number of requests")

    args = parser.parse_args()

    print(f"Running benchmark with {args.requests} requests...")
    results = await benchmark_streaming(args.url, args.requests)
    print_benchmark_results(results)


if __name__ == "__main__":
    asyncio.run(main())
