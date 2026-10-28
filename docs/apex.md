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

:::{grid-item-card} {octicon}`code;1.2em` Native SQLcl APEXlang
:class-card: hero-pill

Native `apex validate`, `apex import`, and `apex export` commands managing `.apx` plain text in Git.
:::

:::{grid-item-card} {octicon}`video;1.2em` Native SQLcl Demos
:class-card: hero-pill

Deterministic VHS recordings for native SQLcl and PL/SQL workflows alongside Playwright browser walkthroughs.
:::

::::

## Dual-Mode Vertex AI Connectivity

Oracle APEX 26.1 connects to Vertex AI through the `COFFEE_VERTEX_AI`
Generative AI Service (configured in workspace `COFFEE` with `Used by App Builder = Yes`). The repository provides two configuration modes:

### Method 1 (Primary): Direct Vertex AI Endpoint

In direct mode, Oracle Database makes outbound HTTPS calls directly to Google
Cloud Vertex AI's OpenAI-compatible endpoint:

```text
https://aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/endpoints/openapi
```

DBAs and APEX developers configure network ACLs, workspace credentials, and the
Generative AI Service directly in Oracle SQLcl or SQL*Plus using standard PL/SQL
APIs (`DBMS_NETWORK_ACL_ADMIN`, `APEX_CREDENTIAL`, and `APEX_AI`):

```bash
# Execute the standalone deployment PL/SQL script in SQLcl as ADMIN
sql admin/"$ADMIN_PASSWORD"@myatp_low @src/app/db/sql/deploy/configure-vertex-ai.sql "$OAUTH_TOKEN" "$VERTEX_AI_PROJECT_ID" "global"
```

The script executes the following native Oracle PL/SQL blocks:

```sql
-- 1. Grant outbound network ACLs for Vertex AI
BEGIN
    DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(
        host       => 'aiplatform.googleapis.com',
        lower_port => 443,
        upper_port => 443,
        ace        => xs$ace_type(
            privilege_list => xs$name_list('http', 'connect'),
            principal_name => 'APP',
            principal_type => xs_acl.ptype_db
        )
    );
END;
/

-- 2. Store OAuth2 Bearer token in workspace credential
BEGIN
    APEX_UTIL.SET_WORKSPACE('COFFEE');
    APEX_CREDENTIAL.SET_PERSISTENT_CREDENTIALS(
        p_credential_static_id => 'VERTEX_AI_CRED',
        p_key                  => 'Authorization',
        p_value                => 'Bearer ' || '&OAUTH_TOKEN'
    );
END;
/

-- 3. Live verification call via APEX_AI.GENERATE
SET SERVEROUTPUT ON;
DECLARE
    v_output CLOB;
BEGIN
    APEX_UTIL.SET_WORKSPACE('COFFEE');
    v_output := APEX_AI.GENERATE(
        p_prompt            => 'Recommend a specialty dark roast coffee.',
        p_service_static_id => 'COFFEE_VERTEX_AI'
    );
    DBMS_OUTPUT.PUT_LINE(v_output);
END;
/
```

<div class="soft-backdrop-wrapper">

```{image} _static/demos/sqlcl-vertex-ai.gif
:alt: Native SQLcl PL/SQL Vertex AI Direct Provisioning Demo
:align: center
:width: 100%
```

</div>

*Native SQLcl session executing `configure-vertex-ai.sql` and testing `APEX_AI.GENERATE` directly in the database.*

<div class="soft-backdrop-wrapper">

```{image} screenshots/apex_workspace_utilities.png
:alt: Oracle APEX 26.1 Generative AI Services Configuration
:align: center
:width: 100%
```

</div>

*Oracle APEX 26.1 Workspace Utilities showing `COFFEE_VERTEX_AI` configured with `google/gemini-3.8-flash` and `VERTEX_AI_CRED`.*

### Method 2: Litestar OpenAI-Compatible Gateway

For developer workstations with Context-Aware Access, PKCS#11 hardware keys, or
strict corporate proxies where direct outbound HTTPS from the database
container is restricted, Cymbal Coffee provides an internal gateway:

```text
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

Developers run APEXlang commands directly inside Oracle SQLcl without any Python
wrapper:

```sql
-- Connect to Autonomous Database in SQLcl
sql app/"$DATABASE_PASSWORD"@myatp_low

-- 1. Validate APEXlang source (runs offline without database connection)
apex validate -input src/apex/cymbal-coffee-ops

-- 2. Import APEXlang application into workspace COFFEE
apex import -input src/apex/cymbal-coffee-ops -workspace COFFEE -schema APP -id 100

-- 3. Export round-trip changes back to plain-text APEXlang
apex export -applicationid 100 -exptype APEXLANG -dir src/apex -force

exit
```

<div class="soft-backdrop-wrapper">

```{image} _static/demos/sqlcl-apexlang.gif
:alt: Native SQLcl APEXlang Lifecycle Demo
:align: center
:width: 100%
```

</div>

*Pure SQLcl session demonstrating native `apex validate`, `apex import`, and `apex export` commands.*

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

```{image} screenshots/apex_barista_concierge.png
:alt: Oracle APEX 26.1 Page 6 Vertex AI Coffee Concierge Screenshot
:align: center
:width: 100%
```

</div>

*Page 6 Vertex AI Coffee Concierge prompt and grounded recommendation in Oracle APEX 26.1.*

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

# Record native SQLcl terminal VHS tapes (docs/_tapes/*.tape -> docs/_static/demos/)
# - docs/_tapes/sqlcl-apexlang.tape   -> docs/_static/demos/sqlcl-apexlang.{mp4,gif}
# - docs/_tapes/sqlcl-vertex-ai.tape -> docs/_static/demos/sqlcl-vertex-ai.{mp4,gif}
make docs-demos-shell

# Record Playwright browser walkthroughs (APEX Builder & Page 6 Barista Concierge)
make docs-demos-web

# Run interactive live recording runner
make docs-demos-live

# Clean generated demo media
make docs-demos-clean
```

Generated media files are saved to `docs/_static/demos/` (`*.mp4`, `*.webm`,
`*.gif`) and rendered directly throughout this documentation portal.
