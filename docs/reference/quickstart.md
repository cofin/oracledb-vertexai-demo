# Quickstart

Five minutes from clone to a running Oracle AI Database 26ai + Vertex AI stack:

```bash
# 1. Install Python deps, frontend deps, and built assets
make install

# 2. Bootstrap (one-time): writes .env with LITESTAR_PORT=8000 and VERTEX_AI_LOCATION=global
uv run python manage.py init

# 3. Start Oracle Autonomous AI Database Free 26ai (APEX 26.1.5 + ORDS 26.3 + mTLS wallet)
make start-infra

# 4. Apply schema migrations, SQLSpec extension tables, and committed 3072-dim fixtures
uv run coffee upgrade

# 5. Run the Litestar application server on http://localhost:8000
uv run coffee run
```

The generated `.env` sets `LITESTAR_PORT=8000`, so the chat UI is at
<http://localhost:8000/> and the vector search, Hybrid RRF, and `EXPLAIN PLAN`
explorer is at <http://localhost:8000/explore>. Override the bind port with
`uv run coffee run --port <port>`, `LITESTAR_PORT` (or `GRANIAN_PORT`), or
`PORT`. `uv run coffee run` starts an embedded ASGI `litestar-queues` worker by
default; to run a standalone worker fleet instead, start the web process with
`uv run coffee run --no-worker` and run `uv run coffee worker run` in a second
terminal (check queue health with `uv run coffee worker status`).

`make start-infra` (`uv run python manage.py infra start`) launches persistent
**Oracle Autonomous AI Database Free 26ai**
(`container-registry.oracle.com/database/adb-free:latest-26ai`, container
`cymbal-adb-free`), exports its mTLS wallet into `.envs/tns` for the
`myatp_low` TNS alias on TLS port `1522`, provisions the `APP` parsing schema
and `COFFEE` APEX workspace, and exposes pre-bundled **Oracle APEX 26.1.5 +
ORDS 26.3** at <https://localhost:8443/ords/apex> (Database Actions at
<https://localhost:8443/ords/sql-developer>). For lightweight non-APEX runs or
`make test-integration`, set `ORACLE_CONTAINER_FLAVOR=free` to boot
`gvenzl/oracle-free:latest` on `:1521/freepdb1`.

## Oracle APEX 26.1 + Vertex AI

Configure APEX 26.1 Generative AI (`COFFEE_VERTEX_AI`) against **Gemini 3.8
Flash** using either connectivity mode, then import the bundled APEXlang
application from `src/apex/cymbal-coffee-ops/` (App ID `100`, Page 6 Vertex AI
Coffee Concierge calling `APEX_AI.GENERATE`):

### Method 1 (Primary): Direct Vertex AI OpenAI-Compatible Endpoint

Oracle Database connects directly over HTTPS to Vertex AI's OpenAI-compatible
`/endpoints/openapi` surface (`DBMS_NETWORK_ACL_ADMIN` host ACEs for
`aiplatform.googleapis.com:443`, `VERTEX_AI_CRED` Bearer credential, and
`COFFEE_VERTEX_AI` configured with `model="google/gemini-3.8-flash"` and
`Used by App Builder = Yes`):

```bash
# Provision ACLs, VERTEX_AI_CRED, and COFFEE_VERTEX_AI, then run a live APEX_AI.GENERATE check
uv run python manage.py infra apex configure-vertex \
  --mode direct \
  --project "$VERTEX_AI_PROJECT_ID" \
  --verify

# Refresh the short-lived gcloud Bearer token on VERTEX_AI_CRED without recreating ACLs
uv run python manage.py infra apex configure-vertex --mode direct --refresh-token --verify
```

