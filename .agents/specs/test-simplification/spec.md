# Flow: test-simplification

*Beads: oracledb-vertexai-mzm.10*

## Specification

Restructure the existing test suite for **readability and behavior-focus** with
**zero change to what is under test**. This is a test-only refactor: collapse the
~300 LOC of duplicated mock-graph setup in `test_adk.py`, delete tests that pin
private internals or guard already-removed symbols, normalize async markers to
`@pytest.mark.anyio`, and parametrize repetitive assertion blocks. The only
**source** change is deleting one dead legacy helper (`migrate_sqlcl_connection`)
that has 0 test references.

Project rules enforced here:

- Tests assert **public behavior**, not private attributes / closure `__name__`s /
  msgspec internals / DAG edge indices.
- Async tests use `@pytest.mark.anyio` (or a module `pytestmark`), never
  `@pytest.mark.asyncio`.
- Docstrings describe behavior only — no spec/phase/chapter references.
- No backwards-compat shims: delete dead legacy code completely.

### Dependencies and boundaries

This chapter **DEPENDS ON Ch6/Ch8/Ch9** and assumes their outcomes are already
landed when it runs. In particular:

- **Ch5/Ch6 have already removed the `process_request` non-stream path** on
  `ADKRunner`. At the time this spec was written against branch `feat/inv`,
  `ADKRunner.process_request` still exists (`src/app/domain/chat/services/adk.py:1123`)
  and the bulk of `test_adk.py` exercises it. **Before editing, re-verify** which
  public methods survive: `stream_request` (current `adk.py:985`),
  `_make_tool_factories` (`adk.py:430`), `_build_workflow` (`adk.py:524`),
  `_append_display_history` (`adk.py:577`). If `process_request` is gone, every
  `process_request`-only test below must be **rewritten** against `stream_request`
  / `AsyncTestClient`, not merely deleted — public chat behavior coverage must be
  **preserved**.
- **Ch2 (deadcode-sweep) already deleted** the dead store-method tests and dropped
  their `EXPECTED_KEYS` from `test_named_sql.py`. Do **not** re-do that work.
- **Do NOT re-platform the integration infra.** The project **deliberately does
  NOT use pytest-databases**. Integration tests run against the repo-managed Oracle
  container (`tools/` + `make start-infra`) with data-level isolation:
  migrate → bootstrap → truncate → reseed, pinned to one xdist worker group
  (`src/tests/integration/conftest.py:32-37`, `pytest.mark.xdist_group("oracle_integration")`).
  This chapter is **readability-only**: do not introduce pytest-databases, do not
  change the conftest container strategy, do not alter the truncate/reseed lifecycle.

### Requirements

