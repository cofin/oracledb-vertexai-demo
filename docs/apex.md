# Oracle APEX 26.1 & Vertex AI

Cymbal Coffee bundles a complete, source-controlled **Oracle APEX 26.1**
application (`src/apex/cymbal-coffee-ops/`, Application ID `100`,
`compatibilityMode: 26.1`) targeting the **Autonomous AI Database Free 26ai**
runtime (`adb-free:latest-26ai`).

The application pairs Oracle 26ai vector search and catalog tables with
**Google Cloud Vertex AI** (`google/gemini-3.8-flash`) through the native
`APEX_AI` package (`APEX_AI.GENERATE`), giving operations teams live inventory,
store routing, schema-annotation health checks, and a generative coffee
concierge.

::::{grid} 1 1 2 4
:gutter: 2
:class-container: hero-stack

:::{grid-item-card} {octicon}`database;1.2em` ADB-Free 26ai
:class-card: hero-pill

Bundled **APEX 26.1.5 + ORDS 26.3** running in `cymbal-adb-free` with mTLS wallet support on port `1522` (`myatp_low`).
:::

:::{grid-item-card} {octicon}`zap;1.2em` Vertex AI Grounding
:class-card: hero-pill

`COFFEE_VERTEX_AI` Generative AI Service calling `google/gemini-3.8-flash` via `APEX_AI.GENERATE`.
:::

:::{grid-item-card} {octicon}`code;1.2em` APEXlang in Git
:class-card: hero-pill

Deterministic `.apx` source files managed with SQLcl `26.1.2+` without binary exports.
:::

:::{grid-item-card} {octicon}`video;1.2em` Deterministic Demos
:class-card: hero-pill

Automated VHS terminal recordings and Playwright headless browser walkthroughs.
:::

::::

## Dual-Mode Vertex AI Connectivity

Oracle APEX 26.1 connects to Vertex AI through the `COFFEE_VERTEX_AI`
Generative AI Service (configured in workspace `COFFEE` with `Used by App Builder = Yes`). The repository provides two configuration modes:

### Method 1 (Primary): Direct Vertex AI Endpoint

In direct mode, Oracle Database makes outbound HTTPS calls directly to Google
Cloud Vertex AI's OpenAI-compatible endpoint:

```
https://aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/endpoints/openapi
```

The CLI configurator idempotently appends `DBMS_NETWORK_ACL_ADMIN` host ACEs for
`aiplatform.googleapis.com:443` to parsing schema `APP` and the active APEX
engine schema (`APEX_260100`), creates or updates the `APEX_CREDENTIAL`
(`VERTEX_AI_CRED`) with an OAuth2 Bearer token, registers the Generative AI
Service with model `google/gemini-3.8-flash`, and runs a live `APEX_AI.GENERATE`
smoke verification:

```bash
# Initial provisioning with ACLs, credentials, and verification
uv run python manage.py infra apex configure-vertex --mode direct --project "$VERTEX_AI_PROJECT_ID" --verify

# Rotate short-lived OAuth2 Bearer token (~60 min) without altering ACLs
uv run python manage.py infra apex configure-vertex --mode direct --refresh-token --verify
```

<div class="soft-backdrop-wrapper">

```{image} _static/demos/apex-vertex-ai-setup.gif
:alt: APEX 26.1 & Vertex AI Direct Configuration Demo
:align: center
:width: 100%
```

</div>

*Direct Vertex AI provisioning and smoke test verification running via `manage.py infra apex configure-vertex --mode direct --verify`.*

### Method 2: Litestar OpenAI-Compatible Gateway

For developer workstations with Context-Aware Access, PKCS#11 hardware keys, or
strict corporate proxies where direct outbound HTTPS from the database
container is restricted, Cymbal Coffee provides an internal gateway:

```
http://host.docker.internal:8000/api/apex/ai/v1
```

The gateway is served by `ApexAIController` (`src/app/domain/products/controllers/_apex_ai.py`)
and backed by `GeminiModelClient`. Litestar handles Google Cloud authentication
transparently using Application Default Credentials (ADC) with automatic token
refresh, while Oracle APEX connects to the local gateway using a static or
empty credential:

```bash
uv run python manage.py infra apex configure-vertex --mode gateway --verify
```

<div class="soft-backdrop-wrapper">

```{image} _static/demos/apex-configure-vertex-ai.gif
:alt: Oracle APEX 26.1 Generative AI Services Configuration
:align: center
:width: 100%
```

</div>

*Workspace Utilities Generative AI Services configuration (`COFFEE_VERTEX_AI`) connecting Oracle APEX to Vertex AI.*

## SQLcl 26.1.2+ APEXlang Lifecycle

