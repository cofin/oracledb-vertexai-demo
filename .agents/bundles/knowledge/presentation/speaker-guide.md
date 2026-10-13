---
type: Guide
title: Speaker Guide — Oracle in the Age of Gemini (2026)
description: Audience, story, timing, wording rules, demo approach, and accuracy rules for the Cymbal Coffee DBA talk
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
| Subtitle | How DBAs use Vertex AI to work smarter and build real apps |
| Length | 50 minutes assumed (36 shown slides, 17 skipped backups); adjust the timing table if the slot changes |
| Audience | Senior Oracle DBAs and architects. They know Oracle deeply (`CTXSYS.CONTEXT`, optimizer access paths, SGA sizing, `FOR UPDATE SKIP LOCKED`, privileges and auditing) and are new to embeddings, agents, and MCP |
| Promise | Leave knowing where Gemini fits in your daily work, which DBA chores to hand to an agent, and how a real app uses Oracle for retrieval while Gemini does the talking |
| Demo app | Cymbal Coffee, `github.com/cofin/oracledb-vertexai-demo` |

## The story

The talk follows one arc: start where DBAs already work, move to the DBA work
agents can take off their plate, and finish with an application.

| Section | Slides | Minutes | Message |
| :--- | :--- | :--- | :--- |
| Opening | 1–7 | 7 | Where Oracle runs on Google Cloud, and every place Gemini can touch Oracle data |
| Part 1: Extend your workflow | 8–14 | 11 | Gemini in the terminal, the IDE, and SQL itself: Antigravity, MCP, Select AI |
| Part 2: Be a better DBA | 15–22 | 12 | Agents gather and summarize (plans, AWR, audits, schema notes); the DBA approves every change |
| Part 3: Build real apps | 23–34 | 16 | One Oracle query handles exact words, meaning, routing, and off-menu checks; Gemini only phrases the answer |
| Close | 35–36 | 4 | One thing to try Monday for each part, then questions |

Hand-offs between parts (use them as the `BRIDGE:` lines on slides 14, 22,
and 34):

- End of Part 1: "That's the toolbox. Part 2 is about using it to be a better DBA."
- End of Part 2: "Business users can now get answers without new pipelines. Part 3 is for when you need your own app."
- End of Part 3: "Before you ship, a few Day-2 rules, and then where to start."

## Wording rules

- Write for DBAs. Explain AI terms in Oracle terms (an embedding is a `VECTOR(3072, FLOAT32)` column; an HNSW index is an in-memory graph in the SGA).
- Plain, direct sentences. No AI buzzwords, no dramatic trope headings ("The Trap", "The Secret"), and no count-prefixed buzzword labels ("3-Layer …", "5-Point …").
- Titles stay on one line, 48 characters or fewer. Subtitles say what the slide proves.
- Label timings as example timings from a local run, never as benchmarks.
- Every shown slide's speaker notes end with a `BRIDGE:` line that hands off to the next slide. The recap (35) and thank-you (36) slides are the exceptions.
- Keep the recurring example concrete: Cymbal Coffee's products, stores, and inventory, with the real table and query names from the repo.

## Accuracy rules

The full list, with sources, is in [verified facts](verified-facts.md). The
rules most likely to come up in Q&A:

1. Oracle Text `CONTAINS` / `SCORE` is BM25-style lexical ranking (an inverse-frequency score from 0 to 100), not BM25.
2. Oracle uses the HNSW index only for `ORDER BY VECTOR_DISTANCE(...) FETCH APPROX FIRST n ROWS ONLY`. Ordering by `1 - VECTOR_DISTANCE` or omitting `APPROX` is an exact scan.
3. `VECTOR_DISTANCE` returns a distance: 0 means identical. Similarity is `1 - distance`.
4. HNSW indexes live in the SGA vector memory area; size `vector_memory_size` before creating them.
5. Select AI's `google` provider calls the Gemini API with an API key. Select AI has no Vertex AI provider today. For Vertex AI, use `DBMS_VECTOR`, a Cloud Run function called from SQL, or the application tier.
6. AWR and ASH data require the Oracle Diagnostics Pack license.
7. Agents connect as least-privilege application users, never `SYS` or `SYSTEM`.
8. Standalone Gemini CLI reached end of life in June 2026; Antigravity (`agy` CLI and Antigravity 2.0 IDE) is the successor.
9. Cymbal Coffee runs its own small agent loop on `google-genai` (Vertex AI mode) rather than ADK. When ADK comes up, describe it as Google's managed agent framework (with Agent Engine) and say the demo shows the same loop without a framework.

## Demo approach

Use pre-recorded, muted, trimmed clips and visual walkthroughs, not live
terminal sessions. Slides 13, 17, 25, 28–31, and Backup B17 carry complete,
self-contained SQL and prose walkthrough cards so the talk runs cleanly even
without external video playback; embed or link these muted MP4 clips when
recorded before the event:

| Clip | Slides | Shows |
| :--- | :--- | :--- |
| Plan second opinion | 17, B17 | Antigravity with Oracle MCP finds the full scan and proposes the `FETCH APPROX` rewrite |
| Select AI | 13, B17 | `SELECT AI showsql` and `narrate` against the demo schema (requires Autonomous AI Database; `DBMS_CLOUD_AI` is not in the 26ai Free container) |
| Cymbal Coffee chat | 28–31, B17 | A product question, a store question, and "Do you carry Folgers?", with the telemetry drawer showing the SQL phases |
| Background embedding | 25, B17 (optional) | `uv run coffee bulk-embed` running through the database queue |

## Open decisions

| Decision | Current assumption |
| :--- | :--- |
| Event and slot length | 50 minutes |
| ADK message | Native loop shown; ADK mentioned in one line |
| Demo database for Select AI and the Oracle AI Database Agent | `DBMS_CLOUD_AI` is not present in the local 26ai Free container, so slides 13 and 22 use doc-based SQL and architecture cards unless an Autonomous AI Database on Oracle Database@Google Cloud is provisioned |
| Knowledge Catalog demo | The repo's catalog sync is still a planned spec; slide 20 shows architecture only until it ships |

## Public-repo rule

This repository is public. Committed files must not contain Drive deck IDs or
links, internal tool names or paths, internal go links, or facts that only
appear in internal material. Keep those in `.agents/local/presentation/`
(git-ignored).
