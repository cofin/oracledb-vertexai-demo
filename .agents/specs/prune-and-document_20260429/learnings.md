# Learnings: prune-and-document_20260429

> Notes captured during implementation. Synced from Beads task notes via `/flow:sync`.

## Implementation checkpoint (Ch5.1, 2026-04-30)

- Archived the 8 obsolete spec folders into `.agents/archive/specs/` and the
  8 timestamped knowledge notes into `.agents/archive/knowledge/`.
- The critical archive ignore check must include `.agents/.gitignore`, not only
  the repo-root `.gitignore`; `.agents/.gitignore` contained `archive`, which
  hid the moved files until the rule was removed.
- `.agents/flows.md` now keeps archived specs out of the active registry and
  points future readers at `.agents/archive/specs/`.
- Flow sync/status in this repo is a Beads-backed skill workflow. Do not assume
  a `flow sync` shell subcommand exists.

## Implementation checkpoint (Ch5.2, 2026-04-30)

- Rewrote the active guide set to exactly three files:
  `architecture.md`, `oracle-vector-search.md`, and `adk-agent-patterns.md`.
- Folded the current SQLSpec, Vertex embedding, Oracle vector-memory, ADK
  session, Litestar session, streaming, and DI guidance into those guides.
- Archived the 7 named non-keeper guides plus the 3 merge-source guides and the
  stale `guides/README.md`; the stronger acceptance rule is that
  `.agents/knowledge/guides/` contains only the three evergreen guides.
- `ORACLE_ADK_IN_MEMORY` and `ORACLE_LITESTAR_SESSION_IN_MEMORY` now default to
  true in `DatabaseSettings`, with a unit test locking the SQLSpec extension
  config behavior.

## Implementation checkpoint (Ch5.5, 2026-04-30)

- Rewrote `CLAUDE.md` to point at `.agents/`, the post-Ch2 domain layout,
  handler-argument `Inject[T]`, AnyIO tests, 3072-dimensional embeddings, and
  retained `coffee bulk-embed` / `coffee export-fixtures` lifecycle commands.
- Rewrote `.agents/patterns.md` into the required Architecture / Code Style /
  Testing / Operational Gotchas sections and kept it under 150 lines.
- Regenerated `.agents/index.md` as a flat active-context index.
- Removed the unused `pytest-databases` dependency/plugin and documented the
  actual test model: repo-managed Oracle lifecycle via `make start-infra` and
  `uv run python manage.py database upgrade --no-prompt`; pytest fixtures only prepare
  deterministic schema/data inside that configured database.
- `uv run pytest` now reports no `databases` plugin, and importing
  `pytest_databases` from the synced environment fails as expected.

## Verification checkpoint (Ch5.6, 2026-04-30)

- `make lint` is clean after fixing the archived `SUMMARY.md`/`summary.md`
  case-insensitive filename conflict and the helper-module pyright error.
- `make test` passes: 189 tests, 4 expected third-party warnings (Authlib
  deprecation and ADK pluggable-auth experimental warning).
- `make migrate` now uses `--no-prompt`; the previous command shape aborted in
  noninteractive walkthroughs.
- With the existing healthy Oracle container, `uv run coffee load-fixtures`
  loaded 137 rows and `uv run coffee run` served `/`, `/explore`, and `/schema`
  with HTTP 200.
- Browser smoke found the streamed chat form was disabling the message input
  before `new FormData(form)`, which removes the disabled control from the
  request body and causes the backend to stream `Message cannot be empty`.
  Capture `FormData` before busy-state changes and keep a regression check
  against that ordering.
- Re-reviewed DMA accelerator logging after ADK2 stream smoke. The demo should
  use `app.lib.log.structlog_processors()` / `stdlib_logger_processors()` in
  `app.config`, not Litestar's default processor chains, so TTY stdlib logs do
  not duplicate `message=...`. Keep the narrow ADK/Authlib warning filters and
  static asset log exclusion in tests so real stream exceptions remain visible.
- Restored chat telemetry that the ADK2 rewrite dropped: the product RAG tool
  now captures the actual vector query plus embedding, Oracle vector, and tool
  timings using `RETRIEVAL_QUERY`; streamed and HTMX-rendered assistant
  messages show intent, vector query, phase timings, embedding-cache hit, and
  response-cache hit indicators.
- Remaining manual verification: destructive fresh-clone/start-infra timing,
  browser screenshot capture, and colleague cold readthrough.

## Pre-implementation findings (planning phase, 2026-04-29)

- The `.agents/` knowledge base accumulated **8 timestamped notes + 8 guides** plus 7 archived spec dirs since the project began. Most decisions live in code now; the notes are valuable history but noise to a new contributor.
- **Migration `0001_cymball_coffee_products.sql` is already minimal** — no dead DDL or commented-out experimental code. Ch 1 handles the only required edits (HNSW, 3072, INMEMORY, MD5→SHA256 comment).
- `manage.py init` may pull deleted commands — audit during Phase 3.
- `.gitignore` must NOT exclude `.agents/archive/` — historical context is part of the repo per PRD.
- A 5-minute quickstart bound is ambitious but achievable: the bottleneck is usually `make install-uv && make install` (uv-cached makes this fast on warm machines). Time it on a fresh container to validate.
- `coffee bulk-embed` and `coffee export-fixtures` are app lifecycle commands and
  should stay on `coffee`; clean them up in place instead of moving them to
  `tools/dev/`.
- Keep the public CLI modules readable: command modules should mostly contain
  Click declarations and calls into private `app.cli._helpers` modules. Use
  `@async_inject` for async Click commands instead of local nested async
  wrappers or direct `run_` calls in command modules.
- README should not link stale screenshots. Keep the quickstart compact and
  capture/link fresh chat and explore screenshots during browser verification.