- `test_adk.py` becomes **substantially shorter** (currently 1075 LOC, ~20% of the
  suite) and behavior-focused:
  - Extract a shared `make_runner(...)` / `fake_events(...)` helper to remove the
    ~300 LOC of rebuilt MagicMock graph (currently at `~366-465`, `~723-855`,
    `~923-1010`). Put helpers in a local `conftest.py` (fixtures) or a sibling
    module imported by the test file.
  - **Delete private-surface tests** (replace coverage via public behavior):
    - `test_runner_constructor_takes_session_service_classifier_persona_manager`
      (`~29-36`, `inspect.signature` private-param assertion)
    - `test_runner_stashes_dependencies_on_private_attrs` (`~38-52`, asserts
      `_session_service`/`_classifier`/`_persona_manager`)
    - `test_make_tool_factories_returns_store_query_async_callables` (`~55-81`,
      asserts the exact closure `__name__` set)
    - `test_build_workflow_constructs_llmagent_and_calls_make_workflow` (`~288-323`,
      `LlmAgent`/`make_workflow` kwargs-capture)
    - `test_append_display_history_requires_session_store_contract` (`~662-679`,
      `_append_display_history` AttributeError probe)
    - `test_module_level_tool_functions_are_deleted` (`~1067-1075`, deletion-guard
      for already-removed module-level tools/`ALL_TOOLS`/`_resolve_request_container`).
  - **Keep** the tests that exercise the `_make_tool_factories` / `_build_workflow`
    seams as **behavior** (closures actually delegate to the tools service, capture
    sql_phases, set metric_state, etc.) but **stop asserting on closure `__name__`s**.
    Affected behavior tests to retain (de-duplicated via the shared helper):
    `test_search_products_closure_delegates_to_tools_service` (`~83-110`),
    `test_get_product_details_closure_delegates_to_tools_service` (`~195-207`),
    `test_get_all_store_locations_closure_delegates_to_tools_service` (`~210-222`),
    `test_store_query_closures_delegate_and_capture_sql_phases` (`~225-263`). Where
    these select a closure by `__name__` (e.g. `next(fn for fn in tools if
    fn.__name__ == ...)`), that is selection plumbing, not an assertion — it stays,
    but the standalone "names == {...}" assertion test is deleted.
  - **Fix the module docstring** (`adk.py` test file line ~4): change
    `"Phase 4 surface for ADKRunner: ..."` to a behavior-only description with no
    "Phase 4" reference (e.g. describe that it covers the ADKRunner streaming chat
    surface, closure-bound tools, and per-request workflow construction).
  - Preserve the legitimate public-behavior tests (grounded STORE_LOCATION,
    PRODUCT_AVAILABILITY coordinate masking, ORDER_STATUS unsupported, cached-response
    intent promotion, credential-guard 503 path, last_products persistence,
    stream-no-speculative-delta). Where they currently call `process_request`, route
    them through `stream_request` / `AsyncTestClient` per the dependency note.

- **Normalize async markers** `@pytest.mark.asyncio` → `@pytest.mark.anyio`
  (prefer a module-level `pytestmark = pytest.mark.anyio`):
  - `src/tests/unit/app/utils/test_fixtures.py:34`
  - `src/tests/unit/app/domain/chat/services/test_classifier.py:32,47,78`
  - `src/tests/unit/app/domain/chat/services/test_workflow.py:68`

- **Delete legacy `migrate_sqlcl_connection`** (`tools/lib/utils.py:281-340`) **and**
  its caller branch in `configure_sqlcl_connection_with_password`
  (`tools/lib/utils.py:364-371`). It is an old `mcp_demo` → `cymbal_coffee` SQLcl
  connection-rename shim with **0 test references** (grep confirms only the
  definition + the single internal caller). Removing the caller branch must leave
  `configure_sqlcl_connection_with_password` falling straight through to the normal
  "create new connection" path.

- **Replace `.fn` route-handler unwrapping** (the
  `Controller.handler.fn(object.__new__(Controller), ...)` idiom) with `AsyncTestClient`
  or normal controller instantiation:
  - `src/tests/unit/app/domain/system/controllers/test_metrics_charts.py:46`
  - `src/tests/unit/app/domain/system/controllers/test_metrics_summary_cards.py:32`
  - `src/tests/unit/app/domain/products/controllers/test_vector.py:149`
  - `src/tests/unit/app/domain/products/controllers/test_explain_plan.py:58,79`

- **Replace msgspec-internal asserts and removed-column guards** with concrete-field
  assertions:
  - `src/tests/unit/app/domain/products/controllers/test_vector.py:107,164,167`
    (`row.__struct_fields__`, `not hasattr(row, "distance")`)
  - `src/tests/integration/app/domain/products/services/test_vector_search.py:89,92`
    (`not hasattr(match, "current_price")`, `not hasattr(match, "distance")`)
  - Collapse the `distance`/`current_price` deletion-guards into **one positive
    schema assertion** per call site (assert the fields that *should* be present;
    drop the "must not have X" negatives for already-removed columns).

