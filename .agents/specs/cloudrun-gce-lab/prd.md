# Master PRD: Cloud Run + GCE Oracle DB + Cloud Build private-VPC lab

*PRD ID: `cloudrun-gce-lab`*
*Created: 2026-06-23*
*Status: Planned*
*Beads: `oracledb-vertexai-jw0`*
*Research: [`../../research/research_cloudrun_gce_lab_overhaul/`](../../research/research_cloudrun_gce_lab_overhaul/research.md)*

---

## North Star

Ship a **new, separate hands-on lab** that deploys Cymbal Coffee as a *real* GCP
architecture, so a learner can see how the demo runs "for real" in the cloud:

- The **Litestar webapp runs on Cloud Run** (scales to zero, public HTTPS).
- The **Oracle 26ai database runs on a Container-Optimized OS GCE VM**, as a
  container launched by **cloud-init**, with a **persistent disk** for durable
  data and **no external IP**.
- A **Cloud Build pipeline** (`build → push → coffee upgrade → gcloud run deploy`)
  is the deploy story; the learner triggers it with **`gcloud builds submit`**.
- A **private VPC with Direct VPC egress** lets Cloud Run reach the DB on its
  internal IP; **the database is never reachable from the public internet.**
- All cloud infrastructure is **Terraform** under `tools/deploy/terraform/`; the
  lab teaches `terraform apply` so learners stand the stack up fast and then
  read how each resource is wired.

This is **additive**. The current single-VM lab is preserved (renamed to the
"GCE-only" path) and the new lab "follows" it.

---

## Scope

### In scope
- One backward-compatible app/image change: the container honors Cloud Run `$PORT`.
- Terraform stack: VPC + DB VM (COS) + Artifact Registry + Cloud Build private
  pool + Cloud Run service + IAM + Secret Manager.
- `cloudbuild.yaml` build→migrate→deploy pipeline (manual `gcloud builds submit`).
- Docs: rename current lab to GCE-only; author the new Cloud Run lab; verification + teardown.

### Out of scope / explicitly unchanged
- **Local developer loop is UNCHANGED**: `make start-infra` (local `gvenzl/oracle-free`
  container) + `uv run coffee run` against `localhost:1521`. Nothing here changes
  how the maintainer builds or runs locally. `gcloud builds submit` is the **lab
  deploy story only**, not the local workflow.
- No CI auto-trigger (GitHub push → build) in the core lab — offered only as an
  optional challenge.
- No production HA, no managed Oracle (ADB) path, no Terraform remote state
  backend hardening beyond a documented local/default state for the lab.
- No re-embedding at deploy time: committed fixtures already carry vectors.

---

## Key Research Findings (condensed — see research doc)

1. **GCE can run a container directly, but `gcloud compute instances create-with-container`
   is deprecated.** Use **cloud-init / startup-script `docker run`** on COS. COS 69+
   can mount a persistent disk into the container.
2. **The app is already remote-DB-ready** via `DATABASE_HOST/PORT/SERVICE_NAME/USER/PASSWORD`
   (`src/app/lib/settings.py:79-162`). Pointing Cloud Run at a remote Oracle is config, not code.
3. **`spanner-mc` (`deploy/gcp/cloudbuild.deploy.yml`) is a near-verbatim template**:
   build → tag → push → migrate → `gcloud run deploy ... --vpc-connector`. We swap the
   connector for **Direct VPC egress** and `spannermc database upgrade` for `coffee upgrade`.
4. **Migrating a *private-IP* DB from Cloud Build needs VPC reach.** Default Cloud Build
   workers can't reach private IPs (spanner-mc's migrate step worked only because Spanner is a
   public Google API). Decision: **Cloud Build private pool** peered to the VPC.
5. **`coffee upgrade` does migrate + load committed-embedding fixtures — no Vertex calls.**
   (`product.json.gz` ships `"embedding":[...]`; `bulk-embed` is the separate Vertex command.)
   So the **build pool needs DB reach + Secret Manager but NOT Vertex**; only the Cloud Run
   service needs `roles/aiplatform.user`.

---

## Locked Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **Two separate labs** — rename current `docs/lab.md` → `docs/lab-gce.md`; `docs/lab.md` becomes a "choose your path" index; new `docs/lab-cloud-run.md` | User wants the old lab preserved and a new module to "follow" it; index keeps Sphinx nav stable |
| D2 | **Cloud Build private pool** peered to VPC for the migration step (fallback: Cloud Run Job w/ Direct VPC egress) | Scopes DB-reaching/VPC privileges to the build config, not the deployed service |
| D3 | **Direct VPC egress** for Cloud Run → VPC | Newer Google default: no connector VMs, lower latency, egress-only cost |
| D4 | **Container-Optimized OS** DB VM; Oracle container via cloud-init; **persistent disk** → `/opt/oracle/oradata` | Production-shaped, durable, minimal |
| D5 | **Terraform** under `tools/deploy/terraform/` as the IaC of record; lab teaches `terraform apply` | Learners stand up fast and learn real IaC |
| D6 | **Full `coffee upgrade` every deploy** (migrate + committed-embedding fixtures) | Cheap + idempotent because fixtures carry vectors; no Vertex at build time |
| D7 | **Manual `gcloud builds submit`** is the lab deploy trigger | Clearest "watch it deploy" story; no GitHub OAuth; auto-trigger is a challenge |

