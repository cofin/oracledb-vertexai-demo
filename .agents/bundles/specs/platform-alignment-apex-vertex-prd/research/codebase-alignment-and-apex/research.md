---
type: Research
research_id: codebase-alignment-and-apex
title: SQLSpec 0.69.0 Capabilities, Service Architecture Alignment, Autonomous AI Database Free APEX 26.1, and Automated Demo Recording
description: Primary-source verification of SQLSpec 0.69.0 Oracle 26ai tracing/wallet/service APIs, domain service and Dishka DI standardization, Oracle Autonomous AI Database Free 26ai (APEX 26.1.5 + ORDS 26.3), Direct Vertex AI OpenAI-compatible APEX integration, and VHS + Playwright + FFmpeg video capture.
scope: architecture
tags:
  - research
  - sqlspec
  - architecture
  - oracle-26ai
  - apex
  - vertex-ai
  - video-recording
status: stable
state: promoted
promoted_to: platform-alignment-apex-vertex-prd
confidence: high
created_at: 2026-10-24T18:20:00Z
updated_at: 2026-10-24T19:25:00Z
---

# SQLSpec 0.69.0 Capabilities, Service Architecture Alignment, Autonomous AI Database Free APEX 26.1, and Automated Demo Recording

## 1. SQLSpec 0.69.0 Primary-Source Verification

### Breaking Oracle Driver Feature Key (`enable_AutoLob` Removed)

- `sqlspec.adapters.oracledb` (`0.69.0`) validates `driver_features` against `VALID_ORACLE_DRIVER_FEATURE_KEYS`:
  `enable_numpy`, `enable_lowercase_column_names`, `enable_uuid_binary`, `on_connection_create`, `enable_events`, `events_backend`, `fetch_lobs`, and `enable_session_tracing`.
- `src/app/lib/settings/_database.py:125` currently passes `driver_features={"enable_AutoLob": True}`, which raises `ImproperConfigurationError` at startup on SQLSpec `0.69.0`.
- LOB hydration defaults to `fetch_lobs=True` natively on the main application pool, while `litestar-queues` (`OracledbAsyncQueueStore`) mutates `driver_features["fetch_lobs"] = False` on the dedicated `queue_db` `OracleAsyncConfig` (`session_key="queue_db_session"`).
- `DatabaseSettings.get_queue_config` (`src/app/lib/settings/_database.py:149-168`) omits `"manage_lifespan": True` in `extension_config["litestar"]`; adding `"manage_lifespan": True` guarantees clean shutdown of the `min=1, max=4` queue pool.

### Zero-RTT Session Tracing & Wire-Level SQLCommenter

- Setting `driver_features={"enable_session_tracing": True}` on `OracleAsyncConfig` piggybacks OpenTelemetry trace context (`client_identifier`, `econtext_id`, `module`, `action`) onto Oracle TTC packets with zero extra network round trips.
- Passing `statement_config=default_statement_config().replace(enable_sqlcommenter=True, sqlcommenter_enable_context=True, sqlcommenter_enable_traceparent=True)` appends wire-level OpenTelemetry `traceparent` comments after statement compilation so statement compilation caches are never invalidated.

### Native Autonomous Wallet Handling (`wallet_zip`)

- `sqlspec.adapters.oracledb` exports `extract_oracle_wallet_zip` and `parse_tnsnames_ora`.
- Passing `"wallet_zip": str(Path(self.WALLET_LOCATION).resolve())` and `"wallet_password": conn_params["wallet_password"]` in `DatabaseSettings._build_pool_config` (`_database.py:174-200`) handles both `.zip` archives and pre-extracted wallet directories, converts `ewallet.p12` to unencrypted PKCS#8 `ewallet.pem` (`0o700` directory / `0o600` files) so OpenSSL never blocks on `stdin` in Thin mode, and parses `tnsnames.ora` without mutating `os.environ["TNS_ADMIN"]` or disabling TLS hostname verification (`ssl_ctx.check_hostname = False`).

### `SQLSpecAsyncService`, `SQLFileLoader` & MyPyC `except:` Block Hazard

