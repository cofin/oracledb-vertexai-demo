---
type: Spec
flow_id: oracle-gemini-2026-deck
title: Build the "Oracle in the Age of Gemini" Deck from the Presentation Guide
state: active
plan_revision: 1
plan_commit: null
state_revision: 9
current_task: null
last_operation: 20261013T165500Z-flow-executor-close-1-4-00
operation_targets:
  - "1.4"
last_verified_checkpoint: 2026-10-13T16:55:00Z
created_at: 2026-10-13T15:55:00Z
updated_at: 2026-10-13T16:55:00Z
description: Restructure and rewrite the target Google Slides deck into the 36-slide "Oracle in the Age of Gemini" talk (extend your workflow, be a better DBA, build real apps) plus 17 skipped backups, using the committed presentation guide, the offline manage.py slides tooling, and the oracle-slides skill.
tags:
  - spec
  - presentation
  - slides
  - oracle
  - vertex-ai
parent_prd: null
research: []
---

# Flow: Build the "Oracle in the Age of Gemini" Deck from the Presentation Guide

**Flow ID:** `oracle-gemini-2026-deck`

---

## North Star

The target deck presents the Cymbal Coffee talk for Oracle DBAs exactly as the
presentation guide describes it: 36 shown slides in three parts (extend your
workflow, be a better DBA, build real apps) and 17 skipped backups, with every
claim traceable to `verified-facts.md`, every code card taken from the repo and
highlighted, every shown slide's notes ending in a `BRIDGE:` line (except the
recap and thank-you slides), and no internal identifiers committed to this
public repository.

## Scope

**In scope**

- Structural changes to the target deck: duplicates, order, skip flags.
- Text, code, banner, QR, and notes changes for slides 1–36 and B1–B17.
- Lab checks that close the open items in `verified-facts.md`.
- Re-recorded muted demo clips and a `SLIDES.md` refresh that matches the deck.

**Out of scope**

- Application code changes (the Knowledge Catalog sync stays in its own planned spec).
- New slide templates or masters; the deck keeps its existing layouts and palette.

## Specification

### Inputs examined

- `.agents/bundles/knowledge/presentation/` — speaker guide, storyboard (overview plus four section files), verified facts, porting corrections.
- `.agents/skills/oracle-slides/SKILL.md` — batch workflow, request recipes, palette, gotchas, hygiene rules.
- `tools/slides/` and `manage.py slides` — offline `inventory`, `validate`, `diff`, `highlight`, `qr` (unit tests in `src/tests/unit/tools/slides/`).
- `.agents/local/presentation/` (git-ignored) — deck IDs, source-deck slide map, environment Slides commands.
- `SLIDES.md`, `src/app/db/sql/hybrid.sql`, `src/app/db/migrations/0001_cymball_coffee_products.sql`, `docs/mcp-antigravity.md` — code and SQL quoted on slides.

### Requirements

- **DECK-REQ-01 (Structure):** slides 1–36 appear in storyboard order and are shown; B1–B17 follow slide 36 and are skipped; duplicated slides were created with explicit `objectIds` maps and their ids are recorded in `storyboard.md`.
- **DECK-REQ-02 (Opening and Part 1):** slides 1–14 match `storyboard-opening-and-part1.md`.
- **DECK-REQ-03 (Part 2):** slides 15–22 match `storyboard-part2.md`.
- **DECK-REQ-04 (Part 3):** slides 23–34 match `storyboard-part3-and-close.md`, with SQL quoted from the repo and the porting corrections applied.
- **DECK-REQ-05 (Close, backups, notes):** slides 35–36 and B1–B17 match the guide; QR codes resolve; notes rules hold across the deck.
- **DECK-REQ-06 (Facts and demos):** open checks in `verified-facts.md` are resolved or moved to the do-not-claim list; demo clips are recorded; `SLIDES.md` matches the deck.

### Requirement-to-Task Traceability

