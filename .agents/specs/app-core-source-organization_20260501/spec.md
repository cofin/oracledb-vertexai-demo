# Flow: App Core Source Organization

*Flow ID: `app-core-source-organization_20260501`*
*Chapter 2 of [demo-source-organization_20260501](../demo-source-organization_20260501/prd.md)*
*Beads: `oracledb-vertexai-8jt.2`*
*Depends on: `source-organization-contract_20260501`*
*Status: Planned*

---

## Objective

Make app-level runtime files readable from the top down while preserving lazy
configuration, Litestar logging, domain discovery, environment parsing, and
fixture load/export behavior.

---

## Primary Files

- `src/app/config.py`
- `src/app/lib/log.py`
- `src/app/utils/domains.py`
- `src/app/utils/env.py`
- `src/app/utils/fixtures.py`
- `src/app/server/asgi.py`
- `src/app/server/plugins.py`
- Existing tests under:
  - `src/tests/unit/app/lib/`
  - `src/tests/unit/app/utils/`
  - `src/tests/unit/app/test_ioc*.py`
  - `src/tests/unit/app/domain/test_layout.py`

---

## Requirements

- `src/app/config.py` must keep module-level lazy config via `__getattr__`, but
  public names and `setup_logging()` should be easy to find.
- `src/app/lib/log.py` should split broad mechanics into private sibling modules
  or submodules, for example:
  - `_log_filters.py`
  - `_log_processors.py`
  - `_log_middleware.py`
  - `_log_serialization.py`
- Keep imports from `app.lib.log` stable for current consumers:
  - `structlog_processors`
  - `stdlib_logger_processors`
  - `StructlogMiddleware`
  - `BeforeSendHandler`
  - `after_exception_hook_handler`
  - CLI mode helpers and async log helpers.
- `src/app/utils/domains.py` should keep `DomainPlugin`, `DomainPluginConfig`,
  `discover_domain_controllers()`, and `discover_domain_listeners()` visible
  before private discovery/cache helpers where practical.
- `src/app/utils/fixtures.py` should show `FixtureLoader` and `FixtureExporter`
  before conversion helpers, or move conversion helpers to a private sibling.
- `src/app/utils/env.py` overloads may remain grouped at the top because they are
  the public API; private parsing helpers should stay below the public callable.

---

## Implementation Plan

1. Write or update tests first:
   - Extend logging tests to import the same public names from `app.lib.log`.
   - Extend fixture tests to cover `FixtureLoader` and `FixtureExporter` public
     behavior after helper moves.
   - Update the source organization allowlist from Chapter 1 for app-core files.
2. Reorganize logging:
   - Move filter classes from `src/app/lib/log.py` into a focused private module.
   - Move serializer/processor helpers into a focused private module.
   - Move ASGI middleware and `BeforeSendHandler` into a focused private module
     if it materially reduces `log.py`.
   - Re-export the stable public surface from `log.py`.
3. Reorganize config:
   - Keep lazy globals and `__getattr__` behavior.
   - Move construction details that make `_initialize()` hard to scan into
     private helper functions or a private sibling module only if tests show the
     public surface stays stable.
4. Reorganize utilities:
   - Move fixture conversion helpers below public classes or into
     `src/app/utils/_fixtures.py`.
   - Keep domain discovery public API visible before private iterators/cache
     helpers.
5. Run focused verification:
   - `uv run pytest src/tests/unit/app/lib src/tests/unit/app/utils src/tests/unit/app/domain/test_layout.py -q`
   - `uv run pytest src/tests/unit/app/test_source_organization.py -q`
   - `uv run ruff check src/app/config.py src/app/lib src/app/utils src/app/server`

---

## Acceptance Criteria

- Public imports from `app.config`, `app.lib.log`, and `app.utils.domains` remain
  stable.
- Logging output configuration and warning filters remain covered by tests.
- App-core files no longer require temporary source organization allowlist
  entries except documented framework constraints.
- Focused tests and Ruff pass.
