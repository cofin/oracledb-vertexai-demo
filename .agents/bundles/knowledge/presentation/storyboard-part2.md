---
type: Guide
title: Storyboard — Part 2 (slides 15–22)
description: Slide-by-slide content, code, banners, and speaker notes for the "Be a better DBA" part
tags:
  - presentation
  - storyboard
---

# Storyboard — Part 2: Be a Better DBA (slides 15–22)

### 15. Part 2 · Be a Better DBA

- **Target:** duplicate of `slide_1790707646253493082_268` (new objectId recorded in task 1.1 notes)
- **Subtitle:** Let agents do the legwork; you approve the changes
- **Notes:** Agents are good at gathering, comparing, and summarizing. They are not the ones who should run DDL in production. This part is about getting the first benefit without giving up the second rule.
  BRIDGE: Here's the DBA work worth handing off first.
- **Sources:** new

### 16. DBA Work Worth Handing to an Agent

- **Target:** `slide_sql_quality_v4` (two cards plus banner)
- **Badge:** Part 2 · DBA work
- **Subtitle:** Repetitive, read-heavy, and easy to review
- **Left card — Good first jobs:**
  - **Plan second opinion:** feed it `DBMS_XPLAN` output; get an explanation and a fix script to review.
  - **AWR-lite summaries:** scheduled checks summarized and posted to a channel.
  - **Access audits:** dormant accounts and excess privileges, with a draft revoke script.
  - **Schema notes:** draft `COMMENT ON` and `ANNOTATIONS` from code and sample data.
- **Right card — Keep it safe:** read-only database user first; the agent proposes and a DBA runs any DDL or DML; log every statement the agent runs; start with one schema.
- **Banner:** **Takeaway:** agents gather and summarize; change approval stays with the DBA.
- **Notes:** These come from the DBA ideas in earlier versions of the talk. Each one replaces twenty minutes of copying output between windows with a two-minute review.
  BRIDGE: Let's start with a bad plan.
- **Sources:** NorCal 34; Webinar 25

### 17. Use Case 1: Regressed SQL & Tuning Advisor (`dba_s13`)

- **Target:** `dba_s13` (`T_SCULPTURE` 3-part visual layout)
- **Left card — From Alert to Simple Action:**
  1. **Ask `agy`:** `"Find today's slowest SQL and summarize SQL Tuning Advisor."`
  2. **Save as a Tool:** Add `find_slow_sql` and `tuning_report` to `tools.yaml`.
  3. **Fast Assessment:** Turns a 3-page tuning report into a 1-line fix.
- **Top-right code card:**

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
- **Notes:** In Use Case 1, checkout latency spikes and you ask Antigravity to check the top SQL and summarize SQL Tuning Advisor. Instead of reading three pages of `DBMS_SQLTUNE` text output, `agy` highlights the exact root cause—stale partition statistics—and gives you a single `DBMS_STATS` command to review and run. You save those two `SELECT` statements into `tools.yaml` so the whole team can run the check anytime.
  BRIDGE: Let's look at Use Case 2: RMAN backup and patch readiness analysis.

### 18. Use Case 2: RMAN Backup & Readiness Analyzer (`dba_s19`)

- **Target:** `dba_s19` (`T_FLAME` 3-part visual layout)
- **Left card — Turn Questions Into Queries:**
  1. **Ask in Plain English:** `"Check RMAN backups for the last 7 days and flag warnings."`
  2. **Convert to SQL:** `agy` writes the `V$RMAN_BACKUP_JOB_DETAILS` query for `tools.yaml`.
  3. **Instant Triage:** Pinpoints the one job that hit a recovery area warning.
- **Top-right code card:**

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
- **Notes:** In Use Case 2, you ask Antigravity a plain-English operational question: check our RMAN backups from the last seven days before a patch window. Antigravity writes a clean query against `V$RMAN_BACKUP_JOB_DETAILS` that you can save as a SQLcl script or MCP tool, summarizes the 14 jobs in three lines, and flags that last night's archivelog job warned on Fast Recovery Area space.
  BRIDGE: Once you have a saved SQL check, you can also pipe it straight into the agy CLI.

### 19. Teach Agents Your Schema

