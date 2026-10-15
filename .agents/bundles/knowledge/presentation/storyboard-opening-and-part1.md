---
type: Guide
title: Storyboard — Opening and Part 1 (slides 1–14)
description: Slide-by-slide content, code, banners, and speaker notes for the opening and the "Extend your workflow" part
tags:
  - presentation
  - storyboard
---

# Storyboard — Opening and Part 1 (slides 1–14)

Targets refer to objectIds in the deck (see [storyboard](storyboard.md)).
Facts and sources are in [verified facts](verified-facts.md).

## Opening

### 1. Oracle in the Age of Gemini

- **Target:** `g3f6b77ebb7f_5_0` (title box `g3f6b77ebb7f_5_2`, subtitle `g3f6b77ebb7f_5_4`, speaker line `textbox_1790706618594082759_6`)
- **Title:** Oracle in the Age of Gemini
- **Subtitle:** How DBAs use Vertex AI to work smarter and build real apps
- **Speaker line:** Cody Fincher · Database Black Belts, Google Cloud
- **Notes:** This talk is for people who run Oracle for a living. We start with the tools you already use, move to the DBA work agents can take off your plate, and finish with a real application built on Oracle AI Database 26ai and Vertex AI. Everything I show is in a public repository you can run on a laptop or on Google Cloud.
  BRIDGE: First, who I am and where to find the code.
- **Sources:** NorCal 1

### 2. About the Speaker

- **Target:** `slide_about_me_v4`
- **Content:** Database Black Belts, Google Cloud. LinkedIn `linkedin.com/in/cofin`; GitHub `github.com/cofin` and `github.com/litestar-org` (Litestar and SQLSpec maintainer). Keep the existing photo and QR layout.
- **Notes:** Short. Mention that the demo app is built on open-source Python libraries I maintain, which is why the SQL in this talk is real SQL rather than an ORM.
  BRIDGE: Here's the path we'll take today.
- **Sources:** NorCal 2

### 3. Today's Path: Extend, Improve, Build

- **Target:** `g3f6b77ebb7f_5_8`
- **Badge:** Agenda
- **Subtitle:** Gemini in your tools, then your DBA work, then your apps
- **Cards:**
  - **Extend your workflow:** put Gemini in the terminal, the IDE, and SQL itself with Antigravity, MCP, and Select AI.
  - **Be a better DBA:** hand agents plan reviews, AWR summaries, access audits, and schema notes. You approve every change.
  - **Build real apps:** Cymbal Coffee answers questions with one Oracle query for exact words, meaning, and routing, and uses Gemini only to phrase the answer.
- **Banner:** **Runs on:** Oracle AI Database 26ai · Oracle Database@Google Cloud · Vertex AI
- **Notes:** The order matters. Most DBAs meet AI through their own tools first, then trust it with routine work, and only then build applications on it. Each part ends with something you can try next week.
  BRIDGE: Before the tools, let's look at who is querying your database now.
- **Sources:** NorCal 3 (agenda rewritten into three parts)

### 4. Who Is Querying Oracle Now?

- **Target:** `g3f6b77ebb7f_5_23`
- **Badge:** Why now
- **Subtitle:** Assistants and agents read operational data
- **Left card — Apps:** look things up by key; predictable plans; steady concurrency; answers come from the app's own logic.
- **Right card — Assistants and agents:** ask by meaning ("something bold but low acid"); run several tool calls per question, in bursts; need current rows (stock, orders, store hours); every answer has to be grounded in data you can audit.
- **Banner:** **Takeaway:** the data stays in Oracle; the question is how AI reaches it safely.
- **Notes:** None of this replaces the database. It adds a new kind of client that asks fuzzier questions, more often, and expects fresh answers. That client is what the rest of the talk designs for.
  BRIDGE: Where does Oracle run on Google Cloud today?
- **Sources:** NorCal 4–5

### 5. Oracle Database@Google Cloud Today

- **Target:** `g3f6b77ebb7f_5_36`
- **Badge:** Oracle on Google Cloud
- **Subtitle:** Oracle-managed databases inside Google Cloud data centers
- **Left card — Services:** Exadata Database Service on dedicated infrastructure; Exadata Database Service on Exascale Infrastructure; Autonomous AI Database (serverless); Base Database Service; GoldenGate.
- **Right card — Deployment choices:** Oracle Database@Google Cloud (Oracle runs the database, Google runs the data center, network, and physical security); OCI and Google Cross-Cloud Interconnect for existing OCI estates; self-managed Oracle on Compute Engine or GKE.
- **Banner:** **Source:** docs.cloud.google.com/oracle/database/docs/overview
- **Notes:** This is the same Oracle software and Exadata hardware, provided by Oracle, sitting in Google data centers next to your applications. You pick the service level you want, from co-managed Exadata to fully managed Autonomous.
  BRIDGE: Why would a DBA team choose to run it here?