Cymbal Coffee tracks APEX application definitions exclusively as **APEXlang**
plain text (`.apx`) under `src/apex/cymbal-coffee-ops/`. Developers never commit
opaque binary SQL exports.

```bash
# 1. Verify APEX release and ORDS HTTPS readiness
uv run python manage.py infra apex status

# 2. Run offline APEXlang syntax and schema validation (no database required)
uv run python manage.py infra apex validate --alias cymbal-coffee-ops

# 3. Import APEXlang source into workspace COFFEE
uv run python manage.py infra apex import --alias cymbal-coffee-ops --workspace COFFEE --schema APP --app-id 100

# 4. Export round-trip changes made in APEX Builder back to Git
uv run python manage.py infra apex export --app-id 100 --alias cymbal-coffee-ops

# 5. Scaffold a new starter APEXlang application
uv run python manage.py infra apex generate --alias my-coffee-app

# 6. Export OpenAPI 3.1 specification for APEX REST Data Source catalogs
uv run python manage.py infra apex export-openapi
```

<div class="soft-backdrop-wrapper">

```{image} _static/demos/apexlang-workflow.gif
:alt: SQLcl 26.1.2+ APEXlang Lifecycle Demo
:align: center
:width: 100%
```

</div>

*APEXlang offline validation, import into workspace COFFEE, and round-trip export to version control.*

## Application Pages (`cymbal-coffee-ops`)

The bundled application (`App ID 100`) provides 7 purpose-built pages for
coffee retail operations and AI administration:

| Page | File | Purpose | Key Technologies |
| :--- | :--- | :--- | :--- |
| **Page 1** | `p00001-home.apx` | Operations & AI Overview | Live KPIs across `PRODUCT`, `STORE`, `STORE_PRODUCT_INVENTORY`, and `USER_ANNOTATIONS_USAGE`. |
| **Page 2** | `p00002-products.apx` | Coffee & Bakery Catalog | Interactive report showing roast profiles, prices, stock flags, and 3072-dim vector readiness. |
| **Page 3** | `p00003-stores.apx` | DFW Store Directory | Store locations with keyless Google Maps search links (`UTL_URL.ESCAPE`); zero browser coordinates stored. |
| **Page 4** | `p00004-store-inventory.apx` | Store Inventory | Aggregated in-stock, low-stock, and pickup unit totals across store locations. |
| **Page 5** | `p00005-availability.apx` | Pickup Availability | Store-level inventory precedence over global product stock status. |
| **Page 6** | `p00006-vector-recommendations.apx` | Vertex AI Coffee Concierge | Interactive conversational barista invoking `APEX_AI.GENERATE` grounded in live catalog rows. |
| **Page 7** | `p00007-integration-health.apx` | 26ai & Vertex AI Health | Diagnostics for `APEX_RELEASE` (26.1.5), `VERTEX_AI_CRED`, vector coverage, and schema annotations. |

<div class="soft-backdrop-wrapper">

```{image} _static/demos/apex-barista-concierge.gif
:alt: Oracle APEX 26.1 Vertex AI Coffee Concierge Walkthrough
:align: center
:width: 100%
```

</div>

*Page 6 Vertex AI Coffee Concierge running interactive recommendations grounded in Oracle 26ai product vectors.*

## Production CDN Static Assets

In production environments where Oracle REST Data Services (ORDS) runs as a
stateless container (such as Google Cloud Run) without local `/i/` image mounts,
APEX static assets are loaded from Oracle's public CDN:

```bash
# Point APEX image prefix to static.oracle.com CDN
uv run coffee configure-apex-cdn
```

This executes the wheel-packaged PL/SQL script at `src/app/db/sql/deploy/configure-apex-cdn.sql`,
configuring `IMAGE_PREFIX` to `https://static.oracle.com/cdn/apex/26.1.0/`.
The companion script `src/app/db/sql/deploy/revert-apex-cdn.sql` restores the
local `/i/` prefix for offline local development.

## Reproducing Demo Videos & GIFs

All terminal tapes and browser recordings are deterministic and reproducible
using the repository's demo recorder tooling:

```bash
# Verify prerequisites (vhs, ttyd, ffmpeg, chromium, playwright)
uv run python manage.py demos check

# Record terminal VHS tapes (docs/_tapes/*.tape -> docs/_static/demos/)
make docs-demos-shell

# Record Playwright browser walkthroughs
make docs-demos-web

# Run interactive live recording runner
make docs-demos-live

# Clean generated demo media
make docs-demos-clean
```

Generated media files are saved to `docs/_static/demos/` (`*.mp4`, `*.webm`,
`*.gif`) and rendered directly throughout this documentation portal.
