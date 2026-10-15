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
  - [Opening and Part 1](storyboard-opening-and-part1.md) — slides 1–14
  - [Part 2](storyboard-part2.md) — slides 15–22
  - [Part 3 and close](storyboard-part3-and-close.md) — slides 23–36
  - [Backup slides](storyboard-backups.md) — B1–B17, skipped in presentation mode
- [Verified facts](verified-facts.md) — what can be said on stage, with sources, plus the do-not-claim list
- [Porting corrections](porting-corrections.md) — fixes required when reusing content from earlier versions of the talk

## Related

- Operational skill: `.agents/skills/oracle-slides/SKILL.md`
- Slide tooling: `uv run python manage.py slides --help` (`tools/slides/{cli,deck,diff,highlight,qr,validate}.py`, tested in `src/tests/unit/tools/slides/`)
- Architecture walkthrough the talk draws from: `SLIDES.md`
- Deck IDs, source-deck slide map, and environment commands live in the git-ignored overlay `.agents/local/presentation/`. Never copy them into committed files.
