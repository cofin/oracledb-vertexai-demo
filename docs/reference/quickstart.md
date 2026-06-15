# Quickstart

Five minutes from clone to a running coffee chat:

```bash
# 1. Install Python deps, frontend deps, and built assets
make install

# 2. Bootstrap (one-time): writes .env
uv run python manage.py init

# 3. Start the local Oracle 26ai container
make start-infra

# 4. Apply schema migrations and load committed fixtures
uv run coffee upgrade

# 5. Run the app
uv run coffee run
```

The generated `.env` uses `LITESTAR_PORT=5006`, so the chat UI is at
<http://localhost:5006/>. The vector search and EXPLAIN PLAN explorer is at
<http://localhost:5006/explore>. Set `LITESTAR_PORT` to use a different port.

The managed ADB Free container also exposes APEX at
<https://localhost:8443/ords/apex>. Oracle Estate Explorer is already installed
in that image; startup sets the `MPACK_OEE` password from `OEE_PASSWORD` in
`.env` so it is ready for the demo.

## Vertex AI credentials

The app needs a Google Cloud project with Vertex AI enabled. Set
`VERTEX_AI_PROJECT_ID` (or `GOOGLE_CLOUD_PROJECT`), set `VERTEX_AI_LOCATION`
(or `GOOGLE_LOCATION`), and use either `GOOGLE_APPLICATION_CREDENTIALS`
(service account key path) or `gcloud auth application-default login`.
For API-key mode, leave the project ID empty and set `VERTEX_AI_API_KEY` or
`GOOGLE_API_KEY` instead.

If credentials are missing or `VERTEX_AI_PROJECT_ID` still looks like a
placeholder, the chat endpoint returns `503 AI service unconfigured`
rather than a stack trace.

## Common gotchas

- **`ORA-51962` during migration** — `vector_memory_size` is zero. The
  managed container in `make start-infra` sets `512M` automatically on first
  init via the `tools/oracle/on_init/00_configure_vector_memory.sql` hook; if
  you bypassed that, `tools/oracle/configure_vector_memory.sql` is the manual
  fallback (it targets `4G` on the SPFILE for larger Oracle editions).
- **`gemini-embedding-2-preview` 404** — the project is missing Vertex AI
  permissions or the location doesn't host the embedding model. Try
  `us-central1`.
- **Empty chat replies on first start** — products haven't been embedded
  yet. The committed fixtures already include 3072-dim embeddings, so
  re-run `uv run coffee upgrade`.

## Where to go next

- [The walkthrough](../tour.md) — what one chat message actually does.
- [CLI reference](cli.md) — every demo lifecycle command.
- [For the curious](internals.md) — HNSW, deterministic routing vs ADK
  fallback latency, and the live performance dashboard.
- [Developers](developers.md) — raw migration commands, fixture
  regeneration, and verification.
