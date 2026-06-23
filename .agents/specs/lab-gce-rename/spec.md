# Flow: lab-gce-rename

*Beads: `oracledb-vertexai-jw0.4`*
*Parent PRD: [../cloudrun-gce-lab/prd.md](../cloudrun-gce-lab/prd.md) (Decision D1)*
*Type: docs (Sphinx/MyST) — DOC-ONLY, no source code changes*
*Depends on: nothing (can run in parallel with Ch1 and Ch2)*
*Status: Planned — implementation-ready*

---

## Specification

### Context

The PRD `cloudrun-gce-lab` (Decision D1) ships a **second** hands-on lab — a
production-shaped Cloud Run + private GCE Oracle DB + Cloud Build path — while
**preserving** the current single-VM lab. This chapter does the structural docs
move so the two labs coexist:

1. The current `docs/lab.md` (the all-in-one single-VM GCE workshop) becomes
   `docs/lab-gce.md`.
2. `docs/lab.md` is replaced by a short "choose your path" **index** that links
   the two labs. Keeping the file named `lab.md` preserves the existing
   `:link: lab` index card (`docs/index.md:80`) and the `lab` toctree target
   (`docs/index.md:119`) — Sphinx nav stays stable.
3. A minimal `docs/lab-cloud-run.md` **stub** is created so the build resolves
   the third nav entry and the index link target **now** (Ch5 fills the body).

This chapter is **DOC-ONLY**. No source, no Terraform, no app code.

### Docs build contract (why edits must be precise)

- Docs system: **Sphinx + MyST** (`docs/conf.py:9-20`); `master_doc = "index"`
  (`docs/conf.py:23`).
- Build: `make docs` → `uv run --group docs sphinx-build -W --keep-going -b html docs docs/_build/html`
  (`Makefile:194-197`). **`-W` makes warnings fatal.**
- Consequences of `-W` that constrain this chapter:
  - A `:link:`/toctree entry pointing at a **non-existent docname fails the
    build**. → `docs/lab-cloud-run.md` MUST exist (stub) before it is linked or
    listed in the toctree.
  - A doc file that exists but is **not in any toctree** raises
    `document isn't included in any toctree`, which `-W` turns into a failure. →
    `lab-gce` and `lab-cloud-run` MUST be added to the `Lab` toctree.
- `:link-type: doc` resolves links by **docname** (filename without `.md`), so
  `lab`, `lab-gce`, `lab-cloud-run` are the valid link/toctree tokens.
- MyST extension `colon_fence` is enabled (`docs/conf.py:38`), so the
  `:::{grid-item-card}` syntax used in `docs/index.md` is valid in the new index
  page.

### Current-state analysis (file:line)

- `docs/lab.md` — 628 lines, the full single-VM GCE workshop.
  - H1 (line 1): `# Hands-on Lab: Cymbal Coffee — Oracle 26ai \+ Vertex AI AI-Powered Agent`
  - Content uses MyST-escaped chars (`\+` line 1, `\!` lines 11/258/437/609) — **must be preserved verbatim** by moving the file with `git mv`, not retyping.
- `docs/index.md` — references to `lab`:
  - Lines 79-85: the "Hands-on lab" grid-card.
    - Line 80: `:link: lab`
    - Line 81: `:link-type: doc`
    - Lines 83-84 (card body):
      `The single-file workshop guide for running Cymbal Coffee with Oracle 26ai and` / `Vertex AI.`
  - Lines 115-120: the `Lab` toctree block; line 119 is the single entry `lab`.
- No other repo file links `lab` as a doc target. Confirmed via
  `grep -rn "lab" docs/*.md docs/concepts/*.md docs/reference/*.md README*`
  (only `docs/index.md:80` and `docs/index.md:119` are doc-target references;
  all other "lab" hits are the word "available/availability" or prose). So the
  **only** files to edit are `docs/lab.md` (replace), `docs/index.md` (toctree +
  card body), plus the two new files `docs/lab-gce.md` and `docs/lab-cloud-run.md`.
- `docs/conf.py` has **no glob toctree** and no `exclude_patterns` entry that
  would auto-exclude the new files (`exclude_patterns` = `_build`, `Thumbs.db`,
  `.DS_Store`, `screenshots/**` — `docs/conf.py:24-29`). New `.md` files under
  `docs/` are picked up only via explicit toctree entries.

### Ownership boundaries (cross-chapter)

This is the **sole owner** of the toctree edit and the chooser index. Later
chapters must NOT re-touch them:

- **This chapter (Ch4)**: creates `docs/lab-gce.md` (full content), the new
  `docs/lab.md` chooser, and the `docs/lab-cloud-run.md` **stub**; performs the
  single `docs/index.md` toctree + card-body edit.
- **Ch5 (`cloudrun-lab-authoring`)**: REPLACES the body of `docs/lab-cloud-run.md`
  with the end-to-end walkthrough. It does **not** edit the toctree, the chooser
  index, or `docs/lab-gce.md`.
- **Ch6 (`cloudrun-lab-verification-teardown`)**: fills the
  `## Verify your deployment` / `## Clean up & costs` sections inside
  `docs/lab-cloud-run.md`. No nav edits.

