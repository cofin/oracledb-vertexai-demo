---
name: oracle-slides
description: Use when building, formatting, reviewing, or fixing the "Oracle in the Age of Gemini" presentation from this repository — turning storyboard entries into validated Google Slides batchUpdate requests, highlighting SQL on code cards, generating QR codes, checking slide order and speaker notes, reconciling review comments, or keeping slide claims consistent with the verified-facts chapter.
---

# Oracle Slides

Build and maintain the Cymbal Coffee talk for Oracle DBAs from this repo.
The guide in `.agents/bundles/knowledge/presentation/` says what each slide
must contain; this skill says how to get it onto the deck safely.

## Sources of truth

| What | Where |
| :--- | :--- |
| Story, timing, wording and accuracy rules | `.agents/bundles/knowledge/presentation/speaker-guide.md` |
| Slide order, target objectIds, structural steps | `.agents/bundles/knowledge/presentation/storyboard.md` |
| Per-slide content, code, banners, notes | `.agents/bundles/knowledge/presentation/storyboard-opening-and-part1.md`, `.agents/bundles/knowledge/presentation/storyboard-part2.md`, `.agents/bundles/knowledge/presentation/storyboard-part3-and-close.md`, `.agents/bundles/knowledge/presentation/storyboard-backups.md` |
| Claims and sources; do-not-claim list | `.agents/bundles/knowledge/presentation/verified-facts.md` |
| Fixes for content from earlier talk versions | `.agents/bundles/knowledge/presentation/porting-corrections.md` |
| App architecture and Oracle APEX 26.1 reference | `SLIDES.md`, `src/apex/README.md` (`src/apex/cymbal-coffee-ops/`) |
| Deck IDs, source-deck map, environment Slides commands | `.agents/local/presentation/` (git-ignored) |
| Offline Slides CLI (`inventory`, `validate`, `diff`, `highlight`, `qr`) | `tools/slides/cli.py`, `tools/slides/deck.py`, `tools/slides/diff.py`, `tools/slides/highlight.py`, `tools/slides/qr.py`, `tools/slides/validate.py` |

If the storyboard and the deck disagree, the storyboard wins unless the
speaker has edited the deck by hand; diff first (see "Manual edits").

## Workflow for every batch

1. **Dump** the target deck with the Slides tooling listed in `.agents/local/presentation/deck.md`. Save it under `.agents/local/presentation/dumps/`.
2. **Inspect** it: `uv run python manage.py slides inventory <dump> --text`.
3. **Build** request JSON for one slide range (a list of `batchUpdate` requests) under `.agents/local/presentation/batches/`. Take element objectIds from the dump, never from memory.
4. **Validate**: `uv run python manage.py slides validate <batch> --dump <dump>`. Fix every error; read every warning.
5. **Apply** the batch with the environment's Slides tooling, then apply notes.
6. **Look**: export a thumbnail of every changed slide and view it. Check for overflow, overlap, wrapped titles, and style bleed.
7. **Re-dump** after any structural change (duplicate, delete, reorder) before building the next batch.

## Request recipes

Replace the text of a shape (keeps the shape and position; resets run styles, so restyle afterwards):

```json
[
  {"deleteText": {"objectId": "TITLE_ID", "textRange": {"type": "ALL"}}},
  {"insertText": {"objectId": "TITLE_ID", "insertionIndex": 0, "text": "Vector Search and the Optimizer Rule"}}
]
```

Skip or unskip a slide, and move it (one slide per request, in final order):

```json
[
  {"updateSlideProperties": {"objectId": "SLIDE_ID", "slideProperties": {"isSkipped": true}, "fields": "isSkipped"}},
  {"updateSlidesPosition": {"slideObjectIds": ["SLIDE_ID"], "insertionIndex": 12}}
]
```

Duplicate a slide with an explicit id map, so later requests can target the copy:

```json
{"duplicateObject": {"objectId": "SOURCE_SLIDE", "objectIds": {"SOURCE_SLIDE": "part2_divider", "SOURCE_TITLE": "part2_divider_title"}}}
```

Speaker notes: the notes shape is `slideProperties.notesPage.notesProperties.speakerNotesObjectId` in the dump; replace its text with `deleteText` + `insertText`, or use the environment's notes command.

Code cards: write the code to a file, then (`--language` accepts `oracle`, `sql`, `python`, `bash`, `json`, or `yaml`):

```bash
uv run python manage.py slides highlight query.sql --element CODE_BOX_ID --language oracle --output .agents/local/presentation/batches/code-NN.json
```

