---
type: Research
research_id: research_knowledge_catalog_demo_20261012
title: Google Cloud Knowledge Catalog Enablement, Oracle 26ai Metadata Ingestion, and Agentic Demo Options
description: Primary-source investigation of Google Cloud Knowledge Catalog (formerly Dataplex Universal Catalog), Oracle 26ai metadata/annotations ingestion, OKF v0.2 kcmd sync, MCP Toolbox, LookupContext grounding, and rapid demo architectures for Cymbal Coffee.
scope: integration
tags:
  - research
  - knowledge-catalog
  - dataplex
  - okf
  - oracle
  - mcp
  - vertex-ai
status: stable
state: promoted
promoted_to: knowledge-catalog-grounding-demo
confidence: high
created_at: 2026-10-12T17:50:00Z
updated_at: 2026-10-12T18:24:00Z
---

# Google Cloud Knowledge Catalog Enablement, Oracle 26ai Metadata Ingestion, and Agentic Demo Options

## Executive Summary

1. **Product Identity & Underlying APIs**: **Google Cloud Knowledge Catalog** is the rebranded evolution of **Dataplex Universal Catalog** (`https://docs.cloud.google.com/knowledge-catalog/docs/introduction`). Its underlying Google Cloud service endpoint, IAM roles, CLI command group, and Python SDK remain `dataplex.googleapis.com` (`v1`), `roles/dataplex.*`, `gcloud dataplex`, and `google-cloud-dataplex` (`google.cloud.dataplex_v1`). Enabling `dataplex.googleapis.com` activates both the Knowledge Catalog APIs and Google Cloud's managed remote Dataplex MCP server.
2. **Direct Bridge to Cymbal Coffee's Existing Architecture**:
   - **OKF v0.2 Native Alignment**: Cymbal Coffee already uses the **Open Knowledge Format (`OKF v0.2`)** in `.agents/bundles/`. OKF v0.2 is authored and maintained in `GoogleCloudPlatform/knowledge-catalog/okf/SPEC.md` (`//third_party/knowledge_catalog/okf/`) as the official open-source authoring and exchange format for Google Cloud Knowledge Catalog (`go/okf-pitch`). The official `kcmd` CLI (`npx -y kcmd push <project> <location> <entry-group> --path <bundle> --format okf`) syncs OKF bundles directly into a Knowledge Catalog `EntryGroup`.
   - **Oracle 26ai Native `ANNOTATIONS(...)` Already Exist**: Migration `src/app/db/migrations/0001_cymball_coffee_products.sql:18-246,256,264` already defines rich Oracle 26ai schema annotations (`USER_ANNOTATIONS_USAGE`) across `product`, `store`, `store_product_inventory`, `response_cache`, `embedding_cache`, and `search_metric` (`Display`, `Description`, `Data_Role`, `Privacy`, `Embedding_Model`, `Embedding_Dimensions`, `Enum_Values`, `AI_Surface`, `Maps_Baseline`).
3. **Why Custom Entries / `kcmd` Beats the Managed Oracle Connector for a Fast Demo**:
   - The **Managed Oracle Metadata Connector** (`bigquerydatatransfer.googleapis.com` with `dataSourceId: 'oracle'`, Preview) runs as a batch BigQuery Data Transfer Service job requiring Private Service Connect (PSC) Network Attachments (or public IP + TLS CA), `SYS.COL$` / `SELECT_CATALOG_ROLE` / `ALTER ANY TRIGGER ON SCHEMA` grants, and harvests only raw technical table/column schemas — it ignores Oracle 26ai `USER_ANNOTATIONS_USAGE` and business rules.
   - **Custom Entries + Global System Aspects (`dataplex.googleapis.com/v1`)** or **`kcmd push --format okf`** runs in **<10 seconds** from any laptop or Cloud Run service with zero VPC/PSC or `SYS.COL$` setup, and populates reusable global system aspects (`projects/655216118709/locations/global/aspectTypes/{schema,overview,guidelines,queries}`) plus Business Glossaries (`Glossary`, `GlossaryTerm`, `EntryLink`).
