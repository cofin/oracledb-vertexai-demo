---
type: Guide
title: Storyboard — Opening and Antigravity & Context for DBAs (slides 1–13)
description: Slide-by-slide content, code, takeaways, and speaker notes for the Opening and Antigravity & Context for DBAs sections (slides 1–13)
tags:
  - presentation
  - storyboard
---

# Storyboard — Opening and Antigravity & Context for DBAs (slides 1–13)

Targets refer to objectIds in the 34-slide active deck (see [storyboard](storyboard.md)).
Facts and sources are in [verified facts](verified-facts.md).

## Opening

### 1. Oracle in the Age of Gemini

- **Target:** `dba_s01`
- **Title:** Oracle in the Age of Gemini
- **Subtitle:** Practical AI Agents, MCP Workflows, and Vector Search for Oracle DBAs
- **Speaker line:** Cody Fincher · Database Black Belts, Google Cloud
- **Notes:** This talk is for people who run Oracle for a living. We start with the terminal and IDE tools you already use, move to routine diagnostic and readiness work agents can summarize for your review, and finish with a real application built on Oracle AI Database 26ai, Oracle APEX 26.1, and Vertex AI. Everything shown today lives in a public repository you can run locally or on Google Cloud.
  BRIDGE: First, who I am and where to find the code.
- **Sources:** NorCal 1

### 2. About the Speaker

- **Target:** `dba_s02`
- **Title:** About the Speaker
- **Content:** Database Black Belts, Google Cloud. LinkedIn `linkedin.com/in/cofin`; GitHub `github.com/cofin` and `github.com/litestar-org` (Litestar and SQLSpec maintainer). Keep the existing photo and contact layout.
- **Notes:** Keep this brief. Mention maintaining Litestar and SQLSpec, which is why every database example in this talk is explicit, explainable Oracle SQL with `:bind` parameters rather than hidden ORM queries.
  BRIDGE: Here is where Gemini meets your Oracle estate across tools, operations, and applications.
- **Sources:** NorCal 2

### 3. Where Gemini Meets Your Oracle Estate

- **Target:** `dba_s03` (`T_ICONS_3`)
- **Title:** Where Gemini Meets Your Oracle Estate
- **Subtitle:** Tools in your terminal and IDE, diagnostics and in-database SQL, and operational apps
- **Cards:**
  - **Your DBA toolchain:** connect Antigravity (`agy` CLI and IDE) to Oracle schemas with SQLcl MCP, MCP Toolbox, and managed Google Cloud MCP endpoints.
  - **Your diagnostics and SQL:** summarize `DBMS_XPLAN`, SQL Tuning Advisor, and RMAN checks; ground schemas with `ANNOTATIONS` and Knowledge Catalog; call Gemini from Autonomous AI Database or PL/SQL.
  - **Your applications:** combine `VECTOR(3072, FLOAT32)` HNSW indexes and `CTXSYS.CONTEXT` in one Hybrid RRF SQL turn, with Gemini phrasing grounded answers.
- **Notes:** Most DBAs adopt AI in this exact progression: first inside their own workstation tools, next for read-only diagnostic triage and schema documentation where a DBA still approves every change, and finally inside operational applications. Every section ends with a concrete pattern you can test on a development schema next week.
  BRIDGE: Let's ground where those Oracle databases run on Google Cloud today.
- **Sources:** NorCal 3; AI World 2

### 4. Oracle Database@Google Cloud Services

