# Flow: Prune and Document (prune-and-document_20260429)

*Chapter 5 of [cymbal-coffee-reset_20260429](../cymbal-coffee-reset_20260429/prd.md)*
*Beads epic: `oracledb-vertexai-4d6.5` (blocked by Ch 3 and Ch 4)*

---

## Specification

### Objective

Make `oracledb-vertexai-demo` learnable cold by a new contributor in 30 minutes. Archive obsolete flow specs + knowledge notes; collapse 8 guides to **3 evergreen guides**; trim the CLI to the canonical demo surface; rewrite the root `README.md` as a 5-minute quickstart; update `CLAUDE.md` and `.agents/patterns.md` to reflect the codebase as it actually is after Chapters 1–4. No new functionality; pure simplification.

### Code Analysis Summary (verified 2026-04-29)

**Spec dirs to archive (`mv .agents/specs/<dir> .agents/archive/specs/<dir>`):**

- `agent-ui-update_20251024/` — Oct 2025, pre-reset.
- `chat-modernization_20260226/` — Feb 2026, superseded by master PRD.
- `dark-react-redesign_20260226/` — Feb 2026, frontend deleted in Ch 4.
- `performance-modernization_20260226/` — Feb 2026, performance page collapsed in Ch 4.
- `ui-foundation-routing_20260226/` — Feb 2026, routing model deleted in Ch 4.
- `sql-lab_20260306/` — Mar 2026, exploratory only.
- `enhance-test-coverage/` — undated, low priority.
- `install-simplification_20260429/` — **archive** (decision pinned 2026-04-29): the install-flow work is fully absorbed into Ch 1's dependency bump + Ch 5's quickstart README rewrite; no orphan tasks remain.

**Knowledge notes to archive (`.agents/knowledge/*.md`):**

- `adk-chat-dashboard_20260225.md`
- `fix-tests-and-runner_20260226.md`
- `idempotent-install-commands_20251010.md`
- `initial-setup-synthesis_20260225.md`
- `migrate-to-adk-runner_20251010.md`
- `migrate-to-dishka-di_20251020.md`
- `modernize-oracle-schema_20251017.md`
- `oracle-23ai-features_20251017.md`

