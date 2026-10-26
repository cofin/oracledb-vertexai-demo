---
type: Spec
flow_id: web-and-shell-demo-recordings-and-docs
title: Deterministic VHS and Playwright Demo Video Recorders and Multi-Agent Sentence-Verified Documentation Refresh
state: planned
plan_revision: 1
plan_commit: null
state_revision: 0
current_task: null
last_operation: null
operation_targets: []
last_verified_checkpoint: null
created_at: 2026-10-24T19:41:00Z
updated_at: 2026-10-24T19:41:00Z
description: Fifth stacked PR adding deterministic VHS terminal/SQLcl tapes and runner, headless Playwright + FFmpeg browser video recorder for APEX 26.1 Vertex AI configuration and app creation, and a full sentence-by-sentence multi-agent audit and synchronization across all public Sphinx docs, READMEs, AGENTS.md rules, OKF knowledge chapters, and GHOP review skills.
tags:
  - demos
  - vhs
  - playwright
  - docs
  - apex
  - vertex-ai
parent_prd: platform-alignment-apex-vertex-prd
research: []
---

# Flow: Deterministic VHS and Playwright Demo Video Recorders and Multi-Agent Sentence-Verified Documentation Refresh

**Flow ID:** `web-and-shell-demo-recordings-and-docs`
**Parent PRD:** [`platform-alignment-apex-vertex-prd`](../platform-alignment-apex-vertex-prd/spec.md)
**Depends On:** [`apex-26-vertex-ai-and-app`](../apex-26-vertex-ai-and-app/spec.md) (PR 5 of 5 in stack)
**Proposed Branch & PR Title:** `docs/apex-vertex-demo-recordings` — `docs(demos): add automated vhs and playwright video recorders and refresh apex docs`

---

## Specification

### Code Analysis Summary

Files examined:

- `pyproject.toml:55-95`, `Makefile:191-210`, `manage.py` — Defines `[dependency-groups].docs` (`sphinx`, `furo`, `myst-parser`, `sphinx-copybutton`, `sphinx-design`) and `make docs`, with no `tools/demos/` package, `docs/_tapes/*.tape` files, or `[dependency-groups].demos` (`playwright>=1.50`) group yet.
- Host toolchain verification — `vhs` (`v0.11.0` at `~/.local/bin/vhs`), `ttyd` (`1.7.7` at `/usr/bin/ttyd`), `ffmpeg` (`8.1` with `libx264`, `libvpx-vp9`, `palettegen`, `paletteuse` at `/usr/bin/ffmpeg`), `sql` (`26.1.2.104.2054` at `~/.local/bin/sql`), and headless Chromium (`~/.cache/ms-playwright/chromium-*/chrome-linux/chrome` / `ROD_BROWSER_BIN`) are available for deterministic `.mp4` and `.gif` capture.
- Public docs (`README.md`, `CONTRIBUTING.md`, `SLIDES.md`, `src/app/db/migrations/README.md`, `docs/conf.py`, `docs/index.md`, `docs/tour.md`, `docs/lab.md`, `docs/lab-gce.md`, `docs/lab-cloud-run.md`, `docs/maps.md`, `docs/mcp-antigravity.md`, `docs/concepts/{agent-flow,rag,vector-search}.md`, `docs/reference/{quickstart,cli,api,internals,developers,brand-assets}.md`) — Still describe legacy `gvenzl` `make apex` / `OrdsSidecar` / `enable_AutoLob` / pre-refactor file paths and lack the APEX 26.1 Direct Vertex AI (`/endpoints/openapi`) + Litestar Gateway (`/api/apex/ai/v1`) and automated demo recording workflows.
- Agent rules, OKF knowledge chapters & review skills (`AGENTS.md`, `.agents/AGENTS.md`, `AGENTIC_REVIEW`, `src/tests/{README,AGENTS}.md`, `src/tests/{unit,integration}/AGENTS.md`, `.agents/bundles/product/*.md`, `.agents/bundles/knowledge/**/*.md`, `.agents/skills/**/*.md`) — Reference `enable_AutoLob=True`, `BaseStruct`, `agent_service.py`, `a2a/{card,executor}.py`, `system/services/_health.py`, `products/services/{_inventory,_maps}.py`, `make_container`, and `gvenzl` local APEX installation; every sentence across all documentation surfaces requires verification against the post-PR-4 codebase.

### Relevant Patterns