- **Target:** `dba_s04`
- **Title:** Oracle Database@Google Cloud Services
- **Subtitle:** Oracle-managed databases running inside Google Cloud data centers
- **Left card — Services:** Exadata Database Service on dedicated infrastructure; Exadata Database Service on Exascale Infrastructure; Autonomous AI Database Service; Base Database Service; GoldenGate.
- **Right card — Operating model:** Oracle runs the database hardware and software inside Google Cloud data centers on your VPC network, one network hop from Vertex AI, BigQuery, and Cloud Run; purchase through Google Cloud Marketplace with BYOL and collaborative support, or connect existing OCI estates over Cross-Cloud Interconnect.
- **Source line:** `docs.cloud.google.com/oracle/database/docs/overview`
- **Notes:** This is the same Oracle software and Exadata hardware managed by Oracle, deployed inside Google Cloud data centers next to your applications and Vertex AI endpoints. You choose co-managed Exadata, Exascale, Base Database, or serverless Autonomous AI Database. Check the live public locations page before quoting a region count on stage; backup B13 covers regional availability, Marketplace purchasing, and collaborative support.
  BRIDGE: Let's open with Antigravity and MCP workflows built specifically for Oracle DBAs.
- **Sources:** NorCal 8–9; AI World 5–9; [verified facts](verified-facts.md)

## Antigravity & Context for DBAs

### 5. Antigravity for DBAs

- **Target:** `dba_s05` (section divider)
- **Title:** Antigravity for DBAs
- **Subtitle:** Core AI concepts, MCP servers, and schema context in your terminal and IDE
- **Notes:** Standalone Gemini CLI reached end of life in June 2026, and Antigravity—both the `agy` CLI and the Antigravity 2.0 IDE—is the unified successor. In this section we translate core agent terms into Oracle concepts, wire read-only MCP tools, and layer schema context so the agent writes RAC-safe SQL.
  BRIDGE: First, let's map four core AI terms to protocols every DBA already knows.
- **Sources:** NorCal 26; [verified facts](verified-facts.md)

### 6. Core AI Terms: LLMs, Context, MCP, and A2A

- **Target:** `dba_s06` (`T_TOOLBOX`)
- **Title:** Core AI Terms: LLMs, Context, MCP, and A2A
- **Left card (`Familiar DBA Analogies`):**
  - **LLM (`Gemini`) & Harness (`Antigravity`):** Gemini is the reasoning engine; Antigravity (`agy` CLI + IDE) is the harness managing files, context, and tool approvals.
  - **Context & Embeddings (`≈ GPS Coordinates`):** Context is the active window of rules and schema metadata; embeddings map meaning to `VECTOR(3072, FLOAT32)` coordinates for cosine distance lookup.
  - **MCP (`≈ REST / SOAP for Tools`):** Publishes typed, read-only SQL tool schemas so agents invoke DBA-vetted queries instead of guessing.
  - **A2A (`≈ REST / SOAP With an Agent`):** Lets an application or peer agent delegate tasks to a specialist database agent.
- **Notes:** Ground these terms in interfaces DBAs already trust: Gemini is the reasoning model, Antigravity is the client harness, embeddings behave like high-dimensional GPS coordinates stored in a `VECTOR` column, MCP is a typed `JDBC` or `WSDL` contract for tools, and A2A is `REST` between specialist agents. The agent accelerates synthesis across `GV$` views while the DBA supplies operational rules and change approval.
  BRIDGE: Now let's look at practical DBA workflows inside Google Antigravity across the CLI and IDE.
- **Sources:** NorCal 27–30; [verified facts](verified-facts.md)

### 7. Developing with Google Antigravity: DBA Ideas

- **Target:** `dba_s08` (`T_LAPTOP` with composite IDE + CLI capture and `dba_pipe_demo.gif`)
- **Title:** Developing with Google Antigravity: DBA Ideas
- **Left card (`CLI + IDE Workflows & Practical Ideas`):**
  - **IDE + CLI (`agy`) & Subagents:** Review inline SQL/PLSQL diffs and `DBMS_XPLAN` visually in the IDE, pipe `sql -s` into `agy -p` over SSH, and fan out read-only subagents.
  - **Automatic Annotation Generation:** Draft Oracle 26ai `ANNOTATIONS` and `COMMENT ON` DDL from schema DDL and sample rows for DBA review.
  - **AWR-Lite & SQL Plan Second Opinion:** Summarize `V$SQL` and `V$SYSSTAT` snapshots (respecting Diagnostics Pack licensing) and turn `DBMS_XPLAN` output into reviewable fix scripts.
  - **User Access Audit:** Flag dormant accounts (`DBA_USERS.LAST_LOGIN`) and excess grants, producing a draft revoke script.
