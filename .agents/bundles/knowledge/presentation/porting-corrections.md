---
type: Guide
title: Porting Corrections — Earlier Versions of the Talk
description: Errors and outdated content in earlier decks that must be fixed when their slides are reused
tags:
  - presentation
  - corrections
---

# Porting Corrections — Earlier Versions of the Talk

Earlier versions of this talk (NorCal, Chicago, the webinar, and Oracle AI
World NYC 2026) contain content that is wrong or out of date. Fix these
whenever their slides, code images, or notes are reused.

| # | Earlier content | Problem | Use instead |
| :--- | :--- | :--- | :--- |
| 1 | `SELECT * FROM products WHERE vector_distance(embeddings, :user_embedding) < 0.8` | A distance threshold never uses the HNSW index, and there is no ordering or row limit | `ORDER BY VECTOR_DISTANCE(embedding, :q, COSINE) FETCH APPROX FIRST n ROWS ONLY` (`dba_s32`, slide 30) |
| 2 | Notes: "the closer the number is to 1, the more related the embeddings are" | `VECTOR_DISTANCE` returns a distance; 0 is identical | "Distance 0 is identical; similarity is 1 − distance" |
| 3 | "It's All SQL" join using `ST_Distance(s.location, :user_location) < 5000` | `ST_Distance` is a PostGIS function; the code also has a markdown fence and a `#` comment inside SQL, and uses an exact `FETCH FIRST` | Real `product` / `store_product_inventory` / `store` join with Haversine distance in the app (backup B16) |
| 4 | `textembedding@004`, `text-embedding-004` | Older embedding model | `gemini-embedding-2`, 3,072 dimensions |
| 5 | Gemini 2.5 ecosystem slide; "Gemini 3 Pro" in the architecture | Out of date | Gemini 3.8 Flash for the app; the Select AI model list from Oracle docs for Select AI |
| 6 | Gemini CLI slides, demo videos, and the `gemini extensions install …/oracledb` demo | Standalone Gemini CLI reached end of life in June 2026 | Antigravity (`agy` CLI and 2.0 IDE); confirm the Oracle extension's install path under Antigravity |
| 7 | "Modernize your applications with AI agents using ADK" | The demo app no longer uses ADK; it runs its own loop on `google-genai` | Show the native loop (`AgentRuntime`); mention ADK and Agent Engine in one line as Google's managed option |
| 8 | `intent_exemplar` table plus a classifier LLM call before every search | Replaced by 25 route exemplars across 5 route labels scored in the same SQL turn | `chat_route` in `hybrid-search-turn` (`dba_s34`–`dba_s35`, slides 31–32) |
| 9 | Architecture with "MCP Server for Maps, Grounding Lite" and BigQuery MCP | Not part of the current app | Current architecture from `SLIDES.md` slide 0 (`dba_s30`, slide 28) |
| 10 | "Released last week" (MCP Toolbox); "Gemini in OCI, coming soon to Fusion" | Dated announcements | Current facts only, with dates if needed |
| 11 | "Available in 8 regions today" (heading) with 14 regions listed | Inconsistent; region counts change | Check the public locations page on the day (backup B13) |
| 12 | 10% / 90% data statistic | No primary source | Drop |
| 13 | Speaker notes about the partner reseller program on the agent slides | Notes pasted onto the wrong slides | Write new notes |
| 14 | "Proprietary & Confidential" footers | Wrong for a public talk | Remove |
| 15 | "Coffee Novice" persona JSON and the older system prompt | No longer matches the app | Quote the current persona text from `PersonaManager` in `src/app/domain/system/services/_personas.py` (backup B15) |
| 16 | Legacy local dev port URLs or claims that `adb-free` lacks Oracle APEX 26.1 | App port and local container runtime changed | Litestar runs on `http://localhost:8000`; `container-registry.oracle.com/database/adb-free:latest-26ai` (`26.9.4.1-26ai`, `cymbal-adb-free`) pre-bundles Oracle APEX 26.1.5 + ORDS 26.3 on `https://localhost:8443/ords/apex` |
