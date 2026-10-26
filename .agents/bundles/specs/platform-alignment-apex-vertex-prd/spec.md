---
type: Spec
flow_id: platform-alignment-apex-vertex-prd
title: SQLSpec 0.69.0 Platform Alignment, Codebase Simplification, Autonomous AI Database Free APEX 26.1 + Vertex AI, and Automated Demo Recordings
state: active
plan_revision: 1
plan_commit: "7ff2771"
state_revision: 2
current_task: null
last_operation: checkpoint
operation_targets:
  - domain-standardization-and-debloat
last_verified_checkpoint: "5e3fd17"
created_at: 2026-10-24T19:25:00Z
updated_at: 2026-10-25T15:59:30Z
description: Master PRD roadmap delivering SQLSpec 0.69.0 adoption, frozen msgspec/service/DI standardization and codebase debloating, Oracle Autonomous AI Database Free 26ai (APEX 26.1.5 + ORDS 26.3) migration, Direct Vertex AI + Litestar gateway APEX 26.1 Generative AI integration with a cohesive Cymbal Coffee APEX 26.1 app, and automated VHS + Playwright + FFmpeg shell/browser demo recordings across five stacked PRs.
tags:
  - refactor
  - sqlspec
  - architecture
  - oracle-26ai
  - apex
  - vertex-ai
parent_prd: null
research:
  - research/codebase-alignment-and-apex/research.md
---

# Master PRD: SQLSpec 0.69.0 Platform Alignment, Codebase Simplification, Autonomous AI Database Free APEX 26.1 + Vertex AI, and Automated Demo Recordings

**Flow ID:** `platform-alignment-apex-vertex-prd`

---

## North Star

Deliver a clean, readable, and modern Cymbal Coffee codebase and end-to-end **Oracle AI Database 26ai + APEX 26.1 + Vertex AI** developer experience shipped as a **stacked set of self-contained pull requests**:

1. **Adopt SQLSpec `0.69.0` & Clean Core Foundations**:
   - Upgrade to `sqlspec>=0.69.0`, replacing the removed `enable_AutoLob` driver key with zero-RTT Oracle session tracing (`enable_session_tracing: True`) and wire-level OpenTelemetry `sqlcommenter`, adding `"manage_lifespan": True` on the dedicated `queue_db` pool, and delegating Autonomous mTLS wallet extraction/PEM conversion to `sqlspec.adapters.oracledb.extract_oracle_wallet_zip` (`wallet_zip`).
   - Standardize `FrozenBaseStruct` / `CamelizedFrozenStruct` (`frozen=True, gc=False`), centralized `app.utils.serialization` JSON helpers, `app.lib.exceptions` (`ApplicationError`, `AIServiceUnconfigured`), `OracleLoaderService` (`SQLFileLoader` without `app.config` imports), and decoupled Dishka providers (`DBProvider`, `AIProvider`, `DomainServiceProvider`).
2. **Standardize Every Domain & Remove Dead Code**:
   - Align `system`, `chat`, `ai`, `products`, and `web` domains on `OracleLoaderService`, private `_*` service/controller/schema modules, mypyc-safe post-`except:` SQLSpec fallback queries, and concise single-responsibility files while deleting dead wrappers, compatibility aliases, and `pyproject.toml` `banned-api` per-file ignores.
3. **Move Local Infrastructure to Autonomous AI Database Free 26ai (`adb-free:latest-26ai`)**:
   - Run `container-registry.oracle.com/database/adb-free:latest-26ai` (`26.9.4.1-26ai` bundling Oracle AI Database 26ai + APEX 26.1.5 + ORDS 26.3 on `:8443`) as the default managed development container with automated mTLS wallet export and `ADMIN` schema/workspace bootstrap, while preserving `gvenzl/oracle-free:latest` (`ORACLE_CONTAINER_FLAVOR=free`) for fast ephemeral integration tests.
   - Retire ~1,800 lines of obsolete `gvenzl` SYSDBA APEX/ORDS/health installer code, fix Cloud Run PyApp wheel packaging of `configure-apex-cdn.sql`, and enforce `tools/ci/check_code_hygiene.py` across the entire `tools/` tree and `manage.py`.
