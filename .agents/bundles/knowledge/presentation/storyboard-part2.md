---
type: Guide
title: Storyboard — DBA Use Cases and Gemini Inside 26ai (slides 14–25)
description: Slide-by-slide content, code, takeaways, and speaker notes for The Art of the Possible DBA Use Cases and Gemini Inside Oracle AI Database 26ai (slides 14–25)
tags:
  - presentation
  - storyboard
---

# Storyboard — DBA Use Cases and Gemini Inside 26ai (slides 14–25)

Targets refer to objectIds in the 34-slide active deck (see [storyboard](storyboard.md)).
Facts and sources are in [verified facts](verified-facts.md).

## The Art of the Possible: DBA Use Cases

### 14. The Art of the Possible: DBA Use Cases

- **Target:** `dba_s12` (section divider)
- **Title:** The Art of the Possible: DBA Use Cases
- **Subtitle:** Let agents gather diagnostics and draft actions; DBAs approve every change
- **Notes:** Agents excel at gathering diagnostics across views, comparing plans, and summarizing multi-page reports, while production DDL and DML remain firmly under DBA approval. The next six slides walk through concrete diagnostic, scripting, and ad-hoc analysis workflows you can run with read-only database credentials.
  BRIDGE: Let's start with Use Case 1: triaging regressed SQL and summarizing SQL Tuning Advisor.
- **Sources:** NorCal 34; Webinar 25

### 15. Use Case 1: Regressed SQL & Tuning Advisor

- **Target:** `dba_s13` (`T_SCULPTURE` split card, SQL, and assessment layout)
- **Title:** Use Case 1: Regressed SQL & Tuning Advisor
- **Left card — From Alert to Simple Action:**
  1. **Ask `agy`:** `"Find today's slowest SQL and summarize SQL Tuning Advisor."`
  2. **Save as a Tool:** Add `find_slow_sql` and `tuning_report` to `tools.yaml`.
  3. **Fast Assessment:** Turns a multi-page tuning report into a single action.
- **Top-right code card (`sql`):**

  ```sql
  -- 1. Spot slowest SQL across RAC nodes (saved in tools.yaml)
  SELECT sql_id, plan_hash_value,
         ROUND(elapsed_time / executions / 1e3, 1) AS avg_ms
  FROM gv$sql
  WHERE parsing_schema_name = 'APP' AND executions > 0
  ORDER BY avg_ms DESC FETCH FIRST 5 ROWS ONLY;

  -- 2. Pull SQL Tuning Advisor report for the SQL_ID
  SELECT DBMS_SQLTUNE.REPORT_TUNING_TASK(:task_name) FROM dual;
  ```

- **Bottom-right dark summary card (`agy Assessment -> Simple Action for DBA Review`):**
  - **Finding:** Stale stats on `ORDERS_2026_Q3` (est 1 row vs 1.4M actual)
  - **Benefit:** `94%` faster elapsed time (`420 ms -> 9 ms`)
  - **Action to Review:** `EXEC DBMS_STATS.GATHER_TABLE_STATS('APP', 'ORDERS');`
- **Notes:** When checkout latency spikes, you ask Antigravity to inspect the top SQL across `GV$SQL` and summarize the SQL Tuning Advisor report (noting Tuning Pack licensing where `DBMS_SQLTUNE` is used, or `DBMS_XPLAN` / `DBMS_SPM` baselines otherwise). Instead of paging through long text sections, `agy` isolates stale partition statistics and proposes a single `DBMS_STATS` command for DBA review, while both `SELECT` queries graduate into `tools.yaml`.
  BRIDGE: Let's look at Use Case 2: RMAN backup and patch readiness analysis.
- **Sources:** [verified facts](verified-facts.md)

### 16. Use Case 2: RMAN Backup & Readiness Analyzer

