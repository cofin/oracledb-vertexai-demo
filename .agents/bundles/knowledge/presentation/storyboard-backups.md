---
type: Guide
title: Storyboard — Backup Slides (B1–B17)
description: Skipped deep-dive slides kept after the thank-you slide for questions
tags:
  - presentation
  - storyboard
---

# Storyboard — Backup Slides (B1–B17)

Backups sit after slide 36 and stay skipped in presentation mode. Each one
answers a question that comes up often enough to deserve a prepared slide.
Notes on backups do not need a `BRIDGE:` line.

### B1. AI Search Terms for Oracle DBAs

- **Target:** `slide_1790707646252622210_0`
- **Content:** four plain definitions mapped to Oracle: lexical search (`CONTAINS` / `SCORE`), embedding (`VECTOR(3072, FLOAT32)` from `gemini-embedding-2`), HNSW index (`INMEMORY NEIGHBOR GRAPH` in the SGA), hybrid search (rank fusion in SQL).

### B2. Hybrid Search in Three CTEs

- **Target:** `slide_1790707646252951731_100`
- **Content:** the three building blocks before the full query: a text CTE ranked by `SCORE`, a vector CTE ranked by `VECTOR_DISTANCE` with `FETCH APPROX`, and the fusion step with `FULL OUTER JOIN` and `1 / (:rrf_k + rank)`.

### B3. Oracle AI Database 26ai: What Matters

- **Target:** `slide_1790707646253525778_280`
- **Content:** `VECTOR` columns and HNSW or IVF indexes; native `BOOLEAN`; `JSON` columns (`CHECK (... IS JSON)` where needed); schema `ANNOTATIONS` with `USER_ANNOTATIONS_USAGE`; SQL/PGQ property graphs (`CREATE PROPERTY GRAPH`, `GRAPH_TABLE`).

### B4. Why Agents Need Schema Context

- **Target:** `slide_kc_why_34`
- **Content:** what an agent gets wrong without notes in Cymbal Coffee: store-level stock overrides the global `in_stock` flag; off-menu brands need an explicit answer; browser coordinates are request-scoped and never stored.

### B5. Knowledge Catalog in Action

- **Target:** `slide_kc_action_36`
- **Content:** the same question answered without and with catalog context. Build only after the repo's catalog sync exists; until then keep the slide skipped with a note.

### B6. HNSW vs. IVF and Vector Memory Sizing

- **Target:** `slide_1790707646252745998_31`
- **Content:** HNSW (in-memory graph, fastest, needs the vector memory area) vs. IVF (`ORGANIZATION NEIGHBOR PARTITIONS`, disk-based partitions, lower memory). Size with `DBMS_VECTOR.INDEX_VECTOR_MEMORY_ADVISOR(TABLE_OWNER, TABLE_NAME, COLUMN_NAME, INDEX_TYPE, PARAMETER_JSON, RESPONSE_JSON)`; check `V$SGAINFO` for the vector memory area; rough rule of thumb about 1.3 × rows × dimensions × 4 bytes for `FLOAT32`.

### B7. Term Hits and Score Cliffs in SQL

- **Target:** `slide_1790707646253117540_148`
- **Content:** `hybrid-term-hits` together with a `LAG()` window over ranked scores to find where relevance drops off, as a deterministic alternative to a fixed similarity cutoff.

### B8. SQLSpec and python-oracledb Patterns

- **Target:** `slide_1790707646253357135_220`
- **Content:** named SQL files loaded by name (`-- name: hybrid-search-turn`), Python `list[float]` vectors bound directly, explicit `commit()` after writes, and a separate queue pool so `fetch_lobs=False` stays off the app pool.

### B9. Bulk Embedding with SKIP LOCKED Queues

- **Target:** `slide_1790707646253435033_246`
- **Content:** `uv run coffee bulk-embed` enqueues `products.embed_missing`; workers claim jobs with `FOR UPDATE SKIP LOCKED`; build the HNSW index after the initial load. For very large backfills, mention batch embedding outside the request path and check the current Vertex AI batch options before quoting limits.

### B10. Property Graphs (SQL/PGQ) in Oracle 26ai