4. **Connect APEX 26.1 to Vertex AI & Ship One Cohesive Cymbal Coffee APEX 26.1 App**:
   - Document and automate **Direct Vertex AI OpenAI-compatible connectivity** (`https://aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/endpoints/openapi`, `model="google/gemini-3.8-flash"`) first via `DBMS_NETWORK_ACL_ADMIN`, `APEX_CREDENTIAL`, and the `COFFEE_VERTEX_AI` Generative AI Service (`Used by App Builder = Yes`), paired with a **Litestar OpenAI-compatible Vertex gateway** (`POST /api/apex/ai/v1/chat/completions`) for managed/mTLS environments.
   - Upgrade `src/apex/cymbal-coffee-ops/` (`compatibilityMode: 26.1`) into one approachable Vertex-AI-powered Cymbal Coffee APEX 26.1 application combining live Oracle 26ai catalog/store/inventory/annotation reports, `APEX_AI.GENERATE` coffee concierge prompts, and `/api/apex/*` hybrid recommendation views.
5. **Automate Deterministic Shell & Browser Video Recordings**:
   - Provide fail-fast `vhs` `.tape` recordings (`docs/_tapes/*.tape` + `tools/demos/shell.py`) and headless Python `playwright` + `ffmpeg` browser recordings (`tools/demos/web.py`) generating crisp `.mp4` and palette-optimized `.gif` walkthroughs of configuring APEX 26.1 for Vertex AI and building/running the Cymbal Coffee app.

---

## Architectural Decisions (Resolved)

1. **Clean Current-Plan Specs Only (`Decision 1`)**:
   - Superseded/paused APEX, ADB-Free, and VHS draft specs are retired rather than preserving historical pause/change notes. Still-relevant specs (`knowledge-catalog-grounding-demo` and its child flows) are refined in place to match `OracleLoaderService`, `FrozenBaseStruct`, `Settings.from_env()`, and post-refactor module paths.
2. **APEX 26.1 $\rightarrow$ Vertex AI Connectivity (`Decision 2`)**:
   - **Method 1 (Primary — Direct Vertex AI `/endpoints/openapi`)** is wired and documented first (`manage.py infra apex configure-vertex --mode direct`), provisioning Oracle network ACLs for `aiplatform.googleapis.com`, OAuth2 Bearer `APEX_CREDENTIAL` (`VERTEX_AI_CRED`), and the `COFFEE_VERTEX_AI` Generative AI Service targeting `google/gemini-3.8-flash`.
   - **Method 2 (Secondary — Litestar OpenAI-Compatible Gateway)** is wired alongside it (`POST /api/apex/ai/v1/chat/completions` + `--mode gateway` targeting `http://host.docker.internal:8000/api/apex/ai/v1`) so developers on mTLS/Context-Aware Access workstations or long-running local demos avoid 60-minute OAuth token expiry.
3. **Retire Legacy `gvenzl` SYSDBA APEX Installer & `OrdsSidecar` (`Decision 3`)**:
   - Delete `tools/oracle/{apex_media,apex_install,ords,health}.py` and `tools/oracle/cli/{ords,health,sqlcl}.py` so local APEX 26.1 runs exclusively on `adb-free:latest-26ai`, while retaining `ORACLE_CONTAINER_FLAVOR=free` (`gvenzl/oracle-free`) for `make test-integration` and fixing packaged `src/app/db/sql/deploy/configure-apex-cdn.sql` for Cloud Run jobs.
4. **Single Cohesive Vertex-AI-Powered Cymbal Coffee APEX 26.1 App (`Decision 4`)**:
   - Upgrade `src/apex/cymbal-coffee-ops/` (`compatibilityMode: 26.1`) into one clean, SQLcl-validated APEXlang application showcasing Oracle 26ai relational/annotation reports, `APEX_AI.GENERATE` (`COFFEE_VERTEX_AI`), and `/api/apex/*` health/recommendations, used both as tracked source and for the automated app-creation video walkthrough.

