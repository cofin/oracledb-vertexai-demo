---
type: Guide
title: Storyboard — Oracle in the Age of Gemini (2026)
description: Slide order, archetype mapping, and slide conventions for the 57-slide DBA talk (28 DBA-first core slides, 12 hideable Cymbal Coffee walkthrough slides, Thank You, and 16 unskipped Reference slides)
tags:
  - presentation
  - storyboard
  - slides
---

# Storyboard — Oracle in the Age of Gemini (2026)

The deck is built from the **Oracle AI World 2026 Consolidated Google Cloud slides** template (Cloudstyle 2.0) and ordered **DBA-first** for senior Oracle DBAs (such as Exadata and Autonomous AI Database teams on Oracle Database@Google Cloud):

1. **Opening (`dba_s01`–`dba_s04`)**: Title, Speaker, Where Gemini Meets Your Oracle Estate, Oracle Database@Google Cloud Services.
2. **Antigravity for DBAs (`dba_s05`–`dba_s11`)**: Agents and MCP in DBA Terms, Three Oracle MCP Servers Compared, Antigravity (`agy` CLI + IDE), Connect Antigravity to Oracle@GCP (`mcp_config.json`), Curated Read-Only `tools.yaml`, Rules and Skills (`.agents/AGENTS.md` + `.agents/skills/`).
3. **DBA Use Cases (`dba_s12`–`dba_s22`)**: Vector Query Full-Scan Diagnosis (`DBMS_XPLAN`), Piping a SQLcl Invalid-Object Health Check into `agy -p ... 2>/dev/null`, Detect-to-Approve Workflow, Hot Index Blocks on Insert-Heavy RAC Tables (`SCALE EXTEND`), Long Open Transactions and GoldenGate Lag (`GV$TRANSACTION`), Exadata Smart Scan Offload Health (`V$SYSSTAT`), Access Audits and Dormant Accounts, 26ai Schema `ANNOTATIONS`, Fleet Context with Google Cloud Knowledge Catalog, and Guardrails for Database Agents.
4. **Gemini Inside Oracle AI Database 26ai (`dba_s23`–`dba_s27`)**: Select AI (`DBMS_CLOUD_AI`) on Autonomous AI DB, Reaching Vertex AI from Oracle (`DBMS_VECTOR.UTL_TO_EMBEDDING`), In-Memory Column Store vs SGA Vector Pool vs `embedding_cache`, and Runbook Memory in a `VECTOR` Column.
5. **Actionable Close (`dba_s28`)**: Where to Start on Monday (3 QR codes: MCP Toolbox for Oracle, Google Cloud Knowledge Catalog MCP, and the 26ai Demo Repo).
6. **Build Real Apps — Cymbal Coffee (`dba_s29`–`dba_s40`)**: Self-contained, hideable 12-slide application walkthrough at the end of the talk so DBA-only sessions can skip or condense it without losing the Monday recap.
7. **Thank You (`dba_s41`) & Reference (`dba_s42`–`dba_s57`)**: 16 unskipped deep-dive reference slides grouped after a dedicated `Reference` section divider.

## Slide conventions

- **Title:** one line, 48 characters or fewer, 24 pt Google Sans bold.
- **No per-slide badges, `"Part N"` labels, or bottom status banners:** let the section divider slides (`dba_s05`, `dba_s12`, `dba_s23`, `dba_s29`, `dba_s42`) carry the structure and keep slide copy scannable with detail in speaker notes.
- **No repository file names or paths on slides:** write SQL and configuration examples for public DBA consumption without referencing internal repo paths (`hybrid.sql`, `migration 0001`, `src/app/...`, `SLIDES.md`).
- **Cards:** left-aligned (`alignment: START`) rectangle cards with inset text boxes (`8 pt` horizontal padding) and zero raw markdown backticks (`Roboto Mono` styling on inline SQL/CLI identifiers).
- **Code:** dark code cards (`#161B22`), Roboto Mono (`7.5 pt`–`8.5 pt`), highlighted with `manage.py slides highlight`.
- **Notes:** three to six sentences in the speaker's voice, ending with a `BRIDGE:` line on slides `1`–`40`.

## Slide inventory (`dba_s01`–`dba_s57`)