- **Target:** `slide_1790707646253553449_292`
- **Content:** a small `CREATE PROPERTY GRAPH` over products, stores, and inventory, and a `GRAPH_TABLE` query that starts from a vector match. Mark it as an illustration unless the repo adds a graph.

### B11. Vertex AI from PL/SQL with DBMS_VECTOR

- **Target:** `backup_b11` (duplicate of slide 14)
- **Code card:**

  ```sql
  BEGIN
    DBMS_VECTOR.CREATE_CREDENTIAL(
      credential_name => 'VERTEX_CRED',
      params          => JSON('{"access_token": "<oauth-access-token>"}'));
  END;
  /
  SELECT DBMS_VECTOR.UTL_TO_EMBEDDING(
           'strong coffee for a cold morning',
           JSON('{"provider": "vertexai",
                  "credential_name": "VERTEX_CRED",
                  "url": "https://us-central1-aiplatform.googleapis.com/v1/projects/<project-num>/locations/us-central1/publishers/google/models/",
                  "model": "text-embedding-004:predict"}'))
  FROM dual;
  ```

- **Notes:** the access token is short-lived, so production use needs a job that refreshes the credential. Include `:predict` on the model name (`text-embedding-004:predict` or `gemini-embedding-001:predict`) and pass the numeric GCP project number so `"url"` stays within Oracle 26ai's 128-character buffer.

### B12. Cloud Run Functions as SQL Functions

- **Target:** `backup_b12` (duplicate of slide 14)
- **Code card:**

  ```sql
  BEGIN
    DBMS_CLOUD_ADMIN.ENABLE_PRINCIPAL_AUTH(provider => 'GCP');
  END;
  /
  SELECT param_value FROM cloud_integrations
  WHERE param_name = 'gcp_service_account';

  BEGIN
    DBMS_CLOUD_FUNCTION.CREATE_CATALOG(
      credential_name  => 'GCP$PA',
      catalog_name     => 'VERTEX_FUNCS',
      service_provider => 'GCP',
      cloud_params     => '{"project_id": "<project>"}');
    DBMS_CLOUD_FUNCTION.SYNC_FUNCTIONS(catalog_name => 'VERTEX_FUNCS');
  END;
  /
  ```

- **Notes:** grant the database's Google service account Cloud Functions Invoker and Cloud Run Invoker. The function itself calls Vertex AI with its own service account (`roles/aiplatform.user`), so no keys live in the database. Autonomous AI Database only.

### B13. Regions, Purchasing, and Support

- **Target:** `backup_b13` (duplicate of slide 6)
- **Content:** current regions from the public Oracle Database@Google Cloud locations page (check the count on the day); Marketplace purchase with commitment drawdown, pay-as-you-go or private offer, single Google Cloud bill; bring your own license and keep Oracle Support Rewards; collaborative support (database and billing cases with Oracle, application and networking cases with Google).

### B14. Vertex AI Platform and Model Garden

- **Target:** `backup_b14` (duplicate of slide 7)
- **Content:** Gemini models, Google embedding models, partner and open models in Model Garden, Agent Builder and Agent Engine, ADK, and the MCP and A2A interoperability story. Update every model name against current Vertex AI docs; the lists in earlier decks are out of date.

### B15. System Prompts and Personas

- **Target:** `backup_b15` (duplicate of slide 32)
- **Content:** Cymbal Coffee's base instruction and persona picker (`PersonaManager` in `src/app/domain/system/services/`). Quote the current text from the code, not the older "Coffee Novice" example.

### B16. It's Still All SQL: Vectors + Inventory

- **Target:** `backup_b16` (duplicate of slide 30)
- **Content:** the corrected version of the earlier "It's All SQL!" slide: a vector match on `product` (`ORDER BY VECTOR_DISTANCE(...) FETCH APPROX FIRST 5 ROWS ONLY`) joined to `store_product_inventory` and `store`, filtered to `stock_status <> 'OUT_OF_STOCK'`, with distance to the user computed in the app (Haversine), not with PostGIS functions. Tested against the Cymbal Coffee Oracle 26ai schema.

### B17. Demo Clips

- **Target:** `backup_b17` (duplicate of slide 24)
- **Content:** the re-recorded muted clips listed in the speaker guide, one per slide, as fallbacks for the walkthrough slides.
