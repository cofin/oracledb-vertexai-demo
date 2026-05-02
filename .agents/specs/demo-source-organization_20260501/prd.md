# Master PRD: Demo-First Source Organization

*PRD ID: `demo-source-organization_20260501`*
*Created: 2026-05-01*
*Status: Implemented*
*Beads epic: `oracledb-vertexai-8jt`*

---

## North Star

Make the Cymbal Coffee demo read like a demo app: when someone opens a source
file, the important public story should appear first. Controllers should show
routes, services should show service capabilities, CLI modules should show
commands, and runtime modules should show the public contract before private
mechanics.

Private helpers are still useful, but they should not be the first thing a
reader sees in a public module. If a main file has many small private functions,
move those helpers into a focused sibling private module or package. If a module
is already a private helper surface, split it by responsibility when it has grown
too broad to scan.

No product behavior, route behavior, database behavior, CLI command names, or
test meaning changes are part of this PRD.

---

## Current State Reviewed

Verified against the live tree on 2026-05-01:

- `src/app` and `tools` contain 89 Python files.
- Source layout already has a good direction:
  - Domain packages use `controllers/`, `services/`, and `schemas/`.
  - Public CLI command modules are mostly declarative.
  - `app.cli._helpers` exists for command implementation details.
  - `src/tests/unit/app/domain/test_layout.py` already pins controller package layout.
  - `src/tests/unit/app/cli/test_surface.py` already rejects private command helpers in public CLI modules.
- Several public modules currently open with private helper mechanics or large
  helper blocks before the public story:
  - `src/app/domain/chat/services/adk.py` is 956 lines and starts with 17
    top-level private helpers before `AgentToolsService` and `ADKRunner`.
  - `src/app/domain/products/controllers/_vector.py` starts with four private
    helpers before `VectorController`.
  - `src/app/domain/products/services/services.py` starts with distance and
    location helpers before `ProductService` and `StoreService`.
  - `src/app/domain/products/services/maps.py` starts with URL helpers before
    exported Maps URL builders.
  - `src/app/utils/fixtures.py` starts with fixture conversion helpers before
    `FixtureLoader` and `FixtureExporter`.
  - `src/app/config.py` exposes public lazy attributes, but the main public
    callable `setup_logging()` appears after private initialization/reset logic.
- Several helper-heavy modules are too broad to stay as one comfortable file:
  - `src/app/lib/log.py` is 511 lines and mixes filters, serializers,
    processors, middleware, exception hooks, and before-send extraction.
  - `src/app/cli/_helpers/data_ops.py` is 502 lines and mixes embeddings,
    cache, model info, migrations, fixture loading, and fixture export.
  - `src/app/utils/domains.py` is 363 lines and mixes domain discovery, cache
    state, plugin integration, and startup logging.
  - `tools/lib/utils.py` is 485 lines and mixes env generation, process
    execution, SQLcl checks, MCP config checks, and Gemini setup.
  - `tools/oracle/connection.py`, `database.py`, `health.py`, `wallet.py`, and
    `sqlcl_installer.py` are 397-644 lines each and are operational modules
    where public classes should be easier to see.
- Some nested helpers are legitimate closure points, but they should be
  reviewed intentionally:
  - ADK closure-bound tools inside `ADKRunner._make_tool_factories()` preserve
    request-scoped Dishka services.
  - `StructlogMiddleware()` and `create_run_command()` return closures required
    by the framework/CLI shape.
  - Local parsing helpers such as `parse_plan_rows().cell()` can move out if the
    parent method stays easier to read.

---

## Product Decisions

1. Optimize for cold-read demo comprehension over mechanical alphabetical order.
2. Public modules should show exported classes/functions before private helpers.
3. Private helper modules may start with helper functions, but they must be
   cohesive and named for the responsibility they support.
4. Use focused names over a generic mega `_helpers.py` when the responsibility is
   clear: `_telemetry.py`, `_grounding.py`, `_request_parsing.py`,
   `_logging_processors.py`, `_fixtures.py`, `_embeddings.py`, and similar.
5. Keep existing public imports stable when practical. If a split changes import
   paths, update all consumers and tests in the same chapter.
6. Do not introduce abstract base classes, registries, plugin systems, or broad
   facade layers just to move code around.
7. Preserve closure-bound ADK tools as closures unless a replacement still
   clearly binds request-scoped services and metrics state.
8. Treat source layout tests as guardrails, not a reason to force awkward code
   shapes. Allow private modules and framework-required closures explicitly.
9. Keep implementation changes behavior-neutral: refactor, move, reorder, and
   test existing contracts.
10. The final pass must update `.agents/patterns.md` only with conventions proven
    by the refactor.

---

## Roadmap

### Chapter 1 - `source-organization-contract_20260501`

Define the repository-wide source organization contract and add audit coverage
before moving code.

Deliverables:

- Inventory every Python file under `src/app` and `tools`.
- Add a source organization test that distinguishes public modules from private
  helper modules.
- Extend existing layout tests instead of adding a top-level issue bucket.
- Document the explicit allowlist for framework-required closures and module
  internals.

Acceptance:

- The audit covers all 89 current Python files.
- Tests identify current hotspots without blocking unrelated implementation
  until each chapter updates its allowlist.
- Future public modules cannot start with a run of private helper functions.

### Chapter 2 - `app-core-source-organization_20260501`