| Requirement | Task | Verification Strategy | Primary Files | Primary Tests |
| --- | --- | --- | --- | --- |
| `DECK-REQ-01` | `1.1` | `documentation_validation` | `.agents/bundles/knowledge/presentation/storyboard.md` | `src/tests/unit/tools/slides/` |
| `DECK-REQ-02` | `1.2` | `documentation_validation` | `.agents/bundles/knowledge/presentation/storyboard-opening-and-part1.md` | `src/tests/unit/tools/slides/` |
| `DECK-REQ-03` | `1.3` | `documentation_validation` | `.agents/bundles/knowledge/presentation/storyboard-part2.md` | `src/tests/unit/tools/slides/` |
| `DECK-REQ-04` | `1.4` | `documentation_validation` | `.agents/bundles/knowledge/presentation/storyboard-part3-and-close.md` | `src/tests/unit/tools/slides/` |
| `DECK-REQ-05` | `1.5` | `documentation_validation` | `.agents/bundles/knowledge/presentation/storyboard-backups.md` | `src/tests/unit/tools/slides/` |
| `DECK-REQ-06` | `1.6` | `integration_acceptance` | `.agents/bundles/knowledge/presentation/verified-facts.md`, `SLIDES.md` | `src/tests/unit/tools/slides/` |

---

## Implementation Plan

### Phase 1: Deck build

- [x] 1.1 Structure pass: duplicates, order, and skip flags
- [x] 1.2 Opening and Part 1 content (slides 1–14)
- [x] 1.3 Part 2 content (slides 15–22)
- [x] 1.4 Part 3 content (slides 23–34)
- [ ] 1.5 Close, backups, QR codes, and deck-wide notes pass (35–36, B1–B17)
- [ ] 1.6 Lab checks, demo clips, and `SLIDES.md` refresh

---

## Global Constraints

1. **Public repository:** never commit deck IDs, Drive links, internal tool names or paths, internal go links, dumps, batches, thumbnails, or comment exports. They live in `.agents/local/presentation/` (ignored by `.agents/.gitignore`). Check `git status --short` before every commit.
2. **Validate before applying:** every batch passes `uv run python manage.py slides validate <batch> --dump <fresh dump>` with zero errors, and the deck is re-dumped after every structural change.
3. **Look at every changed slide:** export and view thumbnails; fix overflow, overlap, wrapped titles, and style bleed before moving on.
4. **Accuracy:** claims must match `verified-facts.md`; follow `porting-corrections.md` when reusing earlier material; label timings as example timings.
5. **Wording:** titles at or under 48 characters on one line; no AI buzzwords, dramatic trope headings, or count-prefixed buzzword labels; notes end with `BRIDGE:` on every shown slide except 35 and 36.
6. **Speaker's edits win:** if the deck shows hand edits since the last dump, diff (`manage.py slides diff`) and keep the speaker's wording unless it conflicts with `verified-facts.md`; ask when unsure.

---

## Continuity Snapshot

- **Active Flow / Lifecycle**: `oracle-gemini-2026-deck` (`active`)
- **Current Task & Claimant**: `null` (`null`)
- **Last Verified Checkpoint**: `2026-10-13T16:55:00Z`
- **Key Decisions**:
  - The talk follows the earlier NorCal arc (offerings, Gemini with Oracle, agents today, developer tools, building agents) reorganized into extend / improve / build.
  - Select AI is shown with the Gemini API (`google` provider); Vertex AI paths are `DBMS_VECTOR`, Cloud Run functions from SQL, and the app tier.
  - Cymbal Coffee's native `google-genai` loop is shown; ADK is mentioned in one line.
  - Demos are pre-recorded muted clips, not live terminals.
- **Newest Discoveries**:
  1. The target deck's slide and element objectIds match the Postgres Summit US 2026 deck it was copied from, so storyboard targets are stable across copies.
  2. Earlier decks contain SQL that skips the HNSW index and a PostGIS-only distance function; see `porting-corrections.md`.
- **Blockers & Unblock Conditions**: Event length and demo database availability are assumptions (50 minutes; doc-based diagrams for slides 13 and 22 without an Autonomous AI Database).
- **Next Exact Step**: Claim Task 1.5 (Close, backups, QR codes, and deck-wide notes pass).
- **Plan Identity**: `plan_revision: 1`, `plan_commit: null`
- **State Identity**: `state_revision: 9`, `last_operation: 20261013T165500Z-flow-executor-close-1-4-00`, `operation_targets: ["1.4"]`
- **Relevant Knowledge Paths**:
  - `.agents/bundles/knowledge/presentation/index.md`
  - `.agents/skills/oracle-slides/SKILL.md`
  - `SLIDES.md`
