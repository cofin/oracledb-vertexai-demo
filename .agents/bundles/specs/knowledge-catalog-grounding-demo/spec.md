---
type: Spec
flow_id: knowledge-catalog-grounding-demo
title: Google Cloud Knowledge Catalog Grounding, Oracle 26ai Annotations Sync & Context Ceiling Demo
state: planned
plan_revision: 1
plan_commit: null
state_revision: 0
current_task: null
last_operation: null
operation_targets: []
last_verified_checkpoint: null
created_at: 2026-10-12T18:24:00Z
updated_at: 2026-10-12T18:24:00Z
description: Master PRD roadmap integrating Google Cloud Knowledge Catalog (formerly Dataplex Universal Catalog) and Open Knowledge Format (OKF v0.2) with Oracle AI Database 26ai native schema ANNOTATIONS, a one-command coffee sync-catalog CLI, runtime searchEntries + lookupContext agent grounding, MCP Toolbox & LitestarMCP endpoints, and an interactive Context Ceiling demo UI with K telemetry badge.
tags:
  - spec
  - knowledge-catalog
  - dataplex
  - okf
  - oracle
parent_prd: null
research:
  - research/research_knowledge_catalog_demo_20261012/research.md
---

# Master PRD: Google Cloud Knowledge Catalog Grounding, Oracle 26ai Annotations Sync & Context Ceiling Demo

**Flow ID:** `knowledge-catalog-grounding-demo`

---

## North Star

Deliver a fast, meaningful **Google Cloud Knowledge Catalog + Oracle AI Database 26ai** integration and interactive **"Breaking the Context Ceiling"** demo inside Cymbal Coffee that:

1. **Harvests Oracle 26ai Native `ANNOTATIONS(...)` Directly into Knowledge Catalog & OKF v0.2**:
   - Uses a single CLI command (`uv run coffee sync-catalog`) to query Oracle 26ai's `USER_ANNOTATIONS_USAGE` and `USER_TAB_COLUMNS` (`src/app/db/migrations/0001_cymball_coffee_products.sql:18-264`), combine them with steward-certified agent `guidelines` (2-tier inventory contract, off-menu brand rule, request-scoped coordinate privacy invariant) and Golden SQL `queries`, and write both:
     - **A committed local OKF v0.2 bundle + JSON snapshot** (`src/app/db/fixtures/knowledge_catalog_context.json` and `.agents/bundles/knowledge/catalog/`) for zero-cloud, `<2ms` offline/CI execution and `kcmd push --format okf` compatibility.
     - **Live Google Cloud Knowledge Catalog (`dataplex.googleapis.com/v1`) Custom Entries & Global System Aspects** (`projects/655216118709/locations/global/aspectTypes/{schema,overview,guidelines,queries}`) via `httpx` + `google.auth` ADC (zero VPC/PSC Network Attachment or `SYS.COL$` DBA grants required).
2. **Grounds the Native `google-genai` Agent & Multi-Protocol MCP Surface at Runtime**:
   - Provides a Dishka-managed `KnowledgeCatalogService` supporting both **Live GCP Mode** (`searchEntries(semanticSearch=True)` + `lookupContext(format="yaml", all_schema_fields="true")`) and **Local OKF/Annotations Snapshot Mode**.
   - Binds `lookup_catalog_context` via `declare()` onto the barista `AgentSpec`, exposes `GET /api/catalog/context` (`mcp_tool="lookup_knowledge_catalog"`) on `LitestarMCP` (`POST /mcp`) and `COFFEE_AGENT_CARD` (`/.well-known/agent-card.json`), and adds the prebuilt `dataplex` MCP Toolbox server (`--prebuilt dataplex`) to `tools/lib/utils.py::build_antigravity_mcp_config`.
