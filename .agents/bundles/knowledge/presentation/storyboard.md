---
type: Guide
title: Storyboard — Oracle in the Age of Gemini (2026)
description: Slide order, target slides in the deck, structural steps, and slide conventions for the 36-slide talk plus backups
tags:
  - presentation
  - storyboard
  - slides
---

# Storyboard — Oracle in the Age of Gemini (2026)

The target deck started as a Drive copy of the Postgres Summit US 2026 deck,
so its slide and element objectIds match that deck. "Target" names the
existing slide to rewrite (keeping its objectId), or says which slide to
duplicate. Source labels (NorCal, Chicago, Webinar, AI World) refer to earlier
versions of this talk; the slide-by-slide source map is in the local overlay.

## Slide conventions

- **Title:** one line, 48 characters or fewer, existing title box (18 pt bold on content slides).
- **Subtitle:** one line under the title stating what the slide proves.
- **Badge:** the small pill at the top right names the part or topic (for example `Part 1 · Tools`).
- **Cards:** keep the existing card geometry and palette of the target slide. Light cards use dark text; dark code cards use the code palette from the skill.
- **Code:** dark code card, Roboto Mono, highlighted with `manage.py slides highlight`. Use the exact SQL from the repo where one exists.
- **Banner:** the full-width strip at the bottom starts with a bold lead-in (`Takeaway:`, `Tip:`, `Why 60?`) and stays under about 118 characters.
- **Notes:** three to six sentences in the speaker's voice, ending with a `BRIDGE:` line (except slides 35 and 36).

## Shown slides

| # | Title | Target | Action |
| :--- | :--- | :--- | :--- |
| 1 | Oracle in the Age of Gemini | `g3f6b77ebb7f_5_0` | rewrite |
| 2 | About the Speaker | `slide_about_me_v4` | rewrite |
| 3 | Today's Path: Extend, Improve, Build | `g3f6b77ebb7f_5_8` | rewrite |
| 4 | Who Is Querying Oracle Now? | `g3f6b77ebb7f_5_23` | rewrite |
| 5 | Oracle Database@Google Cloud Today | `g3f6b77ebb7f_5_36` | rewrite |
| 6 | Why Run Oracle on Google Cloud | `slide_converged_arch_v4` | rewrite |
| 7 | Where Gemini Meets Your Oracle Data | `h4eca8d59b73cbebf_3_122` | rewrite |
| 8 | Part 1 · Extend Your Workflow | `slide_1790707646253493082_268` | rewrite, move |
| 9 | Agents and MCP, for DBAs | `slide_1790707646253180850_170` | rewrite |
| 10 | Connecting Oracle to Agents with MCP | `slide_1790707646253253250_197` | rewrite |
| 11 | Antigravity: An Agent in Your Terminal | `slide_1790707646253288048_210` | rewrite, unskip, move |
| 12 | Set Up Oracle MCP and Give It Context | `slide_1790707646253388335_231` | rewrite |
| 13 | Select AI: Ask Oracle in Plain English | `slide_1790707646253004939_120` | rewrite, unskip, move |
| 14 | Gemini and Vertex AI from Inside Oracle | `slide_1790707646252679909_11` | rewrite |
| 15 | Part 2 · Be a Better DBA | `part2_divider` | new |
| 16 | DBA Work Worth Handing to an Agent | `slide_sql_quality_v4` | rewrite |
| 17 | A Second Opinion on a Bad Plan | `slide_agy_walkthrough_27` | rewrite |
| 18 | AWR Summaries and Access Audits | `slide_1790707646252815842_54` | rewrite |
| 19 | Teach Agents Your Schema | `slide_1790707646253576389_302` | rewrite |
| 20 | From Annotations to Knowledge Catalog | `slide_kc_arch_35` | rewrite |
| 21 | Guardrails for Database Agents | `slide_1790707646253090322_138` | rewrite |
| 22 | Oracle AI Database Agent in Gemini Enterprise | `slide_1790707646253149569_158` | rewrite |
| 23 | Part 3 · Build Real Apps | `part3_divider` | new |
| 24 | Cymbal Coffee: How the App Fits Together | `h3b66c3a7511ce890_1_1` | rewrite, unskip, move |
| 25 | Embeddings with Vertex AI, in Oracle | `slide_1790707646252788246_44` | rewrite |
| 26 | Vector Search and the Optimizer Rule | `slide_scann_action_13` | rewrite |
| 27 | Exact Words Still Matter: Oracle Text | `slide_1790707646252711299_21` | rewrite |
| 28 | Vectors Can't Tell What the User Wants | `slide_1790707646252896716_80` | rewrite |
| 29 | Merging Two Rankings with RRF | `slide_1790707646252924686_90` | rewrite |
| 30 | One SQL Turn: Route, Products, Stores | `slide_hybrid_breakdown_21` | rewrite |
| 31 | Catching Off-Menu Brands Without an LLM | `slide_1790707646252980978_110` | rewrite |
| 32 | Grounded Answers vs. Open-Ended Agents | `slide_ai_studio_adk_v4` | rewrite |
| 33 | Share Your Queries with Other Agents | `slide_adk_indb_tools_v4` | rewrite |
| 34 | Day-2 Rules for AI Workloads on Oracle | `slide_1790707646253468658_258` | rewrite |
| 35 | Recap and Where to Start | `slide_1790707646253602272_312` | rewrite |
| 36 | Thank You | `slide_ux_survey_38` | keep (update the survey link if the event provides one) |

