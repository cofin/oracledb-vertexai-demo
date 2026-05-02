# Quickstart

Five minutes from clone to a running coffee chat:

```bash
# 1. Install Python deps and pre-commit hooks
make install

# 2. Bootstrap (one-time): writes .env, syncs frontend deps
uv run python manage.py init --run-install

# 3. Start the local Oracle 26ai container
make start-infra

# 4. Apply schema migrations and load committed product fixtures
uv run coffee upgrade

# 5. Run the app
uv run coffee run
```

The chat UI is at <http://localhost:8000/>. The vector search and EXPLAIN
PLAN explorer is at <http://localhost:8000/explore>.

## Vertex AI credentials

The app needs a Google Cloud project with Vertex AI enabled. Set
`GOOGLE_PROJECT_ID`, `GOOGLE_LOCATION`, and either
`GOOGLE_APPLICATION_CREDENTIALS` (service account key path) or use
`gcloud auth application-default login`.

If credentials are missing or `GOOGLE_PROJECT_ID` still looks like a
placeholder, the chat endpoint returns `503 AI service unconfigured`
rather than a stack trace.

## Common gotchas

- **`ORA-51962` during migration** — `vector_memory_size` is zero. The
  managed container in `make start-infra` configures `512M` automatically
  on first init; if you bypassed that, see
  `tools/oracle/configure_vector_memory.sql`.
- **`gemini-embedding-001` 404** — the project is missing Vertex AI
  permissions or the location doesn't host the embedding model. Try
  `us-central1`.
- **Empty chat replies on first start** — products haven't been embedded
  yet. The committed fixtures already include 3072-dim embeddings, so
  re-run `uv run coffee upgrade`.

## Where to go next

- [The walkthrough](../tour.md) — what one chat message actually does.
- [CLI reference](cli.md) — every demo lifecycle command.
- [For the curious](internals.md) — HNSW, the parallel-vs-sequential
  timeline, and the live performance dashboard.
- [Developers](developers.md) — raw migration commands, fixture
  regeneration, and verification.
