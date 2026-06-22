# Research: Grounded Product RAG Response Guard

**Workspace**: `.agents/research/research_grounded_product_rag_guard/`
**Status**: Complete
**Type**: Integration / Refactoring
**Date**: 2026-06-22
**Branch**: `fix/product-improve`

> **Goal**: Review the branch change that makes product responses more dynamic, research current SQLSpec and ADK 2.0 usage, and identify the safest way to keep the UX warmer without losing the no-hallucination guarantee.

---

## Executive Summary

- **The branch improves tone but weakens the guard.** `_compose_grounded_answer()` asks Gemini for a final customer-facing answer plus `mentioned_products`, then `_validated_grounded_answer()` only validates the declared product list. A model can put unsupported claims in `answer` while leaving `mentioned_products` empty or incomplete, and the app will return the text.
- **The safest pattern is "model selects, Python renders."** Use the LLM for structured selection/routing among retrieved candidates, then render the final customer text from trusted candidate rows. Do not return model-authored product names, prices, or product details as the final answer.
- **ADK 2.0 points in the same direction.** Current ADK docs emphasize graph/dynamic workflows for controlled routing and programmatic logic. This Product RAG branch is already deterministic enough that it does not need a new dynamic workflow yet, but it should keep business invariants in Python rather than in prompt wording.
- **Gemini structured output is useful, but not sufficient by itself.** The Google Gen AI SDK supports `response_mime_type="application/json"` plus `response_schema` / `response_json_schema`. That should be used to constrain a selection object, then the app must still validate every selected id/name against the retrieved candidate set.
- **SQLSpec ADK state should stay on the service path.** SQLSpec's ADK session service persists events and durable state atomically through `append_event_and_update_state()`. Direct `store.update_session_state()` for display history may be acceptable as an app-side shortcut, but it bypasses stale-session protection and should be revisited or at least tested for concurrent writes.
- **Minimal production hardening is small.** Add timeout/fallback, move GenAI response composition behind `VertexAIService` or a chat service boundary, bump the response cache version, use public ADK workflow imports, and add tests for undeclared hallucinations.

---

## Scope

Reviewed local branch changes and current project patterns:

- `src/app/domain/chat/services/_adk_grounding.py`
- `src/app/domain/chat/services/adk.py`
- `src/app/domain/chat/services/workflow.py`
- `src/app/lib/settings.py`
- `pyproject.toml`
- `uv.lock`
- `src/tests/unit/app/domain/chat/services/test_adk_grounding.py`
- `src/tests/integration/app/domain/chat/services/test_chat_workflow.py`
- `.agents/knowledge/guides/adk-agent-patterns.md`
- `.agents/knowledge/guides/architecture.md`
- `.agents/knowledge/guides/oracle-vector-search.md`

Documentation inventory additionally checked:

- `AGENTS.md`
- `README.md`
- `docs/index.md`
- `docs/tour.md`
- `docs/concepts/rag.md`
- `docs/concepts/agent-flow.md`
- `docs/reference/internals.md`
- `docs/reference/api.md`
- `.agents/patterns.md`
- `.agents/tech-stack.md`
- `.agents/specs/docs-accuracy/spec.md`
- `.agents/knowledge/project-guide.md`

External references checked on 2026-06-22:

- ADK 2.0 overview: https://adk.dev/2.0/
- ADK workflows overview: https://adk.dev/workflows/
- ADK dynamic workflows: https://adk.dev/graphs/dynamic/
- ADK session state: https://adk.dev/sessions/state/
- SQLSpec ADK quickstart: https://sqlspec.dev/extensions/adk/quickstart.html
- SQLSpec ADK API reference: https://sqlspec.dev/reference/extensions/adk.html
- Gemini structured output: https://ai.google.dev/gemini-api/docs/structured-output
- Google Gen AI Python SDK docs: https://googleapis.github.io/python-genai/
- Installed Gen AI SDK types: `.venv/lib/python3.12/site-packages/google/genai/types.py`

---