4. **High-Impact Demo Pattern ("Breaking the Context Ceiling")**:
   - Google Cloud's flagship Knowledge Catalog + Oracle demo (*The Supply Chain War Room*, `drive.google.com/open?id=1yHEqmF1zPB1UMU58IYfhBRc5-ojcetP7VYP7mDnFsWs`) and pitch decks (`go/knowledge-catalog-pitch`, `go/okf-pitch`) center on a live **Knowledge Catalog Grounding OFF vs. ON** comparison and **Context X-Ray** telemetry drawer.
   - In Cymbal Coffee, a single CLI command (`uv run coffee sync-catalog`) can harvest Oracle 26ai `USER_ANNOTATIONS_USAGE` + OKF business rules into Knowledge Catalog (and generate a local offline/instant snapshot + Cytoscape.js graph). At runtime, `searchEntries` + `lookupContext` grounds the barista agent on **2-tier inventory precedence**, **coordinate privacy guardrails**, **steward-certified Golden SQL (`hybrid-search-turn`)**, and **off-menu brand rules (`Folgers`/`Starbucks`)**, surfaced in the right-hand telemetry drawer via a dedicated `K` (**Knowledge Catalog**) chip.

---

## 1. Options for Enabling Knowledge Catalog & Ingesting Oracle 26ai Context

| Option | Mechanism & Primary Source | Setup Time | Infrastructure & IAM Prerequisites | Rich Business Context (`guidelines`, `queries`, `ANNOTATIONS`) | Verdict for Cymbal Coffee Demo |
| --- | --- | --- | --- | --- | --- |
| **Option 1: Custom Entries + System Aspects API (`httpx` or `google-cloud-dataplex`)** | `POST/PATCH https://dataplex.googleapis.com/v1/projects/{p}/locations/{l}/entryGroups/{eg}/entries` (`ingest-custom-sources`, `enrich-entries-metadata`) | **~30 sec** (`uv run coffee sync-catalog`) | `gcloud services enable dataplex.googleapis.com`; `roles/dataplex.catalogEditor` or `entryGroupOwner` + `entryOwner`. Zero VPC/PSC. | **Full** — populates global system aspects (`schema`, `overview`, `guidelines`, `queries`, `contacts`) directly from Oracle 26ai `USER_ANNOTATIONS_USAGE` (`0001_cymball_coffee_products.sql:18-246`). | **Recommended primary path** (with local JSON/OKF fallback for zero-cloud offline runs). |
| **Option 2: `kcmd` CLI + Open Knowledge Format (`OKF v0.2`)** | `npx -y kcmd push <project> <location> <entry-group> --path <bundle> --format okf` (`GoogleCloudPlatform/knowledge-catalog/toolbox/mdcode`) | **~2 min** | Node.js `npx`, `dataplex.googleapis.com`, `roles/dataplex.entryOwner`. | **High** — maps each `.md` concept file to an `Entry` with `dataplex-types.global.overview` + `okf` provenance/attestation aspect; also exposes local stdio MCP (`npx -y kcmd mcp --path <dir>`). | **Best companion workflow** — Cymbal Coffee already uses OKF v0.2 in `.agents/bundles/` and can render an interactive Cytoscape graph (`viz.html`). |
| **Option 3: Prebuilt MCP Toolbox (`@toolbox-sdk/server`)** | `npx -y @toolbox-sdk/server@latest --prebuilt dataplex` (and `--prebuilt oracledb`) (`googleapis/mcp-toolbox`) | **~1 min** | `DATAPLEX_PROJECT=<project_id>`, ADC credentials, `roles/dataplex.catalogViewer`. | **Runtime Consumer** — exposes 21 prebuilt MCP tools (`search_entries`, `lookup_context`, `lookup_entry`, `search_aspect_types`, data profile/quality scans) to Gemini CLI / Antigravity / ADK. | **Best zero-code IDE / CLI demo** — add to `tools/lib/utils.py` (`build_antigravity_mcp_config`). |
| **Option 4: Managed Oracle Metadata Connector (Preview)** | `bigquerydatatransfer.googleapis.com` (`dataSourceId: 'oracle'`, `oracle-transfer`) | **30–60+ min** | `bigquerydatatransfer.googleapis.com`, PSC Network Attachment (or public IP + TLS CA), `service-{NUM}@gcp-sa-bigquerydatatransfer` `roles/dataplex.entryGroupImporter`, Oracle `SELECT_CATALOG_ROLE`, `SELECT ON SYS.COL$`, `ALTER ANY TRIGGER ON SCHEMA`. | **Technical schema only** — batch job extracts raw tables/columns (`system=ORACLE AND type=TABLE`), not Oracle 26ai `ANNOTATIONS` or agent guidelines; requires subsequent enrichment step anyway. | **Not recommended for quick demo** — document as enterprise production option for large legacy Oracle estates. |
| **Option 5: GCS Bulk Metadata Import Job** | `gcloud dataplex metadata-jobs create --type=IMPORT` reading `.jsonl` from GCS (`import-metadata`) | **~10 min** | GCS bucket, `roles/dataplex.metadataJobOwner`, `.jsonl` staging pipeline. | **Full**, but asynchronous batch job designed for 10k–1M+ entries (up to 3 GB/job). | **Overkill** for Cymbal Coffee's 6 core Oracle tables. |

