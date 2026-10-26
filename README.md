# Cymbal Coffee: Oracle 26ai + Vertex AI + Oracle APEX 26.1

Reference application demonstrating Oracle AI Database 26ai hybrid search (Oracle Text lexical ranking + HNSW vector search), Google Vertex AI (`gemini-embedding-2` + `gemini-3.8-flash`), and Oracle APEX 26.1 operations powered by Litestar 2, SQLSpec `0.69.0`, Dishka, and HTMX.

<div align="center">
  <img src="docs/screenshots/chat_snippet.png" alt="Cymbal Coffee Chat Snippet" style="background-color: #f9f9f9; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
</div>

## Quickstart

Prerequisites: Python 3.12+, Docker or Podman, `make`, and Google Cloud credentials (ADC or Gemini API key).

```bash
make install
uv run python manage.py init
make start-infra
uv run coffee upgrade
uv run coffee run
```

Open <http://localhost:8000> for the coffee concierge (`/`) and vector explorer (`/explore`).

`make start-infra` starts the **Oracle Autonomous AI Database Free 26ai** container (`cymbal-adb-free`), exports its mTLS wallet into `.envs/tns`, and provisions schema `APP` and workspace `COFFEE` on Oracle APEX 26.1.5 + ORDS 26.3 (<https://localhost:8443/ords/apex>).

For non-APEX testing and ephemeral CI integration tests, set `ORACLE_CONTAINER_FLAVOR=free` to use `gvenzl/oracle-free:latest` on `:1521/freepdb1`.

## Oracle APEX 26.1 + Vertex AI

The APEX application lives in `src/apex/cymbal-coffee-ops/` (App ID `100`), featuring a Page 6 Vertex AI Coffee Concierge using `APEX_AI.GENERATE`.

### 1. Direct Vertex AI (Primary)

Connect APEX directly to Vertex AI's OpenAI-compatible endpoint (`aiplatform.googleapis.com`):

```bash
uv run python manage.py infra apex configure-vertex --mode direct --project "$VERTEX_AI_PROJECT_ID" --verify
# Refresh OAuth2 token:
uv run python manage.py infra apex configure-vertex --mode direct --refresh-token --verify
```

### 2. Litestar Gateway (Secondary)

Route APEX through the local Litestar gateway (`/api/apex/ai/v1`):

```bash
uv run python manage.py infra apex configure-vertex --mode gateway --verify
```

### Validate & Import App

```bash
make apex
uv run python manage.py infra apex validate --alias cymbal-coffee-ops
uv run python manage.py infra apex import --alias cymbal-coffee-ops --workspace COFFEE --schema APP --app-id 100
```

## Architecture

- **Hybrid RRF Search**: Single-query fusion (`hybrid-search-turn`) combining Oracle Text `CONTAINS`/`SCORE` lexical ranking with HNSW `VECTOR(3072, FLOAT32)` cosine similarity (`gemini-embedding-2`).
- **AI Runtime**: Native `AgentRuntime` with Gemini 3.8 Flash, `CallContext` tool bindings, Oracle session/event persistence, LitestarMCP (`/mcp`), and LitestarA2A (`/a2a`).
- **Data Layer**: SQLSpec `0.69.0` async services (`OracleLoaderService`, `OracleVectorSearchService`), inline LOB handling, session tracing, and `litestar-queues` background workers.
- **Operations**: Oracle APEX 26.1 operations console with `APEXlang` source control (`src/apex/cymbal-coffee-ops/`) and automated VHS (`docs/_tapes/`) / Playwright browser recorders (`tools/demos/`).

## Commands

| Command | Purpose |
| :--- | :--- |
| `uv run coffee run` | Start Granian + Litestar on `http://localhost:8000` |
| `uv run coffee worker run` | Start standalone background queue worker |
| `uv run coffee upgrade` | Run migrations and load initial fixtures |
| `uv run coffee bulk-embed` | Generate missing vector embeddings |
| `uv run coffee clear-cache --force` | Clear response and embedding caches |
| `uv run coffee configure-apex-cdn` | Configure APEX CDN URL |
| `uv run python manage.py infra apex status` | Check APEX 26.1 and ORDS 26.3 status |
| `uv run python manage.py infra apex configure-vertex` | Provision Vertex AI in APEX (`--mode direct` or `--mode gateway`) |
| `make docs-demos-shell` | Record terminal demo videos via VHS (`tools/demos/shell.py`) |
| `make docs-demos-web` | Record browser demo videos via Playwright (`tools/demos/web.py`) |
| `make lint` | Run linters, type checks, and code hygiene gates |
| `make test-unit` | Run fast isolated unit tests |
| `make test-integration` | Run live Oracle integration tests |

## Documentation

Full documentation is available via Sphinx:

```bash
make docs        # Build HTML documentation in docs/_build/html
make docs-serve  # Serve documentation on http://localhost:8002
```

## Troubleshooting

- **503 AIServiceUnconfigured**: Configure Vertex AI credentials via `gcloud auth application-default login` or set `VERTEX_AI_API_KEY` / `GOOGLE_API_KEY` in `.env`.
- **ORA-51962 on Vector Index Creation**: On `ORACLE_CONTAINER_FLAVOR=free` or custom databases, set `vector_memory_size=512M` as `SYSDBA` and restart the database.