- **Target:** `dba_s19` (`T_FLAME` split card, SQL, and summary layout)
- **Title:** Use Case 2: RMAN Backup & Readiness Analyzer
- **Left card — Turn Questions Into Queries:**
  1. **Ask in Plain English:** `"Check RMAN backups for the last 7 days and flag warnings."`
  2. **Convert to SQL:** `agy` writes the `V$RMAN_BACKUP_JOB_DETAILS` query for `tools.yaml`.
  3. **Instant Triage:** Pinpoints the one job that hit a recovery area warning.
- **Top-right code card (`sql`):**

  ```sql
  -- Check RMAN backup jobs over the last 7 days (saved in tools.yaml)
  SELECT session_key, input_type, status,
         TO_CHAR(start_time, 'MM-DD HH24:MI') AS started,
         time_taken_display AS duration,
         output_bytes_display AS backup_size
  FROM v$rman_backup_job_details
  WHERE start_time > SYSDATE - 7
  ORDER BY start_time DESC;
  ```

- **Bottom-right dark summary card (`agy Summary -> Simple Action for DBA Review`):**
  - **Status:** 13/14 `ARCHIVELOG` & `DB INCR` jobs `COMPLETED` (avg 18m)
  - **Warning:** `10-13 02:15` job hit `ORA-19809` (FRA reached `88%`)
  - **Action to Review:** `SELECT * FROM v$recovery_file_dest;`
- **Notes:** Before a maintenance window, you ask Antigravity in plain English to check RMAN backup health over the past seven days. Antigravity runs a clean read-only query against `V$RMAN_BACKUP_JOB_DETAILS` that you can save into `tools.yaml`, summarizes all 14 jobs in three lines, and highlights last night's archivelog job that warned on Fast Recovery Area pressure.
  BRIDGE: Once you have a saved SQL check, you can also pipe it directly into the `agy` CLI from any shell script.
- **Sources:** [verified facts](verified-facts.md)

### 17. The Art of the Possible: Power Up Your Scripting

- **Target:** `dba_s14` (`T_LAPTOP` with `dba_pipe_demo.gif` terminal capture)
- **Title:** The Art of the Possible: Power Up Your Scripting
- **Subtitle:** Pipe silent SQLcl checks straight into `agy -p` from jump hosts and shell scripts
- **Left card (`Unix Pipes Meet DBA Runbooks`):**
  - Run read-only SQLcl checks in silent mode (`sql -s`) using a wallet and read-only user
  - Pipe output into `agy -p "..." 2>/dev/null` for dependency ordering or anomaly summaries
  - Produce reviewable SQL scripts or change-ticket notes without granting write access
- **Right code card (`bash`):**

  ```bash
  sql -s mcp_diag_ro/"${ORACLE_DIAG_PASSWORD}"@prd_tp <<'SQL' \
    | agy -p "Order invalid objects by dependency and draft compile DDL; do not execute." 2>/dev/null
  SET PAGESIZE 100 LINESIZE 200 FEEDBACK OFF
  SELECT object_type, object_name, status
  FROM user_objects
  WHERE status <> 'VALID'
  ORDER BY object_type, object_name;
  EXIT
  SQL
  ```

- **Notes:** Show the embedded terminal capture (`dba_pipe_demo.gif`): non-interactive SQLcl lists invalid objects and pipes stdout straight into `agy -p "..." 2>/dev/null`, returning a dependency-ordered recompile script without executing any DDL. That pattern drops cleanly into existing bastion health checks and pre-patch verification scripts.
  BRIDGE: Beyond shell pipes, let's look at a two-turn interactive MCP session for ad-hoc data analysis.
- **Sources:** [speaker guide](speaker-guide.md); [verified facts](verified-facts.md)

### 18. Ad-Hoc Data Analysis: Interactive MCP Queries