---

## 2. Knowledge Catalog Metamodel & Global System Aspects (`655216118709`)

When ingesting Oracle 26ai metadata via Custom Entries (`F4`, `F5`, `F6`), Knowledge Catalog organizes context into four resources:

1. **`EntryGroup`**: `projects/{project}/locations/{location}/entryGroups/cymbal-coffee-oracle` — regional container and IAM boundary (`us-central1` or `global`).
2. **`EntryType`**: Reusable global system entry type `projects/655216118709/locations/global/entryTypes/generic` (or custom `oracle-table` entry type).
3. **`Entry`**: Represents each Oracle 26ai table (`product`, `store`, `store_product_inventory`, `response_cache`, `embedding_cache`, `search_metric`) with:
   - `entrySource.system = "ORACLE"`
   - `entrySource.platform = "Oracle AI Database 26ai"`
   - `fullyQualifiedName = "oracle:cymbal-coffee:FREEPDB1.COFFEE.PRODUCT"`
4. **Global System Aspect Types (`projects/655216118709/locations/global/aspectTypes/{type}`)**:
   - **`655216118709.global.schema`**: Column names, data types (`VECTOR(3072, FLOAT32)`, `JSON`, `BOOLEAN`, `NUMBER`), and column descriptions harvested directly from `USER_TAB_COLUMNS` + `USER_ANNOTATIONS_USAGE`.
   - **`655216118709.global.overview`**: Rich Markdown business summary of the asset and its role in Cymbal Coffee.
   - **`655216118709.global.guidelines`**: Explicit steward-certified rules and guardrails that AI agents must obey when querying or reasoning over the asset.
   - **`655216118709.global.queries`**: Steward-verified Golden SQL queries (e.g., `hybrid-search-turn` RRF fusion, `resolve-products-by-query` 3-tier resolution, Haversine nearest-store lookup).
   - **`655216118709.global.contacts`**: Data Steward and Context Engineer attribution.
5. **Business Glossary (`Glossary`, `GlossaryTerm`, `EntryLink`)**:
   - Captures canonical domain definitions (e.g., *Available-to-Pickup Stock*, *Request-Scoped Browser Coordinates*, *Off-Menu Brand Guardrail*, *Reciprocal Rank Fusion (RRF)*) linked to table entries via `definition` `EntryLink`s.

> **Important Nuance (`F8` vs `F9`)**: Public Knowledge Catalog documentation (`enrich-entries-metadata`) and internal retrieval guides (`go/kc-retrieval-overview`) specify that `lookupContext` **automatically assembles global system aspects** (`schema`, `overview`, `guidelines`, `queries`, `data-profile`, `data-quality-scorecard`) and linked Business Glossary terms into a single LLM-ready YAML/Markdown payload. User-defined custom aspect types are **not** automatically formatted by `lookupContext` and require an explicit `lookupEntry` / `getEntry` (`EntryView.FULL`) call if used. Therefore, putting agent instructions in `655216118709.global.guidelines` and golden SQL in `655216118709.global.queries` gives full native `lookupContext` support without custom aspect overhead.

---

## 3. Runtime Agent Grounding: `searchEntries` + `lookupContext` & MCP

