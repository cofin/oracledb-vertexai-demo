---
type: Pattern
title: Operations Patterns
description: Gotchas and patterns for Oracle HNSW, SGA/PGA, APEX/ORDS, packaging, and CI
tags:
  - operations
  - oracle-26ai
  - packaging
  - deployment
---

# Operations Patterns

<!-- truth: start -->
- HNSW `ORGANIZATION INMEMORY NEIGHBOR GRAPH` indexes require non-zero `vector_memory_size` before index creation. The local Oracle startup scripts configure this before migrations create vector indexes.
- Oracle Free Edition has a hard SGA/PGA cap; the project default vector pool is sized to fit the demo dataset instead of trying to raise SGA targets.
- Local APEX/ORDS stays optional: `make start-infra` is DB-only, while APEX-enabled flows start ORDS through the shared `OrdsSidecar` used by `manage.py infra ords`. ORDS startup must probe the runtime version and fail clearly below 26.1.1; inconclusive version probes are retryable until timeout. `/ords/` readiness may accept routed non-5xx responses, but `/i/` static media readiness must reject 403/404 because the smoke check uses `curl -fsS`.
- `V$SGAINFO` reports the vector pool as `Vector Memory Area`; verification SQL should accept that label.
- `VECTOR(N, FLOAT32)` DDL, `EMBEDDING_DIMENSIONS`, and committed fixture vector lengths are co-versioned. Do not mix older lower-dimensional examples into this app.
- `ORACLE_ADK_IN_MEMORY` and `ORACLE_LITESTAR_SESSION_IN_MEMORY` default to true so SQLSpec extension tables use Oracle INMEMORY where the database supports it.
- `OracleAsyncConfig` uses `connection_config=`; older `pool_config=` wiring can silently drop credentials and surface as `DPY-4001`.
- APEXlang lifecycle commands require SQLcl 26.1.2+ and live under `manage.py infra apex generate|export|validate|import`. Keep source-controlled APEX assets under `src/apex/<alias>/`. SQLcl 26.1.2 generated this repo's APEXlang project with hyphenated directories such as `shared-components/` and `supporting-objects/`; treat generated SQLcl output as authoritative when docs and older notes disagree.
- APEX 26.1 can validate app-level `restDataSource` APEXlang, but this local runtime currently rolls back import with `WWV_WEBSRC_MODULE_RSERVER_FK` when REST Data Sources reference a `restDataSourceServer`. Use SQL-backed APEX reports for importable demo pages and keep REST Source Catalog wiring open until a generated App Builder round-trip or Oracle patch proves the server/data-source import path.
- Logging must use `app.lib.log` processors, set Litestar/Granian env defaults, exclude static-asset logs, and filter only known ADK/Authlib warning noise.
- PyApp onefile releases use the custom Bundle-Patch-Compile path, not `[tool.pyapp]` or `uvx pyapp build`: build assets and wheel, bundle Python 3.13 dependencies with `tools/bundler.py`, patch PyApp to install under the XDG config path (`~/.config/cymbal-coffee` by default), and compile Linux launchers with `cargo zigbuild --target <arch>-unknown-linux-gnu.2.17`.
- `make build-onefile` must force `UV_PYTHON`/`PYAPP_BUILD_PYTHON` to the explicit CPython 3.13 build interpreter because the repo-local `.python-version` remains `3.12` for normal development.
- Release containers wrap the onefile binary, not a separate Python install path. Build from the single distroless Dockerfile at `tools/deploy/docker/Dockerfile`, allow Docker context access to `dist/coffee-*-linux-gnu`, and expose `/app/wallet` with `TNS_ADMIN`/`WALLET_LOCATION` pointed there for read-only Oracle wallet mounts.
- Release CI builds onefiles and containers on native architecture runners: `ubuntu-24.04` for x86_64/amd64 and `ubuntu-24.04-arm` for aarch64/arm64. Cross-compilation via emulation is rejected — both arches build natively in the matrix and the final GitHub Release job downloads `dist/coffee-linux-x86_64` + `dist/coffee-linux-aarch64` plus checksums and attaches them with `fail_on_unmatched_files: true`. Onefile and container smoke checks invoke `coffee upgrade --help` (the packaged end-user command) rather than `coffee run`.
- Docs publish via `.github/workflows/docs.yml` on push to main: builds with `sphinx-build -W --keep-going`, uploads `actions/upload-pages-artifact@v3`, deploys via `actions/deploy-pages@v4`. Do not add `oracledb`, `vertexai`, `google.adk`, `google.cloud`, or `google.genai` to `autodoc_mock_imports` in `docs/conf.py` — they are hard deps and mocking breaks sqlspec's import-time `oracledb.__version__` lookup.
- Docs information architecture is three tiers and locked: `index.md` hero + `tour.md` walkthrough at the front, `concepts/{vector-search,rag,agent-flow}.md` for deep dives, and `reference/{quickstart,cli,api,internals,developers}.md` for the reference appendix. Concept page count is exactly 3 — not 2, not 4. Use the `sphinx-immaterial` theme (not `shibuya`) with custom admonitions `tour-stop`, `oracle-internals`, and `agent-detail` defined in `conf.py`.
- Code embeds in docs use `literalinclude` — Python embeds use `:pyobject:` while SQL embeds use `docs:start-<name>` / `docs:end-<name>` anchor pairs in the source file — never copy-paste a snippet inline. Each embed has a one-or-two-sentence framing paragraph above it that names the file/class and its role so readers know what larger thing the snippet is part of.
- Autodoc scope is intentionally narrow: `AgentOrchestrationService`, `HybridRouteResolver`, `CacheService`, `MetricsService`, `ProductService`, and the three `domain/*/schemas` packages. Do NOT add CLI commands, settings dataclasses, plugin wiring, or IoC providers — their shapes are stable and reading the source is faster than reading generated docs.
- `AsyncTestClient` MUST be entered with `async with`; a bare instance never runs the app lifespan, so Dishka containers (and the Oracle pools they hold) leak across tests in the same process. Fixtures look like `async def client(app): async with AsyncTestClient(app) as c: yield c`.
- HTMX endpoints that also need to accept JSON parse the request body directly (`await request.json()` or `await request.form()`) — do NOT declare them as a typed `data:` body parameter. Litestar's body-DTO path rejects HTMX form posts when the route declares JSON body data.
- `hx-ext="litestar"` belongs only on JSON-templating panels. Scope it out with `ignore:litestar` on partial-HTML-swap surfaces, otherwise the extension intercepts HTML responses and breaks the swap.
- The chat form must capture `FormData` before applying any busy/disabled state to inputs — disabling a control removes it from `new FormData(form)`, which causes the backend to receive an empty message and stream `Message cannot be empty`. Regression-check this ordering.
- Cached chat responses store only the product-lookup `sql_phases`. At read time the cache hit is wrapped in a fresh `get-cached-response` phase so the UI shows both the cache hit and the original product-lookup context without retaining the original cache-miss phase.
- Streaming `/api/chat/stream` exception handling lives inside the async generator: catch broadly, log with `logger.aexception()`, and yield a sanitized SSE `error` event. Do not rely on Litestar exception middleware for failures that occur after SSE headers have been sent — it cannot intercept post-start stream errors.
- If `make lint` fails with `frontend-typecheck` due to missing `tsc` (TypeScript compiler), ensure frontend assets are installed in `src/resources/` by running `uv run python manage.py assets install` first.
- When committing `uv.lock`, ensure it has been resolved using the public PyPI index (e.g., by running with `UV_CONFIG_FILE=/dev/null` and `--default-index https://pypi.org/simple` if your workstation configures a Google-internal repository like `us-python.pkg.dev`), otherwise public CI builds will fail with 401 Unauthorized errors.
- For Oracle Exadata & 26ai DBA agent workflows, connect with account-level read-only diagnostic users (`ALTER USER ... READ ONLY;` enforcing `ORA-28194`), expose vetted `GV$SQL` / `GV$ACTIVE_SESSION_HISTORY` / `V$SYSSTAT` / `V$RMAN_BACKUP_JOB_DETAILS` queries via MCP Toolbox `tools.yaml` (`type: oracle-sql`) or audited `sql -mcp` (`DBTOOLS$MCP_LOG` and `V$SESSION.MODULE`/`ACTION`), and gate any DDL/DML remediation (`DBMS_SPM` plan baseline pins, `ALTER SEQUENCE ... SCALE EXTEND`, `DBMS_PART.CLEANUP_GIDX`) behind deterministic SQL threshold checks and human approval.
<!-- truth: end -->
