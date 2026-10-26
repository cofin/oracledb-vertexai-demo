---
type: Guide
title: Storyboard — Oracle in the Age of Gemini (2026)
description: Slide order, archetype mapping, and slide conventions for the 34-slide DBA talk (Opening, Antigravity & Context for DBAs, The Art of the Possible DBA Use Cases, Gemini Inside 26ai, Cymbal Coffee Reference App, Monday Recap, and Thank You)
tags:
  - presentation
  - storyboard
  - slides
---

# Storyboard — Oracle in the Age of Gemini (2026)

The deck is built from the **Oracle AI World 2026 Consolidated Google Cloud slides** template (Cloudstyle 2.0) and ordered **DBA-first** across **34 active slides** (with all hidden/skipped reference slides purged):

1. **Opening (`dba_s01`–`dba_s04`)**: Title, Speaker, Where Gemini Meets Your Oracle Estate, Oracle Database@Google Cloud Services.
2. **Antigravity & Context for DBAs (`dba_s05`, `dba_s06`, `dba_s08`, `dba_s07`, `dba_s10`, `h33f425bc278cd40f_26_0`, `dba_s11`, `dba_s20`, `dba_s21`)**: Core AI Terms (LLMs, Harness = Antigravity, Context, Embeddings ≈ GPS Coordinates, MCP ≈ REST/SOAP for Tools, A2A ≈ REST/SOAP With an Agent), Developing with Google Antigravity: DBA Ideas (restored from NorCal Slides 33–34: CLI + IDE concepts, Agents & Subagents, Automatic Annotation Generation, AWR-Lite Diagnostics, SQL Plan "Second Opinion", User Access Audit), Where You Can Leverage These Tools Today (SQLcl MCP, MCP Toolbox, and Managed Cloud MCP in Preview), Curated Read-Only `tools.yaml` (preserving *"Your Queries. Your knowledge."*), Context Matters: Higher Accuracy, Fewer Tokens, Why Context Management Is Critical for DBAs (`AGENTS.md`, `SKILL.md`, and 26ai `ANNOTATIONS` + Knowledge Catalog), In-Database Context: Oracle 26ai `ANNOTATIONS`, and Fleet Context: Google Cloud Knowledge Catalog.
3. **The Art of the Possible: DBA Use Cases (`dba_s12`, `dba_s13`, `dba_s19`, `dba_s14`, `h33f425bc278cd40f_86_0`, `SLIDES_API285542424_0`, `dba_s22`)**: **Use Case 1: Regressed SQL & Tuning Advisor** (`GV$SQL` + `DBMS_SQLTUNE.REPORT_TUNING_TASK` $\rightarrow$ concise summary + `DBMS_STATS` action), **Use Case 2: RMAN Backup & Readiness Analyzer** (`V$RMAN_BACKUP_JOB_DETAILS` $\rightarrow$ Fast Recovery Area warning triage), **The Art of the Possible: Power Up Your Scripting** (`sql -s ... | agy -p ... 2>/dev/null`), **Turn 1: Ad-Hoc Data Analysis: Interactive MCP Queries** (`130` unique products, `129` in stock, `1` out of stock `Mirage Macchiato` from `src/app/db/fixtures/product.json.gz`), **Turn 2: Ad-Hoc Data Extracts: Vector Search to CSV** (`vector-search-products` SQL extracting top bold products `RoboRoast` `0.9444`, `Signature Bold Blend` `0.9424`, `Caffeinated Dream` `0.9360`, `Midnight Brew` `0.9337`, `Cosmic Coffee` `0.9326` to `bold_products.csv`, followed by `/exit` from `agy` and bash `ls -lh` + `head -n 6`), and Guardrails for Database Agents.
4. **Gemini Inside Oracle AI Database 26ai (`dba_s23`, `dba_s43`, `dba_s24`, `dba_s26`, `dba_s27`)**: What Are Embeddings & Vector Distance? (GPS analogy + NorCal `"espresso"` example), Select AI (`DBMS_CLOUD_AI`) on Autonomous AI DB, Vector Pool, In-Memory, and Embedding Cache, and Runbook Memory in a `VECTOR` Column.
5. **Build Real Apps — Cymbal Coffee (`dba_s29`, `dba_s38`, `dba_s30`, `dba_s31`, `dba_s32`, `dba_s34`, `dba_s35`)**: The Demo Scenario: Cymbal Coffee AI Barista, Cymbal Coffee Reference Architecture (bordered 2026 UI screenshot on `http://localhost:8000` + 300 DPI animated Dendrite diagram + bundled Oracle APEX 26.1.5 on `https://localhost:8443/ords/apex`), Step 1: Dense Embeddings in Oracle 26ai (`INMEMORY PRIORITY HIGH` explained), Step 2: HNSW Vector Index Configuration in 26ai (`vector_memory_size = 512M` minimum pool on `gvenzl/oracle-free` vs automatic pool management on `adb-free:latest-26ai`), Step 3: Route Intent in SQL (`25` `chat_route` exemplars across `5` route labels, no extra LLM call), and Step 4: It's All SQL — Hybrid RRF (`k = 60`).
6. **Close (`dba_s28`, `dba_s41`)**: Let's Recap: Where to Start on Monday (3 full-width cards) and Thank You (`dba_s41` with closing QR codes, non-overlapping title, and contact block).