- **Source line:** `antigravity.google/docs/mcp`
- **Notes:** Antigravity gives DBAs one agent across both surfaces: a full IDE for reviewing PL/SQL diffs and execution plans, and the `agy` CLI for piping non-interactive SQLcl output from jump hosts or cron scripts. Both share workspace MCP configs in `.agents/mcp_config.json` alongside global configs in `~/.gemini/config/mcp_config.json` (IDE) and `~/.gemini/antigravity-cli/mcp_config.json` (`agy` CLI).
  BRIDGE: Where can you connect Antigravity to your Oracle databases today?
- **Sources:** NorCal 33–34; [verified facts](verified-facts.md); `docs/mcp-antigravity.md`, `tools/lib/utils.py`

### 8. Where You Can Leverage These Tools Today

- **Target:** `dba_s07` (`T_ICONS_3`)
- **Title:** Where You Can Leverage These Tools Today
- **Subtitle:** Oracle MCP options across local wallets, team allowlists, and Google Cloud
- **Cards:**
  - **Interactive SQLcl (`sql -mcp`):** Run `sql -mcp` (SQLcl 25.2+) with saved wallets for ad-hoc IDE and CLI triage; records every agent query in `DBTOOLS$MCP_LOG` and tags `V$SESSION.MODULE` and `ACTION`.
  - **Team Allowlist (`MCP Toolbox`):** Run `toolbox --prebuilt oracledb --stdio` (7 prebuilt checks) or a shared `tools.yaml` allowlist configured in `.agents/mcp_config.json`, `~/.gemini/config/mcp_config.json`, or `~/.gemini/antigravity-cli/mcp_config.json`.
  - **Managed Cloud MCP (`Preview`):** `oracledatabase.googleapis.com/mcp` (`Preview`: 21 control-plane tools across Exadata, Exascale, ADB, BaseDB, ODB Networks, and GoldenGate) plus `dataplex.googleapis.com/mcp` (`Preview`).
- **Notes:** Walk through the three Oracle MCP surfaces and their config targets (`.agents/mcp_config.json` for workspace templates, `~/.gemini/config/mcp_config.json` for global IDE, and `~/.gemini/antigravity-cli/mcp_config.json` for global `agy` CLI, implemented in `tools/lib/utils.py`). Pair wallet-backed TCPS connections with an Oracle 26ai account-level `READ ONLY` user (`CREATE USER mcp_diag_ro ... READ ONLY`, enforced with `ORA-28194`) and never connect agents as `SYS` or `SYSTEM`.
  BRIDGE: Let's look inside `tools.yaml` to see why a DBA-curated tool file beats open `execute_sql`.
- **Sources:** [verified facts](verified-facts.md); `docs/mcp-antigravity.md`, `tools/lib/utils.py`

### 9. A Curated, Read-Only DBA tools.yaml

- **Target:** `dba_s10` (`T_CORAL`)
- **Title:** A Curated, Read-Only DBA tools.yaml
- **Subtitle:** Your Queries. Your knowledge.
- **Left card (`Why Custom Tools Beat Raw SQL`):**
  - Open `execute_sql` permits arbitrary ad-hoc queries
  - `tools.yaml` (`kind: source` / `type: oracle` + `kind: tool` / `type: oracle-sql`) publishes DBA-vetted `SELECT` statements
  - Bakes in RAC-aware `GV$` joins (`s.inst_id = t.inst_id`) and positional `:1` binds
  - Shared in Git across the entire DBA team