- [Documentation Styleguides](../../knowledge/styleguides/general.md) — Concise, factual prose without count-prefixed buzzwords, exclamation marks, or stale historical notes.
- [OKF Layout Tests](../../../../src/tests/unit/test_okf_layout.py) — Enforces valid YAML frontmatter, index reachability, and GHOP review skill structure.

### Requirements

- **PLAT-REQ-16 (Deterministic Shell & SQLcl VHS Tapes and Runner)**:
  - Create `tools/demos/__init__.py` and `tools/demos/shell.py` (`VHSRecorderConfig`, `VHSRecordResult`, `VHSRecorderError`, `resolve_chromium_binary`, `verify_vhs_prerequisites`, `record_vhs_tape`) resolving `ROD_BROWSER_BIN` automatically across `$PATH` and `~/.cache/ms-playwright/**/chrome`, setting `VHS_NO_SANDBOX=true`, and failing fast if `vhs` exits non-zero or produces missing/empty `.mp4` or `.gif` outputs.
  - Create `docs/_tapes/apex-vertex-ai-setup.tape` (showing `manage.py infra apex status`, `manage.py infra apex configure-vertex --mode direct --verify` against Vertex AI `/endpoints/openapi` `google/gemini-3.8-flash`, and a live `APEX_AI.GENERATE` coffee prompt) and `docs/_tapes/apexlang-workflow.tape` (showing `manage.py infra apex validate --alias cymbal-coffee-ops`, `import`, and `export` with SQLcl `26.1.2+`), plus `docs/_static/demos/.gitkeep` and prompt-gated `tools/scripts/record-live-demos.sh`.
- **PLAT-REQ-17 (Headless Playwright + FFmpeg Browser Video Recorder)**:
  - Add `[dependency-groups].demos = ["playwright>=1.50"]` in `pyproject.toml`.
  - Create `tools/demos/web.py` (`WebDemoScenario`, `WebDemoConfig`, `WebDemoResult`, `WebDemoError`, `transcode_webm_to_mp4_and_gif`, `record_web_scenario`) launching headless Chromium (`ignore_https_errors=True` for `https://localhost:8443`, matched `1280x720` `viewport` and `record_video_size`, injected `add_init_script` cursor + click-ripple + step-caption HUD, deterministic `expect(...)` waits, and `context.close()` flush) and transcoding `.webm` via `ffmpeg` to H.264 `yuv420p` `+faststart` `.mp4` and two-pass `palettegen`/`paletteuse` `.gif` for two scripted flows:
    1. `apex-configure-vertex-ai` — Logging into APEX 26.1 (`COFFEE` workspace) $\rightarrow$ Workspace Utilities $\rightarrow$ Web Credentials (`VERTEX_AI_CRED`) & Generative AI Services (`COFFEE_VERTEX_AI`, Direct Vertex AI `/endpoints/openapi`, `google/gemini-3.8-flash`, `Used by App Builder = Yes`) $\rightarrow$ Test Connection.
    2. `apex-create-vertex-app` — Opening Cymbal Coffee (`cymbal-coffee-ops`, APEX 26.1) in App Builder / Runtime and running a live Vertex AI Coffee Concierge recommendation on Page 6 (`APEX_AI.GENERATE`).
  - Wire `tools/demos/cli.py` into `manage.py` (`manage.py demos {shell,web,all,check}`) and add `docs-demos-shell`, `docs-demos-web`, `docs-demos-live`, and `docs-demos-clean` targets in `Makefile` while keeping `make docs` independent of `vhs` and Playwright.
- **PLAT-REQ-18 (Sentence-by-Sentence Multi-Agent Audit & Refresh of All Public Docs, Agent Rules, OKF Knowledge & Review Skills)**:
  - Update and audit **every sentence** across all public documentation files (`README.md`, `CONTRIBUTING.md`, `SLIDES.md`, `src/app/db/migrations/README.md`, `docs/conf.py`, and all 17 `docs/**/*.md` pages) using parallel verification subagents plus automated `src/tests/unit/tools/test_docs_accuracy.py` checks (verifying zero stale file paths, CLI commands, ports, env vars, driver feature keys, or broken links, and zero warnings from `make docs`).
  - Update and audit **every sentence** across all agent operational docs, OKF knowledge/product chapters, test guides, and GHOP review skills (`AGENTS.md`, `.agents/AGENTS.md`, `AGENTIC_REVIEW`, `src/tests/{README,AGENTS}.md`, `src/tests/{unit,integration}/AGENTS.md`, `.agents/bundles/product/*.md`, `.agents/bundles/knowledge/**/*.md`, `.agents/skills/**/*.md`) using parallel verification subagents so every claim matches the exact post-refactor codebase, verified by `validate_agentic_review.py` and `src/tests/unit/test_okf_layout.py`.