---

## Stacked-PR Topology & Roadmap Chapters

Each chapter corresponds to **one self-contained, green-CI pull request** in a linear 5-PR stack (`main` $\leftarrow$ PR 1 $\leftarrow$ PR 2 $\leftarrow$ PR 3 $\leftarrow$ PR 4 $\leftarrow$ PR 5). Every PR uses a conventional title (`<type>(<scope>): <concise summary>`) and a standalone body (`## Summary` and `## Key Changes` grouped by module, with zero multi-PR stack navigation tables and zero `## Verification` command blocks), pushed incrementally to `origin` after `make lint` and unit verification pass.

| PR / Order | Flow ID | Proposed Branch & PR Title | Base Branch | Tasks | Summary |
| --- | --- | --- | --- | --- | --- |
| **PR 1** | [`sqlspec-069-and-core-foundation`](../sqlspec-069-and-core-foundation/spec.md) | `refactor/sqlspec-069-core` — `refactor(core): adopt sqlspec 0.69.0 tracing, wallet config, and loader services` | `main` | `1.1`–`1.4` | Upgrade to `sqlspec>=0.69.0` & `msgspec>=0.22.0`; adopt `enable_session_tracing`, wire `sqlcommenter`, `queue_db` `manage_lifespan`, and `wallet_zip`; add `FrozenBaseStruct`, centralized serialization, `app.lib.exceptions`, and `OracleLoaderService`; decouple `src/app/ioc/` and `src/app/config.py`; tighten nested-import CI gates. |
| **PR 2** | [`domain-standardization-and-debloat`](../domain-standardization-and-debloat/spec.md) | `refactor/domain-standardization` — `refactor(domain): standardize loader services, frozen schemas, and module boundaries` | `refactor/sqlspec-069-core` | `2.1`–`2.4` | Migrate `system`, `chat`, `ai`, `products`, and `web` domains to `OracleLoaderService` and `FrozenBaseStruct`; add shared `app.lib.text_search`; split oversized chat/AI/products modules; fix DFW city filter & mypyc-safe post-`except:` SQLSpec fallbacks; delete dead wrappers/aliases and `pyproject.toml` `banned-api` ignores. |
| **PR 3** | [`adb-free-26ai-and-tools-hygiene`](../adb-free-26ai-and-tools-hygiene/spec.md) | `feat/adb-free-26ai-runtime` — `feat(infra): adopt adb-free 26ai runtime, retire legacy apex sidecar, and enforce tools hygiene` | `refactor/domain-standardization` | `3.1`–`3.4` | Make `adb-free:latest-26ai` (APEX 26.1.5 + ORDS 26.3) the default managed container with mTLS wallet export & `ADMIN` bootstrap (`free` flavor preserved for integration tests); delete legacy `gvenzl` APEX/ORDS/health modules; fix Cloud Run `configure-apex-cdn.sql` packaging & `tools/cli/` bugs; enforce `check_code_hygiene.py` across `tools/` and `manage.py`. |
| **PR 4** | [`apex-26-vertex-ai-and-app`](../apex-26-vertex-ai-and-app/spec.md) | `feat/apex-26-vertex-ai` — `feat(apex): wire direct vertex ai endpoint, openai-compatible gateway, and apex 26.1 app` | `feat/adb-free-26ai-runtime` | `4.1`–`4.3` | Add `manage.py infra apex configure-vertex` provisioning Direct Vertex AI `/endpoints/openapi` (`COFFEE_VERTEX_AI` + `VERTEX_AI_CRED` + network ACLs) as primary method; add `ApexAIController` (`/api/apex/ai/v1/chat/completions`) backed by `GeminiModelClient` as managed/mTLS gateway; upgrade `src/apex/cymbal-coffee-ops/` to APEX 26.1 with live SQL reports and `APEX_AI.GENERATE`. |
| **PR 5** | [`web-and-shell-demo-recordings-and-docs`](../web-and-shell-demo-recordings-and-docs/spec.md) | `docs/apex-vertex-demo-recordings` — `docs(demos): add automated vhs and playwright video recorders and refresh apex docs` | `feat/apex-26-vertex-ai` | `5.1`–`5.4` | Add deterministic `vhs` shell/SQLcl tapes & runner (`tools/demos/shell.py`, `docs/_tapes/*.tape`), headless Playwright + FFmpeg browser video recorder (`tools/demos/web.py`, `make docs-demos-{shell,web,live}`), and run a parallel multi-agent sentence-by-sentence factual audit across `README.md`, Sphinx `docs/`, `AGENTS.md`, OKF knowledge chapters, and review skills. |

