---
name: review-python-backend
description: Review Litestar 2 controllers, Dishka DI providers, settings, litestar-security, and Python 3.12+ code hygiene across src/app/ and src/tests/.
---

# Python Backend Review (`review-python-backend`)

Reviews Python backend changes under `src/app/` and `src/tests/`.

## Capsule Constraints & Google3 Readability Override

- Do not call disabled GHOP tools (`run_command`, `code_search`, `invoke_subagent`, `define_subagent`, `manage_subagents`, `read_url_content`, `search_web`, `schedule`, `generate_image`). Use `view_file`, `grep_search`, `find_by_name`, and `list_dir` only.
- Override Google3 Python readability defaults: this repository uses 4-space indentation, 120-char line length, `pyproject.toml` Ruff/Mypy/Pyright rules, explicit `__init__.py` re-exports, `msgspec.Struct` schemas (`src/app/lib/schema.py`), Dishka `Inject[T]` handler-argument injection, and `litestar-security` `PublicController`.
- Before emitting any review comment, read `references/false-positive-suppressions.md` and `references/backend-checklist.md`. Never flag patterns listed in `references/false-positive-suppressions.md`.