- **Parametrize repetitive assertion blocks** (behavior unchanged):
  - `src/tests/unit/app/lib/test_log.py` — collapse the three near-identical
    `SuppressGranianExcInfoFilter` / `SuppressADKWarningsFilter` record-building
    blocks into parametrized cases (`125-152`, `30-65`).
  - `src/tests/unit/tools/oracle/test_database.py` — the `configure_vector_memory`
    state cases (`134-187`) and `start()` validation cases share a builder; the
    password-profile case is already parametrized (`338-365`) — extend, don't
    duplicate.
  - `src/tests/unit/tools/cli/test_doctor.py` — the two managed-mode memory cases
    (`21-70`) differ only by the docker bytes value and the expected substring;
    parametrize over `(docker_bytes, expected_present)`.
  - `src/tests/unit/app/db/test_named_sql.py` — make `EXPECTED_KEYS` and
    `SERVICE_FILES` **dynamic by globbing** `db/sql/*.sql` (extract every
    `-- name: <key>` directive) and the domain `services/*.py` + `adk.py`, instead
    of the hand-maintained tuples (`19-56`). Keep the existing
    `test_named_query_registry_matches_get_sql_call_sites` invariant.
  - `src/tests/unit/app/lib/test_settings.py` — merge the duplicate ADK/Litestar
    in-memory flag tests (`16-41`, the explicit-flag and default-true cases share a
    body) into one parametrized test, and **move the Vite-root test**
    (`test_vite_config_uses_resources_as_frontend_root`, `77-86`) out of this file
    into a Vite-focused settings module (or a dedicated `test_settings_vite.py`).

- `src/tests/unit/app/domain/chat/services/test_classifier.py` — **drop the deep
  `client.aio.models.generate_content` config-attr assertions**
  (`test_classifier_passes_text_x_enum_config`, `~48-75`: `cfg.response_mime_type`,
  `cfg.response_schema`, `cfg.temperature`, `cfg.system_instruction` substrings).
  Assert on the returned `IntentLabel` (the public contract). The
  enum-value-pin test (`20-29`) and the unknown-label `ValueError` test (`78-89`)
  stay.

- `src/tests/unit/app/domain/chat/services/test_workflow.py` — **stop pinning ADK
  DAG internals**: `workflow.edges[1][1].name` and the `intent._func(...)` /
  `classify_and_respond._func(...)` private-node calls (`47-95`). Assert the
  **observable workflow output** instead (run/invoke the workflow and check the
  merged `{"intent": ..., "answer": ...}` result and `ctx.state["intent"]`). Keep
  the public factory-shape checks that are stable contract (e.g. `make_workflow`
  returns a named `Workflow`); drop the brittle `edges[i][j]` index assertions.

- `make lint && make test` green; public chat-behavior coverage preserved.

### Code Analysis Summary

Greps and reads run on branch `feat/inv`:

