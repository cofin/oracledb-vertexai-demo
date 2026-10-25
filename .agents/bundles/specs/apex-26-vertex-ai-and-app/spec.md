---
type: Spec
flow_id: apex-26-vertex-ai-and-app
title: Direct Vertex AI APEX 26.1 Integration, Litestar OpenAI-Compatible Gateway, and Cohesive Cymbal Coffee APEX 26.1 Application
state: completed
plan_revision: 1
plan_commit: "7ff2771"
state_revision: 3
current_task: null
last_operation: complete
operation_targets:
  - "4.1"
  - "4.2"
  - "4.3"
last_verified_checkpoint: "15348ea"
created_at: 2026-10-24T19:39:00Z
updated_at: 2026-10-25T18:21:00Z
description: Fourth stacked PR provisioning Direct Vertex AI /endpoints/openapi connectivity in Oracle APEX 26.1 (DBMS_NETWORK_ACL_ADMIN, APEX_CREDENTIAL VERTEX_AI_CRED, COFFEE_VERTEX_AI Generative AI Service targeting google/gemini-3.8-flash), adding the Litestar OpenAI-compatible Vertex AI gateway (ApexAIController) for managed/mTLS environments, and upgrading src/apex/cymbal-coffee-ops/ into a single cohesive APEX 26.1 application with SQL reports and APEX_AI.GENERATE concierge features.
tags:
  - apex
  - vertex-ai
  - oracle-26ai
  - apexlang
  - litestar
parent_prd: platform-alignment-apex-vertex-prd
research: []
---

# Flow: Direct Vertex AI APEX 26.1 Integration, Litestar OpenAI-Compatible Gateway, and Cohesive Cymbal Coffee APEX 26.1 Application

**Flow ID:** `apex-26-vertex-ai-and-app`
**Parent PRD:** [`platform-alignment-apex-vertex-prd`](../platform-alignment-apex-vertex-prd/spec.md)
**Depends On:** [`adb-free-26ai-and-tools-hygiene`](../adb-free-26ai-and-tools-hygiene/spec.md) (PR 4 of 5 in stack)
**Proposed Branch & PR Title:** `feat/apex-26-vertex-ai` — `feat(apex): wire direct vertex ai endpoint, openai-compatible gateway, and apex 26.1 app`

---

## Specification

### Code Analysis Summary

Files examined:

- `tools/oracle/cli/apex.py` & `tools/oracle/adb.py` (from PR 3) — Bootstraps `adb-free:latest-26ai` with APEX 26.1.5, ORDS 26.3, schema `APP`, and workspace `COFFEE`, but does not yet provision Oracle network ACLs (`aiplatform.googleapis.com` / `host.docker.internal`), APEX Web Credentials (`VERTEX_AI_CRED`), or the APEX 26.1 Generative AI Service (`COFFEE_VERTEX_AI`).
- `src/app/domain/products/controllers/{__init__,_apex}.py` & `src/app/domain/products/schemas/__init__.py` — Exposes `/api/apex/{products,stores,inventory/summary,stores/{store_id}/inventory,products/{product_id}/availability,recommendations,vector/status,openapi/status}`, without an OpenAI-compatible `/api/apex/ai/v1/{chat/completions,models}` endpoint for APEX 26.1 Generative AI Services running in managed or Context-Aware Access mTLS workstations.
- `src/app/domain/ai/runtime/{_model,_types}.py` — `GeminiModelClient` (`ModelClientProtocol`) streams `AgentEvent` chunks from `gemini-3.8-flash` via Google GenAI SDK (`Client(vertexai=True, ...)`), ready to back an OpenAI Chat Completions adapter without duplicating Vertex client setup.
- `src/apex/README.md:1-25`, `src/apex/cymbal-coffee-ops/application.apx:1-85`, `src/apex/cymbal-coffee-ops/pages/p00001-home.apx`..`p00007-integration-health.apx` — `application.apx:48` still declares `compatibilityMode: 24.2`, Page 1 (`p00001-home.apx`) and Page 6 (`p00006-vector-recommendations.apx`) contain empty `staticContent` stub regions, and no page exercises `APEX_AI.GENERATE` against `COFFEE_VERTEX_AI` or `USER_ANNOTATIONS_USAGE` schema metadata.

