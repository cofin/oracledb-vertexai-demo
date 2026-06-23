# Flow: cloudbuild-cloudrun-pipeline

*Flow ID: `cloudbuild-cloudrun-pipeline`*
*Parent PRD: `cloudrun-gce-lab`*
*Beads epic: `oracledb-vertexai-jw0.3`*
*Type: feature · Status: planned · Created: 2026-06-23*
*Depends on: Ch1 `cloudrun-app-readiness` (`$PORT`-aware image) · Ch2 `gce-oracle-appliance` (private DB at `10.10.0.10:1521`, `coffee-vpc`, `coffee-run-subnet`, `coffee-db-sa`)*

> LAB ONLY. This chapter is the **deploy story** for the new Cloud Run lab. It
> does not change the local developer loop (`make start-infra` +
> `uv run coffee run`). `gcloud builds submit` is the lab deploy trigger, not a
> maintainer workflow.

---

## Specification

### Context

Chapter 3 ships the deploy half of the `cloudrun-gce-lab` PRD: the cloud
resources the app needs (Artifact Registry, Cloud Build private pool, Cloud Run
service, two service accounts + IAM, one Secret Manager secret) plus a
`cloudbuild.yaml` that, on `gcloud builds submit`, does **build → push →
`coffee upgrade` (migrate the PRIVATE DB through the peered pool) → `gcloud run
deploy` (Direct VPC egress)**.

The reference pipeline is `cofin/spanner-mc`'s
`deploy/gcp/cloudbuild.deploy.yml` (build → tag `:latest` → push both →
migrate → `gcloud beta run deploy ... --vpc-connector`). We mirror its shape
and adapt four things:

1. `spannermc database upgrade` → `coffee upgrade`.
2. `--port 8000` → `8080`.
3. `--vpc-connector` → **Direct VPC egress** flags (`--network` / `--subnet` /
   `--vpc-egress`).
4. The migrate step drops `gcr.io/google-appengine/exec-wrapper`: this repo's
   image already has `ENTRYPOINT ["…","coffee"]`, so the build step runs the
   freshly built image as the step `name` with `args: ["upgrade"]`.

### Shared-root Terraform assumption (LOAD-BEARING)

**All `.tf` for Ch2 and Ch3 live in ONE Terraform root: `tools/deploy/terraform/`,
applied as a single `terraform apply`.** Ch3 therefore references Ch2 resources
with **plain HCL resource references** — `google_compute_network.coffee_vpc.id`,
the `coffee-run-subnet` self-link, the `coffee-db-sa` email — **NOT** `data`
sources and **NOT** a separate state. Any reference below to a Ch2 resource
(`google_compute_network.coffee_vpc`, `google_compute_subnetwork.coffee_run_subnet`,
`google_service_account.coffee_db_sa`, `var.project_id`, `var.region`) assumes
that Ch2 has declared it in the same root. If Ch3 is implemented before Ch2,
those references must be stubbed or Ch2 landed first.

### Architecture Contract (verbatim from PRD `.agents/specs/cloudrun-gce-lab/prd.md:122-148`)

| Item | Value |
|------|-------|
| Artifact Registry | `coffee-artifacts` (docker, `us-central1`) |
| Image | `us-central1-docker.pkg.dev/$PROJECT/coffee-artifacts/coffee-app` |
| Private pool | `coffee-build-pool` peered to `coffee-vpc` via range `coffee-buildpool-range` `10.30.0.0/24` |
| Cloud Run | service `coffee-app`, port `8080`, gen2, Direct VPC egress `--network=coffee-vpc --subnet=coffee-run-subnet --vpc-egress=private-ranges-only` |
| Run SA | `coffee-run-sa` → `roles/aiplatform.user`, `roles/secretmanager.secretAccessor` |
| Build SA | `coffee-build-sa` → `roles/run.admin`, `roles/iam.serviceAccountUser`, `roles/artifactregistry.writer`, `roles/secretmanager.secretAccessor` — **NO Vertex** |
| VM SA (Ch2) | `coffee-db-sa` → `roles/secretmanager.secretAccessor` on **both** `coffee-db-password` and `coffee-db-system-password` (bound in Ch3 `iam.tf`) |
| Secrets | `coffee-db-password` (APP user; Cloud Run + build + VM app user) · `coffee-db-system-password` (Oracle SYS; **DB-VM-only**, never Cloud Run/build) — contract amended 2026-06-23 |
| Cloud Run env | `DATABASE_HOST=10.10.0.10`, `DATABASE_PORT=1521`, `DATABASE_SERVICE_NAME=freepdb1`, `DATABASE_USER=app`, `VERTEX_AI_PROJECT_ID=$PROJECT`, `VERTEX_AI_LOCATION=us-central1`, `GOOGLE_GENAI_USE_VERTEXAI=true`, `ORACLE_ADK_IN_MEMORY=true`, `ORACLE_LITESTAR_SESSION_IN_MEMORY=true` |
| Cloud Run secret env | `DATABASE_PASSWORD=coffee-db-password:latest` |

### Code Analysis (file:line evidence)

