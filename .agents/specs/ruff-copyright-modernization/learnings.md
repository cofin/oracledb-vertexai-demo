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