- **Sources:** NorCal 8–9; AI World 6

### 6. Why Run Oracle on Google Cloud

- **Target:** `slide_converged_arch_v4`
- **Badge:** Oracle on Google Cloud
- **Subtitle:** The same Oracle, next to Google's data and AI services
- **Cards:**
  - **Operate:** provision from the Google Cloud console, gcloud, or Terraform; run apps on Compute Engine or GKE next to the database; one monitoring view for apps and databases.
  - **Secure:** databases are reachable only from your VPC network, inside Google's security perimeter.
  - **Buy and support:** purchase through Google Cloud Marketplace (eligible for commitment drawdown); bring existing licenses and keep Oracle Support Rewards; Oracle and Google support work cases together.
- **Banner:** **Takeaway:** BigQuery, Looker, and Vertex AI are a network hop away, not a migration away.
- **Notes:** Use the notes from the Webinar version for common reasons customers move: resilience, low latency between transactions and analytics, a data-center exit without refactoring, and AI on operational data. Do not state a region count here; it lives on backup B13 after checking the public locations page.
  BRIDGE: Here's every place Gemini can touch your Oracle data.
- **Sources:** AI World 5, 8, 9; Webinar 6–7 (notes)

### 7. Where Gemini Meets Your Oracle Data

- **Target:** `h4eca8d59b73cbebf_3_122`
- **Badge:** Map of the talk
- **Subtitle:** Four places Gemini meets Oracle; this talk walks through each
- **Diagram or cards:**
  - **Your tools:** Antigravity with MCP servers for SQLcl, MCP Toolbox, and Oracle Database@Google Cloud (Part 1).
  - **Your SQL:** Select AI with Gemini; `DBMS_VECTOR` calling Vertex AI (Part 1).
  - **Your DBA work:** plan reviews, AWR summaries, access audits, annotations, Knowledge Catalog (Part 2).
  - **Your apps and users:** Cymbal Coffee with Vertex AI embeddings and Gemini; Gemini Enterprise with the Oracle AI Database Agent (Parts 2 and 3).
- **Banner:** **Takeaway:** start where you already work, then carry the same patterns into your applications.
- **Notes:** Use this slide as the map and come back to it at each part divider.
  BRIDGE: Part 1 starts with the tools you already use.
- **Sources:** new; AI World 2 as visual reference

## Part 1 · Extend your workflow

### 8. Part 1 · Extend Your Workflow

- **Target:** `slide_1790707646253493082_268` (move to position 8)
- **Subtitle:** Gemini in the terminal, the IDE, and SQL
- **Notes:** Three tools in this part: an agent in your terminal and IDE, the MCP servers that connect it to Oracle, and Select AI inside the database.
  BRIDGE: First, what an agent is, in DBA terms.
- **Sources:** NorCal 26

### 6. AI Terms for DBAs: LLMs, MCP, and A2A (`dba_s06`)

- **Target:** `dba_s06` (`T_TOOLBOX`)
- **Title:** AI Terms for DBAs: LLMs, MCP, and A2A
- **Left card (`Familiar Protocol Analogies`):**
  - **LLM (`Gemini`):** The reasoning engine—summarizes tuning & RMAN reports, plans, and wait events.
  - **MCP (Agent-to-Tool ≈ `WSDL` / `JDBC`):** Publishes typed, read-only SQL tool schemas so agents call vetted queries.
  - **A2A (Agent-to-Agent ≈ `REST` / `gRPC`):** Lets an app or peer agent delegate database tasks to an Oracle specialist agent.
  - **Two-Way Partnership:** Agent speeds up `GV$` synthesis; you supply RAC rules, context & approval.
- **Notes:** Ground the three AI terms in protocols every DBA already knows: LLM (`Gemini`), MCP (`WSDL`/`JDBC` contract for tools), and A2A (`REST`/`gRPC` between specialist agents).
  BRIDGE: Now let's look at the client that drives both your IDE and CLI: Antigravity.