| Target | Finding |
| --- | --- |
| `test_adk.py` size | `wc -l` = **1075 LOC**. Three near-identical MagicMock graphs rebuilt at `~366-465`, `~723-855`, `~923-1010` (~300 LOC). Each builds `fake_session`/`session_service`/`persona_manager`/`tools_service` + `fake_events()` + `monkeypatch.setattr(adk_module, "Runner"/"LlmAgent"/"make_workflow", ...)` + `_allow_vertex_config`. |
| `adk.py` public surface | `ADKRunner.__init__` (`415`), `_make_tool_factories` (`430`), `_build_workflow` (`524`), `_append_display_history` (`577`), `stream_request` (`985`), `process_request` (`1123`). Module-level: `_collect_workflow_stream`, `AgentToolsService`, `credential_guard_callback`, `_has_vertex_ai_backend_config`, `_ensure_vertex_ai_backend_configured`, `_is_credential_error`, `ADKRunner`. NOTE: `process_request` still present on this branch — Ch5/Ch6 remove it before this chapter runs; verify before editing. |
| Private-surface tests | `test_runner_*` (`29-52`) read `inspect.signature` params + `_session_service`/`_classifier`/`_persona_manager`. `test_make_tool_factories_returns_store_query_async_callables` (`55-81`) asserts the exact `__name__` set of 7 closures. `test_build_workflow_constructs_llmagent_and_calls_make_workflow` (`288-323`) captures `LlmAgent`/`make_workflow` kwargs. `test_append_display_history_requires_session_store_contract` (`662-679`) probes a private method for `AttributeError`. `test_module_level_tool_functions_are_deleted` (`1067-1075`) is a deletion-guard. |
| Docstring violation | `test_adk.py:4` = `"""Phase 4 surface for ADKRunner: ..."""` — violates the behavior-only docstring rule (spec-phase reference). |
| `@pytest.mark.asyncio` users | `grep -rln "pytest.mark.asyncio" src/tests` → only `test_fixtures.py` (`:34`), `test_classifier.py` (`:32,47,78`), `test_workflow.py` (`:68`). Everything else already uses `anyio` (`conftest.py:24`, `integration/.../test_vector_search.py:26`, etc.). |
| `migrate_sqlcl_connection` | `grep -rn "migrate_sqlcl_connection" --include="*.py" .` → **2 hits only**: definition `tools/lib/utils.py:281` and caller `tools/lib/utils.py:367` inside `configure_sqlcl_connection_with_password` (`364-371`). **0 test references**, `0` other callers. `mcp_demo` legacy name has no other refs. Safe full delete. |
| `.fn` unwrap call sites | `grep -rln "\.fn(" src/tests` → `test_metrics_summary_cards.py` (`:32`), `test_explain_plan.py` (`:58,79`), `test_metrics_charts.py` (`:46`), `test_vector.py` (`:149`), and `integration/.../test_vector_http.py` (out of scope unless trivially HTTP-route-able; the four unit files are the target). |
| msgspec / guard asserts | `__struct_fields__` only in `test_vector.py` (`:164`). `hasattr(... "distance")` in `test_vector.py` (`:107,167`) and integration `test_vector_search.py` (`:92`); `hasattr(... "current_price")` in `test_vector_search.py` (`:89`). The file docstrings (`test_vector.py:4-13`) describe these as regression band-aid guards. |
| `db/sql` glob feasibility | `db/sql/` contains exactly `inventory.sql`, `products.sql`, `stores.sql`, `system.sql` — matches `EXPECTED_FILES` (`test_named_sql.py:19`). Named keys are declared as `-- name: <key>` directives (see `test_vector.py:33` regex precedent) → globbable. `SERVICE_FILES` = products/system `services.py` + chat `adk.py` (`52-56`). |
| Parametrization candidates | `test_log.py` 3 Granian + 4 ADK-warning record blocks; `test_doctor.py` 2 memory cases differing only by docker bytes; `test_database.py` `configure_vector_memory` 3-case state machine; `test_settings.py` duplicate in-memory-flag bodies (`16-41`) + misplaced Vite test (`77-86`). |
| Integration infra (DO NOT TOUCH) | `integration/conftest.py` pins all integration items to `xdist_group("oracle_integration")` (`32-37`); lifecycle = migrate (`migrate_up`, `166`) → bootstrap DDL (`_bootstrap_test_schema`, `39`) → truncate (`_truncate_fixture_tables`, `225`) → load `.json.gz` fixtures (`_load_app_fixtures`, `238`) → seed marker (`_seed_marker_product`, `113`), once per worker via `_ORACLE_*_READY` globals. **No pytest-databases.** Readability chapter must not change this. |

## Implementation Plan

### Phase 1: Shared helpers + test_adk.py rewrite

- [x] 1.1 **Re-verify the live ADKRunner surface** before any edit. Read
  `src/app/domain/chat/services/adk.py` and record which of `process_request` /
  `stream_request` / `_make_tool_factories` / `_build_workflow` /
  `_append_display_history` still exist (Ch5/Ch6 should have removed
  `process_request`). Drive all rewrites from the surviving surface.
