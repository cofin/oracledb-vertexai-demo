# Research: APEX 26.1, ORDS 26.1, APEXlang, Gemini Vector Search, and APEX Schema Bridge

**Workspace**: `.agents/research/research_apex26_ords_apexlang_schema_bridge/`
**Status**: Complete
**Type**: Research + integration planning
**Date**: 2026-06-22
**Branch**: `fix/product-improve`

This is research only. No application code was changed.

---

## Executive Summary

- The repo now has an optional local APEX/ORDS path: `make start-infra` starts DB only, while `make apex` runs `uv run python manage.py infra start` and allows APEX/ORDS setup. The code is newer than several open Flow tasks, so Beads/spec state should be reconciled before implementation.
- The current ORDS sidecar defaults to `container-registry.oracle.com/database/ords:latest`. That is too loose for a demo tied to APEX 26.1. Oracle lists **ORDS 26.1.2.140.1916** as the latest download, released 2026-05-27, while APEX 26.1 requires **ORDS 26.1.1 or later**. Pin to a verified 26.1.x image or add a runtime version check instead of silently accepting `latest`.
- Oracle APEX 26.1 was released 2026-05-14, re-released 2026-05-25 for bug 39397271, and has a 26.1.1 patch bundle updated 2026-06-15. The public download can remain the baseline; the patch bundle should be an optional MOS-backed path if credentials are available.
- SQLcl 26.1.2 is the important APEXlang tooling floor. Its APEX commands support generate, export, validate, and import workflows. The local SQLcl exporter generated this repo's APEXlang source with `shared-components` and `supporting-objects`, so the generated tree should be treated as authoritative when older notes mention underscore names.
- Google docs now list **Gemini Embedding 2** model ID `gemini-embedding-2` with 3072-dimensional output. The repo still defaults to `gemini-embedding-2-preview`, which is dimension-compatible but stale. A model migration requires fixture/cache regeneration, not just a string change.
- The best sample APEX app is a small **Cymbal Coffee Operations Console** that uses the same Oracle tables directly for products, stores, and inventory, and uses Litestar REST/OpenAPI only for cross-app AI/search experiences. This shows APEX strengths without duplicating the HTMX chat app.
- APEX should consume the Litestar app through an **OpenAPI REST Source Catalog**. MCP is useful for agent/tooling integration, but APEX is REST/OpenAPI-native. Build a separate schema bridge tool that emits an APEX-safe OpenAPI bundle and, separately, an MCP/tool schema manifest.

---

## Live Repo Findings

### Optional APEX/ORDS runtime is present

- `Makefile` keeps `start-infra` as DB-only: it invokes `manage.py infra start --recreate --skip-apex --skip-ords`.
- `Makefile` adds `make apex`, which runs `manage.py infra start` without those skips.
- `tools/oracle/apex_media.py` defaults to APEX `26.1` and downloads from Oracle's public APEX zip URL.
- `tools/oracle/apex_install.py` stages the APEX media into the database container, runs `apexins.sql`, configures REST, and creates a `COFFEE` workspace/user.
- `tools/oracle/ords.py` starts a sidecar container, maps HTTP 8181 and HTTPS 8443, mounts APEX images at `/i/`, and points ORDS at `freepdb1`.

### Important gaps

- `tools/oracle/ords.py` uses `DEFAULT_ORDS_IMAGE = "container-registry.oracle.com/database/ords:latest"`. APEX 26.1 has a hard ORDS minimum, so this should be pinned or version-checked.
- `tools/oracle/ords.py` currently treats "container is running" as healthy. For this path, health should probe ORDS HTTP and APEX image serving, for example `/ords/`, `/ords/apex`, and `/i/`.
- `tools/oracle/cli/apex.py` only exposes install, upgrade, and status. There is no APEXlang export/import/validate command yet.
- `src/apex/` is absent, so the app has no checked-in APEXlang source.
- `src/app/server/core.py` configures OpenAPI through Litestar and Scalar, and `pyproject.toml` includes `litestar-mcp`, but the Litestar MCP plugin is not wired.
- The current API has useful read paths (`/api/products`, `/api/stores`, `/api/vector-demo`) but APEX will be happier with stable JSON-only operations and non-SSE AI/search endpoints. `/api/chat/stream` is SSE and should not be the first APEX integration target.

