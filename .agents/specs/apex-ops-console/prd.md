# Master PRD: APEX Operations Console and Schema Bridge

*PRD ID: `apex-ops-console`*
*Created: 2026-06-23*
*Status: Planned*
*Beads: `oracledb-vertexai-apxo`*
*Related PRD: `apex-gvenzl-install` (`oracledb-vertexai-apxg`)*

---

## North Star

Turn the optional Oracle APEX path into a teachable Cymbal Coffee demo that is
real enough to show in an official lab:

- A local APEX 26.1 + ORDS runtime starts cleanly, with explicit version and
  health checks instead of "latest" assumptions.
- SQLcl 26.1.2 APEXlang becomes the source-control lifecycle for APEX app
  generation, export, validation, and import under `src/apex/`.
- The APEX sample app demonstrates the same coffee data already in the Litestar
  app: products, stores, inventory, vector search, model status, and grounded
  recommendation flows.
- APEX consumes the Litestar app through OpenAPI / REST Source Catalog artifacts.
- MCP is demonstrated separately for Antigravity and database/tooling use:
  SQLcl MCP, Google MCP Toolbox for Oracle, and optional `litestar-mcp` app
  tools are not conflated with APEX REST Source Catalogs.

This PRD is not migration support. It must produce clean current configs and
delete or replace the old Gemini CLI-specific config path where implementation
touches it.

---

## External Research

### Oracle APEX 26.1

Official Oracle sources reviewed:

- APEX downloads page: <https://www.oracle.com/tools/downloads/apex-downloads/>
- APEX 26.1 release notes: <https://docs.oracle.com/en/database/oracle/apex/26.1/htmrn/about-release-notes.html>
- APEX 26.1 known issues: <https://www.oracle.com/tools/downloads/apex-downloads/apex-261-known-issues/>

Findings:

- Oracle lists APEX 26.1 as released on May 14, 2026 and re-released on
  May 25, 2026 for bug `39397271`.
- Patch bundle `39179920` is APEX 26.1.1 and was updated on June 15, 2026.
  It is available from My Oracle Support, so the public local demo should treat
  patching as optional and separately documented.
- APEX 26.1 requires Oracle Database 19c RU 19.18+ or Oracle AI Database 26ai
  version 23.26.0+, and requires ORDS 26.1.1 or later.
- Oracle recommends installing ORDS before APEX for new installs. The repo
  currently installs APEX before starting ORDS because the local sidecar uses
  staged APEX media/images; the implementation must document and validate that
  choice, not leave it implicit.

### ORDS 26.1

Official Oracle sources reviewed:

- ORDS downloads page: <https://www.oracle.com/database/sqldeveloper/technologies/db-actions/download/>
- ORDS 26.1 developer guide changes: <https://docs.oracle.com/en/database/oracle/oracle-rest-data-services/26.1/orddg/changes-release-26.1-oracle-rest-data-services-developers-guide.html>

Findings:

- ORDS 26.1.2.140.1916 is the latest Oracle-listed ORDS release found in this
  research window, dated May 27, 2026.
- ORDS 26.1 adds AutoREST vector-search support for vector columns. This is a
  useful teaching note, but the Cymbal Coffee APEX app should still consume the
  Litestar curated APIs for demo stability and grounding.
- The official container registry did not expose unauthenticated tag metadata
  through a simple tags endpoint during research. Implementation must verify the
  selected ORDS image by container runtime pull/version checks or an `ords`
  runtime version probe; do not silently rely on `latest`.

### SQLcl 26.1.2 and APEXlang

Official Oracle sources reviewed:

- SQLcl 26.1.2 release notes: <https://www.oracle.com/tools/sqlcl/sqlcl-relnotes-26.1.2.html>
- SQLcl APEX commands: <https://docs.oracle.com/en/database/oracle/sql-developer-command-line/26.1/sqcug/sqlcl-apex-commands-apexlang.html>
- APEXlang project structure: <https://docs.oracle.com/en/database/oracle/sql-developer-command-line/26.1/sqcug/apexlang-project-structure-apexlang.html>
- APEXlang developer guide: <https://docs.oracle.com/en/database/oracle/apex/26.1/apxdc/working-apexlang.html>