### Requirements

**Functional**

- FR1: `docs/lab-gce.md` exists and contains the **current `docs/lab.md`
  content verbatim**, with exactly two changes: (a) the H1 retitled to
  `# Hands-on Lab (Single-VM GCE): Cymbal Coffee — Oracle 26ai + Vertex AI`, and
  (b) a 1-2 sentence intro paragraph inserted immediately under the H1 noting
  this is the all-in-one-VM path and pointing to the Cloud Run lab. All other
  content (steps, challenges, appendix, escaped chars) unchanged.
- FR2: `docs/lab.md` is a short MyST "choose your path" index: H1 + 1-2 sentence
  intro + one shared line about GCP billing + a `::::{grid}` with two
  `grid-item-card`s linking `lab-gce` (single-VM) and `lab-cloud-run`
  (Cloud Run). Full file content is given verbatim in Phase 2 below.
- FR3: `docs/lab-cloud-run.md` exists as a minimal valid stub: H1 + one-line note
  that the full walkthrough is authored in the Cloud Run lab chapter. It must be
  a buildable MyST page (so the index link and toctree entry resolve).
- FR4: `docs/index.md` `Lab` toctree lists three docnames: `lab`, `lab-gce`,
  `lab-cloud-run`.
- FR5: `docs/index.md` "Hands-on lab" card keeps `:link: lab` and updates its
  body to `Choose your deployment path: single-VM GCE or production-shaped Cloud Run.`

**Non-functional**

- NFR1: `git mv` preserves the file history of the moved lab content.
- NFR2: No source/Terraform/app changes. Docs only.
- NFR3: House voice — em-dash titles, lowercase-leading sentence-case intros,
  matching the existing `docs/index.md` / `docs/tour.md` style; on-brand
  "Cymbal Coffee" naming.

### Acceptance criteria

- AC1: `make docs` exits 0 (no `-W` failures). Both labs and the chooser appear
  in the rendered nav under the "Lab" caption.
- AC2: The "Hands-on lab" card on the home page resolves (`:link: lab` → the new
  chooser index), no `undefined label` / `unknown document` warning.
- AC3: No `document isn't included in any toctree` warning for `lab-gce.md` or
  `lab-cloud-run.md`.
- AC4: `docs/lab-gce.md` contains the full original workshop content (Steps 1-7,
  both Challenges, the Appendix) — diff vs original `lab.md` shows only the H1
  line and the inserted intro paragraph as changes.
- AC5: `git log --follow docs/lab-gce.md` shows the history of the original
  `docs/lab.md` (proves `git mv`, not delete+create).
- AC6: No file other than `docs/lab.md`, `docs/lab-gce.md`,
  `docs/lab-cloud-run.md`, and `docs/index.md` is modified.

---

## Implementation Plan

> DOC-ONLY flow — no automated tests. Each phase ends with the doc build as its
> verification gate. Run `make docs` only after all file edits are in place
> (Phase 4), because `-W` fails on any intermediate broken state.

### Phase 1 — Move current lab to `docs/lab-gce.md` (preserve history)

- [ ] 1.1 From the repo root, move the file preserving git history:
  ```shell
  git mv docs/lab.md docs/lab-gce.md
  ```
  After this, `docs/lab.md` no longer exists (recreated in Phase 2) and
  `docs/lab-gce.md` holds the full original content.

- [ ] 1.2 Retitle the H1 of `docs/lab-gce.md`. Replace the **first line**
  (currently `# Hands-on Lab: Cymbal Coffee — Oracle 26ai \+ Vertex AI AI-Powered Agent`)
  with exactly:
  ```markdown
  # Hands-on Lab (Single-VM GCE): Cymbal Coffee — Oracle 26ai + Vertex AI
  ```
  (Note: the new H1 uses a plain `+` and a real em-dash `—`; it drops the
  trailing "AI-Powered Agent". Do not alter any other line.)

- [ ] 1.3 Insert a 1-2 sentence intro paragraph in `docs/lab-gce.md`
  **immediately after the new H1** and **before** the existing
  `Welcome to the **Cymbal Coffee Hands-on Lab**.` paragraph (original line 3).
  Insert exactly this block (a blank line above and below it):
  ```markdown
  This is the **all-in-one** path: the Oracle 26ai database and the Litestar app
  run together on a single Compute Engine VM — the fastest way to see the demo
  end to end. Want a production-shaped split (Cloud Run + a private GCE Oracle DB
  + Cloud Build)? Follow the [Cloud Run lab](lab-cloud-run.md) instead.
  ```
  Leave the rest of the file (the `Welcome to…` paragraph and everything below)
  unchanged.

### Phase 2 — Create the `docs/lab.md` chooser index