---

## Latest External Facts

### APEX 26.1

Sources:

- Oracle APEX downloads: https://www.oracle.com/tools/downloads/apex-downloads/
- APEX 26.1 release notes: https://docs.oracle.com/en/database/oracle/apex/26.1/htmrn/about-release-notes.html
- APEX 26.1 known issues: https://www.oracle.com/tools/downloads/apex-downloads/apex-261-known-issues/
- APEX 26.1 new features: https://docs.oracle.com/en/database/oracle/apex/26.1/htmrn/new-features.html

Findings:

- APEX 26.1 was released 2026-05-14 and re-released 2026-05-25 to address bug 39397271.
- The APEX 26.1.1 patch set bundle was updated 2026-06-15. It includes fixes for APEXlang import/export and an OCI Gemini AI chat tool-call issue.
- APEX 26.1 requires Oracle Database 19c RU 19.18+ or, on Oracle AI Database 26ai, database version 23.26.0+. It runs on Oracle AI Database 26ai Free.
- APEX 26.1 requires ORDS 26.1.1 or later. Oracle recommends installing ORDS before APEX on new installs.
- Relevant APEX 26.1 demo features include APEXlang, new app types, AI features, and BOOLEAN session state support on Oracle AI Database 26ai.

Implication for this repo:

- Keep public APEX 26.1 install support as the default, but make patch bundle support optional. Do not make MOS credentials mandatory for `make install` or `make apex`.
- Since the repo uses Oracle 26ai BOOLEAN and JSON columns already, the APEX app can demonstrate native BOOLEAN session state and forms/report behavior directly against the coffee schema.

### ORDS 26.1

Sources:

- ORDS downloads: https://www.oracle.com/database/sqldeveloper/technologies/db-actions/download/
- ORDS install guide: https://docs.oracle.com/en/database/oracle/oracle-rest-data-services/26.1/ordig/installing-and-configuring-oracle-rest-data-services.html
- ORDS 26.1 developer changes: https://docs.oracle.com/en/database/oracle/oracle-rest-data-services/26.1/orddg/changes-release-26.1-oracle-rest-data-services-developers-guide.html

Findings:

- Oracle lists ORDS 26.1.2.140.1916 as the latest version, released 2026-05-27.
- ORDS supports Java 17 and 21, and the Oracle container image includes GraalVM plus ORDS standalone deployment.
- ORDS 26.1 adds vector search functionality for AutoREST-enabled tables/views featuring vector columns.

Implication for this repo:

- The ORDS container should be constrained to an ORDS line known to satisfy APEX 26.1: at least 26.1.1, preferably 26.1.2 once the actual container registry tag is verified.
- ORDS AutoREST vector support is worth exploring separately, but the demo should keep named SQL/Litestar service boundaries as the primary vector API. AutoREST can be a nice APEX/ORDS comparison, not the core path.

### SQLcl and APEXlang

Sources:

- SQLcl 26.1.2 release notes: https://www.oracle.com/tools/sqlcl/sqlcl-relnotes-26.1.2.html
- APEXlang commands: https://docs.oracle.com/en/database/oracle/sql-developer-command-line/26.1/sqcug/sqlcl-apex-commands-apexlang.html
- APEXlang workflows: https://docs.oracle.com/en/database/oracle/sql-developer-command-line/26.1/sqcug/common-workflows.html
- APEXlang project structure: https://docs.oracle.com/en/database/oracle/sql-developer-command-line/26.1/sqcug/apexlang-project-structure-apexlang.html
- APEXlang command reference: https://docs.oracle.com/en/database/oracle/sql-developer-command-line/26.1/sqcug/apexlang.html

Findings:

- SQLcl 26.1.2 release notes call out APEXlang support and large APEX app export fixes.
- APEXlang supports generate, export, validate, and import lifecycles.
- SQLcl 26.1.2 generated this repo's project structure as:
  - `application.apx`
  - `pages/`
  - `shared-components/`
  - `supporting-objects/`
  - `deployments/default.json`
  - `.apex/apexlang.json`
- `apex import` compiles APEXlang into PL/SQL and executes it against a database connection, using deployment metadata and CLI overrides.

Implication for this repo:

- Add SQLcl 26.1.2+ validation to the APEX path before exposing APEXlang commands.
- Put source under `src/apex/<app-alias>/` and preserve the directory names generated by SQLcl.
- Add wrapper commands around SQLcl instead of hand-writing APEX import/export logic:
  - `uv run python manage.py infra apex generate --alias cymbal-coffee`
  - `uv run python manage.py infra apex export --app-id <id> --output src/apex/cymbal-coffee`
  - `uv run python manage.py infra apex validate --input src/apex/cymbal-coffee`
  - `uv run python manage.py infra apex import --input src/apex/cymbal-coffee --workspace COFFEE --schema APP`

### Gemini Embeddings and Oracle Vector Search

Sources:

- Gemini Embedding 2: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/embedding-2
- Vertex/Gemini text embeddings API: https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/models/text-embeddings-api
- Oracle vector search April 2026 update: https://docs.oracle.com/en/database/oracle/oracle-database/26/vecse/april-2026-release-update-23.26.2.html
- Oracle vector index guidelines: https://docs.oracle.com/en/database/oracle/oracle-database/26/vecse/guidelines-using-vector-indexes.html
- HNSW vector index syntax: https://docs.oracle.com/en/database/oracle/oracle-database/26/vecse/hierarchical-navigable-small-world-index-syntax-and-parameters.html
- Third-party embedding APIs from Oracle Database: https://docs.oracle.com/en/database/oracle/oracle-database/26/vecse/access-third-party-models-vector-generation-leveraging-third-party-rest-apis.html
- Oracle RAG overview: https://docs.oracle.com/en/database/oracle/oracle-database/26/vecse/use-retrieval-augmented-generation-complement-llms.html

Findings:

- Google docs list `gemini-embedding-2` with 3072-dimensional vectors, custom task instructions, adjustable output size, and multimodal input support.
- The repo defaults to `gemini-embedding-2-preview`, `EMBEDDING_DIMENSIONS = 3072`, and Oracle `VECTOR(3072, FLOAT32)`, so the schema shape is compatible with the current non-preview Gemini Embedding 2 direction.
- Oracle AI Vector Search 26ai documentation highlights HNSW and IVF indexes, COSINE distance, target accuracy, and HNSW parameters such as neighbors and EFConstruction.
- April 2026 updates add function-based HNSW indexes, local HNSW indexes for partitions/subpartitions, multi-vector IVF search, and IVF on Iceberg external tables.
- Oracle Database can call third-party embedding providers through REST-backed utilities, including Google AI and Vertex AI, but this repo already has an app-level Vertex embedding service and cache.

Implication for this repo:

- Treat migration from `gemini-embedding-2-preview` to `gemini-embedding-2` as a data migration:
  - update settings/defaults/docs/tests,
  - clear or version embedding cache entries by model,
  - regenerate product/document embeddings with `coffee bulk-embed`,
  - re-export fixtures.
- Keep app-level Gemini embedding generation for now. In-database third-party embedding calls are valuable future research but would duplicate the current service/cache boundary.
- The current HNSW index remains the right demo default. Newer vector features are not necessary unless the demo introduces partitioned inventory/search tables or function-derived vectors.

### OpenAPI, REST Source Catalogs, and MCP

Sources:

- APEX REST Data Sources: https://docs.oracle.com/en/database/oracle/apex/26.1/htmdb/creating-a-REST-data-source.html
- APEX REST Source Catalogs: https://docs.oracle.com/en/database/oracle/apex/26.1/htmdb/managing-REST-source-catalogs.html
- Oracle MCP overview: https://www.oracle.com/mcp/
- Autonomous AI Database MCP: https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/about-mcp-server.html
- OCI Database Tools MCP tutorial: https://docs.oracle.com/en-us/iaas/database-tools/doc/tutorial.html