## Pre-Implementation Branch Behavior

The reviewed branch revision added:

- `_GROUNDED_ANSWER_INSTRUCTION`
- `_GROUNDED_ANSWER_SCHEMA`
- `_candidate_block()`
- `_validated_grounded_answer()`
- `_compose_grounded_answer()`

That Product RAG route retrieved/coerced product rows, asked Gemini to generate a JSON object with `answer`, `off_menu`, `off_menu_term`, and `mentioned_products`, and returned the `answer` if all declared `mentioned_products` matched the candidate names.

The intent is right: give the model room to handle off-menu requests like "Folgers" and preference phrasing like "something bold" while falling back to `_grounded_product_answer()` when generation fails.

The bug is the trust boundary:

```text
model answer text -> app returns directly
model mentioned_products -> app validates
```

The answer text is the user-visible payload. Validating only a model-provided sidecar list does not prove the answer is grounded.

The integration fake currently reinforces this problem:

```python
{
    "answer": "That bold roast is a great way to wake up.",
    "mentioned_products": [],
}
```

That passes the guard because no product names are declared, even though the answer could contain unsupported copy.

---

## Library Findings

### ADK 2.0

ADK 2.0 is generally available for Python as of May 19, 2026. The 2.0 docs emphasize graph-based workflows, dynamic workflows, and collaborative workflows for more controlled agent execution. The migration notes also call out new Event fields (`node_info`, `output`) and warn that bypassing the workflow runner's event control can break determinism.

Relevant implications:

- Use public workflow APIs where possible. `workflow.py` should import `FunctionNode` from `google.adk.workflow`, not from `google.adk.workflow._function_node`.
- Product RAG does not need to become a dynamic workflow just to produce warmer copy. It is a deterministic branch with retrieved candidates and a final response. Keep it as a direct route until it needs resumable multi-node logic.
- If this logic grows, ADK dynamic workflows are a good fit for a programmatic Product RAG flow: retrieve candidates, select, validate, render, and persist state as explicit nodes.

### Google Gen AI Structured Output

The official Gemini structured-output docs frame schema output as useful for data extraction, structured classification, and agentic workflows. That maps well to this use case if the model returns a structured selection, not final product copy.

The installed SDK supports:

- `GenerateContentConfig.response_mime_type`
- `GenerateContentConfig.response_schema`
- `GenerateContentConfig.response_json_schema`
- `HttpOptions.timeout` in milliseconds

Important caveat from the installed type docs: `response_schema` is a subset of OpenAPI schema, and `response_json_schema` accepts JSON Schema but not every feature is supported. Therefore dynamic constraints like "selected product id must be one of these candidate ids" should be validated in Python even if the prompt/schema also includes them.

### SQLSpec ADK

SQLSpec's ADK quickstart says events are persisted automatically when the session service is used with an ADK runner, and each `append_event()` atomically stores the event plus durable state via `append_event_and_update_state()`.

The SQLSpec API reference is stronger: `append_event()` persists the event and post-append durable state atomically, updates the in-memory session after persistence, strips `temp:` keys, and raises on stale sessions instead of silently overwriting.

Relevant implication:

- `ADKRunner._append_display_history()` currently calls `self._session_service.store.update_session_state(session_id, state)` directly. That bypasses the service's event/state atomicity and stale-session behavior. This may be acceptable for app-side display-history state if the team explicitly wants a side channel, but it should be tested and documented. The safer default is to update durable state through ADK events/state deltas.

---

## Prior Art And Pattern Fit

### Pattern A: LLM as final copywriter

Pre-fix branch pattern. The model writes final customer text and the app tries to guard it after the fact.

Pros:

- Most dynamic wording.
- Small code diff.

Cons:

- Not bulletproof unless the app performs robust entity/fact extraction over the final answer.
- Sidecar `mentioned_products` is self-reported by the same model being checked.
- Prices, details, and unsupported product names can slip through unless every text claim is parsed.

Verdict: not recommended for a "bullet proof" route.