- **Target:** `slide_1790707646253576389_302`
- **Badge:** Part 2 · Schema notes
- **Subtitle:** `COMMENT ON` and 26ai `ANNOTATIONS`: notes you should be writing anyway
- **Left card — Why it matters:** column names don't carry units, business rules, or privacy rules. Select AI and MCP tools read comments and annotations when they write SQL. An agent can draft them from your code and sample data; you review them like any DDL.
- **Right code card (from migration `0001`):**

  ```sql
  embedding VECTOR(3072, FLOAT32)
      ANNOTATIONS (
          Display 'Product embedding',
          Embedding_Model 'gemini-embedding-2',
          Distance 'COSINE'
      ),

  COMMENT ON COLUMN store_product_inventory.stock_status IS
    'Inventory status enum: IN_STOCK, LOW_STOCK, or OUT_OF_STOCK';

  SELECT object_name, column_name, annotation_name, annotation_value
  FROM user_annotations_usage
  WHERE object_name = 'PRODUCT';
  ```

- **Banner:** **Tip:** ask the agent to draft annotations for one schema, then review them in a pull request.
- **Notes:** Cymbal Coffee's tables carry annotations such as `Data_Role`, `Privacy`, and `AI_Surface`. They are queryable metadata, so the same notes serve people, Select AI, and agents.
  BRIDGE: Those notes can also feed an enterprise catalog.
- **Sources:** NorCal 24; `src/app/db/migrations/0001_cymball_coffee_products.sql`

### 20. From Annotations to Knowledge Catalog

- **Target:** `slide_kc_arch_35`
- **Badge:** Part 2 · Catalog
- **Subtitle:** Schema notes become context any agent can look up
- **Flow (left to right):**
  1. **Oracle AI Database 26ai:** `COMMENT ON` and `USER_ANNOTATIONS_USAGE`.
  2. **Repository knowledge:** the OKF v0.2 bundle under `.agents/bundles/`.
  3. **Knowledge Catalog:** entries with schema, overview, guidelines, and verified queries.
  4. **Agent:** looks up context (`search_entries`, `lookup_context`) before writing SQL.
- **Banner:** **Note:** Knowledge Catalog's managed MCP server exposes `search_entries`, `lookup_context`, and `lookup_entry`.
- **Notes:** In this repo the catalog sync is a planned spec (`knowledge-catalog-grounding-demo`). Present this as the architecture; only show a live result once the sync exists. Backups B4 and B5 hold the longer version.
  BRIDGE: None of this matters without guardrails.
- **Sources:** repo spec `knowledge-catalog-grounding-demo`

### 21. Guardrails for Database Agents

- **Target:** `slide_1790707646253090322_138`
- **Badge:** Part 2 · Guardrails
- **Subtitle:** The rules you apply to people, written down for agents
- **Cards:**
  - **Identity:** app-scoped database users, never `SYS` or `SYSTEM`; IAM for managed MCP servers (`roles/mcp.toolUser`).
  - **Scope:** read-only first; a curated tool list instead of open `execute_sql`; one schema at a time.
  - **Review:** the agent proposes DDL and DML, a DBA applies it; audit what agents run.
  - **Data:** no secrets in prompts or repositories; keep personal data out of logs (Cymbal Coffee never stores browser coordinates).
- **Banner:** **Takeaway:** least privilege still works; agents just make it more important.
- **Notes:** Unified Auditing already gives you the trail. Treat the agent like a new contractor: a named account, narrow grants, and a reviewer.
  BRIDGE: Business users can get answers too, without new pipelines.
- **Sources:** new; `SLIDES.md` slide 8 (location privacy)

### 22. Oracle AI Database Agent in Gemini Enterprise

- **Target:** `slide_1790707646253149569_158` (card plus QR layout)
- **Badge:** Part 2 · Agents today
- **Subtitle:** Plain-English questions in Gemini Enterprise, answered by Autonomous AI Database
- **Card:**
  - **What it is:** an agent from Google Cloud Marketplace that connects Gemini Enterprise to Select AI agent teams in your database over the A2A protocol.
  - **Setup:** an admin adds it in Gemini Enterprise, enters the database's OAuth client ID and secret, and grants users access.
  - **Security:** answers follow the signed-in user's database permissions.
  - **Requirement:** Autonomous AI Database on Oracle AI Database@Google Cloud.
- **Banner:** **For DBAs:** fewer ad hoc report requests; you own the agent team and its permissions.
- **QR:** Oracle documentation page "Use Oracle AI Database Agent with Google Gemini Enterprise Application"
- **Notes:** This is the no-code path. If the audience has Gemini Enterprise, this is the fastest way to let business users ask questions of Oracle data under the same security model.
  BRIDGE: Part 3 is for when you need your own app.
- **Sources:** verified facts, Oracle AI Database Agent