Findings:

- APEX can create REST Data Sources from endpoint URLs or OpenAPI/Swagger discovery URLs.
- APEX REST Source Catalogs can be created from one OpenAPI file and reused as templates.
- APEX supports common REST authentication options including no auth, basic, OAuth2 client credentials, OCI, certificate/private key, HTTP header, and query string.
- Oracle's MCP direction is agent-oriented: SQLcl local MCP, OCI Database Tools MCP, Autonomous AI Database MCP, and Oracle AI Database MCP.
- APEX does not appear to be an MCP client surface. APEX is the REST/OpenAPI consumer; MCP should be treated as an agent/tooling integration surface.

Implication for this repo:

- Build an OpenAPI-to-APEX bridge first.
- Wire Litestar MCP only for read-only agent/tool use, and export its schema alongside OpenAPI instead of trying to make APEX speak MCP directly.

---

## Recommended APEX Demo App

### Preferred app: Cymbal Coffee Operations Console

This should be a source-controlled APEXlang app under `src/apex/cymbal-coffee-ops/`.

Pages:

1. **Dashboard**
   - Product count, store count, low-stock count, and last embedding refresh.
   - Quick links to menu, stores, inventory, and search lab.

2. **Menu Catalog**
   - Interactive Report or Interactive Grid over `product`.
   - Show category, price, availability booleans, metadata, and image/description fields.
   - Demonstrates Oracle JSON and BOOLEAN support in APEX 26.1.

3. **Store Locator**
   - Map/report using `store.latitude`, `store.longitude`, timezone, hours JSON, and Google Maps no-key URLs.
   - No browser coordinate persistence. If user coordinates are added later, keep them page-session scoped.

4. **Inventory Matrix**
   - Master/detail store-to-inventory view over `store_product_inventory`.
   - Filters for in-stock, low-stock, pickup availability, and category.

5. **Semantic Search Lab**
   - Page item for a natural-language query.
   - Calls the Litestar JSON vector endpoint or a new APEX-friendly `/api/search/products` endpoint.
   - Displays grounded product rows, similarity score, and timing.

6. **Vector Explain Panel**
   - Calls the existing explain-plan API or uses a saved SQL query to show whether the HNSW vector index is used.
   - Useful for conference demos because it proves Oracle vector search is active.

7. **AI Integration Status**
   - Shows configured embedding model, vector dimension, and whether the current app is using `gemini-embedding-2-preview` or `gemini-embedding-2`.
   - Keep this read-only.

Why this app:

- It reuses the same coffee data without competing with the existing Litestar/HTMX customer chat UI.
- It shows APEX's best fit: reports, forms, maps, dashboards, and declarative REST Data Sources.
- It keeps AI calls centralized in the Litestar service unless the demo deliberately compares app-level versus in-database embedding generation.

Alternate app ideas:

- **Customer Coffee Finder**: customer-facing menu, store map, and recommendation search. More polished, but overlaps the current web app.
- **APEXlang Source Demo**: a minimal app whose main purpose is to show generate/export/validate/import. Useful for tooling talks, less useful as a product demo.
- **Inventory Admin Console**: CRUD-heavy admin app for stock updates. Practical, but less visually compelling.

---

## Separate Schema Bridge Tool

Create a repo tool that produces an APEX-safe schema bundle from the Litestar app.

Suggested command shape:

```bash
uv run python manage.py infra apex schemas export \
  --base-url http://host.docker.internal:8000 \
  --output src/apex/catalogs/cymbal-coffee-openapi.json
```

Responsibilities:

- Fetch or generate the Litestar OpenAPI document from the app.
- Filter to APEX-safe operations:
  - include JSON read/search endpoints for products, stores, inventory, and vector demo,
  - exclude SSE chat endpoints,
  - exclude admin/maintenance operations such as cache clearing, fixture export, and migrations.
