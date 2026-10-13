---
type: Guide
title: Verified Facts — Oracle in the Age of Gemini (2026)
description: Claims the talk can make, each with a public source or repo path, plus open checks and the do-not-claim list
tags:
  - presentation
  - facts
  - oracle
  - vertex-ai
  - select-ai
---

# Verified Facts — Oracle in the Age of Gemini (2026)

Every statement on a slide should trace to a row here. Sources are public
documentation pages or files in this repository. Facts checked on 2026-10-13
unless noted.

## Cymbal Coffee (this repository)

| Fact | Source |
| :--- | :--- |
| The app calls Vertex AI with `google-genai` in Vertex AI mode (`vertexai=True`, project and location from settings) | `src/app/ioc/_ai.py`, `src/app/lib/settings/_ai.py` |
| Chat model `gemini-3.8-flash` (served on the `global` location); embedding model `gemini-embedding-2`, 3,072 dimensions | `src/app/lib/settings/_ai.py` |
| `product.embedding` is `VECTOR(3072, FLOAT32)` with `ANNOTATIONS (Display, Embedding_Model, Embedding_Dimensions, Embedding_Purpose, Distance)`; `product` is `INMEMORY PRIORITY HIGH` | `src/app/db/migrations/0001_cymball_coffee_products.sql` |
| HNSW indexes: `ORGANIZATION INMEMORY NEIGHBOR GRAPH DISTANCE COSINE WITH TARGET ACCURACY 95 PARAMETERS (TYPE HNSW, NEIGHBORS 40, EFCONSTRUCTION 500)` on `product`, `embedding_cache`, and `chat_route` | migration `0001` |
| Oracle Text: `CTX_DDL` `MULTI_COLUMN_DATASTORE` preferences `product_search_ds` (name, category, sku, description), `store_search_ds` (name, address, city, state, zip), `route_search_ds` (route_label, title, keywords, exemplar_text); `CTXSYS.CONTEXT` indexes with `SYNC (ON COMMIT)` | migration `0001` |
| `hybrid-search-turn` fuses `CONTAINS`/`SCORE` and `VECTOR_DISTANCE ... FETCH APPROX` with `1 / (:rrf_k + rank)` across `chat_route`, `product`, and `store`; `hybrid-term-hits` counts per-term `CONTAINS` hits over `JSON_TABLE` | `src/app/db/sql/hybrid.sql` |
| `build_oracle_text_query()` strips Oracle Text operators and joins `{token}` with `ACCUM` | `src/app/domain/chat/services/_router.py` |
| Four routes reply from SQL rows; `GENERAL_CONVERSATION` runs the agent loop with five parameterized SQL tools | `SLIDES.md` slide 6; `src/app/domain/ai/` |
| Session and event stores commit before model calls; job queue uses `FOR UPDATE SKIP LOCKED` with a separate pool (`session_key="queue_db_session"`) | `SLIDES.md` slides 3 and 7; `src/app/lib/settings/_database.py` |
| `/mcp` (LitestarMCP) and `/a2a` (LitestarA2A, agent card at `/.well-known/agent-card.json`), optionally gated by `MCP_API_KEY` | `src/app/server/plugins.py`; `AGENTS.md` |
| Browser coordinates are request-scoped, scrubbed from telemetry, and bypass the response cache | `SLIDES.md` slide 8 |
| Example routing timings: ~350–500 ms with a separate classifier call vs ~15–25 ms for the single SQL turn (local run) | `SLIDES.md` slide 4 |
| Default demo schema user is `app` | `src/app/lib/settings/_database.py` (`DATABASE_USER`) |
| Antigravity MCP config lives in `~/.gemini/antigravity/mcp_config.json`; SQLcl MCP is `sql -mcp`; MCP Toolbox runs `--prebuilt oracledb --stdio` | `docs/mcp-antigravity.md` |

## Oracle AI Database 26ai

