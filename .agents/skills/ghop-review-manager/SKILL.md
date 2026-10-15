---
name: ghop-review-manager
description: Maintain root AGENTIC_REVIEW, domain review skills (.agents/skills/review-*), and false-positive suppression catalogs for GHOP AI code review.
---

# GHOP AI Code Review Manager

Maintains the root `AGENTIC_REVIEW` textproto and domain-segmented review skills for GitHub On-Prem (`code-review[bot]`).

## Architecture & Constraints

1. **Root `AGENTIC_REVIEW`**:
   - Must live at the repository root (`AGENTIC_REVIEW`) and be merged to `main` (GHOP stages skills from the default branch before PR checkout).
   - Declare one `review_capability_skills: "<path>"` scalar string per line. Comment lines (`#`) must never contain the token `review_capability_skills`.
2. **Capsule Tool Restrictions**:
   - In GHOP capsules, `run_command`, `code_search`, `invoke_subagent`, `define_subagent`, `manage_subagents`, `read_url_content`, `search_web`, `schedule`, and `generate_image` are disabled.
   - Review skills must never instruct the reviewer to call those disabled tools; rely strictly on `view_file`, `grep_search`, `find_by_name`, and `list_dir`.
3. **Closed-Loop False-Positive Suppressions**:
   - Each `review-*` skill includes `references/false-positive-suppressions.md` with sequential `## \`FP-<DOMAIN>-<NN>\`` entries.
   - Validate changes with `.agents/skills/ghop-review-manager/scripts/validate_agentic_review.py`.