- [x] 1.2 Add a local `src/tests/unit/app/domain/chat/services/conftest.py` (or a
  sibling `_adk_helpers.py`) exporting:
  - `make_runner(*, session_service=None, classifier=None, persona_manager=None,
    intent=IntentLabel.PRODUCT_RAG)` → fully-wired `ADKRunner` with sensible
    MagicMock defaults (auto-built `session_service.get_session`/`create_session`,
    `persona_manager.get_system_prompt`/`get_temperature`, classifier `classify`
    AsyncMock returning `intent`).
  - `fake_events(*events)` / `fake_events(text=..., output=...)` → async generator
    yielding the MagicMock ADK events used at `~386-393`, `~738-743`, `~802-810`.
  - `allow_vertex_config(monkeypatch)` (lift the module-level `_allow_vertex_config`,
    `21-26`) and a `tools_service` builder for the common
    `make_response_cache_key`/`get_cached_chat_response`/`set_cached_chat_response`/
    `search_products_by_vector` shape.
- [x] 1.3 Fix the `test_adk.py` module docstring (line ~4) to a behavior-only
  description (no "Phase 4").
- [x] 1.4 **Delete** the private-surface and deletion-guard tests:
  `test_runner_constructor_takes_session_service_classifier_persona_manager`,
  `test_runner_stashes_dependencies_on_private_attrs`,
  `test_make_tool_factories_returns_store_query_async_callables`,
  `test_build_workflow_constructs_llmagent_and_calls_make_workflow`,
  `test_append_display_history_requires_session_store_contract`,
  `test_module_level_tool_functions_are_deleted`.
- [x] 1.5 Rewrite the retained closure-behavior tests (`83-110`, `195-207`,
  `210-222`, `225-263`) to use `make_runner`/the tools-service builder; keep
  `next(fn for fn in tools if fn.__name__ == ...)` as *selection* but remove any
  standalone `names == {...}` assertion.
- [x] 1.6 Rewrite the `process_request`-based behavior tests against the surviving
  public surface (`stream_request` and/or `AsyncTestClient`), de-duplicated via the
  shared helpers, preserving every behavioral assertion: grounded STORE_LOCATION
  (`470-528`), PRODUCT_AVAILABILITY coordinate masking + cache bypass (`531-601`),
  last_products persistence (`604-659`), ORDER_STATUS unsupported (`682-720`),
  workflow-output intent preference (`723-784`), RAG grounded-to-menu (`787-855`),
  stream-no-speculative-delta (`858-920`), cached-response without model (`923-965`),
  cached-response intent promotion (`968-1009`), credential-error → `AIServiceUnconfigured`
  (`1012-1064`), placeholder-project guard (`340-363`). Keep the standalone
  `_effective_intent` / `_safe_location_context` / `credential_guard_callback` unit
  tests (`113-145`, `326-337`) and the `AgentToolsService` masked-sql-phase tests
  (`147-193`, `266-285`).
- [x] 1.7 Confirm `test_adk.py` LOC dropped substantially (target well under the
  current 1075) and no test asserts a private attr, closure `__name__` set, or
  module-deletion guard.

### Phase 2: anyio normalization

- [x] 2.1 `test_fixtures.py`: add module `pytestmark = pytest.mark.anyio`; remove the
  `@pytest.mark.asyncio` on `test_merge_renders_aliased_target` (`:34`). (This file
  also has `anyio_backend` available from the package conftest.)
- [x] 2.2 `test_classifier.py`: add `pytestmark = pytest.mark.anyio`; remove the
  three `@pytest.mark.asyncio` decorators (`:32,47,78`).
- [x] 2.3 `test_workflow.py`: add `pytestmark = pytest.mark.anyio`; remove the
  `@pytest.mark.asyncio` (`:68`).
- [x] 2.4 `grep -rn "pytest.mark.asyncio" src/tests` returns nothing.

### Phase 3: Legacy migrate_sqlcl_connection removal

- [x] 3.1 Delete `migrate_sqlcl_connection` (`tools/lib/utils.py:281-340`).
- [x] 3.2 Delete the migration branch in `configure_sqlcl_connection_with_password`
  (`tools/lib/utils.py:364-371`, the `if connection_name == "cymbal_coffee" and
  is_sqlcl_connection_saved("mcp_demo"):` block) so the function falls through to the
  normal `.env`-load + create path.