Insert the same text (without the file's final newline) before the highlight requests.

QR codes: `uv run python manage.py slides qr <url> --output .agents/local/presentation/qr/<name>.png`, then insert the PNG from the local file. Image URLs copied from another deck's JSON fail with an access error.

## Design rules

The deck follows the current Google Cloud event styling (Cloudstyle 2.0 as used at Oracle AI World 2026): white canvas, very large headlines with a gradient second line, 3D renders bleeding off the edge, rounded white cards with soft shadows, gradient circle icons, screenshots in laptop or console frames, and the Google Cloud + Oracle logo lockup bottom-left. The template deck ID lives in `.agents/local/presentation/deck.md`.

- **Build from template slides.** Copy the event template deck, then duplicate the template slide whose archetype fits (cover, speaker card, big question, three cards, two cards + render, screenshot split, laptop mockup, diagram, section divider) and rewrite its text. Hand-built shapes on a blank layout are the fallback for code slides only.
- **Vary the archetype.** Consecutive slides use different archetypes; a section never runs three of the same layout in a row.
- **One idea per slide.** About 40 words of body copy plus code at most; supporting detail, caveats, and sources go in speaker notes.
- **Plain chrome.** Title and body only. A bottom takeaway strip appears only when the takeaway is the point of the slide. Section membership shows through dividers, not per-slide badges or "Part N" labels.
- **Public audience.** Describe queries and features in words; leave out repository file names, paths, migration numbers, and internal tool names.
- **QR codes** go on the closing slide; other slides carry a hyperlinked source line.
- **Hideable sections.** Each audience-specific block (for example, the Cymbal Coffee app walkthrough) starts with its own divider and stands alone, so a copy of the deck can skip the whole block.
- **Code cards:** background `#161B22`, Roboto Mono 7.5–8.5 pt, base `#E6EDF3`; token colors come from `tools/slides/highlight.py`. Clone text colors and sizes from the template slide's existing runs instead of hard-coding them.

## Gotchas

- Text indexes are UTF-16 code units. Emoji count twice. `manage.py slides highlight` handles this; hand-built ranges must too.
- `replaceAllText` gives the whole replacement the style of the first matched character; restyle fixed ranges afterwards.
- After `deleteText` + `insertText`, the new text inherits the first surviving paragraph's style; re-apply bold lead-ins and monospace tokens.
- `duplicateObject` without `objectIds` produces random ids; the validator warns about this.
- Adding a slide by layout needs a predefined layout name; this template's empty layout is named `TITLE`.
- Re-dump after every structural change; objectIds of duplicated elements are only known from the map you passed or a fresh dump.

## Review comments and manual edits

1. List comments on the main deck and any copies; record id, author, slide, and text. Treat each comment as a deck-wide rule: apply it to every slide where the same pattern appears, not only the anchored element.
2. Dump each copy and run `uv run python manage.py slides diff <main-dump> <copy-dump>` to find hand edits by slide objectId; keep the speaker's wording.
3. Apply fixes to the main deck first, check thumbnails, then reply to and resolve each thread.

## Accuracy rules

Read `.agents/bundles/knowledge/presentation/verified-facts.md` before writing any claim. The rules that most often go wrong:

- Oracle Text `CONTAINS` / `SCORE` is BM25-style ranking, not BM25.
- HNSW is used only with `ORDER BY VECTOR_DISTANCE(...) FETCH APPROX FIRST n ROWS ONLY`; `VECTOR_DISTANCE` is a distance (0 is identical).
- Select AI's `google` provider uses a Gemini API key; Select AI has no Vertex AI provider. Vertex AI paths: `DBMS_VECTOR` (`vertexai`), Oracle APEX 26.1 `APEX_AI.GENERATE` (`COFFEE_VERTEX_AI` direct `/endpoints/openapi` with `google/gemini-3.8-flash` or Litestar `/api/apex/ai/v1` gateway on `http://localhost:8000`, pre-bundled in `container-registry.oracle.com/database/adb-free:latest-26ai` APEX 26.1.5 + ORDS 26.3), Cloud Run functions from SQL, or the app tier.
- SQLSpec `0.69.0` defaults `fetch_lobs=False` (inline `CLOB`/`BLOB` < 1 GB as `str`/`bytes`) with session tracing and wire-level `sqlcommenter`, and isolates `litestar-queues` (`FOR UPDATE SKIP LOCKED`) on its own pool (`session_key="queue_db_session"`).
- AWR and ASH need the Diagnostics Pack license. Agents use least-privilege users, never `SYS`.
- Label timings as example timings from a local run.

## Public-repo hygiene

This repository is public. Never commit deck IDs or Drive links, internal tool names or paths, internal go links, comment exports, or dumps. Keep them in `.agents/local/presentation/`, which `.agents/.gitignore` ignores. Before committing, run `git status --short` and confirm nothing under `.agents/local/` is staged.

## Done checklist for a slide range

- [ ] Every request batch validated against a dump taken right before it was applied
- [ ] Thumbnails of every changed slide viewed; no overflow, overlap, or style bleed
- [ ] Built from template slides; no three consecutive slides share an archetype
- [ ] Titles fit on one line (48 characters or fewer); code highlighted; no badges, "Part N" labels, repo paths, or stray QR codes
- [ ] Notes written; every shown slide except the closing Thank You slide (slide 34, `dba_s41`) ends with `BRIDGE:`
- [ ] `uv run python manage.py slides inventory <dump>` shows the storyboard order and skip flags
- [ ] Claims match `.agents/bundles/knowledge/presentation/verified-facts.md`; open checks are still marked as open