### Relevant Patterns

- [AI Runtime & Protocols (`domain/ai/`)](../../knowledge/domains/ai-and-protocols.md) — `ModelClientProtocol`, `GeminiModelClient`, coordinate non-persistence.
- [Litestar Security & Vertex AI Gotchas](../../knowledge/gotchas/litestar-security-and-vertex.md) — Inherit `PublicController`, exclude server-to-server JSON endpoints from browser CSRF cookies when invoked by `APEX_AI` / `APEX_WEB_SERVICE`, and obtain ADC access tokens cleanly without logging credentials.
- [Testing Rulebook](../../../../src/tests/AGENTS.md) — Keep unit tests isolated from live Vertex/Oracle calls under `src/tests/unit/tools/` and `src/tests/unit/domain/products/controllers/`.

### Requirements

- **PLAT-REQ-13 (Direct Vertex AI `/endpoints/openapi` Provisioner — Primary Method)**:
  - Create `tools/oracle/apex_vertex.py` (`ApexVertexMode`, `ApexVertexConfig`, `ApexVertexResult`, `ApexVertexConfigurator`) and register `manage.py infra apex configure-vertex` (`--mode direct|gateway` defaulting to `direct`, `--project`, `--location`, `--model` defaulting to `google/gemini-3.8-flash`, `--refresh-token`, `--verify`).
  - In `direct` mode (documented and wired first), idempotently:
    1. Grant `DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE` for `aiplatform.googleapis.com` (`lower_port => 443, upper_port => 443`, `http`) to `APP` and the active APEX engine schema (`APEX_260100`, resolved dynamically from `DBA_REGISTRY` / `ALL_USERS`).
    2. Mint or refresh a Google Cloud OAuth2 access token (`gcloud auth print-access-token` / `google.auth.default`, never echoed or logged) and upsert `APEX_CREDENTIAL` (`p_credential_static_id => 'VERTEX_AI_CRED'`, HTTP Header `Authorization: Bearer <token>`).
    3. Upsert the APEX 26.1 Generative AI Service `COFFEE_VERTEX_AI` (`provider = OPENAI`, `base_url = https://aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/endpoints/openapi`, `model = google/gemini-3.8-flash`, `credential = VERTEX_AI_CRED`, `used_by_app_builder = Y`) in workspace `COFFEE`.
  - In `gateway` mode, configure `APPEND_HOST_ACE` for `host.docker.internal` (`http`), optional `APEX_GATEWAY_API_KEY` credential, and `COFFEE_VERTEX_AI` pointing at `http://host.docker.internal:8000/api/apex/ai/v1` (`model = gemini-3.8-flash`).
  - When `--verify` is passed, execute a live `APEX_AI.GENERATE(p_prompt => ..., p_service_static_id => 'COFFEE_VERTEX_AI')` smoke prompt inside workspace `COFFEE` and report latency and model metadata.
- **PLAT-REQ-14 (Litestar OpenAI-Compatible Vertex AI Gateway — Managed / mTLS Method)**:
  - Add `src/app/domain/products/schemas/_apex_ai.py` defining `FrozenBaseStruct` OpenAI Chat Completions wire types (`OpenAIChatMessage`, `OpenAIChatCompletionRequest`, `OpenAIChatChoice`, `OpenAIChatStreamDelta`, `OpenAIChatStreamChoice`, `OpenAIChatCompletionChunk`, `OpenAIUsage`, `OpenAIChatCompletionResponse`, `OpenAIModelCard`, `OpenAIModelList`) and export them in `src/app/domain/products/schemas/__init__.py`.
  - Add `ApexAIController(PublicController)` in `src/app/domain/products/controllers/_apex_ai.py` (registered in `src/app/domain/products/controllers/__init__.py`) serving `GET /api/apex/ai/v1/models` and `POST /api/apex/ai/v1/chat/completions` (`opt={"exclude_from_csrf": True}`), enforcing constant-time `secrets.compare_digest` Bearer check when `APEX_GATEWAY_API_KEY` is set, translating OpenAI messages (`system`, `developer`, `user`, `assistant`) into `Content` turns for injected `ModelClientProtocol`, and supporting both non-streaming JSON responses and `stream=True` SSE (`text/event-stream` with `data: [DONE]`).
