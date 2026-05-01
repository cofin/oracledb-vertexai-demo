# Cymbal Coffee: Oracle 26ai + Vertex AI + ADK

Reference app for AI-powered product search on Oracle Database 26ai with Google
ADK 2.0, Vertex AI, SQLSpec, Litestar, HTMX, and Vite.

## 5-Minute Quickstart

Prerequisites: Python 3.12+, Docker or Podman-compatible local containers,
`make`, and Google Vertex AI credentials.

```bash
make install-uv
make install
uv run python manage.py init --run-install
make start-infra
uv run python manage.py database upgrade --no-prompt
uv run coffee load-fixtures
uv run coffee run
```

Open <http://localhost:5006>. The chat page is `/`; the Oracle vector explorer
is `/explore`.

If `.env` still has `VERTEX_AI_PROJECT_ID=demo-project`, chat will return a
clean 503 until real Vertex AI credentials are configured. Use Application
Default Credentials or set `GOOGLE_API_KEY` / `VERTEX_AI_API_KEY`.

## What's Inside

- 47 Cymbal Coffee products with committed `gemini-embedding-001` fixtures.
- Oracle `VECTOR(3072, FLOAT32)` storage with HNSW INMEMORY indexes.
- ADK 2.0 workflow with parallel Flash-Lite intent classification and streaming responses.
- HTMX + Tailwind + Alpine pages for chat and vector-plan exploration.
- Oracle-backed response cache, embedding cache, metrics, Litestar sessions, and ADK sessions.

## Architecture

Litestar serves two pages and a small JSON/HTMX API. Dishka provides a
request-scoped SQLSpec Oracle driver plus domain services, while app-scoped
providers own the Google GenAI client, SQLSpec ADK session service, intent
classifier, and ADK runner.

Oracle 26ai stores products, embeddings, caches, metrics, server-side web
sessions, and ADK session/event rows. Vertex AI generates 3072-dimensional
embeddings and Gemini replies; ADK coordinates a workflow graph whose tool calls
close over request-scoped services.

## Common Commands

| Command | Purpose |
| --- | --- |
| `uv run coffee run` | Start the Granian + Litestar dev server |
| `uv run python manage.py database upgrade --no-prompt` | Apply SQLSpec migrations |
| `uv run coffee load-fixtures` | Load committed demo data |
| `uv run coffee bulk-embed --force` | Regenerate product embeddings |
| `uv run coffee export-fixtures` | Refresh committed fixture files |
| `uv run coffee clear-cache --force` | Clear response and embedding caches |
| `uv run coffee model-info` | Check model configuration |
| `make lint` / `make test` | Run repo verification |

## Docs

- Architecture: [.agents/knowledge/guides/architecture.md](.agents/knowledge/guides/architecture.md)
- Maps setup and privacy: [docs/maps.md](docs/maps.md)
- Oracle vector search: [.agents/knowledge/guides/oracle-vector-search.md](.agents/knowledge/guides/oracle-vector-search.md)
- ADK patterns: [.agents/knowledge/guides/adk-agent-patterns.md](.agents/knowledge/guides/adk-agent-patterns.md)
- Oracle vectors: <https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/>
- Vertex AI: <https://cloud.google.com/vertex-ai/docs>
- Litestar: <https://docs.litestar.dev/>

## Troubleshooting

AI service returns 503:
Replace placeholder Vertex settings in `.env` and confirm ADC or API-key auth.
`uv run coffee model-info` shows the active model settings.

HNSW migration fails with `ORA-51962`:
Restart the local database after `vector_memory_size` is configured. See
[oracle-vector-search.md](.agents/knowledge/guides/oracle-vector-search.md).

Chat feels slow:
Use `/explore` to inspect Oracle timing and EXPLAIN PLAN output, then clear stale
caches with `uv run coffee clear-cache --force` before re-testing.
