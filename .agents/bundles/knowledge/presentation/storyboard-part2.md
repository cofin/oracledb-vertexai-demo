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

### 17. A Second Opinion on a Bad Plan

- **Target:** `slide_agy_walkthrough_27` (walkthrough layout)
- **Badge:** Part 2 · Walkthrough
- **Subtitle:** A real case from this app: a vector query that skipped its index
- **Left card — What the agent does:**
  1. You ask Antigravity why product search got slow.
  2. It pulls the plan through MCP (`get_query_plan`, or `DBMS_XPLAN.DISPLAY_CURSOR` through SQLcl) and sees a full scan of `PRODUCT` with no vector index access.
  3. It explains that ordering by `1 - VECTOR_DISTANCE(...)` with `FETCH FIRST` cannot use the HNSW index.
  4. It proposes the rewrite and an `EXPLAIN PLAN` check; you review and apply it.
- **Right code card:**

  ```sql
  -- Before: exact scan of every row
  SELECT id, 1 - VECTOR_DISTANCE(embedding, :q, COSINE) AS similarity
  FROM product
  ORDER BY similarity DESC
  FETCH FIRST 5 ROWS ONLY;

  -- After: uses the HNSW vector index
  SELECT id
  FROM product
  ORDER BY VECTOR_DISTANCE(embedding, :q, COSINE)
  FETCH APPROX FIRST 5 ROWS ONLY;
  ```

- **Banner:** **Check it yourself:** `EXPLAIN PLAN` + `DBMS_XPLAN.DISPLAY` should show a vector index scan, not a full table scan.
- **Notes:** This exact bug existed in an earlier version of Cymbal Coffee. Play the recorded clip if available. The lesson for DBAs: an agent with plan access catches the same mistakes you would, and explains them in your terms.
  BRIDGE: The same pattern works for routine health checks.
- **Sources:** NorCal 34; repo history (`vector-search-products` rewrite)

### 18. AWR Summaries and Access Audits

- **Target:** `slide_1790707646252815842_54` (two columns with a code card)
- **Badge:** Part 2 · Health checks
- **Subtitle:** Scheduled checks that land as a short summary
- **Left card — AWR-lite:** on a schedule, the agent runs top-SQL, session, and tablespace checks (`list_top_sql_by_resource`, `list_active_sessions`, `list_tablespace_usage`), and Gemini writes a five-line summary to a team channel. Anything unusual becomes a ticket for a person. AWR and ASH data need the Diagnostics Pack license.
- **Right code card:**

  ```sql
  -- Accounts nobody has used in 90 days
  SELECT username, account_status, last_login
  FROM dba_users
  WHERE oracle_maintained = 'N'
    AND (last_login IS NULL
         OR last_login < SYSTIMESTAMP - INTERVAL '90' DAY)
  ORDER BY last_login NULLS FIRST;
  ```

- **Banner:** **Takeaway:** the agent drafts the lock or revoke script; a DBA reads it and runs it.
- **Notes:** Mention that the agent's own account needs `SELECT` on the views it reads and nothing more. A good prompt for the audit: "List dormant accounts and the roles they still hold; draft a lock script; do not run it."
  BRIDGE: Agents do better work when your schema explains itself.
- **Sources:** NorCal 34

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