1. **Image ENTRYPOINT makes the migrate step trivial.**
   `tools/deploy/docker/Dockerfile:85` →
   `ENTRYPOINT ["/usr/local/bin/tini", "--", "coffee"]` and `:86`
   `CMD ["run", "--host", "0.0.0.0", "--port", "8080"]`. A cloudbuild step whose
   `name` is the just-built image and `args: ["upgrade"]` runs exactly
   `coffee upgrade` — no `exec-wrapper`. (spanner-mc needed `exec-wrapper`
   because its app was a venv, not an ENTRYPOINT-bearing distroless image.)

2. **`coffee upgrade` = migrate + load committed fixtures, NO Vertex.**
   `src/app/cli/commands.py:161-172` (`upgrade_cmd`) → `_upgrade_database`
   (`src/app/cli/commands.py:89-110`): `migration_commands.upgrade()` then
   `load_fixtures(None)`. Fixtures already carry embeddings (PRD research
   finding #5, `.agents/research/research_cloudrun_gce_lab_overhaul/research.md:68-71`),
   so the build step needs **DB reach + the DB password but NOT
   `roles/aiplatform.user`**. This is the load-bearing reason `coffee-build-sa`
   has no Vertex role.

3. **DB password flows by plain env var.** `src/app/lib/settings.py:94-97` reads
   `DATABASE_PASSWORD` directly from `os.getenv`. Secret Manager injection via
   cloudbuild `secretEnv` (migrate step) and Cloud Run
   `--set-secrets=DATABASE_PASSWORD=coffee-db-password:latest` works with zero
   code change. Host/port/service/user are likewise plain env
   (`src/app/lib/settings.py:90-108`).

4. **spanner-mc template** (`cofin/spanner-mc:deploy/gcp/cloudbuild.deploy.yml`,
   fetched live 2026-06-23): `gcr.io/cloud-builders/docker build` →
   `docker tag …:latest` → `docker push` (sha) → `docker push` (latest) →
   `gcr.io/google-appengine/exec-wrapper … -- spannermc database upgrade` →
   `gcr.io/cloud-builders/gcloud beta run deploy … --vpc-connector …
   --port 8000 --execution-environment gen2 --no-cpu-throttling`. We mirror
   build/tag/push/deploy and adapt the migrate + connector + port as listed
   above.

5. **Private-DB migration needs VPC reach.**
   `.agents/research/research_cloudrun_gce_lab_overhaul/research.md:37,115-116`:
   default Cloud Build workers are not on the VPC and cannot reach
   `10.10.0.10`. Locked decision **D2** (`prd.md:80`) → Cloud Build **private
   pool** peered to `coffee-vpc`. Ch2's firewall `coffee-allow-run-to-db`
   (`prd.md:108`) already admits `10.30.0.0/24` (build pool) → tag `coffee-db`
   on `tcp:1521`, so no new firewall rule is needed in Ch3.

6. **No Terraform root exists yet.** `tools/deploy/` currently contains only
   `docker/` (verified `ls tools/deploy/`). Ch2 + Ch3 jointly create
   `tools/deploy/terraform/` as the single shared root.

### Resolved design decisions

- **D-Q1 Chicken-and-egg (image only exists after a build).** Terraform manages
  `google_cloud_run_v2_service.coffee_app` with a **bootstrap image**
  `us-docker.pkg.dev/cloudrun/container/hello` and
  `lifecycle { ignore_changes = [template[0].containers[0].image] }`. The
  cloudbuild `gcloud run deploy` step swaps the real `:$SHORT_SHA` image on
  every deploy; Terraform never fights it.
  **Rejected alternative:** cloudbuild creates the service first and Terraform
  does not manage it. Rejected because it splits ownership of the service across
  two tools, makes `terraform destroy` incomplete, and hides the service config
  (env/secret/egress) from the IaC of record (PRD D5, `prd.md:83`).

- **D-Q2 Build-pool peering ownership.** Ch3 owns `build_pool.tf`, which
  declares `google_compute_global_address.coffee_buildpool_range`
  (`purpose = "VPC_PEERING"`), `google_service_networking_connection`, and
  `google_cloudbuild_worker_pool.coffee_build_pool`, all referencing Ch2's
  `google_compute_network.coffee_vpc`.

- **D-Q3 Secret version source (amended 2026-06-23 — TWO secrets).** `secrets.tf`
  defines **two** secrets, each with a version sourced from a sensitive variable
  (both set in the **gitignored** `terraform.tfvars`):
  - `coffee-db-password` ← `var.db_password` — the Oracle APP-user password
    (`DATABASE_PASSWORD`). Consumed by Cloud Run, the build migrate step, AND
    Ch2's VM cloud-init (app user). This is the ONLY secret Cloud Run / the
    build pool ever see.
  - `coffee-db-system-password` ← `var.db_system_password` — the Oracle
    SYS/system password. Consumed ONLY by the Ch2 DB VM cloud-init at boot (so
    SYS is never templated into VM metadata/state). It NEVER feeds Cloud Run or
    the build pool.
  **Lab-only secret-hygiene note:** committing passwords into `terraform.tfvars`
  (even gitignored) is acceptable for a teaching lab but is NOT production
  hygiene; production should source the versions from out-of-band secrets.

- **D-Q4 VM SA secret binding (amended — both secrets).** Ch3 `iam.tf` binds the
  Ch2 VM SA (`google_service_account.coffee_db_sa.email`) to
  `roles/secretmanager.secretAccessor` on **both** Ch3 secrets
  (`coffee-db-password` and `coffee-db-system-password`), since the VM cloud-init
  reads both at boot. The Cloud Run and build SAs are UNCHANGED: they bind only
  `coffee-db-password`, never the SYS secret, and the build SA has no Vertex
  role.

- **D-Q5 Deploy SA + auth.** The cloudbuild deploy step sets
  `--service-account=coffee-run-sa@$PROJECT…` (the running service uses the run
  SA, not the build SA) and `--allow-unauthenticated` so the learner can open
  the public URL. Public-but-lab-only; documented as such.

### Requirements

**Functional**

- F1. `terraform apply` in `tools/deploy/terraform/` creates: Artifact Registry
  `coffee-artifacts`; build pool `coffee-build-pool` peered to `coffee-vpc`;
  Cloud Run `coffee-app` (bootstrap image, Direct VPC egress, full env + secret
  env); SAs `coffee-run-sa` + `coffee-build-sa` with the exact roles; secrets
  `coffee-db-password` + `coffee-db-system-password` (each + version); the
  VM-SA secret-accessor bindings on **both** secrets. Cloud Run + build SAs bind
  only `coffee-db-password`.
- F2. `gcloud builds submit --config tools/deploy/gcp/cloudbuild.yaml
  --substitutions=_PROJECT=…,_REGION=us-central1` runs on the private pool and
  performs build → push (`:$SHORT_SHA` + `:latest`) → `coffee upgrade` against
  `10.10.0.10:1521` → `gcloud run deploy coffee-app` with the real image.
- F3. The migrate step injects the DB password via `secretEnv` from
  `availableSecrets.secretManager` (`coffee-db-password:latest`) — no plaintext
  password in the build config.
- F4. The deploy step swaps `coffee-app`'s image to `:$SHORT_SHA`, sets
  `--service-account=coffee-run-sa@…`, `--region=us-central1`, `--port=8080`,
  `--execution-environment=gen2`, Direct VPC egress flags, and
  `--allow-unauthenticated`.

**Non-functional / constraints**

- N1. `coffee-build-sa` MUST NOT hold any Vertex/`aiplatform.*` role.
- N2. No new firewall rule in Ch3 (Ch2's `coffee-allow-run-to-db` already admits
  the build-pool + run-egress ranges on `tcp:1521`).
- N3. Floor-only dependency-style version pins do not apply (no Python deps);
  Terraform `required_providers` use `>=` floors only, no upper caps
  (mirrors the repo "no upper bounds" convention).
- N4. No source code changes. Only files under `tools/deploy/terraform/` and
  `tools/deploy/gcp/cloudbuild.yaml` are created.
- N5. House style: artifacts live under `tools/deploy/` (mirrors existing
  `tools/deploy/docker/`).

### Acceptance criteria

- A1. `cd tools/deploy/terraform && terraform init && terraform validate`
  succeeds.
- A2. `terraform apply` creates all Ch3 resources; `terraform plan` is clean
  afterward (no perpetual diff — proves the `ignore_changes` on the Cloud Run
  image works after a real deploy).
- A3. `gcloud builds submit --config tools/deploy/gcp/cloudbuild.yaml
  --substitutions=_PROJECT=$PROJECT,_REGION=us-central1` completes green; build
  logs show the migrate step connected to `10.10.0.10` and ran migrations +
  fixture load.
- A4. `gcloud run services describe coffee-app --region=us-central1` shows the
  `:$SHORT_SHA` image, `coffee-run-sa`, Direct VPC egress, the full env, and the
  `DATABASE_PASSWORD` secret env; the public URL serves HTTP 200.
- A5. `gcloud projects get-iam-policy $PROJECT --flatten=bindings
  --filter="bindings.members:coffee-build-sa@*"` shows **no** `aiplatform.*`
  role.
- A6. `gcloud secrets get-iam-policy coffee-db-system-password` lists ONLY
  `coffee-db-sa` as a `secretAccessor` (NOT `coffee-run-sa`, NOT
  `coffee-build-sa`) — proves the SYS secret is DB-VM-only. `coffee-db-password`
  lists `coffee-run-sa`, `coffee-build-sa`, and `coffee-db-sa`.

---

## Implementation Plan

> TDD note: this chapter produces only Terraform + YAML config (no application
> source). Per `.agents/patterns.md` Testing rules, **do not add `src/tests`
> for repo structure / workflow YAML / tool scripts.** Verification is by
> `terraform validate`, `gcloud builds submit`, and `gcloud run/describe`
> assertions, captured as explicit verification tasks below instead of pytest.
> Every file below is **paste-ready**; replace nothing except where a `var.` or
> `${…}` substitution is intended.

### Phase 1 — Terraform root scaffolding + Artifact Registry

- [ ] 1.1 Create `tools/deploy/terraform/versions.tf` (shared root provider
  pin; floors only, no upper caps). If Ch2 already created this file in the
  shared root, MERGE rather than overwrite — keep one `terraform` block.

  ```hcl
  # SPDX-FileCopyrightText: 2026 Google LLC
  # SPDX-License-Identifier: Apache-2.0

  terraform {
    required_version = ">= 1.9"
    required_providers {
      google = {
        source  = "hashicorp/google"
        version = ">= 6.0"
      }
    }
  }

  provider "google" {
    project = var.project_id
    region  = var.region
  }
  ```

  > All Ch3 resources (including `google_cloudbuild_worker_pool`) are GA in
  > `hashicorp/google`; no `google-beta` provider is needed. If Ch2 requires
  > `google-beta`, it adds that block in the shared root.

- [ ] 1.2 Ensure `tools/deploy/terraform/variables.tf` declares the variables
  Ch3 consumes. If Ch2 already declares `project_id`/`region`, do NOT redeclare
  them — only ADD `db_password`. (Terraform errors on duplicate variable
  blocks.)

  ```hcl
  # SPDX-FileCopyrightText: 2026 Google LLC
  # SPDX-License-Identifier: Apache-2.0

  # NOTE: project_id and region are declared by Ch2 in the shared root.
  # Only add them here if Ch2 has not. Do not duplicate.
  variable "project_id" {
    type        = string
    description = "Learner's GCP project ID."
  }

  variable "region" {
    type        = string
    description = "Deployment region."
    default     = "us-central1"
  }

  variable "db_password" {
    type        = string
    description = "Oracle APP-user password (DATABASE_PASSWORD). Consumed by Cloud Run, the build migrate step, and the DB VM app user. LAB ONLY: set in gitignored terraform.tfvars."
    sensitive   = true
  }

  variable "db_system_password" {
    type        = string
    description = "Oracle SYS/system password. Consumed ONLY by the Ch2 DB VM cloud-init at boot; never reaches Cloud Run or the build pool. LAB ONLY: set in gitignored terraform.tfvars."
    sensitive   = true
  }
  ```

- [ ] 1.3 Create `tools/deploy/terraform/.gitignore` (protect lab secrets +
  local state). If one exists in the shared root, merge these lines.

  ```gitignore
  terraform.tfvars
  *.tfstate
  *.tfstate.*
  .terraform/
  .terraform.lock.hcl
  ```

- [ ] 1.4 Create `tools/deploy/terraform/terraform.tfvars.example` (committed
  template; the real `terraform.tfvars` is gitignored).

  ```hcl
  project_id         = "your-project-id"
  region             = "us-central1"
  db_password        = "ChangeMe-LabOnly1"
  db_system_password = "ChangeMe-SysLabOnly1"
  ```

- [ ] 1.5 Create `tools/deploy/terraform/artifact_registry.tf`.

  ```hcl
  # SPDX-FileCopyrightText: 2026 Google LLC
  # SPDX-License-Identifier: Apache-2.0

  # Docker registry that holds the coffee-app image built by Cloud Build.
  # Image path: ${var.region}-docker.pkg.dev/${var.project_id}/coffee-artifacts/coffee-app
  resource "google_artifact_registry_repository" "coffee_artifacts" {
    location      = var.region
    repository_id = "coffee-artifacts"
    description   = "Cymbal Coffee app images (lab)."
    format        = "DOCKER"
  }
  ```

- [ ] 1.6 VERIFY phase 1: from repo root run
  `cd tools/deploy/terraform && terraform init && terraform validate`. Expect
  `Success! The configuration is valid.` (Resolve any duplicate-variable or
  duplicate-`terraform`-block errors caused by Ch2 overlap before proceeding.)

### Phase 2 — Cloud Build private pool + VPC peering

- [ ] 2.1 Create `tools/deploy/terraform/build_pool.tf`. References Ch2's
  `google_compute_network.coffee_vpc` directly (shared root). The reserved
  range `coffee-buildpool-range` is `10.30.0.0/24` with `purpose=VPC_PEERING`,
  exactly matching the firewall Ch2 already opened.

  ```hcl
  # SPDX-FileCopyrightText: 2026 Google LLC
  # SPDX-License-Identifier: Apache-2.0

  # Reserved /24 used to peer the Cloud Build private pool into coffee-vpc.
  # Matches the 10.30.0.0/24 source already allowed by Ch2's
  # coffee-allow-run-to-db firewall rule on tcp:1521 -> tag coffee-db.
  resource "google_compute_global_address" "coffee_buildpool_range" {
    name          = "coffee-buildpool-range"
    purpose       = "VPC_PEERING"
    address_type  = "INTERNAL"
    address       = "10.30.0.0"
    prefix_length = 24
    network       = google_compute_network.coffee_vpc.id
  }

  # Establish the servicenetworking peering that the worker pool rides on.
  resource "google_service_networking_connection" "coffee_buildpool_peering" {
    network                 = google_compute_network.coffee_vpc.id
    service                 = "servicenetworking.googleapis.com"
    reserved_peering_ranges = [google_compute_global_address.coffee_buildpool_range.name]
  }

  # Private Cloud Build worker pool peered to coffee-vpc so the migrate step
  # can reach the private Oracle VM at 10.10.0.10:1521. No public egress.
  resource "google_cloudbuild_worker_pool" "coffee_build_pool" {
    name     = "coffee-build-pool"
    location = var.region

    worker_config {
      disk_size_gb   = 100
      machine_type   = "e2-standard-4"
      no_external_ip = false
    }

    network_config {
      peered_network = google_compute_network.coffee_vpc.id
    }

    depends_on = [google_service_networking_connection.coffee_buildpool_peering]
  }
  ```

  > Note on `no_external_ip`: kept `false` so the pool can pull public builder
  > images (`gcr.io/cloud-builders/docker`, `gcloud`) and push to Artifact
  > Registry over Google's public path while STILL reaching `10.10.0.10` via the
  > peering. Ch2's Cloud NAT is not on the pool's path; the pool uses its own
  > egress. If the lab later wants `NO_PUBLIC_EGRESS`, that requires Private
  > Google Access / a NAT on the peered network and is out of scope here.

- [ ] 2.2 VERIFY phase 2: `terraform validate` still succeeds. (Apply is
  deferred to the full-stack verification in Phase 6 because the pool depends on
  Ch2's `coffee_vpc`.)

### Phase 3 — Service accounts + IAM

- [ ] 3.1 Create `tools/deploy/terraform/iam.tf`. Declares both Ch3 SAs, their
  role bindings, and the VM-SA secret-accessor binding (D-Q4). The build SA gets
  `run.admin` + `iam.serviceAccountUser` (act-as the run SA) +
  `artifactregistry.writer` + `secretmanager.secretAccessor` and **NO Vertex**.

  ```hcl
  # SPDX-FileCopyrightText: 2026 Google LLC
  # SPDX-License-Identifier: Apache-2.0

  # --- Cloud Run runtime service account -------------------------------------
  resource "google_service_account" "coffee_run_sa" {
    account_id   = "coffee-run-sa"
    display_name = "Cymbal Coffee Cloud Run runtime SA"
  }

  resource "google_project_iam_member" "run_sa_aiplatform" {
    project = var.project_id
    role    = "roles/aiplatform.user"
    member  = "serviceAccount:${google_service_account.coffee_run_sa.email}"
  }

  resource "google_project_iam_member" "run_sa_secret_accessor" {
    project = var.project_id
    role    = "roles/secretmanager.secretAccessor"
    member  = "serviceAccount:${google_service_account.coffee_run_sa.email}"
  }

  # --- Cloud Build deploy service account (NO Vertex) ------------------------
  resource "google_service_account" "coffee_build_sa" {
    account_id   = "coffee-build-sa"
    display_name = "Cymbal Coffee Cloud Build deploy SA"
  }

  resource "google_project_iam_member" "build_sa_run_admin" {
    project = var.project_id
    role    = "roles/run.admin"
    member  = "serviceAccount:${google_service_account.coffee_build_sa.email}"
  }

  # Lets the build SA deploy a service that RUNS AS coffee-run-sa.
  resource "google_project_iam_member" "build_sa_act_as" {
    project = var.project_id
    role    = "roles/iam.serviceAccountUser"
    member  = "serviceAccount:${google_service_account.coffee_build_sa.email}"
  }

  resource "google_project_iam_member" "build_sa_ar_writer" {
    project = var.project_id
    role    = "roles/artifactregistry.writer"
    member  = "serviceAccount:${google_service_account.coffee_build_sa.email}"
  }

  resource "google_project_iam_member" "build_sa_secret_accessor" {
    project = var.project_id
    role    = "roles/secretmanager.secretAccessor"
    member  = "serviceAccount:${google_service_account.coffee_build_sa.email}"
  }

  # --- Ch2 VM SA -> read BOTH DB secrets at boot (D-Q4, amended) -------------
  # coffee_db_sa is declared by Ch2 in the shared root. The DB VM cloud-init
  # reads the APP password AND the SYS/system password from Secret Manager at
  # boot (so neither is templated into VM metadata/state), so the VM SA needs
  # secretAccessor on BOTH secrets. Cloud Run + build SAs are UNCHANGED: they
  # bind only coffee-db-password (no system secret), and the build SA has NO
  # Vertex role.
  resource "google_secret_manager_secret_iam_member" "db_sa_app_secret_accessor" {
    secret_id = google_secret_manager_secret.coffee_db_password.secret_id
    role      = "roles/secretmanager.secretAccessor"
    member    = "serviceAccount:${google_service_account.coffee_db_sa.email}"
  }

  resource "google_secret_manager_secret_iam_member" "db_sa_system_secret_accessor" {
    secret_id = google_secret_manager_secret.coffee_db_system_password.secret_id
    role      = "roles/secretmanager.secretAccessor"
    member    = "serviceAccount:${google_service_account.coffee_db_sa.email}"
  }
  ```

  > The deploy step also needs the build SA to act as the run SA at the
  > service-resource level. `roles/iam.serviceAccountUser` granted project-wide
  > above covers it; if the lab tightens scope later, replace with a
  > `google_service_account_iam_member` on `coffee_run_sa` granting the build SA
  > `roles/iam.serviceAccountUser`. Project-wide is fine for the lab.

- [ ] 3.2 VERIFY phase 3: `iam.tf` references
  `google_secret_manager_secret.coffee_db_password` (Phase 4). `terraform
  validate` is only truthful once Phase 4 lands — **land 3.1 + 4.1 together**
  (or do Phase 4 first), then run `terraform validate` once and expect success.
  Do NOT treat 3.2 as an independently-passing gate before 4.1 exists.

### Phase 4 — Secret Manager

- [ ] 4.1 Create `tools/deploy/terraform/secrets.tf` (D-Q3).

  ```hcl
  # SPDX-FileCopyrightText: 2026 Google LLC
  # SPDX-License-Identifier: Apache-2.0

  # TWO secrets (PRD contract amended 2026-06-23):
  #   coffee-db-password        -> APP user (DATABASE_PASSWORD). Consumed by
  #                                Cloud Run, the build migrate step, AND the
  #                                DB VM app user. ONLY secret Cloud Run/build see.
  #   coffee-db-system-password -> Oracle SYS/system password. Consumed ONLY by
  #                                the Ch2 DB VM cloud-init at boot. NEVER feeds
  #                                Cloud Run or the build pool (keeps SYS out of
  #                                VM metadata/state).
  # LAB ONLY: values come from gitignored terraform.tfvars. This is NOT
  # production secret hygiene; production should source versions out-of-band,
  # not from committed tfvars.

  # --- APP user password -----------------------------------------------------
  resource "google_secret_manager_secret" "coffee_db_password" {
    secret_id = "coffee-db-password"

    replication {
      auto {}
    }
  }

  resource "google_secret_manager_secret_version" "coffee_db_password_v1" {
    secret      = google_secret_manager_secret.coffee_db_password.id
    secret_data = var.db_password
  }

  # --- Oracle SYS/system password (DB-VM-only; not seen by Cloud Run/build) ---
  resource "google_secret_manager_secret" "coffee_db_system_password" {
    secret_id = "coffee-db-system-password"

    replication {
      auto {}
    }
  }

  resource "google_secret_manager_secret_version" "coffee_db_system_password_v1" {
    secret      = google_secret_manager_secret.coffee_db_system_password.id
    secret_data = var.db_system_password
  }
  ```

- [ ] 4.2 VERIFY phase 4: `terraform validate` succeeds; the Phase 3 secret
  bindings (APP secret for run/build SAs; BOTH secrets for the VM SA) now
  resolve. Confirm only `coffee-db-password` is referenced by `cloud_run.tf` and
  `cloudbuild.yaml`; `coffee-db-system-password` is referenced ONLY by the VM-SA
  binding in `iam.tf` (and, in Ch2, by the VM cloud-init).

### Phase 5 — Cloud Run service (bootstrap image + ignore_changes)

- [ ] 5.1 Create `tools/deploy/terraform/cloud_run.tf` (D-Q1). Bootstrap image +
  `ignore_changes` on the container image; Direct VPC egress block referencing
  Ch2's `coffee-run-subnet`; full env; secret env. Set
  `deletion_protection = false` so `terraform destroy` (Ch6) works for the lab.

  ```hcl
  # SPDX-FileCopyrightText: 2026 Google LLC
  # SPDX-License-Identifier: Apache-2.0

  # Cloud Run service. Terraform creates it with a bootstrap "hello" image and
  # ignores subsequent image changes; cloudbuild's `gcloud run deploy` swaps in
  # the real coffee-app:$SHORT_SHA image on every deploy (D-Q1).
  resource "google_cloud_run_v2_service" "coffee_app" {
    name                = "coffee-app"
    location            = var.region
    deletion_protection = false
    ingress             = "INGRESS_TRAFFIC_ALL"

    template {
      service_account       = google_service_account.coffee_run_sa.email
      execution_environment = "EXECUTION_ENVIRONMENT_GEN2"

      # Direct VPC egress into coffee-vpc / coffee-run-subnet (Ch2).
      # PRIVATE_RANGES_ONLY: private IPs (the DB) go through the VPC; Google
      # APIs / Vertex still use the public path.
      vpc_access {
        network_interfaces {
          network    = google_compute_network.coffee_vpc.id
          subnetwork = google_compute_subnetwork.coffee_run_subnet.id
        }
        egress = "PRIVATE_RANGES_ONLY"
      }

      containers {
        # Bootstrap only; real image set by cloudbuild gcloud run deploy.
        image = "us-docker.pkg.dev/cloudrun/container/hello"

        ports {
          container_port = 8080
        }

        env {
          name  = "DATABASE_HOST"
          value = "10.10.0.10"
        }
        env {
          name  = "DATABASE_PORT"
          value = "1521"
        }
        env {
          name  = "DATABASE_SERVICE_NAME"
          value = "freepdb1"
        }
        env {
          name  = "DATABASE_USER"
          value = "app"
        }
        env {
          name  = "VERTEX_AI_PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "VERTEX_AI_LOCATION"
          value = "us-central1"
        }
        env {
          name  = "GOOGLE_GENAI_USE_VERTEXAI"
          value = "true"
        }
        env {
          name  = "ORACLE_ADK_IN_MEMORY"
          value = "true"
        }
        env {
          name  = "ORACLE_LITESTAR_SESSION_IN_MEMORY"
          value = "true"
        }
        # Only the APP secret (coffee-db-password) reaches Cloud Run. The SYS
        # secret coffee-db-system-password is DB-VM-only and is never wired here.
        env {
          name = "DATABASE_PASSWORD"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.coffee_db_password.secret_id
              version = "latest"
            }
          }
        }
      }
    }

    # cloudbuild owns the deployed image; Terraform must not revert it.
    # client/client_version are stamped by `gcloud run deploy`; ignore them too
    # or `terraform plan` shows a perpetual diff after the first pipeline deploy
    # (would otherwise fail acceptance A2).
    lifecycle {
      ignore_changes = [
        template[0].containers[0].image,
        client,
        client_version,
      ]
    }

    depends_on = [
      google_secret_manager_secret_version.coffee_db_password_v1,
      google_project_iam_member.run_sa_secret_accessor,
    ]
  }

  # LAB ONLY: allow public (unauthenticated) access so the learner can open the
  # URL. The cloudbuild deploy step also passes --allow-unauthenticated; this
  # binding keeps Terraform and the pipeline consistent.
  resource "google_cloud_run_v2_service_iam_member" "coffee_app_public" {
    name     = google_cloud_run_v2_service.coffee_app.name
    location = google_cloud_run_v2_service.coffee_app.location
    role     = "roles/run.invoker"
    member   = "allUsers"
  }

  output "coffee_app_url" {
    description = "Public URL of the Cloud Run service."
    value       = google_cloud_run_v2_service.coffee_app.uri
  }
  ```

- [ ] 5.2 VERIFY phase 5: `terraform validate` succeeds. Confirm the
  `ignore_changes` path is exactly `template[0].containers[0].image` (matches
  the `google_cloud_run_v2_service` schema; a wrong path produces a perpetual
  diff after the first real deploy — A2 catches this).

### Phase 6 — cloudbuild.yaml (build → push → migrate → deploy)

- [ ] 6.1 Create `tools/deploy/gcp/cloudbuild.yaml`. Complete, paste-ready.
  Steps: build (`$SHORT_SHA` + `:latest`) → push both → migrate (built image as
  `name`, `args: ["upgrade"]`, DB env + `secretEnv`) → `gcloud run deploy`
  (Direct VPC egress, run SA, `--allow-unauthenticated`). `options.pool.name`
  pins the private pool; `availableSecrets.secretManager` wires the DB password.

  ```yaml
  # SPDX-FileCopyrightText: 2026 Google LLC
  # SPDX-License-Identifier: Apache-2.0
  #
  # LAB ONLY deploy pipeline for the Cloud Run + private-VPC lab.
  # Trigger:
  #   gcloud builds submit \
  #     --config tools/deploy/gcp/cloudbuild.yaml \
  #     --region=us-central1 \
  #     --substitutions=_PROJECT=$PROJECT_ID,_REGION=us-central1
  # The private pool is pinned via options.pool below; this SUPERSEDES the
  # PRD's `--worker-pool=coffee-build-pool` CLI form (prd.md:130) — do not pass
  # both. `--region` is required so the build runs in the pool's region.

  substitutions:
    _PROJECT: ""            # learner project id (required via --substitutions)
    _REGION: "us-central1"
    _SERVICE: "coffee-app"
    _AR: "coffee-artifacts"

  options:
    logging: CLOUD_LOGGING_ONLY
    pool:
      name: "projects/${_PROJECT}/locations/${_REGION}/workerPools/coffee-build-pool"

  # Only the APP secret is exposed to the build. coffee-db-system-password
  # (Oracle SYS) is DB-VM-only and intentionally NOT wired into this pipeline.
  availableSecrets:
    secretManager:
      - versionName: "projects/${_PROJECT}/secrets/coffee-db-password/versions/latest"
        env: "DATABASE_PASSWORD"

  images:
    - "${_REGION}-docker.pkg.dev/${_PROJECT}/${_AR}/${_SERVICE}:${SHORT_SHA}"
    - "${_REGION}-docker.pkg.dev/${_PROJECT}/${_AR}/${_SERVICE}:latest"

  steps:
    - id: "build"
      name: "gcr.io/cloud-builders/docker"
      args:
        - "build"
        - "-t"
        - "${_REGION}-docker.pkg.dev/${_PROJECT}/${_AR}/${_SERVICE}:${SHORT_SHA}"
        - "-t"
        - "${_REGION}-docker.pkg.dev/${_PROJECT}/${_AR}/${_SERVICE}:latest"
        - "--file"
        - "tools/deploy/docker/Dockerfile"
        - "."

    - id: "push-sha"
      name: "gcr.io/cloud-builders/docker"
      args:
        - "push"
        - "${_REGION}-docker.pkg.dev/${_PROJECT}/${_AR}/${_SERVICE}:${SHORT_SHA}"

    - id: "push-latest"
      name: "gcr.io/cloud-builders/docker"
      args:
        - "push"
        - "${_REGION}-docker.pkg.dev/${_PROJECT}/${_AR}/${_SERVICE}:latest"

    # Migrate the PRIVATE DB through the peered pool. The built image has
    # ENTRYPOINT ["…","coffee"] (tools/deploy/docker/Dockerfile:85), so
    # args:["upgrade"] runs `coffee upgrade` = migrate + load committed-embedding
    # fixtures. NO Vertex is needed here. DB password comes from secretEnv.
    - id: "migrate"
      name: "${_REGION}-docker.pkg.dev/${_PROJECT}/${_AR}/${_SERVICE}:${SHORT_SHA}"
      entrypoint: ""        # use the image ENTRYPOINT (coffee)
      args: ["upgrade"]
      env:
        - "DATABASE_HOST=10.10.0.10"
        - "DATABASE_PORT=1521"
        - "DATABASE_SERVICE_NAME=freepdb1"
        - "DATABASE_USER=app"
      secretEnv:
        - "DATABASE_PASSWORD"

    - id: "deploy"
      name: "gcr.io/cloud-builders/gcloud"
      args:
        - "run"
        - "deploy"
        - "${_SERVICE}"
        - "--image"
        - "${_REGION}-docker.pkg.dev/${_PROJECT}/${_AR}/${_SERVICE}:${SHORT_SHA}"
        - "--project"
        - "${_PROJECT}"
        - "--region"
        - "${_REGION}"
        - "--platform"
        - "managed"
        - "--port"
        - "8080"
        - "--execution-environment"
        - "gen2"
        - "--service-account"
        - "coffee-run-sa@${_PROJECT}.iam.gserviceaccount.com"
        - "--network"
        - "coffee-vpc"
        - "--subnet"
        - "coffee-run-subnet"
        - "--vpc-egress"
        - "private-ranges-only"
        - "--allow-unauthenticated"
  ```

  > Why `entrypoint: ""` on the migrate step: Cloud Build defaults a step's
  > `entrypoint` to the build env, not the image's ENTRYPOINT. Setting it empty
  > makes the step honor the image's own `ENTRYPOINT ["…","coffee"]`, so
  > `args: ["upgrade"]` becomes `coffee upgrade`. (Verified against
  > `tools/deploy/docker/Dockerfile:85`.)
  >
  > Why env (not secret) for host/port/service/user: those are non-secret and
  > the app reads them as plain env (`src/app/lib/settings.py:90-108`). Only the
  > password is a Secret Manager `secretEnv`.
  >
  > Why the migrate step needs no `DATABASE_DSN`: with neither `DATABASE_URL`
  > nor `WALLET_PASSWORD` set, `is_autonomous` is False
  > (`src/app/lib/settings.py:137-139`), so the app synthesizes the DSN from
  > `DATABASE_HOST/PORT/SERVICE_NAME` (`:110-115`). The image's baked
  > `TNS_ADMIN`/`WALLET_LOCATION` (Dockerfile:48-49,62-63) are inert in this
  > mode. Do NOT add `DATABASE_URL` to this step or it silently switches to
  > wallet/autonomous mode and ignores these four envs.
  >
  > **ORDERING INVARIANT (LOAD-BEARING):** the `deploy` step intentionally omits
  > `--set-env-vars` / `--set-secrets`. `gcloud run deploy` on an EXISTING
  > service preserves the env + secret env it is not told to change — so the
  > full env/secret config that Terraform put on `coffee-app` survives each
  > deploy, and the pipeline does not fight Terraform's ownership of service
  > config (mirrors the D-Q1 image-ownership split). Consequence: **`terraform
  > apply` MUST run before the first `gcloud builds submit`.** If `builds
  > submit` runs first (no service, or a service with no env), the deploy
  > creates/leaves a service with no `DATABASE_*` env and no password secret and
  > the revision crashes at startup. Phase 6.2 sequences apply before submit.

- [ ] 6.2 VERIFY full stack (requires Ch1 image build + Ch2 DB up):
  1. `cd tools/deploy/terraform && terraform apply` — all Ch3 resources create.
  2. From repo root: `gcloud builds submit --config tools/deploy/gcp/cloudbuild.yaml --region=us-central1 --substitutions=_PROJECT=$PROJECT_ID,_REGION=us-central1`.
     Expect green; the `migrate` step log shows the migration banner and fixture
     load, proving it reached `10.10.0.10`.
  3. `terraform plan` — expect **no changes** (proves `ignore_changes` works;
     satisfies A2).
  4. `gcloud run services describe coffee-app --region=us-central1 --format="value(spec.template.spec.containers[0].image)"`
     shows the `:$SHORT_SHA` image; `--format="value(status.url)"` URL returns
     HTTP 200 (`curl -fsS`).
  5. `gcloud projects get-iam-policy $PROJECT_ID --flatten=bindings --filter="bindings.members:serviceAccount:coffee-build-sa@${PROJECT_ID}.iam.gserviceaccount.com" --format="value(bindings.role)"`
     lists `run.admin`, `iam.serviceAccountUser`, `artifactregistry.writer`,
     `secretmanager.secretAccessor` and **no** `aiplatform.*` (satisfies A5 / N1).

### Phase 7 — Spec review

- [ ] 7.1 Dispatch `code-reviewer` over the created files
  (`tools/deploy/terraform/*.tf`, `tools/deploy/gcp/cloudbuild.yaml`) for HCL
  schema correctness (esp. `google_cloud_run_v2_service` `vpc_access` /
  `value_source` blocks and the `ignore_changes` path), cloudbuild
  `secretEnv` / `availableSecrets` wiring, and SPDX headers on `.tf` files.
- [ ] 7.2 Confirm no Ch3 file redeclares a Ch2 resource/variable in the shared
  root (no duplicate `project_id`/`region`/`terraform` block), and that all
  cross-chapter references (`coffee_vpc`, `coffee_run_subnet`, `coffee_db_sa`)
  resolve as plain resource references.

---

## Cross-references

- PRD: `.agents/specs/cloudrun-gce-lab/prd.md` (Architecture Contract `:89-148`;
  decisions `:78-86`).
- Research: `.agents/research/research_cloudrun_gce_lab_overhaul/research.md`
  (spanner-mc template `:123-141`; private-pool migration `:115-116`; "no Vertex
  at build" `:68-71`).
- Reference pipeline: `cofin/spanner-mc:deploy/gcp/cloudbuild.deploy.yml`.
- Image: `tools/deploy/docker/Dockerfile:85-86` (ENTRYPOINT/CMD).
- Settings: `src/app/lib/settings.py:90-108,94-97,329-334` (env var names).
- `coffee upgrade`: `src/app/cli/commands.py:89-110,161-172`.
- Ch2 dependencies (shared root): `google_compute_network.coffee_vpc`,
  `google_compute_subnetwork.coffee_run_subnet`,
  `google_service_account.coffee_db_sa`, firewall `coffee-allow-run-to-db`.