## Backup slides (after slide 36, skipped)

| # | Title | Target | Action |
| :--- | :--- | :--- | :--- |
| B1 | AI Search Terms for Oracle DBAs | `slide_1790707646252622210_0` | rewrite, move, skip |
| B2 | Hybrid Search in Three CTEs | `slide_1790707646252951731_100` | rewrite, move, skip |
| B3 | Oracle AI Database 26ai: What Matters | `slide_1790707646253525778_280` | rewrite, move, skip |
| B4 | Why Agents Need Schema Context | `slide_kc_why_34` | rewrite, move, skip |
| B5 | Knowledge Catalog in Action | `slide_kc_action_36` | rewrite, move, skip |
| B6 | HNSW vs. IVF and Vector Memory Sizing | `slide_1790707646252745998_31` | rewrite, keep skipped |
| B7 | Term Hits and Score Cliffs in SQL | `slide_1790707646253117540_148` | rewrite, keep skipped |
| B8 | SQLSpec and python-oracledb Patterns | `slide_1790707646253357135_220` | rewrite, keep skipped |
| B9 | Bulk Embedding with SKIP LOCKED Queues | `slide_1790707646253435033_246` | rewrite, keep skipped |
| B10 | Property Graphs (SQL/PGQ) in Oracle 26ai | `slide_1790707646253553449_292` | rewrite, keep skipped |
| B11 | Vertex AI from PL/SQL with DBMS_VECTOR | `backup_b11` | new, skip |
| B12 | Cloud Run Functions as SQL Functions | `backup_b12` | new, skip |
| B13 | Regions, Purchasing, and Support | `backup_b13` | new, skip |
| B14 | Vertex AI Platform and Model Garden | `backup_b14` | new, skip |
| B15 | System Prompts and Personas | `backup_b15` | new, skip |
| B16 | It's Still All SQL: Vectors + Inventory | `backup_b16` | new, skip |
| B17 | Demo Clips | `backup_b17` | new, skip |

## Structural steps (task 1.1)

Do these before any text changes, re-dumping the deck after each group:

1. Duplicate slide 8's source (`slide_1790707646253493082_268`) twice for slides 15 and 23, passing an explicit `objectIds` map so later requests can target the copies.
2. Duplicate the layout slides listed for B11–B17 the same way, after their source slides have been rewritten (so the copies inherit the new layout text), or duplicate now and rewrite later; record the new objectIds in the task notes.
3. Reorder with one `updateSlidesPosition` request per slide, in final order, using the target column above.
4. Unskip slides 11, 13, and 24; skip every backup; confirm with `manage.py slides inventory` that slides 1–36 are shown and B1–B17 follow slide 36, skipped.
