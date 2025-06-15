#!/usr/bin/env python
"""Generate demo traffic for the performance dashboard."""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx
from rich.console import Console
from rich.table import Table

from app.lib.settings import get_settings

console = Console()

# Get the app URL from settings
settings = get_settings()
APP_URL = settings.app.URL.rstrip("/")

# Constants
HTTP_OK = 200
VECTOR_DEMO_PERCENTAGE = 0.3

# Sample queries for demo
DEMO_QUERIES = [
    "strong morning coffee",
    "smooth afternoon blend",
    "decaf evening option",
    "fruity light roast",
    "bold espresso beans",
    "chocolate notes coffee",
    "nutty flavored coffee",
    "organic fair trade",
    "single origin beans",
    "cold brew concentrate",
    "Ethiopian Yirgacheffe",
    "Colombian supremo",
    "dark roast french",
    "medium roast arabica",
    "vanilla flavored beans",
    "caramel macchiato blend",
    "hazelnut coffee",
    "pumpkin spice seasonal",
    "Christmas blend",
    "Italian espresso",
]


async def make_search_request(client: httpx.AsyncClient, query: str) -> dict[str, Any]:
    """Make a search request to the API."""
    try:
        response = await client.post(
            f"{APP_URL}/chat",
            json={"message": query, "persona": "enthusiast"},
            timeout=30.0,
        )
        if response.status_code == HTTP_OK:
            return {"status": "success", "query": query, "time": response.elapsed.total_seconds() * 1000}
        return {"status": "error", "query": query, "error": f"Status {response.status_code}"}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "query": query, "error": str(e)}


async def make_vector_demo_request(client: httpx.AsyncClient, query: str) -> dict[str, Any]:
    """Make a vector search demo request."""
    try:
        response = await client.post(
            f"{APP_URL}/api/vector-demo",
            data={"query": query},
            timeout=10.0,
        )
        if response.status_code == HTTP_OK:
            return {"status": "success", "query": query, "type": "vector_demo"}
        return {"status": "error", "query": query, "error": f"Status {response.status_code}"}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "query": query, "error": str(e)}


async def generate_demo_traffic(duration_minutes: int = 5, requests_per_minute: int = 20) -> None:
    """Generate realistic demo traffic for the dashboard."""
    console.print("[bold cyan]Starting dashboard demo traffic generator...[/bold cyan]")
    console.print(f"Duration: {duration_minutes} minutes")
    console.print(f"Target rate: {requests_per_minute} requests/minute")
    console.print(f"[yellow]Open {APP_URL}/dashboard to view metrics[/yellow]\n")

    total_requests = 0
    successful_requests = 0
    failed_requests = 0
    start_time = asyncio.get_event_loop().time()

    # Create a table for live stats
    stats_table = Table(title="Demo Traffic Statistics", show_header=True, header_style="bold magenta")
    stats_table.add_column("Metric", style="cyan", no_wrap=True)
    stats_table.add_column("Value", style="green")

    async with httpx.AsyncClient() as client:
        while (asyncio.get_event_loop().time() - start_time) < (duration_minutes * 60):
            # Random query
            query = random.choice(DEMO_QUERIES)  # noqa: S311

            # Mix of regular chat and vector demo requests
            if random.random() < VECTOR_DEMO_PERCENTAGE:  # noqa: S311
                result = await make_vector_demo_request(client, query)
                request_type = "vector"
            else:
                result = await make_search_request(client, query)
                request_type = "chat"

            total_requests += 1
            if result["status"] == "success":
                successful_requests += 1
                console.print(f"✓ [{request_type}] {query[:30]}... ({result.get('time', 'N/A'):.0f}ms)", style="green")
            else:
                failed_requests += 1
                console.print(f"✗ [{request_type}] {query[:30]}... - {result['error']}", style="red")

            # Update stats display periodically
            if total_requests % 10 == 0:
                elapsed_time = asyncio.get_event_loop().time() - start_time
                current_rate = total_requests / (elapsed_time / 60)

                console.clear()
                stats_table = Table(title="Demo Traffic Statistics", show_header=True, header_style="bold magenta")
                stats_table.add_column("Metric", style="cyan", no_wrap=True)
                stats_table.add_column("Value", style="green")
                stats_table.add_row("Total Requests", str(total_requests))
                stats_table.add_row(
                    "Successful", f"{successful_requests} ({successful_requests / total_requests * 100:.1f}%)"
                )
                stats_table.add_row("Failed", str(failed_requests))
                stats_table.add_row("Current Rate", f"{current_rate:.1f} req/min")
                stats_table.add_row("Elapsed Time", f"{elapsed_time:.1f}s")
                console.print(stats_table)

            # Random delay to simulate real traffic patterns
            delay = random.uniform(60 / requests_per_minute * 0.5, 60 / requests_per_minute * 1.5)  # noqa: S311
            await asyncio.sleep(delay)

    # Final stats
    elapsed_time = asyncio.get_event_loop().time() - start_time
    final_rate = total_requests / (elapsed_time / 60)

    console.print("\n[bold green]Demo traffic generation completed![/bold green]")
    final_table = Table(title="Final Statistics", show_header=True, header_style="bold cyan")
    final_table.add_column("Metric", style="cyan", no_wrap=True)
    final_table.add_column("Value", style="green")
    final_table.add_row("Total Requests", str(total_requests))
    final_table.add_row("Successful", f"{successful_requests} ({successful_requests / total_requests * 100:.1f}%)")
    final_table.add_row("Failed", str(failed_requests))
    final_table.add_row("Average Rate", f"{final_rate:.1f} req/min")
    final_table.add_row("Total Duration", f"{elapsed_time:.1f}s")
    console.print(final_table)


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate demo traffic for the performance dashboard")
    parser.add_argument("--duration", type=int, default=5, help="Duration in minutes (default: 5)")
    parser.add_argument("--rate", type=int, default=20, help="Requests per minute (default: 20)")

    args = parser.parse_args()

    try:
        asyncio.run(generate_demo_traffic(args.duration, args.rate))
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo traffic generation stopped by user[/yellow]")


if __name__ == "__main__":
    main()