- Normalize the schema:
  - stable operation IDs,
  - explicit JSON request/response content types,
  - server URL reachable from the ORDS/APEX container,
  - simple auth metadata if enabled,
  - examples for common APEX page items.
- Write:
  - `src/apex/catalogs/cymbal-coffee-openapi.json`,
  - optional `src/apex/catalogs/README.md`,
  - optional APEXlang snippets or generated REST Source Catalog metadata if SQLcl/APEXlang supports a stable representation.
- Validate by importing the OpenAPI file into an APEX REST Source Catalog.

Add a separate MCP export mode:

```bash
uv run python manage.py infra apex schemas export-mcp \
  --output src/apex/catalogs/cymbal-coffee-mcp-tools.json
```

Responsibilities:

- Wire `litestar-mcp` for read-only tool/resource exposure.
- Export a human/agent-readable manifest of MCP tools and resources.
- Keep MCP and APEX OpenAPI outputs separate. APEX consumes OpenAPI; agents consume MCP.

Recommended API additions for APEX:

- `GET /api/stores/{store_id}/inventory`
- `GET /api/products/{product_id}/availability`
- `POST /api/search/products` with JSON body `{ "query": "...", "store_id": "...", "limit": 5 }`
- `POST /api/recommendations` returning grounded JSON, not SSE
- `GET /api/system/ai-status` returning model, dimension, provider, and fixture freshness

Guardrails:

- Read-only first. Do not expose migrations, fixture loading, cache clearing, or admin commands through the APEX catalog or MCP.
- Keep browser coordinates request-scoped and never persist them through APEX REST source state.
- Keep product names/prices/descriptions grounded in Oracle rows, not model output.

---

## Proposed Implementation Sequence

1. **Reconcile Flow state**
   - Mark that ORDS sidecar code exists despite open Beads items.
   - Split remaining work into latest-version hardening, APEXlang source, sample app, and schema bridge.

2. **Harden optional APEX/ORDS runtime**
   - Pin or verify ORDS 26.1.x.
   - Add real ORDS/APEX HTTP health checks.
   - Add APEX media checksum validation and cache invalidation for the 2026-05-25 re-release.
   - Document optional APEX 26.1.1 patch bundle path without making MOS mandatory.

3. **Add APEXlang source lifecycle**
   - Require SQLcl 26.1.2+.
   - Add generate/export/validate/import wrappers.
   - Create `src/apex/cymbal-coffee-ops/` using official APEXlang directory names.

4. **Build the sample APEX app**
   - Start with direct Oracle reports/pages for products, stores, and inventory.
   - Add REST Data Source integration for vector search and AI status.
   - Keep chat as a link or add a JSON recommendation endpoint before integrating it.

5. **Build the schema bridge**
   - Export filtered OpenAPI for APEX REST Source Catalog.
   - Optionally wire and export MCP schema for agent workflows.
   - Add validation that the emitted OpenAPI file is accepted by APEX.

6. **Plan Gemini model migration**
   - Decide whether to move from `gemini-embedding-2-preview` to `gemini-embedding-2`.
   - If yes, regenerate embeddings and committed fixtures in the same change.

---

## Open Questions

1. Should the APEX sample be the recommended **Operations Console** hybrid app, or should it be customer-facing?
2. Should this repo move now from `gemini-embedding-2-preview` to `gemini-embedding-2`, including fixture regeneration?
3. Should public APEX 26.1.0 re-release be the only automated install, with 26.1.1 patch bundle as a documented optional path?
4. Should the schema bridge live under `manage.py infra apex schemas ...`, or should it be a `coffee` maintainer command?

---

## Bottom Line

The next practical Flow should not be "install APEX 26" broadly. The repo already has much of that optional runtime. The highest-value next Flow is:

**Harden the optional APEX 26.1/ORDS 26.1 runtime, add SQLcl-backed APEXlang source lifecycle under `src/apex/`, and create a Cymbal Coffee APEX Operations Console with an OpenAPI REST Source Catalog bridge to the Litestar app.**

MCP should be a parallel agent/tooling export, not the first-class APEX integration path.