---

## Requirement-to-Chapter Traceability

| Requirement ID | Requirement Summary | Owning Chapter | Tasks |
| --- | --- | --- | --- |
| `PLAT-REQ-01` | Upgrade `sqlspec>=0.69.0` and `msgspec>=0.22.0`; replace `enable_AutoLob` with `enable_session_tracing` + wire `sqlcommenter`, add `queue_db` `"manage_lifespan": True`, adopt native `wallet_zip`, and add `slots=True` across all settings dataclasses while removing dead `ADK_*` and duplicate lowercase queue properties | `sqlspec-069-and-core-foundation` | `1.1` |
| `PLAT-REQ-02` | Introduce `FrozenBaseStruct` / `CamelizedFrozenStruct` (`frozen=True, gc=False`), centralized `app.utils.serialization` helpers (`decode_json`, `encode_json_bytes`, `to_schema`), `app.lib.exceptions` (`ApplicationError`, `AIServiceUnconfigured`, `is_expected_service_unavailable`), frozen `SecurityContext` principals, and `OracleLoaderService` (`SQLFileLoader`) | `sqlspec-069-and-core-foundation` | `1.2` |
| `PLAT-REQ-03` | Delete unused `src/app/lib/log/_security.py` and `SuppressADKWarningsFilter`, decouple `src/app/config.py` from `app.server` via `register_reset_hook` and top-level imports, and tighten nested-import CI gates to `src/app/cli/{commands,main}.py` | `sqlspec-069-and-core-foundation` | `1.3` |
| `PLAT-REQ-04` | Decouple `src/app/ioc/` (`DBProvider`, `AIProvider`, `DomainServiceProvider`) from `app.config` and `app.server`, scope `AgentStreamService` to `Scope.APP`, type Vertex credentials via `CredentialProtocol`, and remove `LitestarPersistenceProvider`, `IntegrationsProvider`, and `make_container` aliases | `sqlspec-069-and-core-foundation` | `1.4` |
| `PLAT-REQ-05` | Migrate `system` domain to `OracleLoaderService`, `FrozenBaseStruct`, atomic `MERGE INTO` cache upserts, disjoint metric comparison windows, and split `_personas.py` / `_metrics.py` services while deleting `_health.py` and `ResponseCacheService` / `SystemService` aliases | `domain-standardization-and-debloat` | `2.1` |
| `PLAT-REQ-06` | Extract shared `src/app/lib/text_search.py` (Oracle Text token sanitizer + proximity helper), migrate `chat` domain to `OracleLoaderService` and `FrozenBaseStruct`, split `_composers.py` out of `_grounded.py`, and fix `_KNOWN_CITY_FILTERS` for seeded DFW cities | `domain-standardization-and-debloat` | `2.2` |
| `PLAT-REQ-07` | Migrate `ai` domain (`OracleSessionStore`, `OracleEventStore`, `AgentOrchestrationService`, A2A `_card.py`/`_executor.py`, `_agent.py`/`_history.py`) to `OracleLoaderService` and `FrozenBaseStruct`, push `:limit` into `list-ai-events` SQL, and delete `RunContextRegistry` and `CoffeeToolServices` | `domain-standardization-and-debloat` | `2.3` |
| `PLAT-REQ-08` | Migrate `products` and `web` domains to `OracleLoaderService` and `FrozenBaseStruct` (`paginate_limit_offset`, pure async `VertexAIService.embed_missing_products`, dedicated `_vector.py` with mypyc-safe post-`except:` SQLSpec fallback), delete `_inventory.py`, `_vector_helpers.py`, `MapsService`, `EmbeddingService`, `chat/{exceptions,session}.py`, `BaseStruct`/`CamelizedBaseStruct`, and `pyproject.toml` `banned-api` ignores | `domain-standardization-and-debloat` | `2.4` |
| `PLAT-REQ-09` | Configure `adb-free:latest-26ai` (`cymbal-adb-free`, `:1521/:1522/:8443`, `/u01/data`) as default managed container with mTLS wallet export (`sqlspec.adapters.oracledb.extract_oracle_wallet_zip`), `ADMIN` schema/ORDS/APEX workspace provisioning, and `ORACLE_CONTAINER_FLAVOR=free` retention for `src/tests/integration/conftest.py` | `adb-free-26ai-and-tools-hygiene` | `3.1` |
| `PLAT-REQ-10` | Delete retired `gvenzl` APEX/ORDS/health/SQLcl modules (`tools/oracle/{apex_media,apex_install,ords,health}.py`, `tools/oracle/cli/{ords,health,sqlcl}.py`) and update `ApexLang`, `ApexCatalog`, `manage.py`, and `manage.py infra apex status` for wallet-backed `adb-free:latest-26ai` | `adb-free-26ai-and-tools-hygiene` | `3.2` |
| `PLAT-REQ-11` | Package `configure-apex-cdn.sql` and `revert-apex-cdn.sql` under `src/app/db/sql/deploy/`, align `Dockerfile` and `cloudbuild.yaml` for Cloud Run ORDS jobs, and fix `tools/cli/install.py` string-iteration and `tools/lib/utils.py` port/dead-code defects | `adb-free-26ai-and-tools-hygiene` | `3.3` |
| `PLAT-REQ-12` | Clean remaining inline `#` comments, nested imports, and unslotted dataclasses across `tools/` and `Makefile`, and expand `tools/ci/check_code_hygiene.py` to enforce AST and comment rules across all of `tools/**/*.py` and `manage.py` | `adb-free-26ai-and-tools-hygiene` | `3.4` |
| `PLAT-REQ-13` | Implement `tools/oracle/apex_vertex.py` and `manage.py infra apex configure-vertex` (`--mode direct|gateway`, default `direct`) provisioning Oracle network ACLs, `APEX_CREDENTIAL` (`VERTEX_AI_CRED`), and APEX 26.1 Generative AI Service (`COFFEE_VERTEX_AI`, Vertex `/endpoints/openapi`, `google/gemini-3.8-flash`) with `APEX_AI.GENERATE` verification | `apex-26-vertex-ai-and-app` | `4.1` |
| `PLAT-REQ-14` | Implement `ApexAIController` (`POST /api/apex/ai/v1/chat/completions` and `GET /api/apex/ai/v1/models`) backed by `GeminiModelClient` and typed OpenAI-compatible `FrozenBaseStruct` schemas with optional Bearer API key auth | `apex-26-vertex-ai-and-app` | `4.2` |
| `PLAT-REQ-15` | Upgrade `src/apex/cymbal-coffee-ops/` (`compatibilityMode: 26.1`) into a single cohesive Cymbal Coffee APEX 26.1 application with SQL-backed catalog/store/inventory/annotation reports, `APEX_AI.GENERATE` coffee concierge page (`COFFEE_VERTEX_AI`), and `/api/apex/*` health/recommendations views validated by SQLcl 26.1.2 | `apex-26-vertex-ai-and-app` | `4.3` |
| `PLAT-REQ-16` | Implement `tools/demos/shell.py`, `tools/scripts/record-live-demos.sh`, and fail-fast `vhs` tapes (`docs/_tapes/apex-vertex-ai-setup.tape`, `docs/_tapes/apexlang-workflow.tape`) with automatic Chromium resolution (`ROD_BROWSER_BIN`) and `.mp4` + `.gif` output verification | `web-and-shell-demo-recordings-and-docs` | `5.1` |
| `PLAT-REQ-17` | Implement headless Playwright + FFmpeg browser video recorder (`tools/demos/web.py`, `tools/demos/cli.py`, `[dependency-groups].demos`) scripting Direct Vertex AI setup in APEX Workspace Utilities and Cymbal Coffee APEX 26.1 app creation/concierge execution (`make docs-demos-{shell,web,live}`) | `web-and-shell-demo-recordings-and-docs` | `5.2` |
| `PLAT-REQ-18` | Refresh and run parallel multi-agent sentence-by-sentence factual verification across `README.md`, `CONTRIBUTING.md`, `SLIDES.md`, Sphinx `docs/**`, `AGENTS.md`, `.agents/AGENTS.md`, test guides, `.agents/bundles/{product,knowledge}/**`, and `.agents/skills/**` for SQLSpec `0.69.0`, `adb-free:latest-26ai`, Direct Vertex AI + Gateway APEX 26.1 setup, and demo recorders | `web-and-shell-demo-recordings-and-docs` | `5.3`, `5.4` |

