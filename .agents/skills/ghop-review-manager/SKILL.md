---
name: ghop-review-manager
description: Maintain root AGENTIC_REVIEW, domain review skills (.agents/skills/review-*), and false-positive suppression catalogs for GHOP AI code review.
---

# GHOP AI Code Review Manager

Maintains the root `AGENTIC_REVIEW` textproto and domain-segmented review skills for GitHub On-Prem (`code-review[bot]`).

## Architecture & Constraints

1. **Root `AGENTIC_REVIEW`**:
   - Must live at the repository root (`AGENTIC_REVIEW`) and be merged to `main` (GHOP stages skills from the default branch before PR checkout).
   - Registers the four domain skills in exact order: `.agents/skills/review-python-backend/SKILL.md`, `.agents/skills/review-oracle-sqlspec/SKILL.md`, `.agents/skills/review-ai-and-mcp/SKILL.md`, and `.agents/skills/review-web-htmx/SKILL.md`.
   - Declare one `review_capability_skills: "<path>"` scalar string per line. Comment lines (`#`) must never contain the token `review_capability_skills`.
2. **Capsule Tool & Progressive-Disclosure Restrictions**:
   - Every `review-*/SKILL.md` must stay strictly below `150` lines (`MAX_SKILL_LINES = 150`) and carry matching YAML frontmatter (`name` and `description`).
   - In GHOP capsules, `run_command`, `code_search`, `invoke_subagent`, `define_subagent`, `manage_subagents`, `read_url_content`, `search_web`, `schedule`, and `generate_image` are disabled.
   - Any line in `review-*` markdown files mentioning a disabled tool name must include an explicit negation token (`disabled`, `never`, `do not`, `don't`, `cannot`, `not available`); instruct reviewers to rely strictly on `view_file`, `grep_search`, `find_by_name`, and `list_dir`.
3. **Closed-Loop False-Positive Suppressions & Repository Path Hygiene**:
   - Each `review-*` skill includes a domain checklist and `references/false-positive-suppressions.md` with sequential, globally unique `## \`FP-<DOMAIN>-<NN>\`` headings starting at `01` (`FP-PY-*`, `FP-ORA-*`, `FP-AI-*`, `FP-WEB-*`).
   - Every concrete backticked path starting with `src/`, `tools/`, `Makefile`, `pyproject.toml`, or `manage.py` inside `review-*` files must exist on disk, and all skill docs must stay aligned with current domain modules (`FrozenBaseStruct`, `OracleLoaderService`, `create_container()`, SQLSpec `0.69.0` `fetch_lobs=False`, `ApexController`, `ApexAIController`, `src/apex/cymbal-coffee-ops/`, `tools/oracle/`) without referencing retired symbol tokens checked by `src/tests/unit/test_okf_layout.py`.
   - Validate changes with `PYTHONDONTWRITEBYTECODE=1 uv run --no-sync python .agents/skills/ghop-review-manager/scripts/validate_agentic_review.py`.
