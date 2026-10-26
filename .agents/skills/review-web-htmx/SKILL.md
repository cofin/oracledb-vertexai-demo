---
name: review-web-htmx
description: Review Jinja2 templates, litestar-htmx partial responses, SSE chat frontend contracts, APEXlang store views, and keyless Google Maps URLs.
---

# Web, HTMX & Frontend Review (`review-web-htmx`)

Reviews changes under `src/app/domain/web/` (`src/app/domain/web/controllers/_pages.py` `PageController` and `src/app/domain/web/templates/`), `src/app/domain/chat/controllers/_chat.py`, `src/app/domain/chat/services/_telemetry.py`, `src/app/domain/products/controllers/_products.py`, `src/app/domain/products/controllers/_vector.py`, `src/app/domain/products/services/_maps.py`, `src/resources/`, and `src/apex/cymbal-coffee-ops/`.

## Capsule Constraints

- Do not call disabled GHOP tools (`run_command`, `code_search`, `invoke_subagent`, `define_subagent`, `manage_subagents`, `read_url_content`, `search_web`, `schedule`, `generate_image`). Use `view_file`, `grep_search`, `find_by_name`, and `list_dir` only.
- Before emitting any review comment, read `references/false-positive-suppressions.md` and `references/web-htmx-checklist.md`. Never flag patterns listed in `references/false-positive-suppressions.md`.