Knowledge Catalog provides two primary runtime consumption patterns for AI agents (`F8`, `F10`, `f6`, `f7`, `f8`):

### A. Two-Step Programmatic Retrieval (`dataplex.googleapis.com/v1`)
1. **`searchEntries`** (`POST https://dataplex.googleapis.com/v1/projects/{project}/locations/global:searchEntries`):
   - Runs ACL-aware hybrid semantic (`semanticSearch: true`) + keyword search (e.g. `query: "coffee inventory stock status system=ORACLE"`) across catalog entries in ~1s.
2. **`lookupContext`** (`POST https://dataplex.googleapis.com/v1/projects/{project}/locations/{location}:lookupContext`):
   - Accepts up to 10 `resources` (entry resource names in the same location) and `options`:
     ```json
     {
       "resources": [
         "projects/my-project/locations/us-central1/entryGroups/cymbal-coffee-oracle/entries/product",
         "projects/my-project/locations/us-central1/entryGroups/cymbal-coffee-oracle/entries/store_product_inventory"
       ],
       "options": {
         "format": "yaml",
         "context_budget": "4096",
         "all_schema_fields": "true"
       }
     }
     ```
   - Returns a single token-efficient (~1,200 tokens vs ~8,600 tokens in uncurated RAG) LLM-ready context block containing technical schema, `overview`, steward `guidelines`, linked glossary terms, operational metadata, and verified `queries`.

### B. Zero-Config MCP Server Integration
1. **Google Cloud Managed Remote MCP Server** (`https://docs.cloud.google.com/knowledge-catalog/docs/use-remote-mcp`):
   - Automatically enabled when `dataplex.googleapis.com` is enabled (requires `roles/mcp.toolUser` and `roles/dataplex.catalogViewer`).
2. **MCP Toolbox for Databases (`@toolbox-sdk/server`)** (`googleapis/mcp-toolbox`):
   - Run `npx -y @toolbox-sdk/server@latest --prebuilt dataplex` with `DATAPLEX_PROJECT=<project_id>` to expose 21 tools including `search_entries`, `lookup_context`, and `lookup_entry`.
3. **Cymbal Coffee `LitestarMCP` (`POST /mcp`)**:
   - Because `src/app/server/plugins.py:114` uses `AutowirePlugin`, any controller route decorated with `mcp_tool="lookup_knowledge_catalog"` is automatically exposed on Cymbal Coffee's own `/mcp` endpoint alongside `search_products`, `get_product`, and `get_store_inventory`.

---

## 4. What Makes a Meaningful Demo? ("Breaking the Context Ceiling")

Across Google Cloud's official Knowledge Catalog pitch (`go/knowledge-catalog-pitch`), the Open Knowledge Format pitch (`go/okf-pitch`), and the internal Oracle Database@Google Cloud + Knowledge Catalog demo (*The Supply Chain War Room*, `drive.google.com/open?id=1yHEqmF1zPB1UMU58IYfhBRc5-ojcetP7VYP7mDnFsWs`), the highest-converting demo narrative is **"Breaking the Context Ceiling"** via a live **Knowledge Catalog Grounding OFF vs. ON** comparison across three concrete enterprise failure modes:

| Enterprise Failure Barrier | What Happens in Cymbal Coffee with Knowledge Catalog **OFF** (Ungrounded) | What Happens in Cymbal Coffee with Knowledge Catalog **ON** (`lookupContext` Grounded) |
| --- | --- | --- |
| **1. Technical Shorthand & Multi-Table Semantics** (*"Can I pick up Ethiopian Yirgacheffe in Dallas right now?"*) | An ungrounded agent looks only at `product.in_stock = TRUE` (ignoring store-level `store_product_inventory.stock_status = 'OUT_OF_STOCK'` or `pickup_available = FALSE`) and gives a false availability promise. | `lookupContext` returns the steward-certified **2-Tier Inventory Contract** (`655216118709.global.guidelines` + `queries` aspect on `store_product_inventory`), enforcing `store_product_inventory` precedence (`IN_STOCK` > `LOW_STOCK` > `OUT_OF_STOCK` + `pickup_available`) over global `product.in_stock`. |
| **2. Tribal Rules & Hallucination Guardrails** (*"Do you have Folgers or Starbucks Pike Place in stock?"*) | Dense 3072-dim vector similarity matches `"Folgers"` to in-catalog medium/dark roasts (`similarity ~0.68`); an ungrounded LLM blurs the boundary or fabricates availability. | `lookupContext` injects the **Steward-Certified Off-Menu Brand Policy** (`guidelines` aspect on `product` + Golden RRF per-term lexical hit query): when lexical hit count is `0`, the agent explicitly states Cymbal Coffee does not carry the third-party brand before offering verified in-catalog alternatives. |
| **3. Governance & Privacy Contracts** (*"Find the closest store to my current GPS coordinates and log my search"*) | An ungrounded agent or developer pipeline risks caching or logging raw `latitude`/`longitude` in `response_cache`, `search_metric`, or `agent_event`. | `lookupContext` surfaces the **Oracle 26ai Privacy Annotations** (`Privacy = 'No browser coordinates'` harvested from `USER_ANNOTATIONS_USAGE` on `store`, `response_cache`, and `search_metric`), proving in the **Telemetry Drawer (`K` chip)** that browser coordinates remained strictly request-scoped and cache was bypassed. |

---

## 5. Fastest End-to-End Configuration & Demo Blueprint for Cymbal Coffee

We can deliver a **two-mode (Instant Local OKF + Live Cloud Knowledge Catalog)** integration that configures and runs in **under 2 minutes**:

### Step 1: One-Command CLI Seeder (`uv run coffee sync-catalog`)
Add `sync-catalog` to `src/app/cli/commands.py` + `src/app/cli/_helpers/catalog.py`:
- Queries live Oracle 26ai `USER_ANNOTATIONS_USAGE` and `USER_TAB_COLUMNS` via SQLSpec (`src/app/db/sql/catalog.sql`) to extract all table, column, and vector index annotations (`product`, `store`, `store_product_inventory`, `response_cache`, `embedding_cache`, `search_metric`).
- Merges them with Cymbal Coffee's steward-certified `guidelines` (2-tier inventory contract, off-menu brand rule, coordinate privacy invariant) and `queries` (Golden SQL from `src/app/db/sql/`).
- **Outputs two targets simultaneously**:
  1. **Local OKF v0.2 Bundle + Snapshot** (`.agents/bundles/knowledge/catalog/` + `src/app/db/fixtures/knowledge_catalog_context.json`): Works **instantly with zero GCP setup** for offline/CI demos.
  2. **Live Google Cloud Knowledge Catalog Push** (when `GOOGLE_CLOUD_PROJECT` and `--push` or `KNOWLEDGE_CATALOG_ENABLED=true` are set): Uses `httpx` with `google.auth` ADC (already in `pyproject.toml` via `google-genai`, requiring **zero new heavy dependencies**) to idempotently upsert `EntryGroup` (`cymbal-coffee-oracle`), `Entry` records (`system="ORACLE"`), and global system aspects (`655216118709.global.{schema,overview,guidelines,queries}`) via `dataplex.googleapis.com/v1`.

### Step 2: Runtime `KnowledgeCatalogService` + Agent Tool + MCP Endpoint
- **`KnowledgeCatalogService`** (`src/app/domain/system/services/_catalog.py`, registered in `src/app/ioc`):
  - In **Live GCP Mode**, calls `dataplex.googleapis.com/v1` `searchEntries` + `lookupContext` (`format="yaml"`, `all_schema_fields="true"`).
  - In **Local OKF Mode** (default fallback when offline or `KNOWLEDGE_CATALOG_MODE=local`), serves the exact same YAML context bundle assembled from Oracle 26ai `USER_ANNOTATIONS_USAGE` / committed OKF snapshot in `<2ms`.
- **Closure-Bound Agent Tool (`lookup_catalog_context`)** (`src/app/domain/ai/services/agent_service.py`):
  - Declared with `declare()` on `AgentSpec.tools` so `Gemini 3.8 Flash` can retrieve steward-certified table semantics, privacy rules, and Golden SQL.
- **LitestarMCP Tool (`GET /api/catalog/context`, `mcp_tool="lookup_knowledge_catalog"`)**:
  - Automatically exposed at `POST /mcp` for external MCP clients (Gemini CLI, Antigravity, Cloud Run agents).