- **Target:** `h33f425bc278cd40f_86_0`
- **Title:** Ad-Hoc Data Analysis: Interactive MCP Queries
- **Subtitle:** Turn 1 inside `agy`: inspect live catalog and stock counts over SQLcl MCP
- **Left card (`Conversational Catalog Triage`):**
  - Ask `agy` in plain English: `"How many unique products are in the catalog, and which ones are out of stock?"`
  - `agy` invokes SQLcl MCP (`run-sql`) as `APP` and records the execution in `DBTOOLS$MCP_LOG`
  - Returns exact counts (`130` products, `129` in stock, `1` out of stock: `Mirage Macchiato`)
- **Right code card (`sql`):**

  ```sql
  SELECT COUNT(*) AS total_products,
         SUM(CASE WHEN in_stock THEN 1 ELSE 0 END) AS in_stock_count,
         SUM(CASE WHEN NOT in_stock THEN 1 ELSE 0 END) AS out_of_stock_count
  FROM product;

  SELECT id, sku, name, category, price
  FROM product
  WHERE NOT in_stock;
  -- Result: 130 total | 129 in stock | 1 out of stock (Mirage Macchiato)
  ```

- **Notes:** In Turn 1 of an interactive `agy` session connected to the Cymbal Coffee schema (seeded from `src/app/db/fixtures/product.json.gz`), SQLcl MCP runs native Oracle 26ai `BOOLEAN` predicates (`WHERE NOT in_stock`), logs the `/* LLM in use ... */` audit trail in `DBTOOLS$MCP_LOG`, and confirms `130` total products with `Mirage Macchiato` as the single globally out-of-stock item.
  BRIDGE: In Turn 2 of the same session, we combine Oracle 26ai vector search with a local CSV extract.
- **Sources:** `src/app/db/fixtures/product.json.gz`; [verified facts](verified-facts.md)

### 19. Ad-Hoc Data Extracts: Vector Search to CSV

- **Target:** `SLIDES_API285542424_0`
- **Title:** Ad-Hoc Data Extracts: Vector Search to CSV
- **Subtitle:** Turn 2 inside `agy`: run semantic HNSW search, write `bold_products.csv`, and verify in bash
- **Left card (`Semantic Extract in One Session`):**
  - Follow up in `agy`: `"Export the top 5 boldest coffees by vector similarity to bold_products.csv."`
  - Executes `ORDER BY VECTOR_DISTANCE(..., COSINE) FETCH APPROX FIRST 5 ROWS ONLY`
  - Writes `bold_products.csv` (`RoboRoast` `0.9444`, `Signature Bold Blend` `0.9424`, `Caffeinated Dream` `0.9360`, `Midnight Brew` `0.9337`, `Cosmic Coffee` `0.9326`), then `/exit` to inspect with `ls -lh` and `head -n 6`
- **Right code card (`sql`):**

  ```sql
  SELECT p.id, p.name, p.category, p.price,
         ROUND(1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE), 4)
           AS similarity
  FROM product p
  WHERE p.embedding IS NOT NULL AND p.in_stock
  ORDER BY VECTOR_DISTANCE(p.embedding, :query_vector, COSINE)
  FETCH APPROX FIRST 5 ROWS ONLY;
  ```

- **Notes:** Turn 2 runs the approximate HNSW query (`vector-search-products` in `src/app/db/sql/products.sql`), writes the top five bold roasts (`RoboRoast` at `0.9444` through `Cosmic Coffee` at `0.9326`) to `bold_products.csv`, and exits `agy` (`/exit`) so a quick `ls -lh bold_products.csv && head -n 6 bold_products.csv` confirms the extract on disk.
  BRIDGE: Before moving inside the database engine, let's lock down the guardrails that keep every agent workflow safe.
- **Sources:** `src/app/db/sql/products.sql`; [storyboard](storyboard.md)

### 20. Guardrails for Database Agents