### 7. Antigravity: IDE + CLI Together (`dba_s08`)

- **Target:** `dba_s08` (`T_LAPTOP` with composite IDE + CLI image on `dba_s08_e06`)
- **Title:** Antigravity: IDE + CLI Together
- **Left card (`One Agent Across Both Surfaces`):**
  - **Antigravity IDE:** Edit SQL & PL/SQL, review inline diffs, inspect `DBMS_XPLAN`, and approve MCP calls visually.
  - **Antigravity CLI (`agy`):** Pipe `sql -s` output into `agy -p` from SSH bastions, cron jobs, and shell scripts.
  - **Shared Config:** Both read `~/.gemini/config/mcp_config.json` and `.agents/` rules.
  - **Docs:** `antigravity.google/docs/mcp`
- **Notes:** Antigravity gives DBAs both a full agentic IDE and the `agy` terminal CLI backed by the same MCP config and team rules.
  BRIDGE: Where can you leverage these MCP tools against your Oracle estate today?

### 8. Where You Can Leverage These Tools Today (`dba_s07`)

- **Target:** `dba_s07` (`T_ICONS_3`)
- **Title:** Where You Can Leverage These Tools Today
- **Subtitle:** Three Oracle MCP Options Across Local, Team, and Cloud Workflows
- **Cards:**
  - **1. Interactive SQLcl (`sql -mcp`):** Run `sql -mcp` (SQLcl 25.2+) with saved wallets for ad-hoc IDE/CLI triage; logs every query in `DBTOOLS$MCP_LOG`.
  - **2. Team Allowlist (`MCP Toolbox`):** Run `toolbox --stdio` with 7 prebuilt Oracle checks (`--prebuilt oracledb`) or a shared `tools.yaml` allowlist of read-only SQL.
  - **3. Managed Cloud MCP (`Preview`):** `oracledatabase.googleapis.com/mcp` (`Preview`: Exadata, Exascale, ADB, BaseDB & GoldenGate) + `dataplex.googleapis.com/mcp` (`Preview`).
- **Notes:** Walk through the three Oracle MCP options and clarify both what `tools.yaml` is and that `oracledatabase.googleapis.com/mcp` (in Preview) covers Exadata, Exascale, BaseDB, Autonomous DB, ODB Networks, and GoldenGate.
  BRIDGE: Let's look at the two toolkit files you configure: first `mcp_config.json`, then `tools.yaml`.

### 9. Connect Antigravity to Oracle@GCP (`dba_s09`)

- **Target:** `dba_s09` (`T_SCULPTURE`)
- **Title:** Connect Antigravity to Oracle@GCP
- **Left card (`Wallet + 26ai Read-Only User`):**
  - Config file: `~/.gemini/config/mcp_config.json`
  - Connect over TCPS with `ORACLE_WALLET`
  - Use a 26ai `READ ONLY` user (`CREATE USER mcp_diag_ro ... READ ONLY`)—ignores higher grants and only allows reads
  - Never connect as `SYSDBA`
- **Right code card (JSON):**

  ```json
  {
    "mcpServers": {
      "sqlcl-exadata": {
        "command": "/opt/sqlcl/bin/sql",
        "args": ["-mcp"]
      },
      "oracle-toolbox": {
        "command": "/usr/local/bin/toolbox",
        "args": ["--tools-file", "dba-tools.yaml", "--stdio"],
        "env": {
          "ORACLE_CONNECTION_STRING": "exadb-scan:2484/prd_tp",
          "ORACLE_WALLET": "/etc/oracle/wallets/exadb_prd",
          "ORACLE_USERNAME": "MCP_DIAG_RO",
          "ORACLE_PASSWORD": "${ORACLE_DIAG_PASSWORD}"
        }
      }
    }
  }
  ```

- **Notes:** Highlight Oracle 26ai `READ ONLY` user accounts (`CREATE USER mcp_diag_ro ... READ ONLY` / `ALTER USER mcp_diag_ro READ ONLY`), which enforce read-only access at the account level (`ORA-28194`) even if higher grants exist.
  BRIDGE: Next, let's look at what goes inside `dba-tools.yaml`.

### 10. A Curated, Read-Only DBA tools.yaml (`dba_s10`)

- **Target:** `dba_s10` (`T_CORAL`)
- **Title:** A Curated, Read-Only DBA tools.yaml
- **Left card (`Why Custom Tools Beat Raw SQL`):**
  - Open `execute_sql` allows arbitrary queries
  - `tools.yaml` is a YAML allowlist of DBA-vetted `SELECT` statements
  - Bakes in RAC-aware `GV$` views and `:1` binds
  - Shared in Git across the entire DBA team