### Step 3: Visual Demo UX in Chat & Telemetry Drawer
- Add a **`K` (Knowledge Catalog)** telemetry badge in `src/resources/telemetry.js` alongside `I` (Intent), `E` (Embedding), `O` (Oracle Vector), and `T` (Total).
- Clicking the `K` chip opens the existing slide-over Telemetry Drawer (`#telemetry-popover`) and displays:
  - The matched Knowledge Catalog `Entry` URIs (`oracle:cymbal-coffee:FREEPDB1.COFFEE.PRODUCT`, etc.)
  - Steward-certified `guidelines` and `Privacy` annotations applied during the turn
  - The exact `lookupContext` YAML payload and latency (`runtime_ms`).

---

## 6. Primary Sources & Citations

- **Google Cloud Knowledge Catalog Documentation**:
  - Overview: `https://docs.cloud.google.com/knowledge-catalog/docs/introduction` (`F1`)
  - Transition from Dataplex Universal Catalog: `https://docs.cloud.google.com/knowledge-catalog/docs/transition-dataplex-universal-catalog` (`F1`)
  - About Metadata & Metamodel: `https://docs.cloud.google.com/knowledge-catalog/docs/metadata-overview` (`F4`, `F5`)
  - Ingest Custom Sources (`EntryGroup`, `EntryType`, `Entry`): `https://docs.cloud.google.com/knowledge-catalog/docs/ingest-custom-sources` (`F1`, `F4`, `F5`)
  - Enrich Entries with Metadata (`AspectType`, `Aspect`, System Aspects `655216118709`): `https://docs.cloud.google.com/knowledge-catalog/docs/enrich-entries-metadata` (`F4`, `F5`, `F9`)
  - Manage Business Glossaries: `https://docs.cloud.google.com/knowledge-catalog/docs/manage-glossaries` (`F6`)
  - Managed Oracle Metadata Connector (Preview): `https://docs.cloud.google.com/knowledge-catalog/docs/oracle-transfer` (`F1`, `F2`, `F3`)
  - Retrieve Data Context (`lookupContext`): `https://docs.cloud.google.com/knowledge-catalog/docs/retrieve-data-context` and `https://docs.cloud.google.com/knowledge-catalog/docs/reference/rest/v1/projects.locations/lookupContext` (`F1`, `F8`, `F9`)
  - Use Remote MCP Server: `https://docs.cloud.google.com/knowledge-catalog/docs/use-remote-mcp` (`F1`, `F10`)
- **GitHub & Internal Code Repositories**:
  - `GoogleCloudPlatform/knowledge-catalog` (`//third_party/knowledge_catalog/`): `okf/SPEC.md` (`f1`, `f2`, `f9`), `toolbox/mdcode/` (`kcmd` CLI & MCP server, `f3`, `f10`, `f14`), `samples/discovery/tools.py` (`f4`, `f14`)
  - `googleapis/mcp-toolbox` (formerly `googleapis/genai-toolbox`): `docs/en/integrations/knowledge-catalog/prebuilt-configs/knowledge-catalog.md` (`f6`, `f7`, `f14`), `docs/en/integrations/oracle/prebuilt-configs/oracle.md` (`f6`, `f14`)
  - `//experimental/tinykc`: Local SQLite-backed gRPC emulator for `google.cloud.dataplex.v1.CatalogService` (`f14`)
- **Internal Moma Decks & Demo Scripts**:
  - Knowledge Catalog Hub: `https://sites.google.com/google.com/godataanalytics/products/knowledge-catalog` (`f5`, `f11`, `f13`)
  - Knowledge Catalog Pitch (2026) (`go/knowledge-catalog-pitch`): `https://drive.google.com/open?id=13KWjJ4_XBVcoYgp3WVULljgB74Ii3h1rZIwxDurkeVA` (`f8`, `f11`)
  - Open Knowledge Format (OKF) Pitch (`go/okf-pitch`): `https://drive.google.com/open?id=18upOHR-PsAwee1i430YsRorBJIJ407SPTLILYV428h8` (`f9`, `f10`, `f11`)
  - Knowledge Catalog Search & Retrieval Overview (`go/kc-retrieval-overview`): `https://drive.google.com/open?id=1lELDOiLoqL_5sQLgkS2Ir1hpOVTxJLJsX77vdSlqiEg` (`F8`, `F9`, `f7`, `f8`)
  - Oracle & Knowledge Catalog Demo Script (*The Supply Chain War Room*): `https://drive.google.com/open?id=1yHEqmF1zPB1UMU58IYfhBRc5-ojcetP7VYP7mDnFsWs` (`F4`, `F5`, `F8`, `F9`, `f11`, `f12`, `f14`)