- **Target:** `dba_s22`
- **Title:** Guardrails for Database Agents
- **Subtitle:** The operational rules you apply to people, enforced at the account and tool layer
- **Cards:**
  - **Identity & Read-Only Enforcement:** Dedicated accounts (`CREATE USER mcp_diag_ro ... READ ONLY`, `ORA-28194`), never `SYS` or `SYSTEM`; IAM (`roles/mcp.toolUser`) for managed MCP endpoints.
  - **Curated Tool Scope:** Prefer parameterized `tools.yaml` `SELECT` statements over open `execute_sql`; scope access one schema at a time.
  - **Human Approval & Audit Trail:** Agents propose DDL and DML while DBAs execute changes; audit via Unified Auditing, `DBTOOLS$MCP_LOG`, and `V$SESSION` module/action tags.
  - **Secrets & Privacy:** Keep credentials in wallets or environment variables outside Git, and never persist personal data such as browser coordinates in logs, caches, or telemetry.
- **Notes:** Treat every agent like a new contractor: give it a named read-only account, narrow schema visibility, parameterized SQL tools, Unified Auditing plus `DBTOOLS$MCP_LOG` traceability, and strict data hygiene such as Cymbal Coffee's request-scoped coordinate scrubbing (`SLIDES.md` slide 8).
  BRIDGE: Next, let's look at how Gemini and vector search work inside Oracle AI Database 26ai itself.
- **Sources:** [verified facts](verified-facts.md); `SLIDES.md` slide 8

## Gemini Inside Oracle AI Database 26ai

### 21. Gemini Inside Oracle AI Database 26ai

- **Target:** `dba_s23` (section divider)
- **Title:** Gemini Inside Oracle AI Database 26ai
- **Subtitle:** Vector columns, Select AI and Vertex AI paths, SGA memory pools, and runbook search
- **Notes:** Now we move from external DBA tooling into the Oracle AI Database 26ai engine itself: how `VECTOR` columns and cosine distance behave, which SQL and PL/SQL paths reach Gemini and Vertex AI, and how HNSW interacts with SGA memory pools.
  BRIDGE: Let's start with what an embedding and vector distance actually look like in Oracle terms.
- **Sources:** NorCal 22–24

### 22. What Are Embeddings & Vector Distance?

- **Target:** `dba_s43`
- **Title:** What Are Embeddings & Vector Distance?
- **Subtitle:** GPS coordinates for meaning, stored in a regular `VECTOR(3072, FLOAT32)` column
- **Left card (`Embeddings in Oracle Terms`):**
  - **GPS Analogy:** Latitude and longitude place cities on a 2D map; `gemini-embedding-2` places text (`"espresso"`, `"bold dark roast"`) in a 3,072-float coordinate space (`~12 KB` per row).
  - **Distance vs Similarity:** `VECTOR_DISTANCE(col, :q, COSINE)` returns a distance where `0` is identical; similarity is `1 - distance`.
  - **Optimizer Rule:** Only `ORDER BY VECTOR_DISTANCE(...) FETCH APPROX FIRST :k ROWS ONLY` uses the in-memory HNSW graph; omitting `APPROX` or ordering by `1 - distance` forces a full scan.
- **Right code card (`sql`):**

  ```sql
  SELECT name, category, price,
         ROUND(VECTOR_DISTANCE(embedding, :query_vec, COSINE), 4) AS cosine_dist,
         ROUND(1 - VECTOR_DISTANCE(embedding, :query_vec, COSINE), 4) AS similarity
  FROM product
  WHERE embedding IS NOT NULL
  ORDER BY VECTOR_DISTANCE(embedding, :query_vec, COSINE)
  FETCH APPROX FIRST 5 ROWS ONLY;
  ```

- **Notes:** Use the GPS analogy and the `"espresso"` lookup example: two phrases with related meaning land near each other in 3,072-dimensional space, so `VECTOR_DISTANCE` approaches `0` and `1 - distance` approaches `1`. Just like a B-tree index requires a sargable predicate, Oracle's optimizer only picks `VECTOR INDEX HNSW SCAN` when you order by `VECTOR_DISTANCE(...)` and include `FETCH APPROX`.
  BRIDGE: What if you want to invoke Gemini directly from SQL or PL/SQL on Autonomous AI Database?
