# Learnings: test-simplification

Synced from Beads `oracledb-vertexai-mzm.10` (closed at `adb7aba`).

## test_adk.py rewrite (614 -> 455 LOC, -26%)

- DELETED 6 private-surface / deletion-guard tests:
  `test_runner_constructor_takes_session_service_classifier_persona_manager`,
  `test_runner_stashes_dependencies_on_private_attrs`,
  `test_make_tool_factories_returns_store_query_async_callables` (closure `__name__`
  set assertion), `test_build_workflow_constructs_llmagent_and_calls_make_workflow`
  (LlmAgent/make_workflow kwargs-capture),
  `test_append_display_history_requires_session_store_contract` (AttributeError probe),
  `test_module_level_tool_functions_are_deleted` (deletion-guard).
- REPLACED via behavior: `test_build_workflow_wires_agent_instruction_temperature_and_credential_guard`
  asserts the workflow's agent node carries instruction/temperature/tools/`before_agent_callback`
  (no kwargs-capture, no closure names).
- KEPT and de-duplicated via new `conftest.py` helpers (`make_runner`,
  `make_session_service`, `make_tools_service`, `allow_vertex_config`): closure-delegation
  tests, AgentToolsService masked-sql-phase tests, stream behavior tests
  (no-speculative-delta, relabel-to-PRODUCT_RAG), ChatSettings ttl/version/history-limit
  wiring, credential guard 503 path.
- Docstring fixed from "Phase 4 surface..." to behavior-only.
- Note: by this chapter, `process_request` was already gone (Ch5/6/8); only
  `stream_request` survives. Spec line numbers were stale (file already 614 not 1075 LOC).
- Public chat behavior also covered by the green integration suite
  (`test_chat_http` / `test_chat_workflow`).

## Legacy removal

- Deleted `migrate_sqlcl_connection` (`tools/lib/utils.py`), the `mcp_demo` ->
  `cymbal_coffee` SQLcl rename shim (0 test refs, 0 other callers) AND its caller
  branch in `configure_sqlcl_connection_with_password` so the function falls straight
  through to the create-new-connection path.
- ruff retuned the surviving `# noqa` from `C901, PLR0911` to `PLR0911`.
- `grep migrate_sqlcl_connection|mcp_demo` -> 0 hits.

## anyio normalization

- Added module `pytestmark = pytest.mark.anyio` and removed `@pytest.mark.asyncio`
  in `test_fixtures.py`, `test_classifier.py` (3x), `test_workflow.py` (1x).
- `grep pytest.mark.asyncio src/tests` -> 0 hits.

## struct / guard cleanup

- Removed `__struct_fields__` assertion and `not hasattr(distance/current_price)`
  deletion-guards in `test_vector.py` and integration `test_vector_search.py`;
  replaced with positive concrete-field asserts (name/description/price/similarity
  in range).

## Parametrization

- `test_log.py`: ADK-warnings hide/keep + Granian exc_info 3 cases via a shared
  `_log_record` builder.
- `test_doctor.py`: 2 memory cases -> 1 parametrized over `(docker_bytes, warning_expected)`.
- `test_named_sql.py`: `EXPECTED_KEYS` now globs every `-- name:` directive across
  `db/sql/*.sql`; `SERVICE_FILES` globs `domain/*/services/services.py` + `chat/adk.py`.
  (Stronger, self-maintaining invariant — also covers `list-products`,
  `explain-plan-*` keys the static tuple omitted.)
- `test_settings.py`: merged in-memory-flag explicit/default cases; moved the Vite
  test to a new `test_settings_vite.py`.
- `test_classifier.py`: dropped deep `generate_content` config-attr asserts; assert
  the returned `IntentLabel` (public contract).
- `test_workflow.py`: replaced `edges[i][j]` index / private-node assertions with
  node-by-public-name lookup + observable merge output.

## Deviations (documented)

- `.fn` route-handler accessor NOT replaced with `AsyncTestClient`. These controllers
  use Dishka `FromDishka` injection; `AsyncTestClient` would require booting the
  Oracle-backed Dishka container, converting fast unit tests into container-dependent
  integration tests (violates the readability-only + infra constraints). Verified a
  native `Provide` override fails msgspec validation on `FromDishka` params. `.fn` is
  an established, documented codebase pattern (see `integration/.../test_vector_http.py`
  rationale). Readability win applied instead: replaced cryptic
  `object.__new__(Controller)` with normal `Controller(owner=MagicMock())`
  instantiation in all 4 unit files.
- `test_database.py` LEFT UNTOUCHED: post-Ch4 rewrite, the `configure_vector_memory`
  state-machine + password-profile parametrize targets the spec described no longer
  exist; the file has no heavy duplication to parametrize without risking the 2
  pre-existing failures (`test_database_remove_is_idempotent_when_container_missing`,
  `test_database_start_loads_env_file`) caused by the unrelated dirty
  `tools/oracle/cli/database.py`. Those 2 remain failing exactly as-is;
  `cli/database.py` never touched/staged.