3. **Demonstrates "Breaking the Context Ceiling" Visually in the Chat UI & Telemetry Drawer**:
   - Adds a live **Knowledge Catalog Grounding (`ON` / `OFF`)** toggle in the chat interface (`chat.html.j2` + `chat-stream.js`) so presenters can contrast ungrounded failure modes against steward-grounded execution on the exact same prompt.
   - Adds a dedicated **`K` (Knowledge Catalog)** telemetry badge in `src/resources/telemetry.js` that opens the right-hand slide-over Telemetry Drawer (`#telemetry-popover`) to display matched `oracle:cymbal-coffee:...` entry URIs, active Oracle 26ai `Privacy` / `Data_Role` / `AI_Surface` annotations, steward `guidelines`, and the exact `lookupContext` YAML payload + latency (`catalog_ms`).

---

## Architectural Decisions (Resolved)

1. **Custom Entries + Global System Aspects (`655216118709`) over Managed Oracle Connector (`oracle-transfer`)**:
   - The Managed Oracle Connector (`bigquerydatatransfer.googleapis.com`, Preview) requires PSC Network Attachments, `SYS.COL$` / `SELECT_CATALOG_ROLE` / `ALTER ANY TRIGGER ON SCHEMA` grants, runs as a batch job, and ignores Oracle 26ai `USER_ANNOTATIONS_USAGE`.
   - `coffee sync-catalog` instead queries `USER_ANNOTATIONS_USAGE` directly over the existing SQLSpec connection pool and upserts `EntryGroup` (`cymbal-coffee-oracle`), `Entry` records (`entrySource.system = "ORACLE"`), and global system aspects (`projects/655216118709/locations/global/aspectTypes/{schema,overview,guidelines,queries}`) via `dataplex.googleapis.com/v1` REST using `httpx` and `google.auth` (already installed via `google-genai`).
2. **Global System Aspects (`schema`, `overview`, `guidelines`, `queries`) for `lookupContext` Compatibility**:
   - Public Knowledge Catalog docs (`enrich-entries-metadata`) and `go/kc-retrieval-overview` confirm that `lookupContext` (`POST /v1/projects/{p}/locations/{l}:lookupContext`) automatically assembles the global system aspects (`schema`, `overview`, `guidelines`, `queries`) and linked Business Glossary terms into a single LLM-ready YAML string, whereas user-defined custom aspect types are omitted by `lookupContext`. Encoding Oracle 26ai annotations and steward rules into `overview`, `guidelines`, `schema`, and `queries` guarantees single-call `lookupContext` assembly.
3. **Dual-Mode Execution (`local` Snapshot vs `gcp` Live API)**:
   - `CatalogSettings.mode` defaults to `"auto"` (uses live `dataplex.googleapis.com/v1` when `KNOWLEDGE_CATALOG_ENABLED=true` and `GOOGLE_CLOUD_PROJECT` is a real project, and seamlessly falls back to the committed `src/app/db/fixtures/knowledge_catalog_context.json` snapshot built from `0001_cymball_coffee_products.sql` annotations when running locally/offline or in CI).
4. **Composable Alignment with `coffee-agent-stabilization-and-hybrid-search`**:
   - Settings live in `src/app/lib/settings/_catalog.py` (and re-export via `app.lib.settings`), schemas live in `src/app/domain/system/schemas/_catalog.py`, service logic lives in `src/app/domain/system/services/_catalog.py`, and controller endpoints live in `src/app/domain/system/controllers/_catalog.py` so zero files collide with active tasks in `runtime-stabilization` or `hybrid-rrf-retrieval`.

---

## Roadmap Chapters

