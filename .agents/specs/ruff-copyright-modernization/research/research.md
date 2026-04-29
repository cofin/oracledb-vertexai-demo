# Research: Ruff Copyright Rules & SPDX Support

## Executive Summary
- Ruff's `CPY001` (`missing-copyright-notice`) rule supports SPDX identifiers, specifically `SPDX-FileCopyrightText`.
- This rule is currently in **preview** and requires `preview = true` in the Ruff configuration.
- The rule is **not auto-fixable** by Ruff; headers must be added manually or via external tools.
- Migration to SPDX flags would allow for more concise and machine-readable headers while maintaining compliance.

## Codebase Analysis

### Current State
- **Pattern:** Python headers use the format `# Copyright 2024 Google LLC`.
- **SQL Headers:** Currently lack copyright/license information (only contain descriptive comments).
- **JS/TS Headers:** Currently lack copyright/license information.
- **Ruff Config:** `CPY001` is currently ignored in `pyproject.toml`.
- **License:** The project is licensed under Apache License 2.0 (SPDX: `Apache-2.0`).

### Relevant Modules
- All Python files in `src/` and `tools/` require copyright headers.
- All SQL files in `tools/oracle/` should include copyright and SPDX identifiers.
- All JS/TS files in `src/js/src/` should include copyright and SPDX identifiers.

## Library Documentation

### Ruff (`CPY001`)
- **Version Support:** SPDX support was added in version 0.3.5.
- **Detection Range:** Checks the first 4096 bytes of each file.
- **SPDX Recognition:** Recognizes `SPDX-FileCopyrightText` as a valid copyright notice.
- **Config Example:**
  ```toml
  [tool.ruff]
  preview = true

  [tool.ruff.lint]
  select = ["CPY001"]

  [tool.ruff.lint.flake8-copyright]
  author = "Google LLC"
  ```

### Biome (JS/TS)
- **Status:** No native built-in rule for license headers.
- **Workaround:** Can be implemented via **GritQL plugins** (Biome 2.0+) but is diagnostic-only (no auto-fix).
- **Recommendation:** Use an external tool (e.g., `addlicense` or `reuse`) for consistent multi-language header management.


## Prior Art

### Internal References
- No existing use of SPDX identifiers was found in the codebase.

### External Patterns
- **REUSE Specification:** A popular standard for managing license and copyright information using SPDX identifiers.
- **Google Open Source Guidelines:** Google generally supports SPDX identifiers in new projects to improve clarity and tool compatibility.

### Recommended Approach
1. **Enable Preview Mode:** Set `preview = true` in `pyproject.toml`.
2. **Enable CPY001:** Remove `CPY001` from the `ignore` list and add it to `select`.
3. **Configure Author:** Set `author = "Google LLC"` in `[tool.ruff.lint.flake8-copyright]`.
4. **Migration:** Update existing headers to include SPDX flags if desired, or ensure the current format matches the `notice-rgx` if we keep both.
5. **Automation:** Consider adding a pre-commit hook like `reuse` or `license-headers` to handle the lack of auto-fix in Ruff.

## Risk Assessment

### Technical Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Preview Rule Stability | Medium | Low | Ruff's preview rules are generally stable but might have breaking changes in future releases. |
| Lack of Auto-fix | High | Medium | Manual updates required for all files; risk of inconsistency without a dedicated tool. |
| Configuration Complexity | Low | Low | Requires careful regex if supporting multiple header formats. |

### Integration Risks
- **Backward Compatibility:** Existing files without headers will fail linting once enabled.

### Recovery Strategy
- **Rollback Plan:** Re-add `CPY001` to the `ignore` list in `pyproject.toml`.
- **Checkpoint Strategy:** Implement changes module by module if the codebase is large.

## Open Questions
- Does Google Legal require the *full* license text in every file, or is the SPDX identifier sufficient for this project? (Usually, SPDX + a single root LICENSE file is preferred for modern projects).