- **Right code card (`yaml`):**

  ```yaml
  kind: source
  name: oracle-prod-ro
  type: oracle
  tnsAlias: prd_tp
  tnsAdmin: /etc/oracle/wallets/exadb_prd
  user: ${ORACLE_USERNAME}
  password: ${ORACLE_PASSWORD}
  ---
  kind: tool
  name: list_long_transactions
  type: oracle-sql
  source: oracle-prod-ro
  description: Active transactions running longer than N minutes across RAC.
  statement: |
    SELECT s.inst_id, s.sid, s.serial#, s.username, s.sql_id,
           ROUND((SYSDATE - t.start_date) * 1440, 1) AS active_min
    FROM gv$transaction t
    JOIN gv$session s
      ON s.saddr = t.ses_addr AND s.inst_id = t.inst_id
    WHERE t.start_date < SYSDATE - NUMTODSINTERVAL(:1, 'MINUTE')
    ORDER BY t.start_date
  parameters:
    - name: min_minutes
      type: integer
      description: Minimum transaction age in minutes.
  ```

- **Notes:** Highlight the subtitle—*Your Queries. Your knowledge.*—because every entry in `tools.yaml` encodes a `SELECT` statement your senior DBAs have already tuned and verified across RAC (`s.saddr = t.ses_addr AND s.inst_id = t.inst_id` against `GV$TRANSACTION.START_DATE`), keeping credentials in environment placeholders. Format the dark code card with `tools/slides/highlight.py` (`--language yaml`).
  BRIDGE: Connectivity and curated tools are half the equation; next is why context management matters just as much.
- **Sources:** [verified facts](verified-facts.md)

### 10. Context Matters: Higher Accuracy, Fewer Tokens

- **Target:** `h33f425bc278cd40f_26_0`
- **Title:** Context Matters: Higher Accuracy, Fewer Tokens
- **Subtitle:** Focused schema and operational rules outperform dumping raw dictionary views
- **Left card — Without curated context:** the agent burns turns probing `ALL_TAB_COLUMNS`, misses RAC `INST_ID` predicates, guesses status enums, or touches Diagnostics Pack views on unlicensed databases.
- **Right card — With layered context:** concise team rules, on-demand runbook skills, and table/column annotations steer the first query to the right tables, join keys, and business constraints in a fraction of the tokens.
- **Notes:** Giving an agent a database connection without context is like handing a new contractor SQLcl access without your runbooks or data model notes. Curated context cuts exploratory dictionary queries, reduces token latency, and prevents wrong joins on the first turn.
  BRIDGE: Let's break down the specific context layers that protect an Oracle DBA team.
- **Sources:** NorCal 31–32

### 11. Why Context Management Is Critical for DBAs

- **Target:** `dba_s11` (`T_GRADIENT_3`)
- **Title:** Why Context Management Is Critical for DBAs
- **Subtitle:** Tools give database access; context prevents `V$` mistakes on RAC, license issues, and bad joins
- **Cards:**
  - **Guardrail Rules (`AGENTS.md`):** Always-on team standards: read-only access, query `GV$` instead of `V$` on RAC, respect Diagnostics Pack licenses, and never run DDL or DML.
  - **Runbook Skills (`SKILL.md`):** On-demand playbooks loaded only when needed: SQL Tuning Advisor triage, RMAN backup checks, and patch pre-checks.
  - **Schema & Fleet Metadata:** In-database Oracle 26ai `ANNOTATIONS` and Google Cloud Knowledge Catalog so agents read business rules and join keys before writing SQL.
- **Notes:** Explain how these layers divide responsibility cleanly: `AGENTS.md` holds short, non-negotiable rules loaded on every session, `SKILL.md` holds deep diagnostic playbooks loaded only when relevant so they do not bloat the context window, and `ANNOTATIONS` plus Knowledge Catalog keep schema semantics next to the data.
  BRIDGE: Let's look at how Oracle 26ai `ANNOTATIONS` store that schema context directly inside the data dictionary.