(Each of these is a snapshot of in-flight thinking that's now obsolete; their decisions live in code.)

**Guides — keep exactly 3, archive the rest:**

| Path | Action |
|---|---|
| `.agents/knowledge/guides/architecture.md` | KEEP — rewrite to reflect post-Ch 1–4 state |
| `.agents/knowledge/guides/oracle-vector-search.md` | KEEP — rewrite to cover HNSW INMEMORY + 3072-dim + EXPLAIN PLAN |
| `.agents/knowledge/guides/adk-agent-patterns.md` | KEEP — rewrite to cover ADK 2.0 Workflow + parallel classifier + closure-bound tools |
| `sqlspec-patterns.md` | MERGE into `architecture.md` (named SQL pattern, paginate, filters); then delete |
| `vertex-ai-integration.md` | MERGE into `architecture.md` (embedding model, task_type, dim 3072); then delete |
| `oracle-performance.md` | MERGE into `oracle-vector-search.md` (vector_memory_size, INMEMORY); then delete |
| `litestar-framework.md` | ARCHIVE — covered by `litestar:litestar*` skill docs + CLAUDE.md |
| `sqlcl-usage-guide.md` | ARCHIVE — operational, not foundational |
| `manage-cli-guide.md` | ARCHIVE — `manage.py` survives but its surface is a 3-line README mention |
| `oracle-deployment-tools.md` | ARCHIVE — deployment-specific |
| `oracle-json.md` | ARCHIVE — niche; not in 5-min quickstart |
| `gemini-mcp-integration.md` | ARCHIVE — exploratory |
| `autonomous-database-setup.md` | ARCHIVE — optional deployment path; link from README only |

**CLI surface (`src/app/cli/commands/manage.py` plus `src/app/cli/commands/server.py`):**

- KEEP (PRD must-survive):
    - `python manage.py database upgrade --no-prompt` (SQLSpec migrations)
    - `coffee load-fixtures` (`manage.py` command module; required for the 5-min quickstart)
    - `coffee bulk-embed` (lifecycle command for regenerating committed product embeddings)
    - `coffee export-fixtures` (lifecycle command for refreshing committed fixtures)
    - `coffee clear-cache`
    - `coffee model-info`
    - `coffee run` (hand-rolled wrapper around Granian)
- CLEAN UP:
    - `coffee bulk-embed` — keep on `coffee`; make task type explicit and validate batch size.
    - `coffee export-fixtures` — keep on `coffee`; remove nested async/run wrappers and improve help text.

**Frontend test stubs deleted in Ch 4** — verify they're gone.

**README.md (current 175 lines):**

- Quick Start section is decent but mentions deleted commands (`bulk-embed`).
- Duplicates between "Development Commands" and "Management CLI" sections.
- 7 external resource links — keep only the 3 directly load-bearing (Oracle 26ai, Vertex AI, Litestar).
- Architecture paragraph is fine; expand by 2 sentences to mention ADK 2.0 + HTMX.
- README removes stale screenshot links until current chat/explore screenshots
  are captured during browser verification.

**`CLAUDE.md` (root, 230+ lines):**

- Remove `array.array('f', query_embedding)` example (line 143) — sqlspec native handlers obsolete it.
- Update `from app.lib.di import Inject, inject` example (lines 152-156) — verify `inject()` decorator is still the canonical pattern after Ch 2 (vs handler-arg `Inject[T]`).
- Lines 187-194 (testing section) — verify pytest-asyncio pattern still matches; PRD prefers `@pytest.mark.anyio`.
- "Multi-AI Agent System" header (line 11+) references `specs/AGENTS.md` which no longer exists in the new layout — update link to `.agents/`.
- Quick Reference Skills table — verify quickref files still exist after archival.

**`.agents/patterns.md`:**

- Remove obsolete `make test .ONESHELL` gotcha (Ch 1 already targets this).
- After Ch 2 + Ch 3 + Ch 4, this file should be a focused ~150-line living document, not a kitchen sink. Restructure into 4 sections: Architecture / Code style / Testing / Operational gotchas.

**`.agents/index.md`** — re-generate as a flat index of surviving artifacts.

**Migration `0001_*.sql` (audit):** Per Phase D research, the file is already minimal. **No DDL pruning needed**; only the comment cleanup from Ch 1 (MD5 → SHA256).

### Requirements

1. `.agents/archive/specs/` exists; the 8 listed spec dirs are moved (not deleted) so historical context is preserved but out of the active surface.
2. `.agents/archive/knowledge/` exists; the 8 listed knowledge files moved.
3. `.agents/knowledge/guides/` contains exactly 3 files: `architecture.md`, `oracle-vector-search.md`, `adk-agent-patterns.md`. The merged content from `sqlspec-patterns.md`, `vertex-ai-integration.md`, `oracle-performance.md` is folded in; archived files moved to `.agents/archive/knowledge/guides/`.
4. `coffee bulk-embed` and `coffee export-fixtures` remain on the hand-rolled
   `coffee` command surface. Clean them up in place: explicit embedding task
   type, clearer help text, no local nested async/run wrappers, and coverage so
   future cleanup does not remove them accidentally.
5. `README.md` reduced to ≤120 lines. Sections (in order): Title + 1-line tagline; 5-Minute Quickstart; What's Inside; Architecture (2 paragraphs); Common Commands; Docs; Troubleshooting.
6. `CLAUDE.md`:
   - Delete the `array.array('f', ...)` block.
   - Update DI example to the post-Ch 2 pattern.
   - Update Testing block to reference anyio if applicable.
   - Fix the broken `specs/AGENTS.md` link.
   - Update Project Structure tree to reflect post-Ch 2 domain layout (`controllers/`, `services/`, `schemas/` packages).
7. `.agents/patterns.md` rewritten into 4 sections (Architecture / Code style / Testing / Operational gotchas) with **only the gotchas that are still real** post-Ch 4. ≤150 lines.
8. `.agents/index.md` regenerated as a flat index.
9. README no longer links stale screenshots. Current screenshots are captured during Phase 6 browser verification before being linked again.
10. A new contributor running the README quickstart from a clean clone reaches a working chat reply at `localhost:5006/` within **5 minutes** (assuming Docker is already installed).

### Acceptance Criteria

- `find .agents/specs -maxdepth 1 -type d | wc -l` returns **6** (root + master PRD dir + 4 chapter dirs; the 8 obsolete dirs are gone — including `install-simplification_20260429`).
- `ls .agents/knowledge/guides/` returns exactly: `architecture.md`, `oracle-vector-search.md`, `adk-agent-patterns.md`.
- `ls .agents/archive/specs/ | wc -l` ≥ 8.
- `ls .agents/archive/knowledge/guides/ | wc -l` = 7.
- `uv run coffee --help` lists `bulk-embed` and `export-fixtures`.
- `src/app/cli/commands/manage.py` has no direct `sqlspec.utils.sync_tools.run_`
  usage or local nested `_load_fixtures` / `_export_fixtures` async wrappers;
  async commands use `@async_inject`.
- `wc -l README.md` ≤ 120.
- `grep -E "array\\.array|specs/AGENTS\\.md" CLAUDE.md` returns **zero** matches.
- `wc -l .agents/patterns.md` ≤ 150.
- A new contributor walkthrough (timed by a colleague running fresh): `git clone && make install-uv && make install && uv run python manage.py init --run-install && make start-infra && uv run python manage.py database upgrade --no-prompt && uv run coffee load-fixtures && uv run coffee run` produces a working chat reply within 5 minutes (excluding Docker-image pull time).
- `make lint && make test` green.

### Risks / Known Gotchas

- **Don't delete archived files; move them.** History is valuable for future archaeologists. `git mv` keeps the diff clean.
- **`manage.py` is not in the PRD's must-survive list** — but it bootstraps `init`, which IS. Confirm `manage.py init` still works after Ch 5; if it pulls a deleted command, fix it.
- **Quickref files** under `.claude/skills/` are referenced by `CLAUDE.md` — keep them; they're load-bearing for future sessions. Verify their content still matches post-Ch 1–4.
- **Screenshots** must be current before they are linked from README; stale React-era screenshots are worse than no screenshot.
- **Existing PR / commit messages** may reference deleted files; that's fine, those are immutable history.
- **Archive directory is gitignored?** Verify `.gitignore` does NOT exclude `.agents/archive/` — the PRD wants archived flows preserved in the repo.

---

## Implementation Plan

### Phase 1: Spec + knowledge archival (`oracledb-vertexai-4d6.5.1`) — [x] synced from Beads

- [x] **1.1** **First, verify `.gitignore` does not exclude `.agents/archive/`.** If excluded, edit `.gitignore` to remove the rule before any move (otherwise the moves vanish from the repo).
- [x] **1.2** Create `.agents/archive/specs/` and `.agents/archive/knowledge/` (and `.agents/archive/knowledge/guides/`).
- [x] **1.3** `git mv` each of the 8 obsolete spec dirs into `.agents/archive/specs/`.
- [x] **1.4** `git mv` each of the 8 obsolete knowledge files into `.agents/archive/knowledge/`.
- [x] **1.5** Update `.agents/flows.md`: remove archived flow entries from the active list; add an "Archived" footer section linking to `archive/specs/`.

### Phase 2: Guide consolidation (`oracledb-vertexai-4d6.5.2`) — [x] synced from Beads

- [x] **2.1** Rewrite `.agents/knowledge/guides/architecture.md` from scratch (≤500 lines): high-level diagram, three-provider Dishka layout, named SQL pattern, ADK 2.0 workflow shape, HTMX template + Vite mode. Pull merged content from the 3 archive-bound guides as needed.
- [x] **2.2** Rewrite `.agents/knowledge/guides/oracle-vector-search.md` (≤500 lines): VECTOR(3072), HNSW INMEMORY recipe, vector_memory_size requirement, EXPLAIN PLAN read, similarity vs distance.
- [x] **2.3** Rewrite `.agents/knowledge/guides/adk-agent-patterns.md` (≤500 lines): ADK 2.0 Workflow/BaseNode, closure-bound tools, parallel fan-out, before_agent_callback credential guard, Flash-Lite enum classifier.
- [x] **2.4** `git mv` the 7 archive-bound guides into `.agents/archive/knowledge/guides/`.

### Phase 3: CLI cleanup (`oracledb-vertexai-4d6.5.3`) — [x] synced from Beads

- [x] **3.1** Keep `coffee bulk-embed`; make product-document embedding
  semantics explicit (`RETRIEVAL_DOCUMENT`), validate batch size, and improve
  command/help copy.
- [x] **3.2** Keep `coffee export-fixtures`; improve command/help copy and keep
  it as the lifecycle path for refreshing committed demo fixtures.
- [x] **3.3** Convert `load-fixtures` and `export-fixtures` to `@async_inject`
  async commands; remove local nested async functions and direct `run_` calls.
- [x] **3.4** Update `src/app/cli/commands/__init__.py` so command registration
  docs advertise the retained lifecycle commands.
- [x] **3.5** Smoke: `uv run coffee --help`, `uv run coffee bulk-embed --help`,
  and `uv run coffee export-fixtures --help` exit 0 and list the retained
  commands.

### Phase 4: README rewrite (`oracledb-vertexai-4d6.5.4`) — [x] synced from Beads

- [x] **4.1** Replace `README.md` with the new ≤120-line quickstart structure. Skeleton:

  ```markdown
  # Cymbal Coffee — Oracle 26ai + Vertex AI + ADK Demo
  Reference app for AI-powered apps on Oracle Database with Google ADK 2.0 + Vertex AI.

  ## 5-Minute Quickstart
  1. Prereqs: Python 3.11+, Docker, `make`, `uv`.
  2. `make install`
  3. `uv run python manage.py init --run-install`
  4. `make start-infra`
  5. `uv run python manage.py database upgrade --no-prompt && uv run coffee load-fixtures`
  6. `uv run coffee run` → http://localhost:5006

  ## What's Inside
  - 47 coffee products, 3072-dim Gemini embeddings, HNSW INMEMORY indexes
  - ADK 2.0 chat agent with parallel intent classification
  - HTMX explore page with live EXPLAIN PLAN viewer
  - Oracle-backed response + embedding cache

  ## Architecture
  Two-page Litestar app served via Granian. Vector search on Oracle 26ai with HNSW
  INMEMORY indexes. Chat orchestrated by Google ADK 2.0 (Workflow graph + parallel
  Gemini Flash-Lite intent classifier). Frontend is HTMX + Tailwind v4 + vanilla
  JavaScript + ApexCharts via litestar-vite template mode.

  ## Common Commands
  | Command | Purpose |
  |---|---|
  | `uv run coffee run` | Start dev server (Granian) |
  | `uv run python manage.py database upgrade --no-prompt` | Apply migrations |
  | `uv run coffee load-fixtures` | Load sample coffee data |
  | `uv run coffee model-info` | Verify AI model wiring |
  | `uv run coffee clear-cache` | Reset response + embedding caches |

  ## Docs
  - Architecture: `.agents/knowledge/guides/architecture.md`
  - Vector search internals: `.agents/knowledge/guides/oracle-vector-search.md`
  - ADK patterns: `.agents/knowledge/guides/adk-agent-patterns.md`

  ## Troubleshooting
  - **`vector_memory_size` not allocated:** see `.agents/knowledge/guides/oracle-vector-search.md`
  - **AI model errors:** `uv run coffee model-info`
  - **Tests failing:** check `make start-infra` is healthy
  ```

- [x] **4.2** Remove stale screenshot references from README. Capture current chat/explore screenshots during Phase 6 browser verification before linking them again.

### Phase 5: CLAUDE.md + patterns.md update (`oracledb-vertexai-4d6.5.5`) — [x] synced from Beads

- [x] **5.1** `CLAUDE.md` edits (apply as a single commit, **review the rendered diff before committing** — this file is loaded into every future Claude Code session, so a bad edit propagates broadly):
    - Delete the `array.array('f', query_embedding)` example block (around line 143).
    - Replace the DI example with the post-Ch 2 pattern (handler-arg `Inject[T]` from `app.lib.di`).
    - Update the Testing block: prefer `@pytest.mark.anyio`.
    - Fix the broken link `specs/AGENTS.md` → `.agents/index.md`.
    - Update the Project Structure tree to reflect normalized domain packages (`controllers/`, `services/`, `schemas/`).
- [x] **5.1.5** Open the rendered `CLAUDE.md` in a viewer; confirm the Project Structure tree matches what `tree -L 4 src/app/` actually produces; confirm no stale references to React, `array.array`, or pre-Ch 2 DI.
- [x] **5.2** `.agents/patterns.md` rewrite (≤150 lines, 4 sections):
    - **Architecture:** three-provider Dishka, named SQL, ADK 2.0 workflow shape, HTMX template mode, EXPLAIN PLAN viewer.
    - **Code style:** PEP 604, no future annotations in Dishka providers, `Inject[T]` over `inject()` decorator, async I/O everywhere, `schema_type=` always.
    - **Testing:** anyio fixtures and real-Oracle integration tests against
      the repo-managed Oracle lifecycle (`make start-infra`,
      `uv run python manage.py database upgrade --no-prompt`).
    - **Operational gotchas:** `vector_memory_size >= 4G`, `text/x.enum` requires Flash-Lite, `hot_file` ↔ `vite.config.ts` coupled paths, `ensure_tables()` adds 30-100ms first boot.
- [x] **5.3** Regenerate `.agents/index.md` as a flat index of surviving artifacts.

### Phase 6: Verification + walkthrough (`oracledb-vertexai-4d6.5.6`) — [~] synced from Beads

- [x] **6.1** `make lint && make test` — clean.
- [ ] **6.2** `make install` from a fresh clone (or container): time the full quickstart sequence end-to-end. Document timing in Beads notes; if > 5 minutes excluding image pull, identify the bottleneck.
- [x] **6.3** Open `/` and `/explore` in a browser; capture current screenshots before linking them from README again.
- [ ] **6.4** Have a colleague read the new README cold and try the quickstart. Capture friction points; fix the README, not the colleague.
- [ ] **6.5** Final `git status` audit: zero **untracked** files outside `dist/`, `node_modules/`, `.venv/`. Every change in `src/`, `.agents/`, `docs/`, `pyproject.toml`, `README.md`, `CLAUDE.md` is either a tracked modification or a `git mv` to archive. No surprise additions; no dropped tests.

---

## Sync Notes (2026-05-01)

- Backend state: `oracledb-vertexai-4d6.5.1` through `.5.5` are closed; `oracledb-vertexai-4d6.5.6` remains in progress.
- Verification done in Phase 6 includes lint/test passes, targeted chat/explore regression tests, current chat/explore screenshots, Vite build, Ruff checks, and whitespace checks.
- Current frontend stack is HTMX/Jinja templates plus litestar-vite, Tailwind v4, vanilla JavaScript, and ApexCharts. Alpine was removed during UI regression recovery.
- Latest manual-testing fixes: chat intent telemetry promotes to `PRODUCT_RAG` when a product vector lookup actually ran, chat-side vector lookups write metrics, and the structured EXPLAIN PLAN table wraps instead of forcing horizontal scroll.
- Remaining closeout before Ch 5 can close: fresh-clone quickstart timing or explicit waiver, colleague cold readthrough or explicit waiver, and final git-status audit after shared branch work settles.

---

## Out of Scope (defer to other flows)

- Multi-tenant auth, SAQ/background workers, or new chat transport work. Existing streaming chat remains part of the current recovered UI contract.
- New product/store features are not part of this cleanup chapter. Follow-on PRD `store-location-inventory-chat_20260501` owns store locations, Dallas fixture coverage, inventory, browser geolocation, and Maps integration. Do not prune fixture lifecycle or store-domain documentation that PRD depends on.
- DDL refactoring beyond Ch 1's HNSW + 3072 + INMEMORY changes.
- Renaming `worker_container_var` for naming consistency (separate cleanup flow).
- Docs site / GitHub Pages publishing.