- **Right code card (YAML + embedded Oracle SQL):**
  - Highlighted with composite YAML + Oracle SQL syntax highlighting via `tools/slides/highlight.py`.
- **Notes:** Every tool in `tools.yaml` is a parameterized, read-only `SELECT` statement that DBAs have already tested and tuned.
  BRIDGE: Connectivity and tools are only half the story—why is Context Management critical for DBAs?

### 11. Why Context Management Is Critical for DBAs (`dba_s11`)

- **Target:** `dba_s11` (`T_GRADIENT_3`)
- **Title:** Why Context Management Is Critical for DBAs
- **Subtitle:** Tools give database access—context prevents `V$` mistakes on RAC, license issues, and bad joins
- **Cards:**
  - **1. Guardrail Rules (`AGENTS.md`):** Always-on team standards: read-only access, query `GV$` instead of `V$` on RAC, respect pack licenses, and never run DDL/DML.
  - **2. Runbook Skills (`SKILL.md`):** On-demand playbooks loaded only when needed: SQL Tuning Advisor triage, RMAN backup checks, and patch pre-checks.
  - **3. Schema & Fleet Metadata:** In-database 26ai `ANNOTATIONS` and Knowledge Catalog so the agent knows table business rules and join keys first.
- **Notes:** Explain why connectivity + tools alone aren't enough and how layering `AGENTS.md`, `SKILL.md`, and 26ai `ANNOTATIONS` + Knowledge Catalog prevents `V$` mistakes on RAC, license issues, and bad joins.
  BRIDGE: Let's walk through two visual DBA use cases to see these tools and playbooks in action.

### 13. Select AI: Ask Oracle in Plain English

- **Target:** `slide_1790707646253004939_120` (unskip, move to position 13)
- **Badge:** Part 1 · SQL
- **Subtitle:** Natural language to SQL in Autonomous AI Database, with Gemini
- **Left card — How it works:** a profile names the AI provider, the model, and the tables Select AI may describe. For SQL generation it sends schema metadata, including comments and annotations, not row data; `narrate` sends query results. Actions: `showsql`, `runsql`, `explainsql`, `narrate`, `chat`, plus summarize, translate, and synthetic data.
- **Right code card:**

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

- **Banner:** **Note:** Select AI's Google provider uses a Gemini API key. Need Vertex AI controls? Next slide.
- **Notes:** The credential holds an API key from Google AI Studio, and the database user needs a network ACL for `generativelanguage.googleapis.com`. The model list comes from Oracle's documentation; check it before the event. `APP` is the demo schema owner (the default `DATABASE_USER`).
  BRIDGE: Many enterprises need Vertex AI specifically, so here are the options.
- **Sources:** NorCal 24; verified facts, Select AI

### 14. Gemini and Vertex AI from Inside Oracle

- **Target:** `slide_1790707646252679909_11` (decision-matrix layout)
- **Badge:** Part 1 · Options
- **Subtitle:** What works today, and which paths stay inside Vertex AI
- **Matrix (four columns: Path · Calls · Auth · Status):**

  | Path | Calls | Auth | Status |
  | :--- | :--- | :--- | :--- |
  | Select AI, provider `google` | Gemini API | API key | Documented |
  | Select AI, provider `oci` | Gemini on OCI Generative AI | OCI credentials | Documented |
  | `DBMS_VECTOR`, provider `vertexai` | Vertex AI: embeddings, text, rerank | Access token, rotated | Documented |
  | Cloud Run function from SQL | Vertex AI via the function's service account | Database's Google service account (`GCP$PA`) | Documented building blocks |
  | Application tier (`google-genai`) | Vertex AI | Service account | What Cymbal Coffee does |
  | Select AI calling Vertex AI directly | — | — | Not available today |

- **Banner:** **Takeaway:** need Vertex AI controls (IAM, VPC-SC, GCP billing)? Use `PL/SQL`, Cloud Run, or your app.
- **Notes:** Be precise here; this question comes up with every enterprise audience. Backups B11 and B12 have the SQL for the `DBMS_VECTOR` and Cloud Run function paths.
  BRIDGE: That's the toolbox. Part 2 is about using it to be a better DBA.
- **Sources:** verified facts, Select AI and Vertex AI