- [x] 3.3 Remove any now-unused symbols/imports surfaced by the deletion (the
  `# noqa: PLR0911` on the surviving function may need re-tuning if branch count
  changes). `grep -rn "migrate_sqlcl_connection\|mcp_demo" .` returns 0.

### Phase 4: `.fn` / struct-internal / guard replacements

- [x] 4.1 `test_metrics_charts.py` (`:46`), `test_metrics_summary_cards.py` (`:32`):
  replace `Controller.handler.fn(object.__new__(Controller), ...)` with either
  direct controller-method invocation on an instance, or an `AsyncTestClient` route
  call with DI overrides for the fake services. Keep the same payload assertions.
- [x] 4.2 `test_explain_plan.py` (`:58,79`): same replacement for `explain_plan.fn`;
  the empty-query `ValidationException` case should still raise via the public path.
- [x] 4.3 `test_vector.py` (`:149`): replace `VectorController.vector_search_demo.fn`
  with an `AsyncTestClient` POST (or instance call); keep the `VectorDemo`
  payload/metrics assertions.
- [x] 4.4 `test_vector.py` struct/guard cleanup: replace
  `{...} <= set(row.__struct_fields__)` (`:164`) with direct attribute reads on the
  returned struct (e.g. assert `row.name`, `row.price`, `row.similarity` resolve to
  the expected values); delete the `not hasattr(row, "distance")` negatives
  (`:107,167`) — keep one positive assertion that `price`/`similarity_score` are
  present and correct.
- [x] 4.5 `test_vector_search.py` (integration) guard cleanup: drop
  `not hasattr(match, "current_price")` (`:89`) and `not hasattr(match, "distance")`
  (`:92`); collapse to the existing positive `ProductMatch` field assertions
  (`price > 0`, `similarity_score` in range). Do **not** touch the surrounding
  `driver`/`tracked_product_skus` fixtures or the container lifecycle.

### Phase 5: Parametrization

- [x] 5.1 `test_log.py`: parametrize the `SuppressGranianExcInfoFilter` cases
  (`125-168`) over `(msg, exc_info, expected_filter_result, expect_exc_cleared)` and
  the `SuppressADKWarningsFilter` hide/keep cases (`30-65`) over
  `(message, expected)`. One record-builder helper.
- [x] 5.2 `test_doctor.py`: parametrize the two managed-mode memory tests (`21-70`)
  over `(docker_bytes, warning_expected)`; share the patched `run_command` side
  effect.
- [x] 5.3 `test_database.py`: parametrize the `configure_vector_memory` state cases
  (`134-187`) over the `run_command.side_effect`/expectation tuples where it reduces
  duplication; extend the existing app-password `@pytest.mark.parametrize` (`338-365`)
  to also cover the standalone invalid-app/oee single-case tests (`303-335`) if they
  fit the same shape. Keep behavior identical.
- [x] 5.4 `test_named_sql.py`: make `EXPECTED_KEYS` dynamic — glob `SQL_DIR/*.sql` and
  extract every `-- name: <key>` directive (regex per `test_vector.py:33`
  precedent). Make `SERVICE_FILES` dynamic — glob `DOMAIN_DIR/*/services/services.py`
  plus `chat/services/adk.py`. Keep `EXPECTED_FILES` as the dir-existence check and
  keep `test_named_query_registry_matches_get_sql_call_sites` and
  `test_no_inline_sql_strings_in_domain_services` intact.
- [x] 5.5 `test_settings.py`: merge `test_oracle_adk_and_litestar_session_flags_*`
  and `test_oracle_adk_and_litestar_session_in_memory_default_to_true` (`16-41`) into
  one parametrized test over the env-override vs default cases. **Move**
  `test_vite_config_uses_resources_as_frontend_root` (`77-86`) into a Vite-settings
  test module (`test_settings_vite.py` or the existing Vite-focused location).