---

## Architecture Contract (shared source of truth for all chapters)

All chapter specs MUST use these names, paths, and values. Names are Terraform
locals/variables with these defaults; region/zone/project are variables.

### Identifiers & regions
- `project_id` = var (learner's project) · `region` = `us-central1` · `zone` = `us-central1-c`
- Terraform root: `tools/deploy/terraform/` · cloudbuild: `tools/deploy/gcp/cloudbuild.yaml`
  · cloud-init template: `tools/deploy/gcp/cloud-init-oracle.yaml.tftpl`

### Networking
- VPC: `coffee-vpc` (custom subnet mode)
- Subnet `coffee-subnet` `10.10.0.0/24` (region) — DB VM lives here
- Subnet `coffee-run-subnet` `10.10.1.0/24` (region) — **Cloud Run Direct VPC egress** range
- Reserved range `coffee-buildpool-range` `10.30.0.0/24` (`--purpose=VPC_PEERING`) — Cloud Build private pool peering
- Static internal IP `coffee-db-ip` = `10.10.0.10` (in `coffee-subnet`) → DB VM
- Cloud Router `coffee-router` + Cloud NAT `coffee-nat` (egress for VM image pulls + build pool)
- Firewall:
  - `coffee-allow-iap-ssh`: ingress tcp:22 from `35.235.240.0/20` → tag `coffee-db`
  - `coffee-allow-run-to-db`: ingress tcp:1521 from `10.10.1.0/24` (run egress) **and** `10.30.0.0/24` (build pool) → tag `coffee-db`
  - (no public ingress to the DB; VM has `--no-address`)

### DB VM (Chapter 2)
- Instance `coffee-db` · COS image family `cos-stable` · `e2-standard-4` · **standard (NOT Spot)** · `--no-address` · tag `coffee-db` · static internal IP `coffee-db-ip`
- Data disk `coffee-db-data` (pd-ssd, 50GB) attached; host mount `/mnt/disks/oradata` (ext4, formatted-if-empty, idempotent); container mount `/opt/oracle/oradata`
- Container: `gvenzl/oracle-free:latest`, host-internal `1521:1521`, `--restart always`
  - env: `ORACLE_PASSWORD` (system), `APP_USER=app`, `APP_USER_PASSWORD` (from Secret Manager via VM)
  - hook mounts reproduce `tools/oracle/database.py:461-471`:
    `tools/oracle/on_init/*` → `/container-entrypoint-initdb.d`, `tools/oracle/on_startup/*` → `/container-entrypoint-startdb.d`
    (must include `00_configure_vector_memory.sql`, `db_init.sql`, `00_verify_vector_memory.sql`, `01_startup_test.sql`)
- Service name (PDB): `freepdb1` · app user/password match local defaults (`app` / from secret)
- COS gotcha: cloud-init `write_files`/`runcmd` run **every boot** → all logic idempotent

### Deploy pipeline (Chapter 3)
- Artifact Registry (docker) `coffee-artifacts` (region) → image `us-central1-docker.pkg.dev/$PROJECT/coffee-artifacts/coffee-app`
- Cloud Build **private pool** `coffee-build-pool` peered to `coffee-vpc` via `coffee-buildpool-range`
- `cloudbuild.yaml` steps (run on the private pool):
  1. `docker build -f tools/deploy/docker/Dockerfile -t .../coffee-app:$SHORT_SHA .` (+ `:latest`)
  2. push both tags
  3. **migrate**: run the image entrypoint `coffee upgrade` with env `DATABASE_HOST=10.10.0.10`, `DATABASE_PORT=1521`, `DATABASE_SERVICE_NAME=freepdb1`, `DATABASE_USER=app`, `DATABASE_PASSWORD=$$(secret)` — reaches the private DB because the pool is peered to the VPC. **No Vertex.**
  4. `gcloud run deploy coffee-app --image .../coffee-app:$SHORT_SHA` with the Cloud Run config below
- Trigger: `gcloud builds submit --config tools/deploy/gcp/cloudbuild.yaml --worker-pool=coffee-build-pool` (lab only)

### Cloud Run service (Chapter 3)
- Service `coffee-app` · region `us-central1` · port `8080` · `--execution-environment gen2`
- **Direct VPC egress**: `--network=coffee-vpc --subnet=coffee-run-subnet --vpc-egress=private-ranges-only` (so Google APIs/Vertex still reach the internet path)
- SA `coffee-run-sa@$PROJECT.iam.gserviceaccount.com`
- env: `DATABASE_HOST=10.10.0.10`, `DATABASE_PORT=1521`, `DATABASE_SERVICE_NAME=freepdb1`, `DATABASE_USER=app`,
  `VERTEX_AI_PROJECT_ID=$PROJECT`, `VERTEX_AI_LOCATION=us-central1`, `GOOGLE_GENAI_USE_VERTEXAI=true`,
  `ORACLE_ADK_IN_MEMORY=true`, `ORACLE_LITESTAR_SESSION_IN_MEMORY=true`
- secrets: `--set-secrets=DATABASE_PASSWORD=coffee-db-password:latest`

### IAM (Chapter 3)
- `coffee-run-sa`: `roles/aiplatform.user`, `roles/secretmanager.secretAccessor`
- `coffee-build-sa` (or default CB SA): `roles/run.admin`, `roles/iam.serviceAccountUser` (act as run SA), `roles/artifactregistry.writer`, `roles/secretmanager.secretAccessor` — **NO Vertex**
- `coffee-db` VM SA (`coffee-db-sa`): `roles/secretmanager.secretAccessor` on **both** `coffee-db-password` **and** `coffee-db-system-password` (to read them at boot)

### Secret Manager (Chapter 3) — amended 2026-06-23 (Ch2 finding)
Two secrets (neither password is ever templated into VM metadata or Terraform state):
- `coffee-db-password` — Oracle **APP** user password (`DATABASE_PASSWORD`); consumed by Cloud Run, the build migrate step, **and** the DB VM cloud-init (app user). The ONLY secret Cloud Run / the build see.
- `coffee-db-system-password` — Oracle **SYS/system** password; consumed **only** by the DB VM cloud-init at boot (fetched via metadata-token + Secret Manager REST). Never reaches Cloud Run or the build pool.

---

## Roadmap (6 chapters)

| # | Chapter (`flow_id`) | Beads | Depends on | Deliverable |
|---|---------------------|-------|------------|-------------|
| 1 | `cloudrun-app-readiness` | `oracledb-vertexai-jw0.1` | — | Container honors `$PORT`; documented Cloud Run env/secrets; local loop unaffected |
| 2 | `gce-oracle-appliance` | `oracledb-vertexai-jw0.2` | — | Terraform network + COS DB VM + cloud-init Oracle + persistent disk + firewall; private DB reachable on `10.10.0.10:1521`, durable |
| 3 | `cloudbuild-cloudrun-pipeline` | `oracledb-vertexai-jw0.3` | 1, 2 | Terraform registry/pool/Cloud Run/IAM/secrets + `cloudbuild.yaml`; `gcloud builds submit` builds→migrates→deploys |
| 4 | `lab-gce-rename` | `oracledb-vertexai-jw0.4` | — | `docs/lab.md`→`docs/lab-gce.md`; `lab.md` index; Sphinx nav fixed |
| 5 | `cloudrun-lab-authoring` | `oracledb-vertexai-jw0.5` | 2, 3, 4 | `docs/lab-cloud-run.md` end-to-end walkthrough + challenges |
| 6 | `cloudrun-lab-verification-teardown` | `oracledb-vertexai-jw0.6` | 3, 5 | Verification checklist + troubleshooting + cost + `terraform destroy` teardown |

**Suggested execution order:** 1 → 2 → 3 → 4 → 5 → 6 (1, 2, and 4 can run in parallel).

---

## Global Constraints

1. **No local-loop regression.** Every change must keep `make start-infra` + `uv run coffee run`
   working unchanged against local `gvenzl/oracle-free`. Ch1's `$PORT` change defaults to `8080`.
2. **DB never public.** The DB VM has no external IP; `tcp:1521` ingress is allowed only from the
   Cloud Run egress and build-pool ranges. Verification (Ch6) must prove the DB is unreachable publicly.
3. **No re-embedding at deploy.** `coffee upgrade` loads committed-embedding fixtures; the build
   pipeline must not require Vertex credentials.
4. **House style.** Terraform + cloudbuild artifacts live under `tools/deploy/` (mirrors existing
   `tools/deploy/docker/`). Docs are Sphinx/MyST under `docs/`. No backwards-compat shims
   (per repo conventions). Floor-only dependency pins.
5. **Privacy.** Browser geolocation rules and no-key Maps behavior are untouched; nothing in this
   PRD persists coordinates.
6. **Planning-only until `flow-implement`.** No source code is modified during planning.

---

## Risks (see research risk table for the full matrix)

- **Private-DB migration** — mitigated by D2 (private pool peered to VPC).
- **DB data loss on Spot** — mitigated by standard VM + persistent disk (contract pins non-Spot).
- **Lab complexity for beginners** — mitigated by Terraform one-shot apply + D1 separate module.
- **Always-on DB VM cost** — documented in Ch6; `terraform destroy` for teardown.
- **Internal IP drift** — mitigated by the reserved static internal IP `10.10.0.10`.
- **COS every-boot cloud-init** — mitigated by idempotent disk format/mount + `docker run` guard.

---

## Open Items (non-blocking, resolved during chapter implementation)
- Exact COS persistent-disk mount approach (cloud-init `runcmd` mkfs/mount vs `gce-containers` metadata) — Ch2 picks the idempotent path.
- Whether to expose a private DNS name in addition to the static IP (cosmetic) — Ch2 may add `coffee-db.internal`.
- Terraform state backend for the lab (local default vs GCS) — Ch5 documents local default; GCS as a challenge.
