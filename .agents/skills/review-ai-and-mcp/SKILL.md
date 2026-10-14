---
name: review-ai-and-mcp
description: Review the native Gemini 3.8 Flash AgentRuntime, Vertex AI gemini-embedding-2 integration, LitestarMCP 0.15, LitestarA2A, and coordinate privacy.
---

# Native AI Runtime, MCP & A2A Review (`review-ai-and-mcp`)

Reviews changes under `src/app/domain/ai/`, `src/app/domain/chat/`, and `src/app/ioc/_ai.py`.

## Capsule Constraints

- Do not call disabled GHOP tools (`run_command`, `code_search`, `invoke_subagent`, `define_subagent`, `manage_subagents`, `read_url_content`, `search_web`, `schedule`, `generate_image`). Use `view_file`, `grep_search`, `find_by_name`, and `list_dir` only.
- Before emitting any review comment, read `references/false-positive-suppressions.md` and `references/ai-mcp-checklist.md`. Never flag patterns listed in `references/false-positive-suppressions.md`.