- [x] 5.6 `test_classifier.py`: in `test_classifier_passes_text_x_enum_config`
  (`48-75`), drop the `cfg.response_mime_type`/`response_schema`/`temperature`/
  `system_instruction` assertions; assert the returned `IntentLabel` for the input.
  Keep the enum-pin (`20-29`) and unknown-label (`78-89`) tests.
- [x] 5.7 `test_workflow.py`: replace `workflow.edges[i][j]...` index assertions and
  `intent._func(...)` / `classify_and_respond._func(...)` private-node calls (`47-95`)
  with an observable-output assertion (invoke the workflow; assert the merged
  `{"intent", "answer"}` result and `ctx.state["intent"]`). Keep the stable
  `make_workflow` returns named `Workflow` contract check.

### Phase 6: Verification

- [x] 6.1 `grep -rn "pytest.mark.asyncio" src/tests` → empty.
- [x] 6.2 `grep -rn "migrate_sqlcl_connection\|mcp_demo" .` → empty.
- [x] 6.3 `grep -rn "__struct_fields__" src/tests` → empty; `grep -rn '\.fn(' src/tests`
  → no unit-controller hits (integration HTTP file excluded by scope if untouched).
- [x] 6.4 `grep -rn 'hasattr.*\(distance\|current_price\)' src/tests` → no
  deletion-guard negatives remain.
- [x] 6.5 `wc -l src/tests/unit/app/domain/chat/services/test_adk.py` → substantially
  below 1075.
- [x] 6.6 `make start-infra` then `make lint && make test` green.

## Acceptance

- `test_adk.py` is substantially shorter and behavior-focused; the duplicated
  ~300 LOC mock graph is replaced by shared `make_runner`/`fake_events` helpers.
- No test asserts private attributes (`_session_service` etc.), closure `__name__`
  sets, msgspec `__struct_fields__`, ADK DAG `edges[i][j]` internals, or
  already-removed module symbols (deletion-guards gone).
- The removed-column guards (`distance`, `current_price`) are collapsed into single
  positive schema assertions.
- All async tests use `@pytest.mark.anyio`; no `@pytest.mark.asyncio` remains.
- `migrate_sqlcl_connection` and its caller branch are deleted; 0 references remain.
- `.fn` route-handler unwrapping is replaced by `AsyncTestClient` / normal controller
  instantiation in the four unit controller tests.
- Repetitive assertion blocks (`test_log.py`, `test_database.py`, `test_doctor.py`,
  `test_named_sql.py`, `test_settings.py`) are parametrized; `EXPECTED_KEYS`/
  `SERVICE_FILES` are derived by globbing.
- `test_classifier.py` asserts the public `IntentLabel` contract;
  `test_workflow.py` asserts observable workflow output, not DAG internals.
- Public chat-behavior coverage is preserved (no behavioral regression in what is
  under test).
- The integration container strategy is unchanged: no pytest-databases, same
  migrate→bootstrap→truncate→reseed lifecycle, same single-worker xdist pin.
- `make lint && make test` green.

## Verification

```bash
# Marker normalization
grep -rn "pytest.mark.asyncio" src/tests            # expect: no output

# Legacy helper fully gone
grep -rn "migrate_sqlcl_connection\|mcp_demo" .     # expect: no output

# Private-surface / struct-internal / unwrap idioms gone
grep -rn "__struct_fields__" src/tests              # expect: no output
grep -rn "\.fn(" src/tests/unit                     # expect: no controller-handler unwraps
grep -rn "_session_service\|_make_tool_factories.*__name__" src/tests/unit/app/domain/chat/services/test_adk.py

# Removed-column deletion guards gone
grep -rEn 'not hasattr\(.*(distance|current_price)' src/tests   # expect: no output

# test_adk.py shrank
wc -l src/tests/unit/app/domain/chat/services/test_adk.py

# Full gates (requires repo-managed Oracle)
make start-infra
uv run python manage.py database upgrade --no-prompt
make lint
make test
```