## Slide conventions

- **Title:** one line, 48 characters or fewer, 22.5–23 pt Google Sans bold.
- **Full-Width 3-Card Layout (`x = 36..684 pt`, `w = 204 pt` each):** All 3-card slides (`T_FLORAL_3`, `T_ICONS_3`, `T_GRADIENT_3`, `T_GOLD_3`) use `xs = (36.0, 258.0, 480.0)`, `w = 204.0` across the full `648 pt` content width (`720 pt` slide width with symmetric `36 pt` margins), deleting all old narrow template card/icon shapes underneath.
- **No per-slide badges, `"Part N"` labels, or bottom status banners:** let the section divider slides (`dba_s05`, `dba_s12`, `dba_s23`, `dba_s29`) carry the structure and keep slide copy scannable with detail in speaker notes.
- **No repository file names or paths on slides:** write SQL and configuration examples for public DBA consumption without referencing internal repo paths (`hybrid.sql`, `migration 0001`, `src/app/`, `SLIDES.md`).
- **Cards:** left-aligned (`alignment: START`) rectangle cards with inset text boxes (`10 pt` horizontal padding) and zero raw markdown backticks (`Roboto Mono` styling on inline SQL/CLI identifiers).
- **Code:** dark code cards (`#161B22`), Roboto Mono (`7.5 pt`–`8.5 pt`), highlighted with `manage.py slides highlight`.
- **Notes:** three to six sentences in the speaker's voice, ending with a `BRIDGE:` line on slides `1`–`33`.

## Active Slide Inventory (34 Slides)

| # | Object ID | Section | Title |
| :--- | :--- | :--- | :--- |
| 1 | `dba_s01` | Opening | Oracle in the Age of Gemini |
| 2 | `dba_s02` | Opening | About the Speaker |
| 3 | `dba_s03` | Opening | Where Gemini Meets Your Oracle Estate |
| 4 | `dba_s04` | Opening | Oracle Database@Google Cloud Services |
| 5 | `dba_s05` | Antigravity & Context | Antigravity for DBAs |
| 6 | `dba_s06` | Antigravity & Context | Core AI Terms: LLMs, Context, MCP, and A2A |
| 7 | `dba_s08` | Antigravity & Context | Developing with Google Antigravity: DBA Ideas |
| 8 | `dba_s07` | Antigravity & Context | Where You Can Leverage These Tools Today |
| 9 | `dba_s10` | Antigravity & Context | A Curated, Read-Only DBA tools.yaml |
| 10 | `h33f425bc278cd40f_26_0` | Antigravity & Context | Context Matters: Higher Accuracy, Fewer Tokens |
| 11 | `dba_s11` | Antigravity & Context | Why Context Management Is Critical for DBAs |
| 12 | `dba_s20` | Antigravity & Context | In-Database Context: Oracle 26ai ANNOTATIONS |
| 13 | `dba_s21` | Antigravity & Context | Fleet Context: Google Cloud Knowledge Catalog |
| 14 | `dba_s12` | The Art of the Possible | The Art of the Possible: DBA Use Cases |
| 15 | `dba_s13` | The Art of the Possible | Use Case 1: Regressed SQL & Tuning Advisor |
| 16 | `dba_s19` | The Art of the Possible | Use Case 2: RMAN Backup & Readiness Analyzer |
| 17 | `dba_s14` | The Art of the Possible | The Art of the Possible: Power Up Your Scripting |
| 18 | `h33f425bc278cd40f_86_0` | The Art of the Possible | Ad-Hoc Data Analysis: Interactive MCP Queries |
| 19 | `SLIDES_API285542424_0` | The Art of the Possible | Ad-Hoc Data Extracts: Vector Search to CSV |
| 20 | `dba_s22` | The Art of the Possible | Guardrails for Database Agents |
| 21 | `dba_s23` | Gemini Inside 26ai | Gemini Inside Oracle AI Database 26ai |
| 22 | `dba_s43` | Gemini Inside 26ai | What Are Embeddings & Vector Distance? |
| 23 | `dba_s24` | Gemini Inside 26ai | Select AI with Gemini on Autonomous AI DB |
| 24 | `dba_s26` | Gemini Inside 26ai | Vector Pool, In-Memory, and Embedding Cache |
| 25 | `dba_s27` | Gemini Inside 26ai | Runbook Memory in a VECTOR Column |
| 26 | `dba_s29` | Build Real Apps | Build Real Apps: Cymbal Coffee |
| 27 | `dba_s38` | Build Real Apps | The Demo Scenario: Cymbal Coffee AI Barista |
| 28 | `dba_s30` | Build Real Apps | Cymbal Coffee Reference Architecture |
| 29 | `dba_s31` | Build Real Apps | Step 1: Dense Embeddings in Oracle 26ai |
| 30 | `dba_s32` | Build Real Apps | Step 2: HNSW Vector Index Configuration in 26ai |
| 31 | `dba_s34` | Build Real Apps | Step 3: Route Intent in SQL (No Extra LLM Call) |
| 32 | `dba_s35` | Build Real Apps | Step 4: It's All SQL — Hybrid RRF (k = 60) |
| 33 | `dba_s28` | Close | Let's Recap: Where to Start on Monday |
| 34 | `dba_s41` | Thank You | Thank You |
