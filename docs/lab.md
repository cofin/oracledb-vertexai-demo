# Hands-on Lab: Cymbal Coffee — Oracle 26ai + Vertex AI

Cymbal Coffee ships two hands-on labs covering **Oracle AI Database 26ai** Hybrid Reciprocal Rank Fusion (`CTXSYS.CONTEXT` + HNSW `VECTOR(3072, FLOAT32)` `FETCH APPROX`), **Google Cloud Vertex AI** (`gemini-embedding-2` + `gemini-3.8-flash`), **Oracle APEX 26.1** (`APEX_AI.GENERATE` + **ORDS 26.3**), **SQLSpec `0.69.0`**, and **Litestar 2** (`http://localhost:8000`). Pick the topology that matches how you want to run the demo. Both paths assume a Google Cloud account with billing or workshop credits enabled.

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} {octicon}`server;1.1em` Single-VM GCE (+ APEX 26.1 & Vertex AI)
:link: lab-gce
:link-type: doc

Everything on one Compute Engine VM — **Autonomous AI Database Free 26ai** (`adb-free:latest-26ai`, pre-bundling **Oracle APEX 26.1.5 + ORDS 26.3** on `https://localhost:8443/ords/apex` with mTLS wallet service `myatp_low` on TLS port `1522`) and the **Litestar 2** app (`http://localhost:8000`) side by side, including the full **APEX 26.1 -> Vertex AI** and **Cymbal Coffee — Vertex AI & Operations** (`App ID 100`) walkthrough.
:::

:::{grid-item-card} {octicon}`cloud;1.1em` Cloud Run + Private VPC
:link: lab-cloud-run
:link-type: doc

Production-shaped split architecture — the PyApp distroless `coffee-app` container and stateless `coffee-ords` (`ords:26.3`, configured via packaged `src/app/db/sql/deploy/configure-apex-cdn.sql`) on Cloud Run, reaching a private GCE Oracle 26ai database (`10.10.0.10:1521/freepdb1`) over Direct VPC egress via a peered Cloud Build worker pool.
:::

::::

## Topology Comparison

| Capability | Single-VM GCE / Local Workstation ([`lab-gce`](lab-gce.md)) | Cloud Run + Private VPC ([`lab-cloud-run`](lab-cloud-run.md)) |
|---|---|---|
| **Litestar App Runtime** | `uv run coffee run` on Granian (`http://localhost:8000`) | Distroless PyApp onefile container (`coffee-app`) on Cloud Run (`PORT=8080`) |
| **Oracle 26ai Database** | `container-registry.oracle.com/database/adb-free:latest-26ai` (`cymbal-adb-free`, volume `cymbal-adb-data`, `.envs/tns` mTLS wallet, service `myatp_low` on TLS port `1522`) | Private Container-Optimized OS GCE VM (`coffee-db`, `10.10.0.10:1521/freepdb1`, no external IP) |
| **Oracle APEX & ORDS** | Pre-bundled **Oracle APEX 26.1.5 + ORDS 26.3** at `https://localhost:8443/ords/apex` (workspace `COFFEE`, schema `APP`, Database Actions at `https://localhost:8443/ords/sql-developer`) | Stateless Cloud Run service `coffee-ords` (`ords:26.3`) loading static assets from Oracle CDN via `coffee configure-apex-cdn` |
| **APEX 26.1 -> Vertex AI** | Direct Vertex AI `/endpoints/openapi` (`google/gemini-3.8-flash`, `VERTEX_AI_CRED`, `COFFEE_VERTEX_AI`) or Litestar OpenAI-compatible gateway (`http://host.docker.internal:8000/api/apex/ai/v1`) | Direct Vertex AI `/endpoints/openapi` (`COFFEE_VERTEX_AI`) or Cloud Run Litestar gateway (`$RUN_URL/api/apex/ai/v1`) |
| **SQLSpec `0.69.0` Layer** | `OracleLoaderService`, `enable_session_tracing`, wire-level `sqlcommenter`, `wallet_zip` extraction, `FrozenBaseStruct`, isolated `queue_db` | Identical `SQLSpec 0.69.0` async driver and isolated `queue_db` pool over Direct VPC egress |

> **Local Container Note:** `make start-infra` (`uv run python manage.py infra start`) defaults to `adb-free:latest-26ai` so local development and the Single-VM GCE lab include mTLS wallet connectivity, **Oracle APEX 26.1.5**, and **ORDS 26.3** out of the box. Setting `ORACLE_CONTAINER_FLAVOR=free` (`gvenzl/oracle-free:latest`) is reserved for lightweight non-APEX runs and `make test-integration`.