Findings:

- SQLcl 26.1.2 supports the APEXlang lifecycle: generate, export, validate, and
  import.
- SQLcl 26.1.2 release notes call out APEXlang support and APEX export fixes.
- Oracle's APEXlang guide explicitly points developers toward APEX skills for
  popular AI coding agents, SQLcl validation, blueprints, and import/export
  workflows.
- Official APEXlang directories use underscores, including
  `shared_components/` and `supporting_objects/`. Any older plan text with
  hyphenated names must be corrected.
- SQLcl MCP support still exists, but the repo's old Gemini CLI config writer
  targets `~/.gemini/settings.json`; that is no longer the clean Antigravity
  shape.

### Official Oracle Skills

Official Oracle sources reviewed:

- Oracle Skills repository: <https://github.com/oracle/skills>
- Oracle Skills APEX domain: <https://raw.githubusercontent.com/oracle/skills/main/apex/SKILL.md>
- Oracle Skills Database domain: <https://raw.githubusercontent.com/oracle/skills/main/db/SKILL.md>
- Oracle Skills Claude plugin marketplace: <https://raw.githubusercontent.com/oracle/skills/main/.claude-plugin/marketplace.json>
- SQLcl MCP Server docs: <https://docs.oracle.com/en/database/oracle/sql-developer-command-line/26.1/sqcug/sqlcl-mcp-server.html>

Findings:

- Oracle publishes `oracle/skills` as source-backed, installable skills for
  Oracle technologies.
- The official top-level skills to use for this work are `apex` and `db`.
  There is not a separate top-level ORDS skill; ORDS guidance lives under the
  Database skill in `db/ords/`.
- The APEX skill currently routes APEX app generation through the APEXlang
  domain, especially `apex/apexlang/references/workflows/apex-generation.md`
  and domain reference files.
- The Database skill covers ORDS, SQLcl, SQLcl MCP, Oracle vector search,
  DBMS_VECTOR, Oracle container images, and agent-safe database workflows.
- The Database skill's recommended MCP path is SQLcl basics, least-privilege
  privileges, then `db/sqlcl/sqlcl-mcp-server.md`.
- The repository ships a Claude plugin marketplace for `apex` and `db`. For
  this PRD, treat Oracle Skills as official guidance to install or reference,
  not as vendored application source, unless a later implementation decision
  deliberately vendors a pinned copy.

### APEX REST Source Catalogs and OpenAPI

Official Oracle source reviewed:

- APEX REST Source Catalogs: <https://docs.oracle.com/en/database/oracle/apex/26.1/htmdb/managing-REST-source-catalogs.html>

Findings:

- APEX can generate REST Source Catalogs from a single OpenAPI document.
- APEX supports a catalog refresh URL and catalog-level auth defaults.
- The app should export an APEX-safe OpenAPI subset rather than making the
  full Litestar OpenAPI schema the public catalog contract.

### Antigravity and MCP

Official Google sources reviewed:

- Antigravity Editor MCP docs: <https://antigravity.google/docs/mcp>
- Antigravity IDE MCP docs: <https://antigravity.google/docs/ide-mcp>
- Antigravity CLI migration docs: <https://antigravity.google/docs/gcli-migration>
- Antigravity CLI plugins and skills docs: <https://antigravity.google/docs/cli-plugins>
- Antigravity CLI features docs: <https://antigravity.google/docs/cli-features>

Findings:

- Antigravity Editor / IDE custom MCP config is `~/.gemini/config/mcp_config.json`.
- Antigravity CLI global MCP config is `~/.gemini/antigravity-cli/mcp_config.json`.
- Antigravity CLI workspace MCP config is `.agents/mcp_config.json`.
- Antigravity plugins can include a plugin-root `mcp_config.json`.
- Antigravity CLI keeps workspace rules in `AGENTS.md` / `GEMINI.md`, moves
  workspace skills from `.gemini/skills/` to `.agents/skills/`, and supports
  workspace MCP in `.agents/mcp_config.json`.
- Modern remote MCP config uses `serverUrl`. Legacy `url` or `httpUrl` keys
  are migration-era details and should not be emitted by this repo.

### Google MCP Toolbox for Oracle

Official Google sources reviewed:

- MCP Toolbox repository: <https://github.com/googleapis/mcp-toolbox>
- Oracle prebuilt config: <https://mcp-toolbox.dev/integrations/oracle/prebuilt-configs/oracle/>
- MCP client connection docs: <https://mcp-toolbox.dev/documentation/connect-to/mcp-client/>

Findings:

- MCP Toolbox is the Google database MCP server to demonstrate alongside
  Antigravity. The project was renamed from `genai-toolbox` to `mcp-toolbox`.
- The Oracle prebuilt config uses environment variables such as
  `ORACLE_CONNECTION_STRING`, `ORACLE_USERNAME`, `ORACLE_PASSWORD`,
  `ORACLE_WALLET`, and `ORACLE_USE_OCI`.
- The Oracle tool set includes SQL execution, table listing, active sessions,
  query plans, and related database inspection tools.
- MCP Toolbox supports stdio and Streamable HTTP MCP transports. For this repo,
  default to local stdio configs first, with remote examples documented only as
  optional.

### Gemini Embedding 2

Google source reviewed:

- Gemini Embedding 2 model card: <https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/embedding-2>

Finding:

- `gemini-embedding-2` is the current non-preview model name with 3072
  dimensional float output. The repo currently defaults to
  `gemini-embedding-2-preview`. Migrating embeddings would require cache
  invalidation and fixture regeneration, so this PRD only exposes the current
  model in APEX-facing status. A separate PRD should own the data migration.

---

## Current Code Findings

### APEX / ORDS Runtime

- `tools/oracle/ords.py:29` sets
  `DEFAULT_ORDS_IMAGE = "container-registry.oracle.com/database/ords:latest"`.
- `tools/oracle/ords.py:193-208` treats container-running state as readiness;
  it does not probe `/ords/` or `/i/`.
- `tools/oracle/cli/database.py:103-139` starts the DB, optionally installs
  APEX, starts ORDS, and prints access info, but ORDS has no explicit nested
  lifecycle CLI yet.
- `tools/oracle/cli/apex.py:44-82` exposes only `install`, `upgrade`, and
  `status`.
- `manage.py:95-96` registers only `manage.py infra apex` as a nested subgroup.

### SQLcl and Legacy Gemini MCP Config

- `tools/oracle/sqlcl_installer.py:29-31` downloads
  `sqlcl-latest.zip`.
- `tools/oracle/sqlcl_installer.py:147-171` returns raw `sql -V` output but
  does not parse a minimum version or capability set.
- `tools/oracle/sqlcl_installer.py:318-335` verifies only that the `sql`
  executable exists.
- `tools/cli/install.py:215-292` checks for the old `gemini` executable and
  writes SQLcl MCP config as Gemini CLI integration.
- `tools/lib/utils.py:224-244` checks `~/.gemini/settings.json`.
- `tools/lib/utils.py:353-406` writes `mcpServers.sqlcl` to
  `~/.gemini/settings.json`.

### Litestar APIs and OpenAPI

- `pyproject.toml:18-29` already includes `litestar-mcp`.
- `src/app/server/plugins.py:54-92` does not initialize a `litestar-mcp`
  plugin.
- `src/app/server/core.py:55-60` builds the app OpenAPI config with Scalar.
- `src/app/domain/products/controllers/_products.py:14-63` exposes list
  products and list stores.
