# Cymbal Coffee: Oracle 26ai + Vertex AI + Native AI Runtime

Reference app for AI-powered product search on Oracle AI Database 26ai with
single-query Hybrid RRF retrieval (Oracle Text lexical ranking + HNSW vector
search), Vertex AI `gemini-embedding-2`, native `google-genai` `AgentRuntime`
(`Gemini 3.8 Flash`), `LitestarMCP`, `LitestarA2A`, `litestar-queues`, SQLSpec,
HTMX, and Vite.

<div align="center">
  <img src="docs/screenshots/chat_snippet.png" alt="Cymbal Coffee Chat Snippet" style="background-color: #f9f9f9; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
</div>

## Quickstart

Prerequisites: Python 3.12+, Docker or Podman-compatible local containers,
`make`, and Google Vertex AI (or Gemini API key) credentials.

```bash
make install
uv run python manage.py init
make start-infra
uv run coffee upgrade
uv run coffee run
```

`make install` bootstraps `uv` if it isn't already on your PATH, then
installs Python and frontend dependencies and builds the Vite assets that
Litestar serves. `manage.py init` walks you through `.env` (deployment mode,
database connection, Vertex AI project) without re-running the install.

Open <http://localhost:5006>. The chat page is `/`; the Oracle vector explorer
is `/explore`.

If `.env` still has `VERTEX_AI_PROJECT_ID=demo-project`, chat returns a
clean 503 until real Vertex AI credentials are configured. Use Application
Default Credentials or set `GOOGLE_API_KEY` / `VERTEX_AI_API_KEY`.

## What's Inside

- 130 Cymbal Coffee products, 17 stores, 14 route exemplars, and committed `gemini-embedding-2` fixtures.
- Oracle `VECTOR(3072, FLOAT32)` storage with HNSW `INMEMORY NEIGHBOR GRAPH` (`FETCH APPROX`) and `CTXSYS.CONTEXT` `MULTI_COLUMN_DATASTORE` indexes.
- Single-query Oracle 26ai Hybrid RRF routing & retrieval (`hybrid-search-turn` + `hybrid-term-hits`) fusing BM25-style lexical ranking (`CONTAINS`/`SCORE`) and HNSW cosine similarity—skipping a separate LLM intent classifier call.
- Native `AgentRuntime` (`google-genai`, `Gemini 3.8 Flash`) with closure-bound tools, Oracle-backed `agent_session` / `agent_event` stores, `LitestarMCP` (`POST /mcp`), `LitestarA2A` (`POST /a2a`), and `litestar-queues` background workers on Oracle 26ai.
- HTMX + Tailwind + vanilla JavaScript pages for chat and vector-plan exploration.

## End-user commands

| Command | Purpose |
| --- | --- |
| `uv run coffee run [--no-worker]` | Start the Granian + Litestar server (with embedded queue worker by default) |
| `uv run coffee worker run` | Start a standalone `litestar-queues` worker fleet |
| `uv run coffee worker status` | Inspect background task queue counts |
| `uv run coffee upgrade` | Apply migrations and load committed demo data |
| `uv run coffee bulk-embed [--enqueue]` | Refresh embeddings inline or enqueue `products.embed_missing` |
| `uv run coffee clear-cache --force` | Clear response and embedding caches |
| `uv run coffee model-info` | Check active model configuration |

## Documentation

The published docs site is the home for the long-form material:

- **Walkthrough** — what one chat message actually does, end to end.
- **Concepts** — vectors in Oracle, Hybrid RRF RAG, native AI runtime routing, and map links.
- **Reference** — quickstart, CLI reference, API reference, and a "for the curious" appendix.
- **Developers** — raw migration entrypoint, fixture regeneration, and
  verification commands. Start here if you intend to modify the demo.

External references:

- Oracle vectors: <https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/>
- Vertex AI: <https://cloud.google.com/vertex-ai/docs>
- Litestar: <https://docs.litestar.dev/>
- SQLSpec: <https://sqlspec.dev>

## Troubleshooting

AI service returns 503:
Replace placeholder Vertex settings in `.env` and confirm ADC or API-key auth.
`uv run coffee model-info` shows the active model settings.

HNSW migration fails with `ORA-51962`:
Restart the local database after `vector_memory_size` is configured.

Chat feels slow:
Use `/explore` to inspect Oracle timing and EXPLAIN PLAN output, then clear stale
caches with `uv run coffee clear-cache --force` before re-testing.