### Requirement-to-Task Traceability

| Requirement | Task | Verification Strategy | Primary Files | Primary Tests |
| --- | --- | --- | --- | --- |
| `PLAT-REQ-16` | `5.1` | `behavior_tdd` | `tools/demos/{__init__,shell}.py`, `docs/_tapes/{apex-vertex-ai-setup,apexlang-workflow}.tape`, `docs/_static/demos/.gitkeep`, `tools/scripts/record-live-demos.sh` | `src/tests/unit/tools/test_demo_recordings.py` |
| `PLAT-REQ-17` | `5.2` | `behavior_tdd` | `pyproject.toml`, `tools/demos/{web,cli}.py`, `manage.py`, `Makefile` | `src/tests/unit/tools/test_web_recorder.py` |
| `PLAT-REQ-18` | `5.3` | `documentation_validation` | `README.md`, `CONTRIBUTING.md`, `SLIDES.md`, `src/app/db/migrations/README.md`, `docs/conf.py`, `docs/**/*.md` | `src/tests/unit/tools/test_docs_accuracy.py` |
| `PLAT-REQ-18` | `5.4` | `documentation_validation` | `AGENTS.md`, `.agents/AGENTS.md`, `AGENTIC_REVIEW`, `src/tests/{README,AGENTS}.md`, `src/tests/{unit,integration}/AGENTS.md`, `.agents/bundles/product/*.md`, `.agents/bundles/knowledge/**/*.md`, `.agents/skills/**/*.md` | `src/tests/unit/test_okf_layout.py` |

---

## Implementation Plan

### Phase 1: VHS Shell Recorder, Playwright Web Recorder & Multi-Agent Sentence-Verified Documentation

- [ ] 5.1 Implement deterministic VHS shell/SQLcl recorder (`tools/demos/shell.py`), `.tape` scripts (`docs/_tapes/`), and prompt-gated live recording wrapper
- [ ] 5.2 Implement headless Playwright + FFmpeg browser video recorder (`tools/demos/web.py`, `tools/demos/cli.py`, `manage.py demos`, `Makefile` targets)
- [ ] 5.3 Refresh and run parallel multi-agent sentence-by-sentence factual audit across `README.md`, `CONTRIBUTING.md`, `SLIDES.md`, and all Sphinx `docs/` pages
- [ ] 5.4 Refresh and run parallel multi-agent sentence-by-sentence factual audit across `AGENTS.md`, test guides, OKF product/knowledge chapters, and GHOP review skills

---

## Continuity Snapshot

- **Active Flow / Lifecycle**: `web-and-shell-demo-recordings-and-docs` (`planned`)
- **Current Task & Claimant**: `null`
- **Last Verified Checkpoint**: `null`
- **Key Decisions**:
  - Split the sentence-by-sentence documentation audit across two strictly disjoint tasks (`5.3` for public `README.md` + Sphinx `docs/**` with `test_docs_accuracy.py` + `make docs`, and `5.4` for `AGENTS.md` + OKF `.agents/bundles/{product,knowledge}/**` + `.agents/skills/**` with `test_okf_layout.py` + `validate_agentic_review.py`) so parallel domain audit subagents inspect every sentence against live source files without overlap.
  - Keep `make docs` completely independent of `vhs`, `playwright`, and a live `adb-free` container by referencing static assets gracefully and gating live regeneration behind `make docs-demos-{shell,web,live}`.
- **Newest Discoveries**:
  1. Splitting documentation surfaces into `5.3` (22 public doc files) and `5.4` (57 agent/OKF/skill files) enables dedicated sentence-by-sentence subagent verification shards (~8–12 files per auditor subagent) checking every path, symbol, SQL clause, CLI flag, env var, and architectural claim against the repository.
- **Blockers & Unblock Conditions**: Depends on `apex-26-vertex-ai-and-app`.
- **Next Exact Step**: Claim and execute Task `5.1` (`tasks/5.1.md`) after `apex-26-vertex-ai-and-app` completes.
- **Plan Identity**: `plan_revision: 1`, `plan_commit: null`
- **State Identity**: `state_revision: 0`, `last_operation: null`, `operation_targets: []`
- **Relevant Knowledge Paths**:
  - `.agents/bundles/specs/platform-alignment-apex-vertex-prd/research/codebase-alignment-and-apex/research.md`
  - `.agents/bundles/knowledge/styleguides/general.md`
  - `src/tests/unit/test_okf_layout.py`