| Order | Flow ID | Title | Depends On | Tasks | Summary |
| --- | --- | --- | --- | --- | --- |
| 1 | [`knowledge-catalog-foundation`](../knowledge-catalog-foundation/spec.md) | Oracle 26ai `USER_ANNOTATIONS_USAGE` Harvester, OKF v0.2 Bundle & `coffee sync-catalog` CLI | None | `1.1`–`1.2` | Add `catalog.sql` dictionary/annotation queries, `CatalogSettings`, typed `msgspec.Struct` schemas, committed `knowledge_catalog_context.json` + OKF v0.2 bundle, and `uv run coffee sync-catalog` (`--push`, `--export-okf`) with `httpx` REST v1 upsert for `dataplex.googleapis.com`. |
| 2 | [`knowledge-catalog-runtime-and-mcp`](../knowledge-catalog-runtime-and-mcp/spec.md) | Runtime `KnowledgeCatalogService`, `lookupContext` Agent Grounding & MCP Integration | `knowledge-catalog-foundation` | `2.1`–`2.2` | Implement `KnowledgeCatalogService` (`search_entries` + `lookup_context` in live GCP and `<2ms` local snapshot modes), register Dishka provider, bind `lookup_catalog_context` tool on `AgentSpec`, wire `use_knowledge_catalog` turn grounding, expose `GET /api/catalog/context` (`mcp_tool="lookup_knowledge_catalog"`), and add `--prebuilt dataplex` to `tools/lib/utils.py`. |
| 3 | [`knowledge-catalog-demo-ux-and-docs`](../knowledge-catalog-demo-ux-and-docs/spec.md) | Interactive "Context Ceiling" Demo UI, `K` Telemetry Drawer Badge & Slides/Docs | `knowledge-catalog-runtime-and-mcp` | `3.1`–`3.2` | Add the **Knowledge Catalog Grounding (`ON`/`OFF`)** toggle in `chat.html.j2` + `main.js`, add the **`K` (Knowledge Catalog)** badge and Context X-Ray phase renderer in `telemetry.js`, and update `SLIDES.md`, `AGENTS.md`, `README.md`, and `.agents/bundles/knowledge/architecture/knowledge-catalog.md`. |

---

## Requirement-to-Chapter Traceability

| Requirement ID | Requirement Summary | Owning Chapter | Tasks |
| --- | --- | --- | --- |
| `KC-REQ-01` | Extract Oracle 26ai `USER_ANNOTATIONS_USAGE` and `USER_TAB_COLUMNS` via named SQL and model Knowledge Catalog entries, global system aspects (`655216118709`), and `lookupContext` payloads with `msgspec.Struct` schemas and `CatalogSettings` | `knowledge-catalog-foundation` | `1.1` |
| `KC-REQ-02` | Provide `uv run coffee sync-catalog` CLI command and committed offline snapshot + OKF v0.2 bundle that syncs Oracle 26ai metadata, steward guidelines, and Golden SQL to local OKF files and live `dataplex.googleapis.com/v1` | `knowledge-catalog-foundation` | `1.2` |
| `KC-REQ-03` | Implement `KnowledgeCatalogService` supporting both live `dataplex.googleapis.com/v1` (`searchEntries` + `lookupContext`) and deterministic local snapshot retrieval with Dishka DI registration | `knowledge-catalog-runtime-and-mcp` | `2.1` |
| `KC-REQ-04` | Bind `lookup_catalog_context` agent tool, wire `use_knowledge_catalog` request toggle into chat orchestration/telemetry, expose `GET /api/catalog/context` (`mcp_tool="lookup_knowledge_catalog"`), and add `dataplex` MCP Toolbox config helper | `knowledge-catalog-runtime-and-mcp` | `2.2` |
| `KC-REQ-05` | Render interactive Knowledge Catalog Grounding `ON`/`OFF` toggle in chat UI and `K` (Knowledge Catalog) badge + Context X-Ray drawer view in `telemetry.js` | `knowledge-catalog-demo-ux-and-docs` | `3.1` |
| `KC-REQ-06` | Document the Knowledge Catalog + Oracle 26ai `ANNOTATIONS` + OKF v0.2 architecture and "Breaking the Context Ceiling" demo script in `SLIDES.md`, `AGENTS.md`, `README.md`, and `.agents/bundles/knowledge/architecture/knowledge-catalog.md` | `knowledge-catalog-demo-ux-and-docs` | `3.2` |

---

## Global Constraints