| Fact | Source |
| :--- | :--- |
| `CONTAINS` / `SCORE` uses an inverse-frequency (TF-IDF family) score from 0 to 100; Oracle's only "BM25" is client-generated sparse vectors, so call Oracle Text "BM25-style ranking" | Oracle Text reference (scoring algorithm) |
| HNSW is used only for `ORDER BY VECTOR_DISTANCE(...)` with `FETCH APPROX FIRST n ROWS ONLY`; `FETCH FIRST` or ordering by an expression over the distance is an exact search | Oracle AI Vector Search guide; confirmed against migration and query plans in this repo |
| HNSW indexes require the SGA vector memory area (`vector_memory_size`); creation fails with `ORA-51962` when it is too small | Oracle AI Vector Search guide |
| Hybrid Vector Indexes build their own chunks and vectors with in-database models, so they cannot reuse vectors created by Vertex AI; that is why the app fuses ranks in plain SQL | Oracle AI Vector Search guide (hybrid vector index restrictions) |
| `DBMS_VECTOR` / `DBMS_VECTOR_CHAIN` support Vertex AI as a third-party REST provider for embeddings (text and image), text generation, and rerank (the rerank endpoint is the Vertex AI ranking API on `discoveryengine.googleapis.com`); the Vertex AI credential is `{"access_token": "..."}` (requires `CREATE CREDENTIAL` and a host network ACL); embedding endpoint `https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT/locations/LOCATION/publishers/google/models/`; `DBMS_VECTOR.UTL_TO_EMBEDDING` concatenates `url || model` directly so `"model"` requires the `:predict` suffix (for example `text-embedding-004:predict`, `gemini-embedding-001:predict`, `gemini-embedding-2:predict`, or `multimodalembedding:predict`), and `SYS.DBMS_VECTOR` in 26ai buffers `"url"` at 128 characters (`ORA-06502` if longer, so use the numeric GCP project number when the project ID is long) | docs.oracle.com/en/database/oracle/oracle-database/26/vecse/supported-third-party-provider-operations-and-endpoints.html; .../vecse/create_credential-dbms_vector.html; verified against `SYS.DBMS_VECTOR.UTL_TO_EMBEDDING` in Oracle AI Database 26ai Free (`23.26.0.0.0`) |
| `DBMS_VECTOR.INDEX_VECTOR_MEMORY_ADVISOR` has two overloads: `(INDEX_TYPE, NUM_VECTORS, DIM_COUNT, DIM_TYPE DEFAULT 'FLOAT32', PARAMETER_JSON DEFAULT NULL, RESPONSE_JSON OUT CLOB)` and `(TABLE_OWNER, TABLE_NAME, COLUMN_NAME, INDEX_TYPE, PARAMETER_JSON DEFAULT NULL, RESPONSE_JSON OUT CLOB)` | docs.oracle.com/en/database/oracle/oracle-database/26/vecse/index_vector_memory_advisor-dbms_vector.html; verified against `ALL_ARGUMENTS` in Oracle AI Database 26ai Free (`23.26.0.0.0`) |

## Select AI and Vertex AI

| Fact | Source |
| :--- | :--- |
| Select AI (`DBMS_CLOUD_AI`) is an Autonomous AI Database package and is not present in the Oracle AI Database 26ai Free container (`SELECT object_name FROM all_objects WHERE object_name = 'DBMS_CLOUD_AI'` returns 0 rows) | Verified against `gvenzl/oracle-free:latest` (`23.26.0.0.0`) |
| Select AI's `google` provider calls the Gemini API at `generativelanguage.googleapis.com` with an API key from Google AI Studio (`DBMS_CLOUD.CREATE_CREDENTIAL(username => 'GOOGLE', password => '<api_key>')`) and needs a network ACL for that host | docs.oracle.com/en/cloud/paas/autonomous-database/serverless/adbsb/select-ai-manage-profiles.html; .../select-ai-examples.html (Example: Select AI with Google) |
| Google models listed for Select AI: `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-3.1-pro-preview`, `gemini-3-flash-preview` (default), `gemini-3-flash-pro-preview`, `gemini-3.5-flash`; embeddings `gemini-embedding-001`, `gemini-embedding-2-preview`, `text-embedding-004` (default) | .../adbsb/select-ai-about.html (Select your AI Provider and LLMs) |
| Select AI's `oci` provider (OCI Generative AI) offers `google.gemini-2.5-pro`, `google.gemini-2.5-flash`, `google.gemini-2.5-flash-lite` | .../adbsb/select-ai-about.html |
| Select AI sends schema metadata (including table and column comments) for SQL generation, not row data; `narrate` sends query results to the model | .../adbsb/select-ai-about.html (Usage Guidelines) |
| Supported Select AI providers: `openai`, `cohere`, `azure`, `database`, `oci`, `google`, `anthropic`, `huggingface`, `aws`; `provider_endpoint` without `provider` is treated as OpenAI-compatible | .../adbsb/dbms-cloud-ai-package.html (Profile Attributes) |
| Select AI credentials support bearer tokens, vault secrets, and principal authentication with Azure service principal as the documented example; there is no `vertexai` Select AI provider and no documented use of `GCP$PA` in AI profiles | .../adbsb/dbms-cloud-ai-package.html |
| Autonomous AI Database can create a Google service account (`DBMS_CLOUD_ADMIN.ENABLE_PRINCIPAL_AUTH(provider => 'GCP')`, credential `GCP$PA`, name in `CLOUD_INTEGRATIONS`); it uses one-hour OAuth tokens managed by the database | .../adbsb/google-service-account.html |
| `DBMS_CLOUD_FUNCTION.CREATE_CATALOG(credential_name => 'GCP$PA', service_provider => 'GCP', ...)` wraps Google Cloud Run functions as SQL functions; the service account needs Cloud Functions Invoker and Cloud Run Invoker | .../adbsb/user-defined-functions-gpc.html |
| Oracle AI Database Agent: Google Cloud Marketplace agent that lets Gemini Enterprise call Select AI agent teams in Autonomous AI Database over A2A, configured with the database's OAuth client ID and secret, with per-user permissions | .../adbsb/use-oracle-ai-database-agent-google-gemini-enterprise-application.html; .../adbsb/configure-agent-google-marketplace-administrator.html |