To inspect or configure the same objects manually in the APEX UI
(<https://localhost:8443/ords/apex>, workspace `COFFEE`), open **Workspace
Utilities -> Web Credentials** (`VERTEX_AI_CRED`, HTTP Header `Authorization`
set to `Bearer <token>`) and **Workspace Utilities -> Generative AI**
(`COFFEE_VERTEX_AI`, Provider `OpenAI`, Base URL
`https://aiplatform.googleapis.com/v1/projects/<project>/locations/global/endpoints/openapi`,
Model `google/gemini-3.8-flash`, `Used by App Builder = Yes`).

### Method 2 (Secondary): Litestar OpenAI-Compatible Gateway

For zero-expiry local development or mTLS workstations where gcloud access
tokens cannot leave the host directly, point `COFFEE_VERTEX_AI` at Litestar's
OpenAI-compatible proxy (`http://host.docker.internal:8000/api/apex/ai/v1`,
implemented by `ApexAIController` in
`src/app/domain/products/controllers/_apex_ai.py`, with optional Bearer auth via
`APEX_GATEWAY_API_KEY`):

```bash
uv run python manage.py infra apex configure-vertex --mode gateway --verify
```

### Importing the APEXlang App and Recording Walkthroughs

```bash
# Install SQLcl 26.1.2+ to ~/.local/bin/sql (~/.local/sqlcl) and check live APEX/ORDS readiness
make install-sqlcl
make apex

# Validate and import src/apex/cymbal-coffee-ops/ into workspace COFFEE (App ID 100)
uv run python manage.py infra apex validate --alias cymbal-coffee-ops
uv run python manage.py infra apex import --alias cymbal-coffee-ops --workspace COFFEE --schema APP --app-id 100

# Optional: configure static APEX CDN assets on remote/Cloud Run ADB deployments
uv run coffee configure-apex-cdn

# Optional: verify VHS/Playwright prerequisites and re-record shell & browser demo videos
uv run --group demos python manage.py demos check
make docs-demos-shell
make docs-demos-web
```

## Vertex AI credentials

The app requires a Google Cloud project with the Vertex AI API enabled. Set
`VERTEX_AI_PROJECT_ID` (or `GOOGLE_CLOUD_PROJECT` / `GOOGLE_PROJECT_ID`), set
`VERTEX_AI_LOCATION` (or `GOOGLE_CLOUD_LOCATION` / `GOOGLE_LOCATION`, defaulting
to `global`), and authenticate with either
`gcloud auth application-default login` or `GOOGLE_APPLICATION_CREDENTIALS`
(service account key path). For API-key mode, leave the project ID empty and set
`VERTEX_AI_API_KEY` or `GOOGLE_API_KEY`.

If credentials are missing or `VERTEX_AI_PROJECT_ID` is still a placeholder,
REST AI endpoints return HTTP `503 Service Unavailable` (`AIServiceUnconfigured`)
and `POST /api/chat/stream` emits a structured SSE `error` event rather than an
unhandled stack trace.

## Common gotchas

- **`ORA-51962` during migration** — `vector_memory_size` is zero. The default
  `adb-free:latest-26ai` container (`make start-infra`) manages vector memory
  automatically, and `ORACLE_CONTAINER_FLAVOR=free` (`gvenzl/oracle-free:latest`)
  sets `vector_memory_size = 512M` automatically on first creation via
  `tools/oracle/on_init/00_configure_vector_memory.sql` (verified on startup by
  `tools/oracle/on_startup/00_verify_vector_memory.sql`). On a self-managed
  Oracle instance without container hooks, set `vector_memory_size` on the
  SPFILE as `SYSDBA` and restart the instance (`512M` on Free Edition, or up to
  `4G` on Standard and Enterprise Edition).
- **Vertex AI model `404` (`gemini-3.8-flash` or `gemini-embedding-2`)** —
  keep `VERTEX_AI_LOCATION=global` (the default written by
  `uv run python manage.py init`, required for `gemini-3.8-flash`), confirm the
  Vertex AI API (`aiplatform.googleapis.com`) is enabled on the project, and
  verify the caller has `roles/aiplatform.user`.
- **Empty chat replies on first start** — fixtures have not been loaded yet.
  The committed datasets in `src/app/db/fixtures/` include `3072`-dimension
  `gemini-embedding-2` embeddings for all `130` products and `25` route
  exemplars, so re-run `uv run coffee upgrade`.

## Where to go next

- [The walkthrough](../tour.md) — what one chat message actually does.
- [CLI reference](cli.md) — every demo lifecycle command.
- [For the curious](internals.md) — HNSW, single-query Hybrid RRF routing,
  and the live performance dashboard.
- [Developers](developers.md) — raw migration commands, fixture
  regeneration, and verification.
