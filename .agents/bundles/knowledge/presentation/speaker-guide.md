---
type: Guide
title: Speaker Guide — Oracle in the Age of Gemini (2026)
description: Audience, DBA-first story arc, timing, wording rules, demo approach, and accuracy rules for the Oracle DBA talk
tags:
  - presentation
  - speaker-guide
  - oracle
  - vertex-ai
---

# Speaker Guide — Oracle in the Age of Gemini (2026)

## The talk at a glance

| Item | Value |
| :--- | :--- |
| Title | Oracle in the Age of Gemini |
| Subtitle | Practical AI Agents, MCP Workflows, and Vector Search for Oracle DBAs |
| Length | 45–50 minutes (34 active slides: 25 DBA-first core slides + 7 Cymbal Coffee reference app slides + Monday Recap + Thank You) |
| Audience | Senior Oracle DBAs and database engineers (Exadata Database Service and Autonomous AI Database on Oracle Database@Google Cloud). They know Oracle internals (`DBMS_XPLAN`, `GV$TRANSACTION`, `V$SYSSTAT`, `CTXSYS.CONTEXT`, SGA sizing, `FOR UPDATE SKIP LOCKED`) and want concrete MCP configurations, diagnostic SQL, and safe operational patterns |
| Promise | Leave with working Antigravity + Oracle MCP configurations, copy-pasteable 26ai and Exadata diagnostic SQL, an understanding of Knowledge Catalog and in-database Gemini options, and a reference application architecture |
| Demo app | Cymbal Coffee, `github.com/cofin/oracledb-vertexai-demo` |

## The story

The deck is structured **DBA-first** across **34 active slides** (`storyboard.md`) so that Slides 1–25 deliver the entire DBA workflow, Antigravity + MCP configurations, diagnostic SQL, Knowledge Catalog, and in-database Gemini patterns, followed by the 7-slide **Cymbal Coffee** application walkthrough (Slides 26–32), Monday Recap (Slide 33), and Thank You (Slide 34).

| Section | Slides | Minutes | Message |
| :--- | :--- | :--- | :--- |
| Opening | `1`–`4` (`dba_s01`–`dba_s04`) | 4 | Where Oracle runs on Google Cloud, and the three integration surfaces where Gemini meets Oracle |
| Antigravity & Context for DBAs | `5`–`13` (`dba_s05`–`dba_s21`) | 10 | Core AI terms, Antigravity (`agy` CLI + IDE) DBA ideas, SQLcl MCP / MCP Toolbox / Cloud MCP, curated read-only `tools.yaml`, `AGENTS.md` / `SKILL.md`, 26ai `ANNOTATIONS`, and Knowledge Catalog |
| The Art of the Possible: DBA Use Cases | `14`–`20` (`dba_s12`–`dba_s22`) | 12 | Regressed SQL & SQL Tuning Advisor (`GV$SQL` + `DBMS_SQLTUNE`), RMAN Backup & Readiness Analyzer (`V$RMAN_BACKUP_JOB_DETAILS`), piping SQLcl into `agy`, interactive MCP data analysis & CSV extracts, and agent guardrails |
| Gemini Inside Oracle AI Database 26ai | `21`–`25` (`dba_s23`–`dba_s27`) | 8 | Embeddings & vector distance in Oracle terms, Select AI (`DBMS_CLOUD_AI`) on Autonomous AI DB, SGA Vector Pool vs In-Memory Column Store vs `embedding_cache`, and runbook memory in a `VECTOR` column |
| Build Real Apps: Cymbal Coffee | `26`–`32` (`dba_s29`–`dba_s35`) | 10 | How a production Python + Oracle 26ai app combines `VECTOR(3072, FLOAT32)`, HNSW (`vector_memory_size`), `CTXSYS.CONTEXT`, and single-query Hybrid RRF (`k = 60`) |
| Close & Thank You | `33`–`34` (`dba_s28`, `dba_s41`) | 2 + Q&A | Three immediate Monday steps with QR links (MCP Toolbox, Knowledge Catalog MCP, 26ai Demo Repo) and Q&A |