## Oracle Database@Google Cloud and Google Cloud tooling

| Fact | Source |
| :--- | :--- |
| Services: Exadata Database Service, Autonomous AI Database Service, Base Database Service, Exadata Database Service on Exascale Infrastructure, GoldenGate | docs.cloud.google.com/oracle/database/docs/overview |
| Public locations page lists 14+ regions across North America (`us-east4`, `us-west2`, `us-central1`, `northamerica-northeast1`, `northamerica-northeast2`), South America (`southamerica-east1`), Europe (`europe-west2`, `europe-west3`, `europe-west12`), Asia (`asia-northeast1`, `asia-northeast2`, `asia-south1`, `asia-south2`), and Australia; check the live locations page on the day of the talk before quoting a number | docs.cloud.google.com/oracle/database/docs/locations; cloud.google.com/oracle/database/docs/supported-regions-zones |
| MCP Toolbox `oracledb` prebuilt server (`toolbox --prebuilt oracledb --stdio`) exposes 7 prebuilt tools: `execute_sql`, `list_tables`, `get_query_plan`, `list_active_sessions`, `list_top_sql_by_resource`, `list_tablespace_usage`, and `list_invalid_objects` | mcp-toolbox.dev/documentation/prebuilt-configs/prebuilt-oracledb/; github.com/googleapis/genai-toolbox/blob/main/internal/prebuiltconfigs/tools/oracledb.yaml |
| Remote MCP endpoint `https://oracledatabase.googleapis.com/mcp`; requires the Oracle Database@Google Cloud API, OAuth over IAM, and `roles/mcp.toolUser`; exposes control-plane tools `list_autonomous_databases` and `create_autonomous_database` | `docs/mcp-antigravity.md`; docs.cloud.google.com/oracle/database/docs/use-oracle-database-mcp-server |
| Knowledge Catalog (formerly Dataplex Universal Catalog) managed MCP server at `https://dataplex.googleapis.com/mcp` with `search_entries`, `lookup_context`, `lookup_entry` | docs.cloud.google.com/knowledge-catalog/docs/use-remote-mcp |
| Standalone Gemini CLI reached end of life in June 2026; Antigravity (`agy` CLI and Antigravity 2.0 IDE) succeeds it; the `gemini-cli-extensions/oracledb` extension packages MCP Toolbox `oracledb` and works with Antigravity, or servers can be registered directly in `~/.gemini/antigravity/mcp_config.json` | Antigravity announcement; github.com/gemini-cli-extensions/oracledb; `docs/mcp-antigravity.md` |

## Open checks (task 1.6)

- **Deferred (requires live Autonomous AI Database instance):** Optional lab test pointing Select AI (`DBMS_CLOUD_AI`) at an OpenAI-compatible Cloud Run gateway in front of Vertex AI. `DBMS_CLOUD_AI` is not bundled in the local Oracle AI Database 26ai Free container (`23.26.0.0.0`), so this remains untested and is not claimed on any slide.
- **Deferred (pre-event screen capture):** Muted 1080p MP4 screen recordings for the walkthrough slides (`speaker-guide.md`). Slides 13, 17, 25, 28–31, and B17 carry complete, self-contained SQL and prose walkthrough cards so the deck is stage-ready without external video files.

## Do not claim

- "Oracle Text uses BM25."
- "Select AI supports Vertex AI" or "Select AI uses `GCP$PA` for Gemini." Not documented today (and the optional OpenAI-compatible Cloud Run gateway pattern is untested).
- Region counts, interconnect counts, or security-feature dates taken from internal material.
- The "10% of data is accessible, 90% can be unlocked by AI" statistic (no primary source found).
- Benchmarks. Timings in this talk are example timings from a local run.
- Product names or model lists from earlier decks (Gemini 2.5 ecosystem, Model Garden lists) without re-checking them.