- **Sources:** NorCal 38–41; `SLIDES.md` slide 1; [verified facts](verified-facts.md)

### 23. Select AI with Gemini on Autonomous AI DB

- **Target:** `dba_s24`
- **Title:** Select AI with Gemini on Autonomous AI DB
- **Subtitle:** Natural-language SQL on Autonomous AI Database, plus enterprise Vertex AI paths
- **Left card (`Select AI & Vertex AI Paths`):**
  - **Select AI (`DBMS_CLOUD_AI`, `provider: "google"`):** Autonomous AI Database sends schema metadata (`COMMENT ON`, `ANNOTATIONS`) to the Gemini API (`generativelanguage.googleapis.com`, API key) for `showsql`, `runsql`, `explainsql`, and `narrate`, and pairs with Gemini Enterprise via the Marketplace Oracle AI Database Agent over A2A on Autonomous AI Database on Oracle Database@Google Cloud.
  - **Vertex AI Controls (IAM, VPC-SC, GCP Billing):** Select AI has no native `vertexai` provider today; call Vertex AI from Oracle via `DBMS_VECTOR` (`provider: "vertexai"`), Oracle APEX 26.1 `APEX_AI.GENERATE` (`google/gemini-3.8-flash` on `/endpoints/openapi` or an app gateway), Cloud Run functions (`DBMS_CLOUD_FUNCTION` + `GCP$PA`), or your application tier (`google-genai`).
- **Right code card (`sql`):**

  ```sql
  BEGIN
    DBMS_CLOUD.CREATE_CREDENTIAL(
      credential_name => 'GEMINI_CRED',
      username        => 'GOOGLE',
      password        => '<gemini-api-key>');
    DBMS_CLOUD_AI.CREATE_PROFILE(
      profile_name => 'COFFEE_GEMINI',
      attributes   => '{"provider": "google",
                        "credential_name": "GEMINI_CRED",
                        "model": "gemini-3.5-flash",
                        "object_list": [{"owner": "APP"}]}');
  END;
  /
  EXEC DBMS_CLOUD_AI.SET_PROFILE('COFFEE_GEMINI');
  SELECT AI showsql which stores have Ethiopian beans in stock;
  ```

- **Source line:** `docs.oracle.com/en/cloud/paas/autonomous-database/serverless/adbsb/select-ai-manage-profiles.html`
- **Notes:** Be precise here because enterprise teams always ask about IAM and VPC Service Controls: `DBMS_CLOUD_AI` is an Autonomous AI Database package whose `google` provider calls `generativelanguage.googleapis.com` with an API key (absent from base `gvenzl/oracle-free`). When you require Vertex AI governance from inside Oracle, use `DBMS_VECTOR` (`vertexai` provider, backup B11), `DBMS_CLOUD_FUNCTION` (`GCP$PA`, backup B12), or Oracle APEX 26.1.5 `APEX_AI.GENERATE` (`COFFEE_VERTEX_AI`, pre-bundled in `container-registry.oracle.com/database/adb-free:latest-26ai` and used by `src/apex/cymbal-coffee-ops/` App ID `100` via `tools/oracle/apex_vertex.py`).
  BRIDGE: Next, let's clarify how Oracle 26ai separates the SGA Vector Memory Pool, the In-Memory column store, and embedding caches.
- **Sources:** NorCal 24; [verified facts](verified-facts.md); `tools/oracle/apex_vertex.py`, `src/apex/README.md`

### 24. Vector Pool, In-Memory, and Embedding Cache