- `src/app/domain/products/controllers/_vector.py:52-154` exposes vector demo
  search, but it is HTMX-shaped and not ideal as the stable APEX REST Source
  contract.
- `src/app/domain/chat/controllers/_chat.py:59-118` exposes SSE chat and
  session clear; it should not be the primary APEX integration surface.
- `src/app/domain/system/controllers/_system.py:10-20` only serves the favicon;
  there is no APEX-friendly AI/system status endpoint.

### Coffee Data Services

- `src/app/domain/products/services/services.py:83-95` contains the core
  product vector search service method.
- `src/app/domain/products/services/services.py:101-219` contains store,
  nearest-store, and product availability methods.
- `src/app/domain/products/services/services.py:225-288` contains Vertex AI
  embedding behavior and the current preview model guard.
- `src/app/domain/products/services/services.py:291-377` contains the
  OracleVectorSearchService search and explain-plan behavior.
- `src/app/domain/products/schemas/_products.py:16-159` contains current
  product, store, inventory, vector match, vector demo, and explain-plan
  schemas. APEX-specific response schemas should extend this surface without
  breaking existing API responses.

### APEX Source

- `src/apex/` is currently absent. The new app should start at
  `src/apex/cymbal-coffee-ops/` and follow the official APEXlang directory
  names.

---

## Product Decisions

1. **Create a new roadmap rather than broadening the old infra PRD.**
   `apex-gvenzl-install` remains the history of record for first-boot
   APEX/ORDS/APEXlang plumbing. This PRD reconciles its open gaps, then adds the
   demo app and schema bridge.

2. **Build an Operations Console, not a customer storefront.**
   The APEX app should feel like a database/operator demo: products, stores,
   inventory, vector recommendations, model/status diagnostics, and API catalog
   connectivity. The Litestar HTMX web UI remains the customer-facing browser
   experience.

3. **Use official current versions, but verify what the container runs.**
   Target APEX 26.1 public media, document optional APEX 26.1.1 MOS patching,
   require ORDS 26.1.1+, prefer ORDS 26.1.2 where available, and require
   SQLcl 26.1.2+ for APEXlang. Implementation must probe runtime versions.

4. **APEXlang source lives under `src/apex/`.**
   Use `src/apex/cymbal-coffee-ops/` with official underscore directories:
   `shared_components/`, `supporting_objects/`, `deployments/`, `.apex/`,
   `pages/`, and `application.apx`.

5. **OpenAPI is the APEX bridge. MCP is the agent/tooling bridge.**
   APEX REST Source Catalogs consume a filtered OpenAPI document. Antigravity,
   SQLcl MCP, MCP Toolbox, and optional `litestar-mcp` are separate developer
   tooling demos.

6. **Generate clean Antigravity configs only.**
   Do not preserve old Gemini CLI migration behavior in the repo commands.
   Replace `~/.gemini/settings.json` writes with current Antigravity config
   outputs:
   `~/.gemini/config/mcp_config.json`,
   `~/.gemini/antigravity-cli/mcp_config.json`, and
   `.agents/mcp_config.json`.

7. **Re-add MCP Toolbox install/config support.**
   The installer should support a current command such as
   `python manage.py install mcp-toolbox` or `python manage.py install mcp`.
   It should install or verify MCP Toolbox and emit Antigravity-ready Oracle
   config snippets.

8. **Do not migrate the embedding model inside this PRD.**
   Expose current model/status to APEX, but leave `gemini-embedding-2` migration
   to a separate data/fixture PRD because it touches committed embeddings and
   cache behavior.

9. **Use official Oracle Skills as the APEX/ORDS/SQLcl guidance layer.**
   Document and optionally install the Oracle `apex` and `db` skills for
   Antigravity/Codex-compatible agent workflows. Do not invent local APEXlang or
   ORDS instructions when the official skills already cover the topic. Keep MCP
   Toolbox support because it demonstrates Google's database MCP path; pair it
   with Oracle SQLcl MCP rather than replacing one with the other.

