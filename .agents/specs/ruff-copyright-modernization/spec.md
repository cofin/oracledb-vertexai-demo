# Specification: Ruff Copyright Modernization

Modernize license and copyright management by enabling Ruff's `CPY001` rule and migrating to SPDX-compliant headers.

## 1.0 Context
- **Flow ID:** `ruff-copyright-modernization`
- **Research:** `.agents/specs/ruff-copyright-modernization/research/research.md`
- **Tech Stack:** Ruff, Python 3.11+, SPDX/REUSE

## 2.0 Goals
- Enable Ruff's `CPY001` (`missing-copyright-notice`) rule to enforce copyright headers.
- Configure Ruff to recognize both traditional and SPDX-style headers (`SPDX-FileCopyrightText`).
- Migrate core project files to the modern header format.
- Add automation to handle the lack of auto-fix support in Ruff.

## 3.0 Implementation Plan

### Phase 1: Configuration
- [x] Uninstall traditional `pre-commit` and install `prek` (`uv tool install prek && prek install`).
- [x] Codify SPDX license mandate in `.agents/patterns.md` and styleguides.
- [x] Enable `preview = true` in `pyproject.toml`.
- [x] Remove `CPY001` from the `ignore` list in `pyproject.toml`.
- [x] Configure `[tool.ruff.lint.flake8-copyright]` with `author = "Google LLC"`.
- [x] Define `notice-rgx` to support both traditional and SPDX formats. [bb41489]
- [x] Verify that running `uv run ruff check` now flags missing/incorrect headers. [bb41489]

### Phase 2: Core Migration
- [ ] Update Python headers in `src/app/` to SPDX format (`SPDX-FileCopyrightText`).
- [ ] Update Python headers in `tools/` to SPDX format.
- [ ] Add SQL copyright comments with SPDX identifiers to `tools/oracle/*.sql`.
- [ ] Add JS/TS copyright headers with SPDX identifiers to `src/js/src/`.
- [ ] Ensure `__init__.py` files are covered.
- [ ] Verify compliance across all languages.

### Phase 3: Automation & Verification
- [ ] Add a pre-commit hook (e.g., `license-headers` or similar) to automatically insert headers since Ruff doesn't support fixing.
- [ ] Run full project validation (`make lint`) to ensure zero regressions.
- [ ] Document the new header standard in `.agents/code-styleguides/python.md`.

## 4.0 Acceptance Criteria
- `uv run ruff check` passes with `CPY001` enabled.
- All Python files in `src/` and `tools/` have a valid copyright header.
- New files automatically receive a header via pre-commit or documented manual steps.
- SPDX identifiers are used consistently.

## 5.0 Beads Tasks
- [x] task: Replace pre-commit with prek
- [x] task: Codify SPDX license mandate in project patterns and styleguides
- [x] task: Configure Ruff for CPY001 and SPDX support [bb41489]
- [ ] task: Migrate Python headers (src + tools) to SPDX format
- [ ] task: Add SQL copyright comments to tools/oracle/
- [-] task: Migrate src/js/ headers to SPDX format (obsolete — src/js deleted in Ch 4)
- [ ] task: Research/Implement Biome GritQL plugin for JS/TS header checks
- [ ] task: Integrate pre-commit automation for multi-language license headers
- [ ] task: Update Python styleguide with license requirements