---

## Global Constraints

1. **Zero Inline `#` Comments & Top-Level Imports Only**: Never write inline `#` comments in Python files (`src/app/`, `src/tests/`, `tools/`, `manage.py`), and never use function-scoped imports outside lazy CLI subcommand dispatch in `src/app/cli/{main,commands}.py`. Explain design intent and edge cases in Google-style docstrings.
2. **Module & Class Organization**: Every module under `src/app/` and `tools/` defines a module docstring, grouped top-level imports, `__all__`, and public classes/functions before private `_...` helpers. Order class members strictly as: class attributes $\rightarrow$ `__init__` $\rightarrow$ `@property` $\rightarrow$ public methods $\rightarrow$ private `_...` methods.
3. **Frozen Value Objects & Centralized Serialization**: Use `FrozenBaseStruct` / `CamelizedFrozenStruct` (`msgspec.Struct(..., frozen=True, gc=False)`) for wire, config, and domain value objects, `@dataclass(frozen=True, slots=True)` (or `@dataclass(slots=True)`) for mutable runtime context holders, and centralized JSON helpers in `app.utils.serialization`. Never leave backward-compatibility aliases or re-export shims behind once callers are migrated.
4. **Settings, DI & MyPyC Safety**:
   - Provider modules in `src/app/ioc/` must never include `from __future__ import annotations` and must never import `app.config` or `app.server`.
   - Domain services inherit from `OracleLoaderService` (`self.get_sql("<name>")`) rather than importing `db_manager` from `app.config`.
   - Keep `DatabaseSettings.get_queue_config()` (`session_key="queue_db_session"`, `"manage_lifespan": True`) isolated from `DatabaseSettings.get_config()` so `litestar-queues` `fetch_lobs=False` never mutates the main application pool.
   - Never run fallback SQLSpec database queries inside an `except:` block under `sqlspec[mypyc]`; exit `except:` first so `sys.exc_info()` clears before executing fallback SQL.