---

## Roadmap

| Ch | Flow | Beads | Depends on | Risk |
| --- | --- | --- | --- | --- |
| 1 | APEX runtime hardening and Flow reconciliation (`apex-runtime-hardening`) | `oracledb-vertexai-apxo.1` | related to `apex-gvenzl-install` | high |
| 2 | SQLcl 26.1.2 APEXlang lifecycle (`apexlang-lifecycle`) | `oracledb-vertexai-apxo.2` | Ch1 | medium |
| 3 | APEX-safe coffee data API and OpenAPI contract (`apex-ops-api`) | `oracledb-vertexai-apxo.3` | Ch1 | medium |
| 4 | Schema bridge and Antigravity MCP configuration (`apex-schema-bridge`) | `oracledb-vertexai-apxo.4` | Ch3 | medium |
| 5 | Cymbal Coffee APEX Operations Console app (`apex-ops-app`) | `oracledb-vertexai-apxo.5` | Ch2, Ch3, Ch4 | high |
| 6 | APEX demo verification and docs (`apex-demo-verification-docs`) | `oracledb-vertexai-apxo.6` | Ch1-Ch5 | medium |

Each chapter has an implementation worksheet at `.agents/specs/<flow>/spec.md`.

---

## Chapter Deliverables

### Chapter 1 - `apex-runtime-hardening`

- Refresh the current ORDS sidecar plan against the already-landed code.
- Replace `:latest` as the default ORDS image policy with an explicit version
  target or a documented runtime verification strategy.
- Add ORDS/APEX HTTP readiness probes for `/ords/` and `/i/`.
- Add explicit `manage.py infra ords start|stop|restart|status|logs|remove`
  or equivalent nested commands instead of hiding ORDS only inside DB start.
- Record the APEX 26.1 re-release and optional APEX 26.1.1 patch handling in
  docs and installer status output.
- Reconcile the old `apex-gvenzl-install` open chapters so implementation
  does not duplicate stale tasks.
- Route ORDS and container guidance through Oracle's `db` skill files:
  `db/ords/*` and `db/containers/ords.md`.

### Chapter 2 - `apexlang-lifecycle`

- Add SQLcl 26.1.2+ version parsing and APEXlang capability verification.
- Add APEXlang generate/export/validate/import wrappers under
  `manage.py infra apex`.
- Create `src/apex/cymbal-coffee-ops/` using official APEXlang layout names.
- Make the app source round-trip deterministic in tests where possible and in
  Oracle smoke verification where required.
- Route APEX app generation through Oracle's `apex` skill and APEXlang
  workflow references.

### Chapter 3 - `apex-ops-api`

- Add stable JSON endpoints designed for APEX REST Source Catalogs:
  inventory summary, store inventory, product availability, vector
  recommendations, explain/status data, and AI model status.
- Keep the existing HTMX and chat endpoints intact.
- Add msgspec response schemas with stable operation IDs and schema names.
- Export enough OpenAPI metadata for APEX to generate useful catalog entries.
- Use Oracle Database skill references for vector search and ORDS REST design
  where endpoint decisions touch Oracle-specific semantics.

### Chapter 4 - `apex-schema-bridge`

- Add a filtered OpenAPI export for APEX, not the entire app schema.
- Add REST Source Catalog documentation and optional refresh URL guidance.
- Add clean Antigravity MCP config generation for SQLcl MCP, MCP Toolbox for
  Oracle, and optional app MCP.
- Re-add `manage.py install mcp-toolbox` or a clearly named equivalent.
- Add install/check guidance for the official Oracle `apex` and `db` skills.
- Remove the implementation path that writes Gemini CLI MCP config to
  `~/.gemini/settings.json`.

### Chapter 5 - `apex-ops-app`

