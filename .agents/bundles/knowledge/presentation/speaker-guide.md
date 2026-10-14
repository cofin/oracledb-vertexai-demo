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
| Length | 45–50 minutes (28 DBA-first core slides + 12 hideable Cymbal Coffee app walkthrough slides + Thank You + 16 unskipped Reference slides) |
| Audience | Senior Oracle DBAs and database engineers (Exadata Database Service and Autonomous AI Database on Oracle Database@Google Cloud). They know Oracle internals (`DBMS_XPLAN`, `GV$TRANSACTION`, `V$SYSSTAT`, `CTXSYS.CONTEXT`, SGA sizing, `FOR UPDATE SKIP LOCKED`) and want concrete MCP configurations, diagnostic SQL, and safe operational patterns |
| Promise | Leave with working Antigravity + Oracle MCP configurations, copy-pasteable 26ai and Exadata diagnostic SQL, an understanding of Knowledge Catalog and in-database Gemini options, and a reference application architecture |
| Demo app | Cymbal Coffee, `github.com/cofin/oracledb-vertexai-demo` |

## The story

The deck is structured **DBA-first** so that the first 28 slides deliver the entire DBA workflow, diagnostic SQL, Knowledge Catalog, in-database Gemini patterns, and Monday action plan, while the 12-slide **Cymbal Coffee** application walkthrough (`dba_s29`–`dba_s40`) sits at the end as a self-contained section that can be presented in full or hidden for pure-DBA sessions.

| Section | Slides | Minutes | Message |
| :--- | :--- | :--- | :--- |
| Opening | `dba_s01`–`dba_s04` | 4 | Where Oracle runs on Google Cloud, and the three integration surfaces where Gemini meets Oracle |
| Antigravity for DBAs | `dba_s05`–`dba_s11` | 10 | MCP in DBA terms, the three Oracle MCP servers, Antigravity (`agy` CLI + IDE), `mcp_config.json`, read-only `tools.yaml`, and `.agents/` rules/skills |
| DBA Use Cases | `dba_s12`–`dba_s22` | 14 | HNSW plan diagnosis, piping SQLcl into `agy`, detect-to-approve workflows, RAC scalable sequences, long transactions, Exadata Smart Scan offload, access audits, 26ai `ANNOTATIONS`, Knowledge Catalog, and guardrails |
| Gemini Inside Oracle 26ai | `dba_s23`–`dba_s27` | 8 | Select AI (`DBMS_CLOUD_AI`), `DBMS_VECTOR.UTL_TO_EMBEDDING` to Vertex AI, SGA Vector Pool vs In-Memory Column Store vs `embedding_cache`, and runbook vector search |
| Where to Start on Monday | `dba_s28` | 2 | Three immediate steps with QR links (MCP Toolbox, Knowledge Catalog MCP, 26ai Demo Repo) |
| Build Real Apps: Cymbal Coffee | `dba_s29`–`dba_s40` | 10 (optional) | How a production Python + Oracle 26ai app combines HNSW, `CTXSYS.CONTEXT`, plain-SQL RRF, `JSON_TABLE` guards, and `/mcp` + `/a2a` |
| Thank You & Reference | `dba_s41`–`dba_s57` | Q&A | 16 unskipped deep-dive reference cards for Q&A and leave-behind reading |

## Wording and visual rules

- Write for senior Oracle DBAs. Explain AI concepts in exact Oracle terms (an embedding is a `VECTOR(3072, FLOAT32)` column; an HNSW index is an `INMEMORY NEIGHBOR GRAPH` in the SGA Vector Memory Pool).
- Keep slide copy concise and scannable; put multi-sentence explanations in speaker notes.
- No per-slide badges, `"Part N"` labels, or bottom status banners.
- Never reference internal repository file names (`hybrid.sql`, `migration 0001`, `src/app/...`, `SLIDES.md`) on slides.
- Titles stay on one line, 48 characters or fewer.
- Every core slide (`dba_s01`–`dba_s40`) ends its speaker notes with a `BRIDGE:` line that hands off to the next slide.

## Accuracy rules

The full list, with sources, is in [verified facts](verified-facts.md). The rules most likely to come up in Q&A:

1. Oracle Text `CONTAINS` / `SCORE` is BM25-style lexical ranking (an inverse-frequency score from 0 to 100), not BM25.
2. Oracle uses the HNSW index only for `ORDER BY VECTOR_DISTANCE(...) FETCH APPROX FIRST n ROWS ONLY`. Ordering by `1 - VECTOR_DISTANCE` or omitting `APPROX` forces an exact scan.
3. `VECTOR_DISTANCE` returns a distance: 0 means identical. Similarity is `1 - distance`.
4. HNSW indexes live in the SGA Vector Memory Pool (`vector_memory_size`, tracked in `V$VECTOR_MEMORY_POOL`), which is separate from the Database In-Memory column store (`inmemory_size`, tracked in `V$IM_SEGMENTS`).
5. Select AI's `google` provider calls the Gemini API (`generativelanguage.googleapis.com`) with an API key. Select AI has no native `vertexai` provider today; for Vertex AI from SQL, use `DBMS_VECTOR.UTL_TO_EMBEDDING` / `UTL_TO_GENERATE_TEXT`, a Cloud Run function via `DBMS_CLOUD_FUNCTION`, or the application tier.
6. AWR and ASH views require the Oracle Diagnostics Pack license; always note `V$SESSION` / `V$SQL` / `V$SYSSTAT` alternatives.
7. Agents connect as least-privilege diagnostic or application users (`SELECT_CATALOG_ROLE`), never `SYS` or `SYSTEM`.
8. Standalone Gemini CLI reached end of life in June 2026; Antigravity (`agy` CLI and Antigravity 2.0 IDE) is the successor and reads `~/.gemini/config/mcp_config.json` and `.agents/mcp_config.json`.

## Demo approach

Slides `dba_s08` and `dba_s14` embed a muted terminal capture (`dba_pipe_demo.gif`) showing a non-interactive SQLcl invalid-object check piped into `agy -p "..." 2>/dev/null`, producing a dependency-ordered recompile plan without executing DDL. Every SQL and configuration slide carries complete, self-contained SQL/YAML/JSON cards so the presentation runs cleanly without live network dependencies.

## Public-repo rule

This repository is public. Committed files must not contain Drive deck IDs or links, customer-internal names or topology details, internal tool names or paths, internal go links, or facts that only appear in internal material. Keep those in `.agents/local/presentation/` (git-ignored).
