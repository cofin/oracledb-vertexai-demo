# Oracle APEX 26.1 APEXlang Source (`src/apex/`)

Source-controlled Oracle APEX 26.1 APEXlang application directory targeting the bundled Autonomous AI Database Free 26ai runtime (`container-registry.oracle.com/database/adb-free:latest-26ai`, APEX 26.1.5 + ORDS 26.3 on `https://localhost:8443/ords/apex`, workspace `COFFEE`, parsing schema `APP`).

## Vertex AI Connectivity (`COFFEE_VERTEX_AI`)

Provision the `COFFEE_VERTEX_AI` Generative AI Service in workspace `COFFEE` before exercising Page 6 (**Vertex AI Coffee Concierge**) or APEX Assistant in App Builder:

### Method 1 (Primary): Direct Vertex AI OpenAI-Compatible Endpoint

Connects Oracle APEX 26.1 directly to Google Cloud Vertex AI (`/endpoints/openapi`) with `google/gemini-3.8-flash`, provisioning `DBMS_NETWORK_ACL_ADMIN` host ACEs for `aiplatform.googleapis.com:443` and an OAuth2 Bearer `APEX_CREDENTIAL` (`VERTEX_AI_CRED`):

```bash
uv run python manage.py infra apex configure-vertex --mode direct --project "$VERTEX_AI_PROJECT_ID" --verify
# Rotate the short-lived OAuth2 Bearer token (~60 minutes) without recreating ACLs:
uv run python manage.py infra apex configure-vertex --mode direct --refresh-token --verify
```

### Method 2 (Managed / mTLS Workstations): Litestar OpenAI-Compatible Gateway

Routes `COFFEE_VERTEX_AI` through Cymbal Coffee's local Litestar gateway (`http://host.docker.internal:8000/api/apex/ai/v1`, served by `ApexAIController` at `GET /api/apex/ai/v1/models` and `POST /api/apex/ai/v1/chat/completions` and backed by `GeminiModelClient` with optional `APEX_GATEWAY_API_KEY` Bearer authentication) so ADC refresh and Context-Aware Access mTLS certificates are handled automatically by the Python host without token rotation:

```bash
uv run python manage.py infra apex configure-vertex --mode gateway --verify
```

## SQLcl 26.1.2+ APEXlang Lifecycle

Inspect runtime status and validate, import, export, or scaffold `src/apex/cymbal-coffee-ops/` (`mmdVersion: 26.1.0+3102`, Application ID `100`) with SQLcl `26.1.2` or newer (`make install-sqlcl`):

```bash
# Report live APEX_RELEASE version and ORDS HTTPS readiness
uv run python manage.py infra apex status

# Offline compiler validation (no running database required)
uv run python manage.py infra apex validate --alias cymbal-coffee-ops

# Import into workspace COFFEE (schema APP) on adb-free:latest-26ai
uv run python manage.py infra apex import --alias cymbal-coffee-ops --workspace COFFEE --schema APP --app-id 100

# Round-trip export from workspace COFFEE back to APEXlang source
uv run python manage.py infra apex export --app-id 100 --alias cymbal-coffee-ops

# Generate starter APEXlang source files for a new application alias
uv run python manage.py infra apex generate --alias my-coffee-app

# Export the /api/apex/* OpenAPI 3.1 subset (ApexController) for APEX REST Source Catalog inspection
uv run python manage.py infra apex export-openapi
```

## Production CDN Static Assets (`coffee configure-apex-cdn`)

For stateless cloud ORDS deployments where APEX static assets are served from Oracle's public CDN rather than local `/i/` mounts, run the packaged `coffee` command (executes `src/app/db/sql/deploy/configure-apex-cdn.sql` as `ADMIN` with wallet or `SYSDBA`; `src/app/db/sql/deploy/revert-apex-cdn.sql` is packaged alongside it to restore `/i/`):

```bash
uv run coffee configure-apex-cdn
```

## Application Pages (`cymbal-coffee-ops`)

- **Page 0 (`p00000-global-page.apx`)**: Global Page — application-wide `globalPage: 0` container reserved for shared regions.
- **Page 1 (`p00001-home.apx`)**: Operations & AI Overview — live `PRODUCT`, `VECTOR(3072, FLOAT32)`, `STORE`, `STORE_PRODUCT_INVENTORY`, and `USER_ANNOTATIONS_USAGE` KPI metrics.
- **Page 2 (`p00002-products.apx`)**: Coffee & Bakery Catalog — catalog pricing, roast metadata, stock flags, and 3072-dimensional `gemini-embedding-2` readiness.
- **Page 3 (`p00003-stores.apx`)**: DFW Store Directory — seeded store hours and keyless Google Maps search links (zero user browser coordinates stored).
- **Page 4 (`p00004-store-inventory.apx`)**: Store Inventory — aggregated `IN_STOCK`, `LOW_STOCK`, `OUT_OF_STOCK`, and pickup unit totals per store.
- **Page 5 (`p00005-availability.apx`)**: Pickup Availability — store-level `STORE_PRODUCT_INVENTORY` precedence over global `PRODUCT.IN_STOCK`.
- **Page 6 (`p00006-vector-recommendations.apx`)**: Vertex AI Coffee Concierge — interactive `P6_PROMPT` / `P6_CATEGORY` prompt invoking `APEX_AI.GENERATE` (`p_service_static_id => 'COFFEE_VERTEX_AI'`) grounded on live `PRODUCT` rows.
- **Page 7 (`p00007-integration-health.apx`)**: 26ai & Vertex AI Health — `APEX_RELEASE`, `VERTEX_AI_CRED` readiness, vector coverage, and `USER_ANNOTATIONS_USAGE` catalog inspection.
- **Page 9999 (`p09999-login.apx`)**: Login Page — APEX workspace authentication entry point (`/ords/r/coffee/cymbal-coffee-ops/login`).

> **Import Round-Trip Note**: Pages query local schema `APP` tables and `APEX_AI.GENERATE` directly without app-level `restDataSourceServer` references, avoiding the `WWV_WEBSRC_MODULE_RSERVER_FK` import rollback when moving between workspaces.

## Deterministic Demo Recordings (`manage.py demos`)

Terminal VHS tapes (`docs/_tapes/{sqlcl-apexlang,sqlcl-vertex-ai}.tape`) and headless Playwright + FFmpeg browser walkthroughs (`apex-configure-vertex-ai` and `apex-create-vertex-app` in `tools/demos/web.py`) record `.mp4` and `.gif` artifacts under `docs/_static/demos/`:

```bash
uv run --group demos python manage.py demos check
make docs-demos-shell
make docs-demos-web
make docs-demos-live
```
