---
type: Guide
title: Litestar Security, Dishka, APEX 26.1 & Vertex AI Gotchas
description: Dishka runtime annotations, VERTEX_AI_LOCATION=global, coordinate privacy, ADB-Free 26ai, APEX 26.1 Vertex AI modes, SQLcl ORA-02291, and demo recording traps
tags:
  - gotchas
  - dishka
  - litestar-security
  - apex-26ai
  - vertex-ai
---

# Litestar Security, Dishka, APEX 26.1 & Vertex AI Gotchas

## 1. Dishka Provider Modules Must Omit `from __future__ import annotations`

- **Trap**: Dishka inspects `@provide` parameter and return annotations at runtime when `create_container()` and `get_providers()` in `src/app/ioc/__init__.py` assemble `ConfigProvider`, `DBProvider`, `AIProvider`, and `DomainServiceProvider`. Adding `from __future__ import annotations` to `src/app/ioc/_config.py`, `src/app/ioc/_database.py`, `src/app/ioc/_ai.py`, or `src/app/ioc/_domain.py` turns annotations into strings and breaks container construction.
- **Rule**: Never add `from __future__ import annotations` in `src/app/ioc/*.py` (enforced by `tools/ci/check_code_hygiene.py`).

## 2. Vertex AI Preview Gemini Models Require `VERTEX_AI_LOCATION=global`

- **Trap**: Calling `gemini-3.8-flash` against a regional Vertex AI endpoint (such as `us-central1`) fails with `404 NOT_FOUND`.
- **Rule**: `AISettings` (`src/app/lib/settings/_ai.py`) defaults `location` (`VERTEX_AI_LOCATION` or `GOOGLE_CLOUD_LOCATION`) to `"global"` via `AISettings.resolve_location()`, while keeping `gcp_region` (`GCP_REGION`, default `"us-central1"`) separate for GCP deployment infrastructure.

## 3. Placeholder `GOOGLE_CLOUD_PROJECT` Must Raise Typed 503 (`AIServiceUnconfigured`)

- **Trap**: Unconfigured `.env` files with placeholder project IDs (`your-project-id`, `your-gcp-project-id`, `demo-project`) cause unhandled 500 tracebacks during Vertex AI calls if not caught early, or cause `Settings.configure_genai_env()` (`src/app/lib/settings/__init__.py`) to pop a valid `GOOGLE_API_KEY` if checked with a plain truthy string check.
- **Rule**: Validate against `PLACEHOLDER_VALUES` via `settings.ai.has_valid_project_id()` and `settings.ai.has_valid_api_key()` in `Settings.configure_genai_env()` and `AIProvider.provide_genai_client()` (`src/app/ioc/_ai.py`), raising `AIServiceUnconfigured` (mapped to HTTP 503 with setup guidance) when neither is configured.

## 4. `PublicController` / `SecureController` Inheritance and Machine CSRF Exemptions

- **Trap**: Inheriting from bare `litestar.Controller` bypasses `litestar-security` policy enforcement, while leaving CSRF enabled on machine-to-machine JSON/SSE POST endpoints breaks external MCP, A2A, and Oracle APEX callers that do not carry browser `XSRF-TOKEN` cookies.
- **Rule**: Every HTTP controller must inherit from `PublicController` or `SecureController` (enforced by `tools/ci/check_litestar_security.py` and Ruff `TID251`). Machine POST endpoints (`POST /mcp`, `POST /a2a`, and `POST /api/apex/ai/v1/chat/completions` in `src/app/domain/products/controllers/_apex_ai.py`) declare `opt={"exclude_from_csrf": True}` and enforce constant-time API key or Bearer token checks (`MCP_API_KEY` in `src/app/lib/security.py`, `APEX_GATEWAY_API_KEY` in `ApexAIController`).

## 5. Browser Coordinates and Multi-Turn Session Context Must Bypass Global Response Cache

- **Trap**: Caching or logging `LocationContext` (`latitude`, `longitude`) leaks user geolocation across sessions or into database tables, and caching multi-turn follow-up responses (where `history` or `session.state["last_products"]` is active, such as *"Is it available near me?"* or *"Which of those is lowest acid?"*) contaminates global `response_cache` across sessions.
- **Rule**: Use `safe_location_context()` and `request_coordinates()` in `src/app/domain/chat/services/_telemetry.py`, bypass `CacheService` reads and writes whenever browser coordinates or prior session context (`has_session_context=has_session_context(history, session_state)`) are present, and never store coordinates in `agent_session`, `agent_event`, `response_cache`, or `search_metric`.

