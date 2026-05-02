# Learnings: Ruff Copyright Modernization

## [2026-04-29 17:37] - Phase 1 Task 8: Replace pre-commit with prek

- **Implemented:** Uninstalled traditional `pre-commit` and installed `prek`.
- **Reason:** `prek` is a faster, Rust-based alternative that supports existing `.pre-commit-config.yaml` files.
- **Verification:** Ran `prek run --all-files`. Applied standard fixes to multiple markdown files.
- **Learning:** `prek` is significantly faster and uses `uv` for dependency management.

## [2026-04-29 17:40] - Phase 1 Task 9: Codify SPDX license mandate in project patterns and styleguides

- **Implemented:** Updated `.agents/patterns.md` and `.agents/code-styleguides/python.md`.
- **Mandate:** Concisely use SPDX identifiers (`SPDX-FileCopyrightText` and `SPDX-License-Identifier`) instead of full license blocks.
- **Pattern:**
  - Python/SQL/Shell: `# SPDX-FileCopyrightText: 2024 Google LLC`
  - JS/TS: `// SPDX-FileCopyrightText: 2024 Google LLC`

---

## 2026-04-30 — Configure Ruff for CPY001 + SPDX support [bb41489]

- **Discovery:** `select = ["ALL"]` + `preview = true` already activates CPY001; no need to remove from ignore (it never was). The default Ruff regex `(?i)Copyright\s+\d{4}…` accidentally accepts current headers because every line still includes literal `Copyright YYYY`.
- **Decision:** Add explicit `notice-rgx = '(?i)(?:Copyright|SPDX-FileCopyrightText:)\s+(?:Copyright\s+)?(?:\(C\)\s+)?\d{4}([-,]\s*\d{4})*'` to lock acceptance criteria — both traditional `Copyright YYYY Google LLC` and SPDX `SPDX-FileCopyrightText: YYYY Google LLC` (with or without literal `Copyright`).
- **Boundary:** `.agents/` is project metadata, not project code. The single Python collection there (`agent-ui-update_20251024/tmp/{benchmark,load_test}_streaming.py`, 379 LOC of archived benchmarks) was generating ~60 lint errors unrelated to the demo. Added `extend-exclude = [".agents"]` so spec-tree archival material is out of lint scope.
- **Pinning:** New `src/tests/unit/test_copyright_config.py` (12 cases) asserts author, ignore-list absence, regex match/reject behavior, and full src/ Python coverage — locks the configuration against silent regressions.
- **Followup:** `a0l.4 (Migrate src/js/ headers)` is now obsolete because Ch 4 deleted the entire src/js/ React tree. Marked `[-]` in spec; Beads task should be closed as obsolete.

---

## 2026-05-02 — Prek license-header automation [d0b1c66]

- **Implemented:** Added `tools/license_headers.py` and a local `license-headers` hook that runs before Ruff, so missing source-owned headers are inserted before CPY001 evaluates files.
- **Coverage:** The tool handles Python/shell/YAML/TOML/Makefile/Dockerfile, JS/TS, SQL, CSS, and Jinja templates while skipping generated and public asset outputs.
- **Gotcha:** Dockerfile parser directives such as `# syntax=docker/dockerfile:1.7` must remain first; the insertion logic preserves them before adding the header.