- **Local Cymbal Coffee Codebase**:
  - Oracle 26ai DDL & Native `ANNOTATIONS`: `src/app/db/migrations/0001_cymball_coffee_products.sql:11-335` (`f1`–`f7`)
  - Named SQL Queries: `src/app/db/sql/products.sql`, `stores.sql`, `inventory.sql`, `system.sql`, `ai-runtime.sql` (`f1`–`f7`, `f12`)
  - Native AI Runtime & Orchestration: `src/app/domain/ai/runtime/_tools.py:30-156`, `_spec.py:18-139`, `_stream.py:28-215`, `src/app/domain/ai/services/agent_service.py:22-158` (`f10`–`f12`, `f14`, `f19`)
  - LitestarMCP & A2A Wiring: `src/app/server/plugins.py:35-160`, `src/app/domain/ai/a2a/card.py:8-33` (`f13`, `f20`)
  - Frontend SSE & Telemetry Drawer: `src/resources/chat-stream.js:173-402`, `src/resources/telemetry.js:6-343` (`f14`–`f16`)
  - CLI & DI Wiring: `src/app/cli/commands.py:25-223`, `src/app/ioc.py:1-151`, `src/app/lib/settings.py:210-486` (`f17`, `f18`)

---

## 7. Limitations & Resolved Contradictions

### Limitations
- The Managed Oracle Metadata Connector (`oracle-transfer`) and `lookupContext` API (`projects.locations/lookupContext`) are currently in Public Preview (with `lookupContext` targeting GA in Q4 2026 per `go/kc-retrieval-overview`), and `lookupContext` requires all (up to 10) entry resources in a single request to reside in the same location.
- Data Products (`DataProduct`, `DataAsset`) in Knowledge Catalog currently support 1P analytical assets (BigQuery, Iceberg REST, Cloud Storage) rather than custom 3rd-party Oracle entries, so Oracle assets should be organized via `EntryGroup`, `Glossary`, and `EntryLink`.
- `pyproject.toml` does not currently include `google-cloud-dataplex`; however, `httpx` and `google-auth` (via `google-genai`) are already installed, so calling the REST v1 endpoints (`entries`, `searchEntries`, `lookupContext`) directly via `httpx` avoids adding a new SDK dependency unless preferred.

### Resolved Contradictions
- **`lookupContext` vs. User-Defined Custom Aspect Types (`F8` vs `F9`)**: Public docs (`enrich-entries-metadata`) note that user-defined custom aspect types are not automatically assembled by Gemini context tools, whereas `lookupContext` natively formats reusable global system aspects (`655216118709.global.{schema,overview,guidelines,queries}`) and linked Business Glossary terms. **Resolution**: Store Cymbal Coffee's Oracle 26ai annotations, agent guardrails, and golden queries inside the global system aspects (`schema`, `overview`, `guidelines`, `queries`) so `lookupContext` returns them in a single call.
- **Repository & Tool Naming (`f6` vs `f7`)**: Earlier documentation refers to `googleapis/genai-toolbox` and `dataplex-search-entries` / `dataplex-lookup-context`, whereas the repository has been renamed to `googleapis/mcp-toolbox` (`@toolbox-sdk/server`) with docs under `docs/en/integrations/knowledge-catalog/` while preserving `--prebuilt dataplex` and `dataplex-*` aliases for backward compatibility.
- **Local Table Naming in Planned Specs (`f2`, `f4`, `f12`)**: Some draft spec prose references `coffee_store` and `search_metrics`, whereas the authoritative migration `0001_cymball_coffee_products.sql:49,198` and all named SQL files use `store` and `search_metric` (and `runtime-stabilization` adds `0002` for `agent_session`/`agent_event`). Always target `store` and `search_metric`.