Reorganize app-level runtime modules so public contracts are visible first.

Primary files:

- `src/app/config.py`
- `src/app/lib/log.py`
- `src/app/utils/domains.py`
- `src/app/utils/env.py`
- `src/app/utils/fixtures.py`
- `src/app/server/asgi.py`
- `src/app/server/plugins.py`

Acceptance:

- `config.py` keeps lazy initialization behavior, but public access and logging
  setup are easier to find.
- `log.py` is split into cohesive private modules for filters, processors, and
  ASGI/before-send mechanics without changing logging output contracts.
- Domain discovery and fixture utilities keep exported API first.
- Existing config, logging, fixture, and domain layout tests pass.

### Chapter 3 - `domain-source-organization_20260501`

Make domain controllers and product/store services read public-first.

Primary files:

- `src/app/domain/chat/controllers/_chat.py`
- `src/app/domain/products/controllers/_products.py`
- `src/app/domain/products/controllers/_vector.py`
- `src/app/domain/products/services/services.py`
- `src/app/domain/products/services/maps.py`
- `src/app/domain/products/schemas/_products.py`
- `src/app/domain/system/controllers/_metrics.py`
- `src/app/domain/web/controllers/_pages.py`

Acceptance:

- Controller modules show controller classes and route handlers before parsing,
  response-formatting, or error-classification helpers.
- Product/store service files show `ProductService`, `StoreService`,
  `VertexAIService`, and `OracleVectorSearchService` as the main story.
- Distance, location hint matching, Maps URL formatting, vector request parsing,
  metrics badge formatting, and trend calculation move into focused private
  modules or below public classes where that is clearer.
- Endpoint and service tests pass without behavior changes.

### Chapter 4 - `adk-runner-source-organization_20260501`

Split the ADK runner so a reader sees `AgentToolsService` and `ADKRunner`
before telemetry and grounding mechanics.

Primary files:

- `src/app/domain/chat/services/adk.py`
- `src/app/domain/chat/services/workflow.py`
- New private modules under `src/app/domain/chat/services/` as needed.
- `src/tests/unit/app/domain/chat/services/test_adk.py`
- `src/tests/integration/app/domain/chat/services/test_chat_workflow.py`

Acceptance:

- `adk.py` shrinks to public service/runner orchestration plus minimal constants.
- Product grounding, SQL phase formatting, response cache phase formatting,
  history/event coercion, effective intent logic, and tool-result recording live
  in named private modules.
- Closure-bound ADK tools remain request-scoped and metric-aware.
- Streaming and non-streaming response payload keys remain unchanged.

### Chapter 5 - `cli-tools-source-organization_20260501`

Reorganize CLI helpers and operational tools without changing operator-facing
commands.

Primary files:

- `src/app/cli/commands/manage.py`
- `src/app/cli/_helpers/data_ops.py`
- New focused modules under `src/app/cli/_helpers/`
- `tools/lib/utils.py`
- `tools/cli/*.py`
- `tools/oracle/*.py`
- `tools/oracle/cli/*.py`

Acceptance:

- Public `coffee` command modules remain declarative and do not grow local
  private helper functions.
- `app.cli._helpers.data_ops` is split into focused helper modules or converted
  into a private package while preserving command behavior.
- Large `tools/oracle` modules show public dataclasses/classes and command
  surfaces before low-level command building and parsing helpers.
- CLI surface and tool tests pass.

### Chapter 6 - `source-organization-verification_20260501`

Run the final whole-tree verification and persist only durable conventions.

Deliverables:

- Re-run the source organization audit across all Python files.
- Tighten or remove temporary allowlist entries added during the earlier
  chapters.
- Update `.agents/patterns.md` with the public-first source organization rule.
- Run aggregate repo gates.

Acceptance:

- No unreviewed Python file remains outside the contract.
- `make lint` passes.
- `make test` passes.
- `git diff --check` passes.
- `.agents/patterns.md` captures the durable convention.

---

## Global Constraints

1. Planning and implementation must preserve user changes already present in the
   shared worktree. Do not revert unrelated edits.
2. Do not change public route paths, CLI command names, settings names, SQL names,
   migration behavior, fixture data, or ADK response payload keys as part of
   this PRD.
3. Prefer moving existing code over rewriting logic.
4. Keep imports explicit and local to existing package boundaries.
5. Public modules should not begin with private helper runs unless the module is
   itself private or the exception is documented in the organization test.
6. Private helper modules must be cohesive. Do not create one large dumping-ground
   `_helpers.py` where smaller named modules would be clearer.
7. Keep type hints and existing SPDX headers on every moved or created file.
8. Keep source-layout tests in existing module-path test buckets under
   `src/tests/unit/app/...` or `src/tests/unit/tools/...`.
9. Run focused tests during each chapter, then `make lint`, `make test`, and
   `git diff --check` before declaring the PRD implemented.
10. If an implementation chapter discovers a behavior bug, file or split that as
    a separate task unless fixing it is required to keep the refactor correct.

---

## Out Of Scope

- Adding new demo features.
- Replacing Dishka, SQLSpec, Litestar, HTMX, Granian, ADK, or Vertex AI patterns.
- Renaming public API schemas or wire fields.
- Changing Oracle migrations or fixtures.
- Redesigning UI layouts.
- Collapsing the `tools/` package into `src/app`.