### Pattern B: LLM as selector, Python as renderer

The model returns only a structured object such as:

```json
{
  "mode": "off_menu_alternative",
  "selected_product_ids": ["SKU-123"],
  "off_menu_term": "Folgers",
  "preference_summary": "bold morning coffee"
}
```

The app validates `selected_product_ids` against retrieved candidates and renders final copy from DB fields.

Pros:

- Keeps dynamic intent handling and off-menu recognition.
- Prevents model-authored product names, prices, and product details from reaching the user.
- Easy to unit test.
- Fits ADK 2.0's programmatic workflow guidance.

Cons:

- Wording variety is template-based unless renderer variants are added.
- Requires a small renderer layer.

Verdict: recommended.

### Pattern C: Hybrid renderer with constrained reason phrase

The model selects product ids and optionally emits a short reason phrase, but the app never lets the reason introduce product names, prices, or facts. The renderer inserts trusted product data.

Pros:

- Slightly more natural phrasing than pure templates.
- Still blocks model-authored catalog facts.

Cons:

- The reason phrase needs strict sanitization, max length, and fallback.
- More complex than Pattern B.

Verdict: acceptable later, but start with Pattern B.

---

## Recommended Approach

### 1. Replace final-answer generation with structured selection

Add a small structured response schema with fields like:

- `mode`: `recommend`, `off_menu_alternative`, `no_safe_selection`
- `selected_product_ids`: list of stable candidate identifiers, or names if ids are not available in every row
- `off_menu_term`: customer-named item that Cymbal does not carry
- `preference_summary`: optional short phrase, not directly rendered as product fact

Validation rules:

- `mode` must be one of the known values.
- Every selected id/name must exist in the current candidate set.
- `recommend` and `off_menu_alternative` require at least one selected product when candidates exist.
- `no_safe_selection` must not include selected products.
- Ignore or reject any model-provided price, product description, or product name outside identifiers.
- On any parse/validation failure, return `_grounded_product_answer()`.

Renderer rules:

- Product names come only from the candidate rows.
- Prices come only from `_format_price(product.get("price"))`.
- Descriptions come only from candidate rows, and only when a renderer variant needs them.
- Off-menu copy may include `off_menu_term` after trimming and length-limiting.

Example rendered outputs:

- Recommendation: `For something bold, try Sumatra Dark ($4.00). It is bold and earthy.`
- Off-menu: `Cymbal Coffee does not carry Folgers, but Sumatra Dark ($4.00) is the closest match for a bold cup.`
- No safe selection: existing deterministic fallback.

### 2. Add latency controls

Wrap the composition call in a small timeout:

```python
async with asyncio.timeout(get_settings().chat.grounded_answer_timeout_seconds):
    ...
```

If adding a setting is more churn than desired, use a module constant first, for example `2.5` seconds. The fallback should be deterministic and silent to the user.

The SDK also exposes `HttpOptions.timeout` in milliseconds, but this project already has a shared `VertexAIService` client. A per-call `asyncio.timeout()` is the smallest local guard; client-level timeout can be a later service configuration cleanup.

### 3. Move the GenAI call behind a service boundary

Do not reach through:

```python
tools_service.vertex_ai_service.client.aio.models.generate_content(...)
```

from `_adk_grounding.py`.

Better options:

- Add `VertexAIService.generate_structured_content(...)`.
- Or add `AgentToolsService.compose_grounded_product_selection(...)` if this should remain chat-specific.

This centralizes model config, credential classification, logging, SDK API-version choices, and future timeout settings.

### 4. Bump response cache version

The generated response semantics changed. Before this hardening pass, `CHAT_RESPONSE_CACHE_VERSION` defaulted to `menu-grounded-v1`.

Set it to a new value, for example:

```text
menu-grounded-v2
```

Otherwise old cached answers can mask the new guard behavior during manual testing and demos.

### 5. Use public ADK imports

Change:

```python
from google.adk.workflow._function_node import FunctionNode
```

to:

```python
from google.adk.workflow import FunctionNode
```

The installed package publicly exports `FunctionNode`, and the ADK docs show workflow APIs coming from `google.adk.workflow`.

### 6. Revisit display-history state persistence

Preferred: persist display-history updates through ADK event/state delta mechanisms so SQLSpec's `SQLSpecSessionService.append_event()` remains the durable write boundary.

If preserving direct `store.update_session_state()`:

- Add a comment explaining why display history is intentionally app-side state.
- Add a unit test or integration test for last-write/concurrency behavior.
- Keep `temp:` and request-scoped privacy rules intact. Browser coordinates must not be persisted.

### 7. Tighten ADK dependency lower bound

Before this hardening pass, `pyproject.toml` allowed:

```text
google-adk>=2.0.0b1
```

The lockfile has `google-adk==2.3.0`, and ADK 2.0 is GA. If the branch depends on ADK 2 workflow surfaces, prefer a GA lower bound:

```text
google-adk>=2.0.0
```

or, if local tests confirm 2.3 behavior is required:

```text
google-adk>=2.3.0
```

Do not keep a beta lower bound unless the project intentionally supports pre-GA ADK 2.

---

## Docs And Guides To Update

These documentation updates are part of the work. Do not merge the runtime
change without updating the live guidance, because the docs are the source that
future agents will follow.

### Accuracy rule

Do not document the recommended selector/renderer architecture as current until
the code actually implements it.

Pre-implementation branch state observed during research:

- `_compose_grounded_answer()` asks Gemini for final answer text.
- `_validated_grounded_answer()` validates only the model-declared
  `mentioned_products` sidecar.
- Therefore docs must not claim the current branch is bulletproof.

Target state for the implementation:

- Gemini may return a structured product selection only.
- Python validates selected ids/names against retrieved candidates.
- Python renders the final customer answer from candidate rows.
- Product RAG still emits a single final SSE event and no speculative deltas.

### Must update: active agent guidance

| File | Required update |
|------|-----------------|
| `AGENTS.md` | In `ADK Chat`, add the Product RAG guard rule: use classifier-first routing; the model may only produce structured selection/routing data; final product names, prices, and descriptions must come from retrieved rows. Keep the note that browser coordinates are request-scoped and not persisted. |
| `.agents/patterns.md` | Replace the pre-fix Product RAG paragraph that says `_compose_grounded_answer()` writes final words and "the no-hallucination guarantee holds." That claim is inaccurate for the reviewed branch state. The replacement should state the implemented target: structured selection, Python validation, Python rendering, timeout/fallback, and `AIServiceUnconfigured` for credential failures. |
| `.agents/knowledge/project-guide.md` | Update `AI And Chat` so Product RAG is described as "structured selection plus deterministic rendering from returned Cymbal Coffee products," not generic model-authored copy. Preserve the `last_products` context rule for availability follow-ups. |
| `.agents/knowledge/guides/adk-agent-patterns.md` | Update `Runtime Shape`, `Closure-Bound Tools`, `Streaming`, and `Cache And Metrics` with the new Product RAG path. The guide should say grounded routes do not stream deltas; Product RAG may use Gemini structured output for selection; final text is rendered from row data; guard failures/timeouts fall back to `_grounded_product_answer()`. |
| `.agents/knowledge/guides/architecture.md` | Update `Chat Flow` so the Product RAG branch shows vector search -> structured selection -> validation -> renderer -> final event. If the implementation moves the GenAI call into `VertexAIService`, mention that boundary here. |
| `.agents/tech-stack.md` | If `pyproject.toml` changes from `google-adk>=2.0.0b1`, update the ADK version line. Also revise `Chat Runner Flow` from "formatted only from returned rows" to the precise target wording: selected by structured output if used, rendered only from returned rows. |
| `.agents/specs/docs-accuracy/spec.md` | Add a Product RAG guard chapter or checklist item so docs-accuracy work verifies these exact claims. The existing docs-accuracy spec predates this branch and will not catch the new `_compose_grounded_answer()` wording risk. |