- **Target:** `dba_s26`
- **Title:** Vector Pool, In-Memory, and Embedding Cache
- **Subtitle:** Distinct SGA memory areas plus an in-database cache table for repeat queries
- **Cards:**
  - **SGA Vector Memory Pool (`vector_memory_size`):** Stores HNSW `INMEMORY NEIGHBOR GRAPH` indexes (`V$VECTOR_MEMORY_POOL` `1MB` and `64KB` pools; raises `ORA-51962` if undersized; size with `DBMS_VECTOR.INDEX_VECTOR_MEMORY_ADVISOR`).
  - **Database In-Memory Column Store (`inmemory_size`):** Separate SGA pool (`V$IM_SEGMENTS`); `INMEMORY PRIORITY HIGH` populates scalar filter columns (`in_stock`, `category`, `price`) alongside HNSW and is a safe no-op when `inmemory_size = 0`.
  - **Table-Backed `embedding_cache`:** Stores unique `(text_hash, model)` keys mapped to `VECTOR(3072, FLOAT32)` (`INMEMORY PRIORITY HIGH`, `hit_count`) so repeat prompts skip external Vertex AI RPCs.
- **Notes:** DBAs routinely ask whether HNSW consumes `inmemory_size`—it does not. HNSW lives in `vector_memory_size` (`V$VECTOR_MEMORY_POOL`, managed automatically on Autonomous AI Database Free or set to a `512M` minimum inside `gvenzl/oracle-free`'s ~1.5 GB SGA cap in `tools/oracle/on_init/00_configure_vector_memory.sql`), while `INMEMORY PRIORITY HIGH` accelerates scalar predicates in `V$IM_SEGMENTS` and `embedding_cache` (`embedding_cache_uk` in `src/app/db/migrations/0001_cymball_coffee_products.sql` and `src/app/db/sql/system.sql`) eliminates redundant embedding calls.
  BRIDGE: Before we switch to Cymbal Coffee, here is one DBA-native table you can build with these exact primitives: runbook memory.
- **Sources:** [verified facts](verified-facts.md); `tools/oracle/on_init/00_configure_vector_memory.sql`, `src/app/db/sql/system.sql`

### 25. Runbook Memory in a VECTOR Column

- **Target:** `dba_s27`
- **Title:** Runbook Memory in a VECTOR Column
- **Subtitle:** Index resolved `ORA-` postmortems and RAC runbooks directly inside Oracle 26ai
- **Left card (`Semantic DBA Knowledge Base`):**
  - Store incident postmortems, `ORA-` symptoms, and verified remediation steps in a `dba_runbook` table with `VECTOR(3072, FLOAT32)` and `CTXSYS.CONTEXT`
  - Publish a read-only `search_runbooks` query in `tools.yaml` so `agy` retrieves past fixes by symptom meaning and exact error code
  - Keeps operational memory inside Oracle under Data Guard, RMAN backup, and Unified Auditing controls
- **Right code card (`sql`):**

  ```sql
  CREATE TABLE dba_runbook (
      id         NUMBER GENERATED BY DEFAULT ON NULL AS IDENTITY PRIMARY KEY,
      ora_code   VARCHAR2(32),
      title      VARCHAR2(255) NOT NULL,
      resolution CLOB          NOT NULL,
      embedding  VECTOR(3072, FLOAT32)
  );

  SELECT ora_code, title,
         ROUND(1 - VECTOR_DISTANCE(embedding, :symptom_vec, COSINE), 4) AS score
  FROM dba_runbook
  ORDER BY VECTOR_DISTANCE(embedding, :symptom_vec, COSINE)
  FETCH APPROX FIRST 3 ROWS ONLY;
  ```

- **Notes:** Storing team runbooks in a `VECTOR(3072, FLOAT32)` column lets `agy` match *"GC buffer busy waits spiking on sequence inserts"* to a past scalable-sequence remediation (`SCALE EXTEND`) without standing up a separate vector database. The exact same table, HNSW index, and hybrid SQL pattern powers customer-facing applications.
  BRIDGE: Let's put every piece together in a working reference application: Cymbal Coffee.
- **Sources:** [verified facts](verified-facts.md)