| # | Object ID | Section | Title |
| :--- | :--- | :--- | :--- |
| 1 | `dba_s01` | Opening | Oracle in the Age of Gemini |
| 2 | `dba_s02` | Opening | About the Speaker |
| 3 | `dba_s03` | Opening | Where Gemini Meets Your Oracle Estate |
| 4 | `dba_s04` | Opening | Oracle Database@Google Cloud Services |
| 5 | `dba_s05` | Antigravity for DBAs | Antigravity for DBAs |
| 6 | `dba_s06` | Antigravity for DBAs | Agents and MCP in DBA Terms |
| 7 | `dba_s07` | Antigravity for DBAs | Three Oracle MCP Servers Compared |
| 8 | `dba_s08` | Antigravity for DBAs | Antigravity: What DBAs Use It For |
| 9 | `dba_s09` | Antigravity for DBAs | Connect Antigravity to Oracle@GCP |
| 10 | `dba_s10` | Antigravity for DBAs | A Curated, Read-Only DBA tools.yaml |
| 11 | `dba_s11` | Antigravity for DBAs | Give the Agent Context: Rules and Skills |
| 12 | `dba_s12` | DBA Use Cases | DBA Use Cases |
| 13 | `dba_s13` | DBA Use Cases | Why Is This Vector Query Doing a Full Scan? |
| 14 | `dba_s14` | DBA Use Cases | Pipe a SQLcl Health Check Into Antigravity |
| 15 | `dba_s15` | DBA Use Cases | Act on the Outcome: Detect to Approve |
| 16 | `dba_s16` | DBA Use Cases | Hot Index Blocks on Insert-Heavy RAC Tables |
| 17 | `dba_s17` | DBA Use Cases | Long Open Transactions and Replication Lag |
| 18 | `dba_s18` | DBA Use Cases | Is Exadata Smart Scan Still Offloading? |
| 19 | `dba_s19` | DBA Use Cases | Access Audits and Dormant Accounts |
| 20 | `dba_s20` | DBA Use Cases | Teach Agents Your Schema: 26ai ANNOTATIONS |
| 21 | `dba_s21` | DBA Use Cases | Fleet Context: Google Cloud Knowledge Catalog |
| 22 | `dba_s22` | DBA Use Cases | Guardrails for Database Agents |
| 23 | `dba_s23` | Gemini Inside 26ai | Gemini Inside Oracle AI Database 26ai |
| 24 | `dba_s24` | Gemini Inside 26ai | Select AI with Gemini on Autonomous AI DB |
| 25 | `dba_s25` | Gemini Inside 26ai | Reaching Vertex AI From Oracle |
| 26 | `dba_s26` | Gemini Inside 26ai | In-Memory, Vector Pool, and Embedding Cache |
| 27 | `dba_s27` | Gemini Inside 26ai | Runbook Memory in a VECTOR Column |
| 28 | `dba_s28` | Close | Where to Start on Monday |
| 29 | `dba_s29` | Build Real Apps (Hideable) | Build Real Apps: Cymbal Coffee |
| 30 | `dba_s30` | Build Real Apps (Hideable) | Cymbal Coffee Reference Architecture |
| 31 | `dba_s31` | Build Real Apps (Hideable) | Dense Embeddings in Oracle 26ai |
| 32 | `dba_s32` | Build Real Apps (Hideable) | HNSW Vector Index and Optimizer Rule |
| 33 | `dba_s33` | Build Real Apps (Hideable) | Lexical Ranking with CTXSYS.CONTEXT |
| 34 | `dba_s34` | Build Real Apps (Hideable) | Route Intent in SQL, Not a Second LLM Call |
| 35 | `dba_s35` | Build Real Apps (Hideable) | Reciprocal Rank Fusion (k = 60) in Plain SQL |
| 36 | `dba_s36` | Build Real Apps (Hideable) | One SQL Turn: Routes, Products, and Stores |
| 37 | `dba_s37` | Build Real Apps (Hideable) | Catching Off-Menu Brands with JSON_TABLE |
| 38 | `dba_s38` | Build Real Apps (Hideable) | Grounded SQL Replies vs Open-Ended Turns |
| 39 | `dba_s39` | Build Real Apps (Hideable) | Expose Validated Queries Over /mcp and /a2a |
| 40 | `dba_s40` | Build Real Apps (Hideable) | Day-2 Operational Rules for Oracle AI Apps |
| 41 | `dba_s41` | Thank You | Thank you |
| 42 | `dba_s42` | Reference | Reference |
| 43 | `dba_s43` | Reference | Reference: AI Search Terms for Oracle DBAs |
| 44 | `dba_s44` | Reference | Reference: Sizing vector_memory_size |
| 45 | `dba_s45` | Reference | Reference: HNSW vs IVF on RAC and Exadata |
| 46 | `dba_s46` | Reference | Reference: Plain-SQL RRF vs Hybrid Index |
| 47 | `dba_s47` | Reference | Reference: In-DB Embeddings with DBMS_VECTOR |
| 48 | `dba_s48` | Reference | Reference: Select AI Profile Attributes |
| 49 | `dba_s49` | Reference | Reference: Select AI Generation Modes |
| 50 | `dba_s50` | Reference | Reference: Keyless Google Auth (GCP$PA) |
| 51 | `dba_s51` | Reference | Reference: Oracle AI DB Agent in Marketplace |
| 52 | `dba_s52` | Reference | Reference: Exadata Service vs Autonomous DB |
| 53 | `dba_s53` | Reference | Reference: Pinning Plans with DBMS_SPM |
| 54 | `dba_s54` | Reference | Reference: Global Index Cleanup (DBMS_PART) |
| 55 | `dba_s55` | Reference | Reference: Alert Log Triage in SQL |
| 56 | `dba_s56` | Reference | Reference: Escaping Input for CTXSYS.CONTEXT |
| 57 | `dba_s57` | Reference | Reference: Queue Polling with SKIP LOCKED |