- Build the APEXlang app source for the Cymbal Coffee Operations Console.
- Demonstrate:
  - product catalog browsing
  - store/location inventory reports
  - low-stock/out-of-stock views
  - product availability by store
  - vector recommendation/search panels
  - API/model/runtime status
  - REST Source Catalog integration health
- Keep APEX as a consumer of the Litestar APIs; do not reimplement business
  logic in APEX PL/SQL unless needed for APEX wiring.
- Use Oracle's APEXlang skill workflow to generate and refine source, then use
  SQLcl validation before import.

### Chapter 6 - `apex-demo-verification-docs`

- Add repeatable smoke checks for APEX install, ORDS readiness, APEXlang
  validation, OpenAPI export, MCP config generation, and a minimal APEX app
  round trip.
- Add Sphinx docs for the APEX app, APEXlang lifecycle, REST Source Catalog
  bridge, and "MCP configuration and usage in Antigravity".
- Add a documented "official Oracle Skills" section that explains `apex` and
  `db`, where ORDS lives, and how they complement SQLcl MCP and MCP Toolbox.
- Keep the formal lab content uploadable as one markdown file; Sphinx should
  include or reference that single markdown source rather than splitting it
  into many lab fragments.

---

## Global Constraints

- Planning and implementation must preserve unrelated in-flight docs/logo/lab
  work in this branch.
- Do not add Gemini CLI migration support. Replace old hooks with current
  Antigravity config paths.
- Do not put APEX app source outside `src/apex/`.
- Do not use hyphenated APEXlang official directory names.
- Do not persist browser coordinates. APEX-facing APIs can expose seeded store
  coordinates but must not log or store user coordinates.
- Do not make APEX depend on SSE chat.
- Do not migrate embedding fixtures or cache data in this PRD.
- Use named SQL and typed service boundaries when adding production database
  queries.
- Preserve `make start-infra` as DB-only. APEX remains opt-in through
  `make apex` / infra commands unless the user explicitly changes that policy.

---

## Acceptance Criteria

- A new developer can run the optional APEX path and see APEX 26.1 served
  through ORDS with a real readiness check.
- SQLcl 26.1.2+ APEXlang commands can generate, validate, export, and import
  the tracked app source.
- `src/apex/cymbal-coffee-ops/` contains source-controlled APEXlang app assets.
- APEX can create or refresh a REST Source Catalog from the filtered OpenAPI
  artifact.
- APEX pages demonstrate real Cymbal Coffee product, store, inventory, vector,
  and model/status data from the Litestar app.
- Antigravity docs and generated configs demonstrate current MCP config paths:
  IDE, CLI global, CLI workspace, and optional plugin-root configs.
- `manage.py install mcp-toolbox` or the chosen equivalent exists, verifies
  the current MCP Toolbox package, and emits Oracle config guidance.
- Official Oracle `apex` and `db` skills are documented as the source-backed
  agent guidance for APEXlang, ORDS, SQLcl MCP, vector search, and container
  selection.
- Old Gemini CLI MCP config writes to `~/.gemini/settings.json` are gone from
  touched installer paths.
- `make lint` and `make test` pass for code changes, with additional APEX/ORDS
  smoke checks documented and run where local runtime is available.

---

## Out Of Scope

- Migrating from Gemini CLI config files.
- Migrating embeddings from `gemini-embedding-2-preview` to
  `gemini-embedding-2`.
- Making APEX the primary UI for the demo.
- Replacing Litestar HTMX pages or ADK chat behavior.
- Production-hardening ORDS TLS, reverse proxy, or OAuth beyond local demo
  needs.

---

## Review Questions

No product decision blocks implementation. Defaults:

- Use "Cymbal Coffee Operations Console" as the APEX app name.
- Keep APEX runtime opt-in.
- Generate both Antigravity IDE and CLI MCP configs, with workspace config in
  `.agents/mcp_config.json` and plugin examples as optional docs.
- Keep MCP Toolbox and APEX REST Source Catalogs separate in UI text and docs.