5. **Security, Secret Hygiene & Coordinate Privacy**:
   - Every HTTP controller inherits from `PublicController` or `SecureController` (`litestar_security`).
   - Browser coordinates (`latitude`, `longitude`, `radius_miles`) remain opt-in and strictly request-scoped, never persisted to database tables, caches, metrics, APEX session state, or logs.
   - Never log, echo, or commit passwords, wallet passphrases, or OAuth2 bearer tokens; `.envs/` remains gitignored.
6. **Test Suite & Stacked-PR Discipline**:
   - Preserve all 9 `KEEP_LIST_PATHS` and the 3-`conftest.py` ratchet enforced by `src/tests/unit/test_test_suite_guards.py`; place all new tool unit tests flat under `src/tests/unit/tools/test_*.py` following the 5-section test layout (zero `class Test*`, docstrings on every `def test_*`, helpers before tests).
   - Sign all Git commits (`commit.gpgsign=true`), push each stacked PR branch incrementally to `origin` via `ggh` after `make lint` (`make py-check`) and unit verification pass, and write clean conventional PR titles/bodies without multi-PR stack tables or `## Verification` sections.

---

## Continuity Snapshot

- **Active Flow / Lifecycle**: `platform-alignment-apex-vertex-prd` (`active`)
- **Current Task & Claimant**: `null`
- **Last Verified Checkpoint**: `5e3fd17`
- **Key Decisions**:
  - Adopt SQLSpec `0.69.0` (`enable_session_tracing`, wire `sqlcommenter`, `queue_db` `manage_lifespan`, `wallet_zip`, `OracleLoaderService`) and `FrozenBaseStruct` (`frozen=True, gc=False`) in PR 1, followed by domain-wide standardization and dead-code removal in PR 2.
  - Switch local managed infrastructure to `container-registry.oracle.com/database/adb-free:latest-26ai` (APEX 26.1.5 + ORDS 26.3) and retire legacy `gvenzl` SYSDBA APEX/ORDS installers in PR 3 while keeping `gvenzl/oracle-free` for ephemeral `make test-integration`.
  - Wire Direct Vertex AI (`/endpoints/openapi`, `google/gemini-3.8-flash`) first alongside the Litestar OpenAI-compatible gateway (`/api/apex/ai/v1/chat/completions`) and upgrade `src/apex/cymbal-coffee-ops/` (`compatibilityMode: 26.1`) into one cohesive Vertex-AI-powered app in PR 4.
  - Automate deterministic shell (`vhs`) and browser (`playwright` + `ffmpeg`) demo recordings and synchronize documentation in PR 5.