## Wording and visual rules

- Write for senior Oracle DBAs. Explain AI concepts in exact Oracle terms (an embedding is a `VECTOR(3072, FLOAT32)` column; an HNSW index is an `INMEMORY NEIGHBOR GRAPH` in the SGA Vector Memory Pool).
- Keep slide copy concise and scannable; put multi-sentence explanations in speaker notes.
- No per-slide badges, `"Part N"` labels, or bottom status banners.
- Never reference internal repository file names (`hybrid.sql`, `migration 0001`, `src/app/`, `SLIDES.md`) on slides.
- Titles stay on one line, 48 characters or fewer.
- Every active slide except the final Thank You slide (slides `1`–`33`, ending before `dba_s41`) ends its speaker notes with a `BRIDGE:` line that hands off to the next slide.

## Accuracy rules

The full list, with sources, is in [verified facts](verified-facts.md). The rules most likely to come up in Q&A:

1. Oracle Text `CONTAINS` / `SCORE` is BM25-style lexical ranking (an inverse-frequency score from 0 to 100), not BM25.
2. Oracle uses the HNSW index only for `ORDER BY VECTOR_DISTANCE(...) FETCH APPROX FIRST n ROWS ONLY`. Ordering by `1 - VECTOR_DISTANCE` or omitting `APPROX` forces an exact scan.
3. `VECTOR_DISTANCE` returns a distance: 0 means identical. Similarity is `1 - distance`.
4. HNSW indexes live in the SGA Vector Memory Pool (`vector_memory_size`, tracked in `V$VECTOR_MEMORY_POOL`), which is separate from the Database In-Memory column store (`inmemory_size`, tracked in `V$IM_SEGMENTS`).
5. Select AI's `google` provider calls the Gemini API (`generativelanguage.googleapis.com`) with an API key. Select AI has no native `vertexai` provider today; for Vertex AI from SQL or PL/SQL, use `DBMS_VECTOR.UTL_TO_EMBEDDING` / `UTL_TO_GENERATE_TEXT`, Oracle APEX 26.1 `APEX_AI.GENERATE` (`COFFEE_VERTEX_AI` against Vertex AI's OpenAI-compatible `/endpoints/openapi` endpoint or Litestar's `/api/apex/ai/v1` gateway on `http://localhost:8000`), a Cloud Run function via `DBMS_CLOUD_FUNCTION`, or the application tier.
6. AWR and ASH views require the Oracle Diagnostics Pack license; always note `V$SESSION` / `V$SQL` / `V$SYSSTAT` alternatives.
7. Agents connect as least-privilege diagnostic or application users (`SELECT_CATALOG_ROLE`), never `SYS` or `SYSTEM`.
8. Standalone Gemini CLI reached end of life in June 2026; Antigravity (`agy` CLI and Antigravity 2.0 IDE) is the successor and reads `.agents/mcp_config.json` (workspace), `~/.gemini/config/mcp_config.json` (global IDE), and `~/.gemini/antigravity-cli/mcp_config.json` (global `agy` CLI).

## Demo approach

Slides `dba_s08` and `dba_s14` embed a muted terminal capture (`dba_pipe_demo.gif`) showing a non-interactive SQLcl invalid-object check piped into `agy -p "..." 2>/dev/null`, producing a dependency-ordered recompile plan without executing DDL. Every SQL and configuration slide carries complete, self-contained SQL/YAML/JSON cards so the presentation runs cleanly without live network dependencies.

## Public-repo rule

This repository is public. Committed files must not contain Drive deck IDs or links, customer-internal names or topology details, internal tool names or paths, internal go links, or facts that only appear in internal material. Keep those in `.agents/local/presentation/` (git-ignored).