### Must update: published docs

| File | Required update |
|------|-----------------|
| `README.md` | Change "Deterministic product, store, and availability chat routes" if Product RAG keeps an LLM selection call. Suggested wording: "Grounded product, store, and availability chat routes with deterministic rendering and an ADK 2.0 general-chat fallback." |
| `docs/index.md` | The Vertex AI card currently says "`gemini-embedding-2-preview` for retrieval, Gemini for the answer." If final text is Python-rendered, change this to "Gemini for routing/selection" or "Gemini assists selection; Oracle rows render answers." Keep the hero claim that answers are grounded in real menu rows. |
| `docs/tour.md` | Step 5 and the diagram currently say the runner formats one grounded final event. Keep that if true, but add the selector step if implemented: Flash-Lite intent -> embedding -> Oracle candidates -> Gemini structured selection -> Python renderer -> SSE final. |
| `docs/concepts/rag.md` | The diagram currently shows grounding context -> Gemini -> grounded answer, while the text says the deterministic route formats final answers from rows. Update the diagram and text to avoid implying Gemini writes final catalog facts. Recommended diagram: Oracle vector match -> candidate rows -> structured selector -> validator -> row renderer -> grounded answer. |
| `docs/concepts/agent-flow.md` | In `Grounded Routes` and `ADK Fallback`, clarify that Product RAG final text is rendered from retrieved rows. If the general ADK fallback calls the product tool and gets relabeled to `PRODUCT_RAG`, it must use the same selector/validator/renderer path. |
| `docs/reference/internals.md` | Update `Deterministic vs ADK latency`. If Product RAG includes an extra structured-generation call, the docs should not imply "no LLM call" on the route; it should say "no speculative deltas" and explain the bounded selector call. Add any new telemetry fields such as `grounded_answer_mode` or `grounded_answer_ms` to the metrics table if they are implemented. |
| `docs/reference/api.md` | If a public `VertexAIService.generate_structured_content()` or `AgentToolsService.compose_grounded_product_selection()` method is added and becomes part of the documented service boundary, include it through the existing autodoc scope or explain why it remains internal. |

### Optional update: plans and diagrams

| File | Required update |
|------|-----------------|
| `.agents/plans/ADK2.md` | This is an aspirational migration plan, not live docs. Do not rewrite it as current behavior. Add only a caveat if the selector/renderer change creates a conflict with the plan's ADK state or memory examples. |
| `docs/reference/cli.md` | No change expected unless a new cache-clear or model-info behavior is added for the Product RAG response cache version. |
| `docs/maps.md` | No change expected. The coordinate privacy rules stay the same. |
| `docs/concepts/vector-search.md` | No change expected unless the Product RAG SQL shape changes to include stable ids/SKUs for selection. If it does, update the `ProductMatch` row description. |

### Documentation validation commands

Use these checks after implementation and docs edits:

```bash
rg -n "no-hallucination|hallucination|_compose_grounded_answer|Gemini for the answer|formats the final answer|deterministic product" AGENTS.md README.md docs .agents --glob '!**/archive/**' --glob '!**/research/**'
rg -n "google-adk>=2.0.0b1|ADK 2.2|ADK 2.0" AGENTS.md README.md docs .agents pyproject.toml --glob '!**/archive/**' --glob '!**/research/**'
```

Manual check: every remaining mention of "deterministic Product RAG" must mean
deterministic final rendering, not "no model call exists."

---

## Implementation Sketch

High-level structure:

```python
class GroundedProductSelection(msgspec.Struct):
    mode: Literal["recommend", "off_menu_alternative", "no_safe_selection"]
    selected_product_ids: list[str] = []
    off_menu_term: str = ""
    preference_summary: str = ""
```

Selection flow:

```text
1. Coerce candidate product rows.
2. Build compact candidate payload with ids/names/prices/descriptions.
3. Ask Gemini for a structured selection object.
4. Parse JSON.
5. Validate selected ids/names against candidates.
6. Render final customer answer from candidate rows.
7. On any timeout, parse failure, validation failure, or non-credential SDK error, use deterministic fallback.
8. On credential/config errors, raise AIServiceUnconfigured as today.
```

Candidate payload should include stable identifiers when available. If the current Product RAG rows do not include ids/SKUs, update the named SQL mapping to include them; otherwise use exact names as the temporary key and validate casefolded names.

Telemetry fields worth recording in `search_metrics`:

- `grounded_answer_mode`: `structured`, `template`, `timeout`, `rejected`, `error`
- `grounded_answer_ms`
- `grounded_answer_error_type`
- `grounded_selected_count`

These can stay internal and should not surface in the customer copy.

---

## Test Plan

Focused tests first:

- `src/tests/unit/app/domain/chat/services/test_adk_grounding.py`
  - rejects answer text hallucination when `mentioned_products` is empty
  - accepts off-menu request only through a validated selected candidate
  - rejects selected product id/name not in candidates
  - falls back on malformed JSON
  - falls back on timeout
  - falls back on non-credential SDK error
  - raises `AIServiceUnconfigured` on credential/config errors
  - skips model call for empty candidates
  - renders prices from candidate rows, not model output
- `src/tests/unit/app/domain/chat/services/test_adk.py`
  - response cache key uses bumped default cache version
  - deterministic Product RAG still writes expected final event fields
  - display history / `last_products` still persists as expected if that path changes
- `src/tests/integration/app/domain/chat/services/test_chat_workflow.py`
  - update fake model to return structured selection, not final copy
  - add one off-menu scenario if integration test cost stays low

Then run:

```bash
uv run pytest src/tests/unit/app/domain/chat/services/test_adk_grounding.py -q
uv run pytest src/tests/unit/app/domain/chat/services/test_workflow.py src/tests/unit/app/domain/chat/services/test_adk.py -q
make lint
make test
```

Oracle-backed integration tests only need to be run if the named SQL or row mapping changes.

---

## Risk Assessment

| Risk | Severity | Recommendation |
|------|----------|----------------|
| Model answer text can contain undeclared unsupported products/details | High | Do not return model-authored final answer text |
| Slow extra Gemini call adds latency to Product RAG | Medium | Add timeout and deterministic fallback |
| GenAI client access leaks SDK details into grounding module | Medium | Move call behind `VertexAIService` or chat service boundary |
| Existing response cache hides behavior change | Medium | Bump cache version |
| Direct ADK store state updates race with SQLSpec session service semantics | Medium | Prefer service/event path or add concurrency coverage |
| Private ADK import breaks on package cleanup | Low | Use public `google.adk.workflow` export |
| ADK beta lower bound permits older pre-GA behavior | Low | Raise lower bound to GA/current tested version |

---

## Open Decisions

1. **Renderer strictness**: Recommended strict mode is "no model-authored customer copy." If the demo strongly needs more variety, allow only sanitized reason snippets after the first strict version lands.
2. **Candidate key**: Prefer stable product ids/SKUs in the selection schema. Use names only if the current Product RAG result shape cannot cheaply include ids.
3. **Timeout setting**: Decide whether to add `ChatSettings.grounded_answer_timeout_seconds` now or use a private constant for the first hardening pass.
4. **ADK state path**: Decide whether `display_history` is ADK state or app-side side-channel state. If app-side, document and test it.
5. **Dependency lower bound**: Choose `google-adk>=2.0.0` versus `>=2.3.0` based on the oldest version the project wants to support.

---

## Recommended Next Work

1. Patch the guard to structured selection plus deterministic rendering.
2. Add timeout/fallback and cache-version bump in the same PR.
3. Move GenAI structured generation behind a service method.
4. Replace the private ADK import.
5. Update the docs and guides listed above in the same PR, with wording that matches the code that actually landed.
6. Add focused guard tests before running aggregate gates.
7. Open a follow-up task for SQLSpec ADK state persistence if it is too large for the same PR.