- **Newest Discoveries**:
  1. SQLSpec `0.69.0` removes `enable_AutoLob` from `VALID_ORACLE_DRIVER_FEATURE_KEYS` and adds `enable_session_tracing`, wire-level `sqlcommenter`, and `extract_oracle_wallet_zip` (`wallet_zip`).
  2. `adb-free:latest-26ai` (`26.9.4.1-26ai`) ships Oracle AI Database 26ai with APEX 26.1.5 and ORDS 26.3 pre-installed on `:8443`, unblocking native APEXlang and Generative AI Services without SYSDBA.
  3. Ordering PR 2 tasks as `system` (`2.1`) $\rightarrow$ `chat` (`2.2`) $\rightarrow$ `ai` (`2.3`) $\rightarrow$ `products`/`web` (`2.4`) allows every legacy alias and dead service (`InventoryService`, `MapsService`, `EmbeddingService`, `RunContextRegistry`, `CoffeeToolServices`) to be removed cleanly with zero cross-task file overlap and green tests at every commit.
  4. Packaging `configure-apex-cdn.sql` under `src/app/db/sql/deploy/` fixes a broken path lookup (`BASE_DIR.parents[1] / "tools"`) inside distroless Cloud Run PyApp builds.
- **Blockers & Unblock Conditions**: None
- **Next Exact Step**: Branch `feat/adb-free-26ai-runtime` from `refactor/domain-standardization` and execute `adb-free-26ai-and-tools-hygiene` Tasks `3.1`–`3.4`.
- **Plan Identity**: `plan_revision: 1`, `plan_commit: "7ff2771"`
- **State Identity**: `state_revision: 2`, `last_operation: checkpoint`, `operation_targets: ["domain-standardization-and-debloat"]`
- **Relevant Knowledge Paths**:
  - `.agents/bundles/specs/platform-alignment-apex-vertex-prd/research/codebase-alignment-and-apex/research.md`
  - `.agents/bundles/knowledge/architecture/system-architecture.md`
  - `.agents/bundles/knowledge/domains/core-lib-ioc-server-cli.md`
  - `.agents/bundles/knowledge/gotchas/oracle-sqlspec-and-queues.md`
  - `src/tests/AGENTS.md`