- `SQLSpecAsyncService` (`sqlspec.service`) defines `__slots__ = ("_config", "_loader", "_session", "_transaction_key", "_transaction_state")` and requires **exactly one** of `session` or `config` (`SQLSpecAsyncService(session=..., *, config=..., loader=...)`). It provides `provide_session()`, `paginate()`, `paginate_limit_offset()`, `get_one()`, `get_one_or_none()`, `exists()`, and `begin_transaction()`.
- `SQLFileLoader` (`sqlspec.loader`) loads `src/app/db/sql/*.sql` directly via `loader.load_sql(BASE_DIR / "db" / "sql")`, eliminating `from app.config import db_manager` imports inside domain services.
- **Fixture Loader Retention**: `src/app/utils/fixtures.py` (`FixtureLoader` / `FixtureExporter` using `open_fixture_async` + `sql.merge(dialect="oracle")`) must remain in place because SQLSpec `0.69.0`'s `load_table_fixtures_async` double-quotes lowercase table identifiers (`"store"` triggers `ORA-00942` on unquoted Oracle tables) and `_ON_CONFLICT_FAMILIES` omits `"oracle"`.
- **MyPyC `except:` Block Rule**: Under `sqlspec[mypyc]`, calling an async SQLSpec driver method *inside* an `except:` block can observe a non-`None` `sys.exc_info()[1]` inside compiled frames. Always capture the error summary inside `except:`, exit the `except:` block so `sys.exc_info()` clears, and run fallback SQLSpec queries after the `try...except` block.

---

## 2. Service Architecture Alignment & Codebase Debloat Audit

1. **Frozen No-GC Wire & Domain Structs**:
   - Standardize `FrozenBaseStruct(msgspec.Struct, frozen=True, gc=False, omit_defaults=True)` and `CamelizedFrozenStruct(FrozenBaseStruct, rename="camel")` in `src/app/lib/schema.py` so hot-path value objects omit CPython `PyGC_Head` cyclic GC overhead.
   - Route all JSON encoding/decoding through `src/app/utils/serialization.py` (`encode_json`, `encode_json_bytes`, `decode_json`, `to_schema`, `sanitize_for_json`) rather than calling `json.loads` / `json.dumps` / `msgspec.json.encode` directly across domain modules.
2. **DI & Composition-Root Boundaries**:
   - Remove `app.config` and `app.server` imports from `src/app/ioc/_database.py`, `src/app/ioc/_ai.py`, and `src/app/ioc/_domain.py`.
   - Inject `SQLFileLoader` into an `OracleLoaderService(OracleAsyncService)` base class exposing `self.get_sql("<name>")` and `self.provide_app_session()`.
   - Register `register_reset_hook` in `src/app/config.py` so `config._reset()` runs registered cleanup callbacks without importing `app.server.plugins`.
3. **Domain Module Hygiene & Dead-Code Removal**:
   - Remove legacy `google.adk` log filters (`SuppressADKWarningsFilter`), dead `ADK_*` settings fields, unused `src/app/lib/log/_security.py` (`BeforeSendHandler`), pass-through `src/app/domain/products/services/_inventory.py` (`InventoryService`), redundant `MapsService` wrapper class, unused `RunContextRegistry`, `CoffeeToolServices`, and legacy compatibility aliases (`ResponseCacheService`, `SystemService`, `EmbeddingService`, `LitestarPersistenceProvider`, `IntegrationsProvider`, `make_container`), then delete the `banned-api` per-file ignores in `pyproject.toml:305-313`.
   - Split oversized modules (`src/app/domain/chat/services/_grounded.py` at 835 lines, `src/app/domain/ai/services/agent_service.py` at 683 lines, `src/app/domain/system/services/_health.py`, and `src/app/domain/products/services/_embedding.py`) into focused private `_*` modules (`_grounded.py` + `_composers.py`, `_agent.py` + `_history.py`, `_personas.py` + `_metrics.py`, `_embedding.py` + `_vector.py`).
   - Fix `_KNOWN_CITY_FILTERS` in chat location parsing to match the seeded Dallas-Fort Worth stores (`dallas`, `plano`, `fort worth`, `arlington`, `frisco`, `irving`).
   - Package `configure-apex-cdn.sql` and `revert-apex-cdn.sql` under `src/app/db/sql/deploy/` so `coffee configure-apex-cdn` works inside wheel and distroless PyApp Cloud Run images (`tools/deploy/docker/Dockerfile`).

---

## 3. Autonomous AI Database Free 26ai & APEX 26.1 + Vertex AI Integration

### Unmerged Branch Audit & Container Verification

- Audit of all local and remote branches in `oracledb-vertexai-demo` confirmed zero unmerged APEX work exists outside `main` (`src/apex/cymbal-coffee-ops/`, `tools/oracle/apex_*.py`, and `src/app/domain/products/controllers/_apex.py` are all already merged on `main`).
- `container-registry.oracle.com/database/adb-free:latest-26ai` (and `ghcr.io/oracle/adb-free:latest-26ai`, release `26.9.4.1-26ai`) bundles **Oracle AI Database 26ai**, **Oracle APEX 26.1.5**, and **ORDS 26.3** pre-configured on HTTPS `:8443`, with persistent data at `/u01/data` and mTLS wallet generation at `/u01/app/oracle/wallets/tls_wallet` (`myatp_low`).
- Because `adb-free:latest-26ai` pre-installs APEX 26.1.5 and ORDS 26.3 (and denies `SYSDBA`), the local `gvenzl` SYSDBA APEX installer and ORDS sidecar modules (`tools/oracle/{apex_media,apex_install,ords}.py`, `tools/oracle/cli/ords.py`, plus unused `tools/oracle/{health,cli/health,cli/sqlcl}.py`) are retired, while `ORACLE_CONTAINER_FLAVOR=free` (`gvenzl/oracle-free:latest`) remains the lightweight ephemeral database backend for `make test-integration`.