## 6. ADB-Free 26ai Default Container vs `ORACLE_CONTAINER_FLAVOR=free`

- **Trap**: Assuming `make start-infra` boots plain `gvenzl/oracle-free:latest` on `:1521/freepdb1` misses mTLS wallet requirements and port collisions, while running `cymbal-adb-free` alongside a leftover `oracle-free-db` container collides on host port `1521`.
- **Rule**: Default development (`make start-infra` via `tools/oracle/database.py` and `tools/oracle/adb.py`) runs `container-registry.oracle.com/database/adb-free:latest-26ai` (`cymbal-adb-free`) with automatic vector memory management, built-in APEX `26.1` and ORDS `26.3` on `https://localhost:8443/ords/apex`, and an exported `.envs/tns` mTLS wallet connecting to `myatp_low` on `:1522`. Use `ORACLE_CONTAINER_FLAVOR=free` (`gvenzl/oracle-free:latest` on `:1521/freepdb1`) for lightweight `make test-integration` runs without APEX/ORDS.

## 7. APEX 26.1 Direct Vertex AI Token Expiry vs Litestar OpenAI-Compatible Gateway

- **Trap**: Direct Vertex AI connections from inside Oracle APEX `26.1` fail with `ORA-24247` if `DBMS_NETWORK_ACL_ADMIN` host ACEs are not granted to both `APP` and the `APEX_NNNNNN` engine schema, fail with `404` if `location` is regional instead of `global` or `model` omits the `google/` prefix, and expire after ~60 minutes because `VERTEX_AI_CRED` holds a static OAuth2 Bearer access token.
- **Rule**: In Direct mode (`tools/oracle/apex_vertex.py`), configure `https://aiplatform.googleapis.com/v1/projects/<project>/locations/global/endpoints/openapi` with `model="google/gemini-3.8-flash"`, `VERTEX_AI_LOCATION=global`, and host ACEs on `aiplatform.googleapis.com:443`, and refresh expired OAuth2 tokens via `uv run python manage.py infra apex configure-vertex --mode direct --refresh-token --verify`. When running on mTLS workstations or avoiding manual 60-minute token rotation, use Gateway mode (`--mode gateway`), pointing `COFFEE_VERTEX_AI` at `ApexAIController` (`GET /api/apex/ai/v1/models` and `POST /api/apex/ai/v1/chat/completions` at `http://host.docker.internal:8000/api/apex/ai/v1`, optional `APEX_GATEWAY_API_KEY`) to reuse Litestar's auto-refreshing ADC and mTLS credentials.

## 8. SQLcl `26.1.2+` APEXlang Import Constraint (`ORA-02291: WWV_WEBSRC_MODULE_RSERVER_FK`)

- **Trap**: SQLcl `26.1.2+` (`tools/oracle/apex_lang.py`) passes `apex validate` on APEXlang `restDataSource` definitions bound to external Remote Servers, but `apex import` (`project import`) rolls back with `ORA-02291: integrity constraint (APEX_260100.WWV_WEBSRC_MODULE_RSERVER_FK) violated - parent key not found` when workspace-level Remote Server metadata is absent during import.
- **Rule**: Keep `src/apex/cymbal-coffee-ops/` self-contained by querying local `APP` schema tables in SQL and invoking `APEX_AI.GENERATE(p_service_static_id => 'COFFEE_VERTEX_AI')` directly in PL/SQL page processes rather than binding APEXlang pages to external `restDataSourceServer` references.

## 9. VHS and Playwright Demo Recording Traps (`tools/demos/shell.py`, `tools/demos/web.py`)

- **Trap**: VHS terminal recording (`tools/demos/shell.py`) fails on Linux workstations when Go Rod cannot locate Chromium or hits unprivileged user-namespace sandbox restrictions; headless Playwright browser recording (`tools/demos/web.py`) fails TLS verification against `adb-free`'s self-signed `https://localhost:8443` certificate and leaves `.webm` video buffers truncated if `ffmpeg` runs before the browser context closes.
- **Rule**: Always pass `ROD_BROWSER_BIN` (pointing to an executable Chromium binary) and `VHS_NO_SANDBOX=true` when running VHS tapes (`make docs-demos-shell`), and in Playwright (`make docs-demos-web`) pass `ignore_https_errors=True` to `browser.new_context(...)` and call `context.close()` before invoking `ffmpeg` to transcode `.webm` into `.mp4` and `.gif`.