1. **Zero Inline Comments in Python**: Never use inline `#` comments in Python files (except required `# noqa:` directives or `# docs:start-*` / `# docs:end-*` Sphinx anchors). Use Google-style docstrings exclusively.
2. **Modern Python Typing & Layout**: Use PEP 585/604 types (`list[str]`, `X | None`), `msgspec.Struct` / `CamelizedBaseStruct`, module layout (`docstring` $\rightarrow$ grouped top-level imports $\rightarrow$ `__all__` $\rightarrow$ public classes/functions $\rightarrow$ private `_...` helpers), and class layout (class attributes $\rightarrow$ `__init__` $\rightarrow$ properties $\rightarrow$ public methods $\rightarrow$ private `_...` helpers).
3. **Dishka DI Discipline**: Any file in `src/app/ioc` must never include `from __future__ import annotations`. Controller handlers use `Inject[T]` without `@inject` decorators.
4. **Coordinate Privacy Invariant**: Browser geolocation coordinates (`latitude`, `longitude`, `accuracy`) remain strictly request-scoped and must never be persisted to Knowledge Catalog entries, `agent_session`, `agent_event`, `response_cache`, `search_metric`, or logs.
5. **Zero Heavy New SDK Dependencies**: Use `httpx` and `google.auth` (already installed in `pyproject.toml`) to call `https://dataplex.googleapis.com/v1` REST endpoints directly so lockfile footprint and startup time remain minimal.

---

## Continuity Snapshot

- **Active Flow / Lifecycle**: `knowledge-catalog-grounding-demo` (`planned`)
- **Current Task & Claimant**: `null`
- **Last Verified Checkpoint**: `null`
- **Key Decisions**:
  - Harvest Oracle 26ai `USER_ANNOTATIONS_USAGE` (`0001_cymball_coffee_products.sql:18-264`) + steward `guidelines` + Golden SQL `queries` into Knowledge Catalog global system aspects (`projects/655216118709/locations/global/aspectTypes/{schema,overview,guidelines,queries}`) via `uv run coffee sync-catalog`.
  - Support both Live GCP (`dataplex.googleapis.com/v1` `searchEntries` + `lookupContext`) and instant Local OKF/Snapshot modes (`src/app/db/fixtures/knowledge_catalog_context.json`).
  - Surface a live **Knowledge Catalog Grounding `ON`/`OFF`** toggle in chat and a **`K` (Knowledge Catalog)** badge in the right-hand Telemetry Drawer.
- **Newest Discoveries**:
  1. `GoogleCloudPlatform/knowledge-catalog` owns the `OKF v0.2` specification (`okf/SPEC.md`) and `kcmd` CLI (`kcmd push --format okf`), matching Cymbal Coffee's `.agents/bundles/` format (`research_knowledge_catalog_demo_20261012`).
  2. `0001_cymball_coffee_products.sql:18-264` already defines Oracle 26ai `ANNOTATIONS(...)` on tables, columns, and vector indexes (`USER_ANNOTATIONS_USAGE`).
  3. `lookupContext` automatically formats global system aspects (`655216118709.global.{schema,overview,guidelines,queries}`) and linked Business Glossary terms, but omits user-defined custom aspect types unless `lookupEntry(view=FULL)` is called.
- **Blockers & Unblock Conditions**: None
- **Next Exact Step**: Approve plan and run `/flow:implement knowledge-catalog-foundation` starting with Task `knowledge-catalog-foundation:1.1`.
- **Plan Identity**: `plan_revision: 1`, `plan_commit: null`
- **State Identity**: `state_revision: 0`, `last_operation: null`, `operation_targets: []`
- **Relevant Knowledge Paths**:
  - `.agents/bundles/specs/knowledge-catalog-grounding-demo/research/research_knowledge_catalog_demo_20261012/research.md`
  - `.agents/bundles/knowledge/architecture/oracle-26ai-hybrid-rrf.md`
  - `.agents/bundles/knowledge/domains/ai-runtime-mcp-a2a.md`
  - `.agents/bundles/knowledge/patterns/architecture.md`