### Connecting APEX 26.1 to Vertex AI (Two Supported Paths)

1. **Method 1 (Primary — Direct Vertex AI OpenAI-Compatible Endpoint)**:
   - Vertex AI exposes an OpenAI-compatible Chat Completions endpoint at `https://aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/endpoints/openapi` (supporting `model="google/gemini-3.8-flash"`).
   - Provisioned idempotently from `ADMIN` / workspace `COFFEE`:
     1. `DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE` granting `http` privilege on `aiplatform.googleapis.com` to `APP` and `APEX_260100`.
     2. `APEX_CREDENTIAL.CREATE_CREDENTIAL` / `SET_PERSISTENT_CREDENTIALS` configuring `VERTEX_AI_CRED` (`HTTP Header` `Authorization: Bearer <oauth2_token>` minted via `google.auth` / `gcloud auth application-default print-access-token`, refreshable via CLI).
     3. APEX 26.1 **Generative AI Service** `COFFEE_VERTEX_AI` (OpenAI-compatible provider pointing at the Vertex `/endpoints/openapi` base URL, model `google/gemini-3.8-flash`, `Used by App Builder = Yes`) invoked from SQL/PL/SQL and regions via `APEX_AI.GENERATE(p_prompt => ..., p_service_static_id => 'COFFEE_VERTEX_AI')`.
2. **Method 2 (Secondary / Managed Workstation Fallback — Litestar OpenAI-Compatible Vertex Gateway)**:
   - Exposes `POST /api/apex/ai/v1/chat/completions` and `GET /api/apex/ai/v1/models` on Litestar backed by `GeminiModelClient` (with optional Bearer key verification).
   - Allows `cymbal-adb-free` to point `COFFEE_VERTEX_AI` at `http://host.docker.internal:8000/api/apex/ai/v1` whenever automatic ADC token refresh or workstation mTLS (`aiplatform.mtls.googleapis.com`) is required without 60-minute OAuth token rotation.

### Cohesive Cymbal Coffee APEX 26.1 Application (`src/apex/cymbal-coffee-ops/`)

- Upgrade `src/apex/cymbal-coffee-ops/application.apx` from `compatibilityMode: 24.2` to `26.1` and replace empty `staticContent` placeholder regions with working SQL-backed KPI/report regions, `APEX_AI.GENERATE` coffee concierge prompts (`COFFEE_VERTEX_AI`), and `APEX_WEB_SERVICE` `/api/apex/*` health/recommendation views (avoiding app-level `restDataSourceServer` FK import rollbacks in SQLcl 26.1.2 `apex import`).

---

## 4. Automated Shell & Browser Video Recording Pipeline

### Verified Toolchain Capabilities

- **Terminal / SQLcl Workflows (`vhs` + `ffmpeg` + `ttyd`)**:
  - Declarative `docs/_tapes/*.tape` files executed with `VHS_NO_SANDBOX=true` and automatic `ROD_BROWSER_BIN` discovery (resolving system `google-chrome`/`chromium` or Playwright's cached Chromium binary when Chrome is not on `$PATH`), `Hide`...`Show` setup blocks, `Wait+Screen` assertions, and dual `.mp4` + `.gif` outputs in `docs/_static/demos/`.
- **Web Browser Workflows (Headless Python `playwright` + `ffmpeg`)**:
  - Python `playwright` (`[dependency-groups].demos = ["playwright>=1.50"]`) launches headless Chromium (`ignore_https_errors=True` for `https://localhost:8443/ords/`, matched `1280x720` `viewport` and `record_video_size`) with an injected `add_init_script` cursor, click-ripple, and step-caption HUD.
  - Raw `.webm` captures transcode via `ffmpeg` into crisp H.264 `.mp4` (`-c:v libx264 -crf 18 -preset slow -tune stillimage -pix_fmt yuv420p -movflags +faststart`) for Sphinx/HTML5 `<video autoplay loop muted playsinline>` embeds and two-pass palette-optimized `.gif` (`palettegen=stats_mode=diff` + `paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle`) for `README.md`.
