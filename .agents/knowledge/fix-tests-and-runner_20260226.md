# Knowledge Entry: fix-tests-and-runner_20260226

- **Flow ID:** `fix-tests-and-runner_20260226`
- **Description:** Restore ADK runner UI context behavior and repair test-suite breakages
- **Completed:** 2026-02-26
- **Archived:** 2026-02-26
- **Topics:** adk, runner, chat, testing

<!-- truth: start -->
## Summary
This flow closed the remaining runner + controller + UI gaps after migration by preserving and rendering enriched ADK context in the SPA chat experience. It also verified backend stability through targeted and full-suite pytest runs.

## Patterns Elevated
- Preserve ADK runner context fields (`intent_details`, `search_details`, `store_details`, `products_found`, `stores_found`) through controller response payloads and UI rendering.

## Key Files
- `app/domain/chat/services/adk.py`
- `app/domain/chat/controllers.py`
- `src/js/web/src/routes/chat.tsx`
- `src/js/web/src/routes/chat.test.tsx`
- `tests/unit/test_chat_api_controller.py`
- `.agent/archive/fix-tests-and-runner_20260226/spec.md`

## Learnings (verbatim)

- ADKRunner already exposes rich context (`intent_details`, `search_details`, `store_details`, `products_found`, `stores_found`); the API/controller layer must preserve these fields to avoid UI regressions.
- Keep `/api/chat` response backward compatible while extending `search_metrics` with richer context payloads.
- UI verification is safer when tests assert rendered contextual fields (products/stores/results), not only final answer text.
<!-- truth: end -->