- **Sources:** [verified facts](verified-facts.md)

### 12. In-Database Context: Oracle 26ai ANNOTATIONS

- **Target:** `dba_s20`
- **Title:** In-Database Context: Oracle 26ai ANNOTATIONS
- **Subtitle:** Store units, privacy rules, and AI hints beside the columns they describe
- **Left card — Why it matters:** column names alone do not convey stock precedence, embedding dimensions, or coordinate privacy rules. Select AI, SQLcl MCP, and catalog harvesters read `COMMENT ON` and `USER_ANNOTATIONS_USAGE` directly from Oracle.
- **Right code card (`sql`):**

  ```sql
  embedding VECTOR(3072, FLOAT32)
      ANNOTATIONS (
          Display 'Product embedding',
          Embedding_Model 'gemini-embedding-2',
          Embedding_Dimensions '3072',
          Embedding_Purpose 'document',
          Distance 'COSINE'
      ),

  COMMENT ON COLUMN store_product_inventory.stock_status IS
    'Inventory status enum: IN_STOCK, LOW_STOCK, or OUT_OF_STOCK';

  SELECT object_name, column_name, annotation_name, annotation_value
  FROM user_annotations_usage
  WHERE object_name = 'PRODUCT';
  ```

- **Notes:** Unlike external wiki pages that drift out of date, Oracle 26ai `ANNOTATIONS` live in DDL and are queryable through `USER_ANNOTATIONS_USAGE`. In this repository (`src/app/db/migrations/0001_cymball_coffee_products.sql`), tables and columns declare `Display`, `Data_Role`, `Privacy`, `Embedding_Model`, and `AI_Surface` annotations—and an agent can draft them for existing schemas while DBAs review the DDL in a pull request.
  BRIDGE: Those in-database annotations also scale across an entire fleet through Google Cloud Knowledge Catalog.
- **Sources:** NorCal 24; `src/app/db/migrations/0001_cymball_coffee_products.sql`; [verified facts](verified-facts.md)

### 13. Fleet Context: Google Cloud Knowledge Catalog

- **Target:** `dba_s21`
- **Title:** Fleet Context: Google Cloud Knowledge Catalog
- **Subtitle:** Turn schema annotations into governed context across your Oracle estate
- **Flow (left to right):**
  1. **Oracle AI Database 26ai:** `COMMENT ON` and `USER_ANNOTATIONS_USAGE` harvested via the managed Oracle metadata connector (`Preview`, Private Service Connect + `SELECT_CATALOG_ROLE`).
  2. **Open Knowledge Format (`OKF v0.2`):** version-controlled domain glossaries, join guidelines, and verified SQL patterns.
  3. **Knowledge Catalog:** governed entries combining technical schema metadata with business rules.
  4. **Managed Remote MCP (`dataplex.googleapis.com/mcp`):** agents call `search_entries`, `lookup_context`, and `lookup_entry` before writing SQL.
- **Source line:** `docs.cloud.google.com/knowledge-catalog/docs/use-remote-mcp`
- **Notes:** Knowledge Catalog (formerly Dataplex Universal Catalog) imports Oracle metadata on a schedule via its managed connector (`Preview` since 2026-06-22) and serves governed context to agents over `https://dataplex.googleapis.com/mcp`. In this repository, automated OKF v0.2 catalog harvesting is tracked as a planned roadmap spec (`.agents/bundles/specs/knowledge-catalog-grounding-demo/spec.md`), so present this slide as the fleet architecture; backups B4 and B5 cover the deeper walkthrough.
  BRIDGE: Now that the tools and context are wired up, let's see what DBAs can build and automate with them.
- **Sources:** [verified facts](verified-facts.md); `.agents/bundles/specs/knowledge-catalog-grounding-demo/spec.md`