- [ ] 2.1 Create a fresh `docs/lab.md` with **exactly** the following content
  (verbatim — this is the complete file):
  ```markdown
  # Hands-on Lab: Cymbal Coffee — Oracle 26ai + Vertex AI

  Cymbal Coffee ships **two** hands-on labs. Pick the one that matches how you
  want to run the demo — the simplest single-VM path, or a production-shaped
  cloud architecture. Both paths assume a GCP account with billing/credits
  enabled.

  ::::{grid} 1 1 2 2
  :gutter: 3

  :::{grid-item-card} {octicon}`server;1.1em` Single-VM GCE
  :link: lab-gce
  :link-type: doc

  Everything on one Compute Engine VM — Oracle 26ai and the Litestar app side by
  side. The fastest way to get the demo running.
  :::

  :::{grid-item-card} {octicon}`cloud;1.1em` Cloud Run
  :link: lab-cloud-run
  :link-type: doc

  Production-shaped: the app on Cloud Run, a private GCE Oracle 26ai database,
  and a Cloud Build deploy pipeline over a private VPC.
  :::

  ::::
  ```

### Phase 3 — Create the `docs/lab-cloud-run.md` stub

- [ ] 3.1 Create `docs/lab-cloud-run.md` with **exactly** the following content
  (this is the complete stub file; Ch5 replaces the body, Ch6 adds its
  verification/teardown sections):
  ```markdown
  # Hands-on Lab (Cloud Run): Cymbal Coffee — Oracle 26ai + Vertex AI

  The full walkthrough is authored in the Cloud Run lab chapter. Until then, use
  the [single-VM GCE lab](lab-gce.md) to run the demo end to end.
  ```

### Phase 4 — Wire Sphinx nav in `docs/index.md`

- [ ] 4.1 Update the "Hands-on lab" card body. In `docs/index.md`, the card is at
  lines 79-85. Keep `:link: lab` (line 80) and `:link-type: doc` (line 81)
  unchanged; replace **only** the body text.

  **Before** (lines 79-85):
  ```markdown
  :::{grid-item-card} {octicon}`mortar-board;1.1em` Hands-on lab
  :link: lab
  :link-type: doc

  The single-file workshop guide for running Cymbal Coffee with Oracle 26ai and
  Vertex AI.
  :::
  ```

  **After**:
  ```markdown
  :::{grid-item-card} {octicon}`mortar-board;1.1em` Hands-on lab
  :link: lab
  :link-type: doc

  Choose your deployment path: single-VM GCE or production-shaped Cloud Run.
  :::
  ```

- [ ] 4.2 Update the `Lab` toctree to list all three docnames. The block is at
  `docs/index.md:115-120`.

  **Before** (lines 115-120):
  ```markdown
  ```{toctree}
  :hidden:
  :caption: Lab

  lab
  ```
  ```

  **After**:
  ```markdown
  ```{toctree}
  :hidden:
  :caption: Lab

  lab
  lab-gce
  lab-cloud-run
  ```
  ```
  (Order: chooser first, then the two labs — matches the card order on the
  chooser page.)

### Phase 5 — Verify the build

- [ ] 5.1 Build the docs with warnings-as-errors:
  ```shell
  make docs
  ```
  Expect exit 0 and `Docs built at docs/_build/html/index.html`. If `-W` reports
  `document isn't included in any toctree` or `unknown document`, a Phase 2-4
  step is incomplete — fix before proceeding.

- [ ] 5.2 Confirm the move preserved history and the content is intact:
  ```shell
  git log --follow --oneline docs/lab-gce.md | head -3
  git diff --stat
  ```
  `git log --follow` must show pre-move commits (AC5). `git diff --stat` /
  `git status` must show only `docs/lab.md`, `docs/lab-gce.md`,
  `docs/lab-cloud-run.md`, and `docs/index.md` touched (AC6).

- [ ] 5.3 (Optional spot check) Confirm the three Lab entries render in nav and
  the home-page card link resolves by opening
  `docs/_build/html/index.html` (or `make docs-serve`).

### Phase 6 — Registry + Beads (only if Beads backend active)

- [ ] 6.1 Add the `cloudrun-gce-lab` PRD (and this chapter) to `.agents/flows.md`
  if not already present (the registry currently has no `cloudrun-gce-lab`
  entry). Mark Chapter 4 `lab-gce-rename` planned.
- [ ] 6.2 If a Beads backend is active, create child tasks under epic
  `oracledb-vertexai-jw0.4` matching the proposed task list and attach context
  notes. **Skip all `bd` invocations if SessionStart reported Beads
  Missing/Disabled** — in that mode this `spec.md` is the source of truth.

---

## Risks & notes

- **`-W` brittleness**: the build only passes once all four files are in their
  final state. Do not run `make docs` between Phase 1 and Phase 4 expecting
  success — intermediate states (e.g. `lab.md` removed but toctree still says
  `lab`) will fail. Phase 5 is the single verification gate.
- **Forward-reference ownership**: `docs/lab-cloud-run.md` is a stub here on
  purpose. Its real walkthrough (Ch5) and verify/teardown sections (Ch6) are
  out of scope. The stub keeps `-W` green today.
- **Verbatim move**: use `git mv` + a single-line H1 edit + one inserted
  paragraph. Do not reformat or re-escape the moved body — the original uses
  MyST-escaped `\+` / `\!` that must survive.