- **PLAT-REQ-15 (Single Cohesive Vertex-AI-Powered Cymbal Coffee APEX 26.1 Application)**:
  - Upgrade `src/apex/cymbal-coffee-ops/application.apx` (`compatibilityMode: 26.1`, clear application title `Cymbal Coffee — Vertex AI & Operations`) and refine Pages 1–7 and `shared-components/lists.apx` into one approachable, SQLcl-validatable APEXlang application:
    - **Page 1 (`p00001-home.apx`)**: Operations & AI Overview KPIs (`PRODUCT` catalog/embedding coverage, `STORE` count, `STORE_PRODUCT_INVENTORY` low-stock/pickup alerts, `USER_ANNOTATIONS_USAGE` AI metadata count).
    - **Page 2 (`p00002-products.apx`)**: Coffee & Bakery Catalog Interactive Report (`PRODUCT` with roast, tasting notes, price in dollars, in-stock status, and `EMBEDDING IS NOT NULL` vector readiness badge).
    - **Page 3 (`p00003-stores.apx`)**: DFW Store Directory Interactive Report (`STORE` with hours and keyless `https://www.google.com/maps/search/?api=1&query=...` link; zero user browser coordinates stored or accepted).
    - **Page 4 (`p00004-store-inventory.apx`)** & **Page 5 (`p00005-availability.apx`)**: Store Inventory & Pickup Availability reports reflecting store-level inventory precedence over global `PRODUCT.IN_STOCK`.
    - **Page 6 (`p00006-vector-recommendations.apx`)**: **Vertex AI Coffee Concierge & Recommendations** — interactive prompt region (`P6_PROMPT`, `P6_CATEGORY`) calling `APEX_AI.GENERATE(p_prompt => ..., p_system_prompt => ..., p_service_static_id => 'COFFEE_VERTEX_AI')` grounded on Cymbal Coffee catalog context alongside `/api/apex/recommendations` JSON-table / SQL hybrid results.
    - **Page 7 (`p00007-integration-health.apx`)**: **Oracle 26ai, APEX 26.1 & Vertex AI Health** — live `USER_ANNOTATIONS_USAGE` catalog inspection, `APEX_RELEASE` / `APEX_WORKSPACE_CREDENTIALS` readiness summary, and vector embedding coverage.
  - Update `src/apex/README.md` with the exact Direct Vertex AI + Gateway + SQLcl 26.1.2 `validate` / `import` / `export` workflow.

### Requirement-to-Task Traceability

| Requirement | Task | Verification Strategy | Primary Files | Primary Tests |
| --- | --- | --- | --- | --- |
| `PLAT-REQ-13` | `4.1` | `behavior_tdd` | `tools/oracle/apex_vertex.py`, `tools/oracle/cli/apex.py`, `tools/oracle/__init__.py` | `src/tests/unit/tools/test_apex_vertex.py` |
| `PLAT-REQ-14` | `4.2` | `behavior_tdd` | `src/app/domain/products/schemas/{_apex_ai,__init__}.py`, `src/app/domain/products/controllers/{_apex_ai,__init__}.py` | `src/tests/unit/domain/products/controllers/test_apex_ai_gateway.py` |
| `PLAT-REQ-15` | `4.3` | `behavior_tdd` | `src/apex/README.md`, `src/apex/cymbal-coffee-ops/application.apx`, `src/apex/cymbal-coffee-ops/pages/p0000{1..7}-*.apx`, `src/apex/cymbal-coffee-ops/shared-components/lists.apx` | `src/tests/unit/tools/test_apexlang_app_source.py` |

