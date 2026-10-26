---
type: Index
title: Presentation Guide — Oracle in the Age of Gemini (2026)
description: Speaker guide, storyboard, verified facts, and porting corrections for the Cymbal Coffee talk aimed at Oracle DBAs
tags:
  - presentation
  - slides
  - oracle
  - vertex-ai
---

# Presentation Guide — Oracle in the Age of Gemini (2026)

This guide is the source of truth for building and delivering the talk that
uses Cymbal Coffee to show Oracle DBAs how Gemini and Vertex AI extend their
workflow, help them do better DBA work, and then help them build real
applications.

## Chapters

- [Speaker guide](speaker-guide.md) — audience, story, timing, voice, demo approach, and accuracy rules
- [Storyboard](storyboard.md) — slide order, target slides in the deck, structural steps, and slide conventions
  - [Opening and Antigravity & Context for DBAs](storyboard-opening-and-part1.md) — slides 1–13 (`dba_s01`–`dba_s21`)
  - [DBA Use Cases and Gemini Inside 26ai](storyboard-part2.md) — slides 14–25 (`dba_s12`–`dba_s27`)
  - [Build Real Apps: Cymbal Coffee and Close](storyboard-part3-and-close.md) — slides 26–34 (`dba_s29`–`dba_s41`)
  - [Backup reference catalog](storyboard-backups.md) — B1–B17 reference deep-dives (purged from the 34-slide active deck; append and mark skipped only when an event copy needs Q&A backups)
- [Verified facts](verified-facts.md) — what can be said on stage, with sources, plus the do-not-claim list
- [Porting corrections](porting-corrections.md) — fixes required when reusing content from earlier versions of the talk

## Related

- Operational skill: [`.agents/skills/oracle-slides/SKILL.md`](../../../skills/oracle-slides/SKILL.md)
- Slide tooling: `uv run python manage.py slides --help` (`tools/slides/cli.py`, `tools/slides/deck.py`, `tools/slides/diff.py`, `tools/slides/highlight.py`, `tools/slides/qr.py`, `tools/slides/validate.py`, tested in `src/tests/unit/tools/slides/`)
- Architecture walkthrough and Oracle APEX 26.1 reference: [`SLIDES.md`](../../../../SLIDES.md) and [`src/apex/README.md`](../../../../src/apex/README.md) (`src/apex/cymbal-coffee-ops/`)
- Deck IDs, source-deck slide map, and environment commands live in the git-ignored overlay `.agents/local/presentation/`. Never copy them into committed files.
