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

### 9. Agents and MCP, for DBAs

- **Target:** `slide_1790707646253180850_170` (layered stack layout)
- **Badge:** Part 1 · Tools
- **Subtitle:** A model, a set of tools, and the right context
- **Layers (top to bottom):**
  - **Model:** Gemini on Vertex AI decides the next step.
  - **Tools:** MCP servers are the only things the agent can actually run.
  - **Context:** rules, skills, and schema notes tell it how your shop works.
  - **Database:** the same users, roles, and auditing you already enforce.
- **Side note:** why specialized agents: gated data access, a clear role, curated context, and less to read on every turn. MCP is one standard way to connect tools: write the server once and use it from any client.
- **Banner:** **Takeaway:** an agent can only do what its tools and its database user allow.
- **Notes:** MCP is like a driver standard for AI tools. You don't build a connector per model; you run one server per data source and every compatible client can use it.
  BRIDGE: Here are the MCP servers for Oracle.
- **Sources:** NorCal 17–20

### 10. Connecting Oracle to Agents with MCP

- **Target:** `slide_1790707646253253250_197`
- **Badge:** Part 1 · MCP
- **Subtitle:** Local SQL, prebuilt DBA tools, and managed database operations
- **Cards:**
  - **SQLcl MCP:** `sql -mcp`. Oracle's own server; runs SQL as the connected user over local stdio.
  - **MCP Toolbox for Databases:** `toolbox --prebuilt oracledb --stdio`. Prebuilt tools such as `execute_sql`, `list_tables`, `get_query_plan`, `list_active_sessions`, `list_top_sql_by_resource`, `list_tablespace_usage`, and `list_invalid_objects`.
  - **Oracle Database@Google Cloud remote MCP:** `https://oracledatabase.googleapis.com/mcp`. Authenticates with IAM (`roles/mcp.toolUser`); manages Autonomous databases rather than running SQL.
- **Banner:** **Tip:** give every server an app-scoped database user; never `SYS` or `SYSTEM`.
- **QR:** MCP Toolbox repository
- **Notes:** Confirm the Toolbox tool names and the remote server's tool list against current docs before the event (task 1.6). The point for DBAs: you choose the tool surface, and a curated tool list is safer than raw `execute_sql`.
  BRIDGE: The client that ties these together is Antigravity.
- **Sources:** NorCal 21; Chicago 16; `docs/mcp-antigravity.md`

### 11. Antigravity: An Agent in Your Terminal

- **Target:** `slide_1790707646253288048_210` (unskip, move to position 11)
- **Badge:** Part 1 · Tools
- **Subtitle:** The `agy` CLI and the Antigravity 2.0 IDE
- **Left card — What DBAs use it for:** coding and scripting, research, task automation, debugging, database analysis, custom workflows.
- **Right card — How you shape it:** rules, skills, and workflows checked into the repo; MCP servers in `mcp_config.json`; packaged extensions such as an Oracle Database extension (confirm the install path under Antigravity).
- **Banner:** **2026 update:** standalone Gemini CLI reached end of life in June 2026; Antigravity is the successor.
- **Notes:** Earlier versions of this talk demoed Gemini CLI. Everything shown there works in Antigravity, and the configuration lives in the same home-directory files.
  BRIDGE: Setting it up for Oracle takes a few minutes.
- **Sources:** NorCal 27–28, 32–33; AI World 11–14

### 12. Set Up Oracle MCP and Give It Context

- **Target:** `slide_1790707646253388335_231`
- **Badge:** Part 1 · Setup
- **Subtitle:** One config file and a few habits
- **Left code card (JSON):**

  ```json
  {
    "mcpServers": {
      "sqlcl": { "command": "/opt/sqlcl/bin/sql", "args": ["-mcp"] },
      "oracle-toolbox": {
        "command": "/usr/local/bin/toolbox",
        "args": ["--prebuilt", "oracledb", "--stdio"],
        "env": {
          "ORACLE_CONNECTION_STRING": "localhost:1521/FREEPDB1",
          "ORACLE_USERNAME": "app",
          "ORACLE_PASSWORD": "<set locally>"
        }
      }
    }
  }
  ```

- **Right card — Give it context:** be specific; point at files and links; say what done looks like; keep rules and skills in the repo; iterate.
- **Banner:** **Tip:** the file lives in `~/.gemini/antigravity/mcp_config.json`; keep passwords out of the repo.
- **QR:** `docs/mcp-antigravity.md` in the repository
- **Notes:** Use absolute executable paths, because desktop apps start without your shell's `PATH`. The repo's `manage.py install mcp-toolbox` command installs the Toolbox binary.
  BRIDGE: Now, Gemini inside SQL itself.
- **Sources:** NorCal 29; `docs/mcp-antigravity.md`

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