---

## Implementation Plan

### Phase 1: Direct Vertex AI Provisioner, OpenAI-Compatible Gateway & Cohesive APEX 26.1 App

- [x] 4.1 Implement `tools/oracle/apex_vertex.py` and `manage.py infra apex configure-vertex` (`--mode direct|gateway`, network ACLs, `VERTEX_AI_CRED`, `COFFEE_VERTEX_AI`, `APEX_AI.GENERATE` verification)
- [x] 4.2 Implement `ApexAIController` (`/api/apex/ai/v1/chat/completions` & `/api/apex/ai/v1/models`) backed by `GeminiModelClient` and `FrozenBaseStruct` OpenAI schemas
- [x] 4.3 Upgrade `src/apex/cymbal-coffee-ops/` (`compatibilityMode: 26.1`) with live Oracle 26ai reports, `APEX_AI.GENERATE` coffee concierge, and `USER_ANNOTATIONS_USAGE` health views

---

## Continuity Snapshot

- **Active Flow / Lifecycle**: `apex-26-vertex-ai-and-app` (`completed`)
- **Current Task & Claimant**: `null`
- **Last Verified Checkpoint**: `15348ea`
- **Key Decisions**:
  - Wire and document Direct Vertex AI (`/endpoints/openapi`, `model="google/gemini-3.8-flash"`) as `--mode direct` (default) first, with `--refresh-token` for fast OAuth2 Bearer rotation and `--mode gateway` targeting `ApexAIController` (`/api/apex/ai/v1`) for zero-expiry local dev and mTLS workstations.
  - Keep all APEX 26.1 application regions in `src/apex/cymbal-coffee-ops/` free of app-level `restDataSourceServer` FK dependencies so SQLcl 26.1.2 `apex validate`, `apex import`, and `apex export` round-trip cleanly without `WWV_WEBSRC_MODULE_RSERVER_FK`.
- **Newest Discoveries**:
  1. Tasks `4.1` (`e425c95`) and `4.2` (`b42e69e`) completed cleanly across disjoint directories (`tools/oracle/*` vs `src/app/domain/products/*`) with `APEX_GATEWAY_API_KEY` exposed on `AppSettings`.
  2. Excluding `POST /api/apex/ai/v1/chat/completions` from browser cookie CSRF (`opt={"exclude_from_csrf": True}`) enables Oracle `APEX_AI` / `UTL_HTTP` server-to-server requests without browser CSRF cookies while enforcing optional `secrets.compare_digest` Bearer authentication.
  3. APEXlang `26.1.0+3102` compiles `src/apex/cymbal-coffee-ops/` offline (`manage.py infra apex validate --alias cymbal-coffee-ops`) using `action: submitPage` for the Page 6 `ask-concierge` button (`15348ea`).
- **Blockers & Unblock Conditions**: None.
- **Next Exact Step**: Branch `docs/apex-vertex-demo-recordings` from `feat/apex-26-vertex-ai` and execute `web-and-shell-demo-recordings-and-docs` Tasks `5.1`–`5.4`.
- **Plan Identity**: `plan_revision: 1`, `plan_commit: "7ff2771"`
- **State Identity**: `state_revision: 3`, `last_operation: complete`, `operation_targets: ["4.1", "4.2", "4.3"]`
- **Relevant Knowledge Paths**:
  - `.agents/bundles/specs/platform-alignment-apex-vertex-prd/research/codebase-alignment-and-apex/research.md`
  - `.agents/bundles/knowledge/domains/ai-and-protocols.md`
  - `.agents/bundles/knowledge/gotchas/litestar-security-and-vertex.md`
