# Flow: gce-oracle-appliance

> Chapter 2 of PRD `cloudrun-gce-lab` (Beads epic `oracledb-vertexai-jw0.2`).
> INFRA ONLY — Terraform + cloud-init. No application source code changes.
> Source of truth for names/CIDRs/IPs: `.agents/specs/cloudrun-gce-lab/prd.md`
> → "Architecture Contract".

## Specification

### Context

The PRD ships a second, "real deployment" lab: the Litestar app runs on Cloud
Run and the Oracle 26ai database runs on a **Container-Optimized OS (COS)** GCE
VM as a `gvenzl/oracle-free` container launched by **cloud-init**, with a
**persistent disk** for durable data and **no external IP**. This chapter builds
the network and the DB appliance only.

The deliverable is a Terraform-provisioned **private** Oracle reachable on
`10.10.0.10:1521/freepdb1` from inside `coffee-vpc` (Cloud Run egress range +
Cloud Build pool range), never from the public internet, whose data survives VM
recreation. Migrations and fixtures (`coffee upgrade`) are **not** run here; they
run in Chapter 3 from the build pool. Chapter 2's job is to make the appliance
exist, be healthy, have the Oracle 26ai **vector memory pool allocated**, and
have the `app` user usable.

All `.tf` files (Ch2 network + VM, Ch3 registry/pool/run/iam/secrets) live in a
**single Terraform root** `tools/deploy/terraform/` and are applied together as
one stack (`terraform apply`). Ch2 creates `providers.tf`, `variables.tf`,
`network.tf`, `db_vm.tf`, `outputs.tf`, the cloud-init template, and the root
`.gitignore`. Ch3 adds `registry.tf`, `buildpool.tf`, `cloudrun.tf`, `iam.tf`,
`secrets.tf` into the same root. Because the root is shared, `db_vm.tf` may
reference the Ch3-owned secret version directly (see "Cross-chapter coupling").

### Code-analysis summary (read-only; file:line)

The COS appliance must reproduce the local container contract from
`tools/oracle/database.py`:

- `DEFAULT_IMAGE = "gvenzl/oracle-free:latest"` — `tools/oracle/database.py:34`
- `PDB_SERVICE_NAME = "freepdb1"` — `tools/oracle/database.py:35`
- `_build_run_command()` — `tools/oracle/database.py:415-474`:
  - `-p 1521:1521` — lines 424-425.
  - Env (lines 427-434): `ORACLE_SYSTEM_PASSWORD`, `ORACLE_PASSWORD` (SYS/system
    password), `APP_USER_PASSWORD`, `APP_USER`. PRD contract maps the VM env to
    `ORACLE_PASSWORD` (system), `APP_USER=app`, `APP_USER_PASSWORD` (from secret).
  - Data volume `oracle-db-data:/opt/oracle/oradata` — lines 436-437. On the VM
    this becomes the persistent disk: host `/mnt/disks/oradata` → container
    `/opt/oracle/oradata`.
  - Restart policy — lines 438-440 (local `unless-stopped`; PRD pins `always` on
    the VM).
  - Healthcheck `healthcheck.sh`, interval 10s, timeout 5s, retries 10 — lines
    446-454 (script is baked into the gvenzl image).
  - Hook mounts — lines 460-471: every `*.sql`/`*.sh` in `tools/oracle/on_init/`
    → `/container-entrypoint-initdb.d/<name>`; `tools/oracle/on_startup/` →
    `/container-entrypoint-startdb.d/<name>` (`:z` SELinux relabel).
- Config defaults — `tools/oracle/database.py:39-86`: `app_user="app"`,
  host/container port `1521`.

The four hook SQL files the VM must carry (reproduce verbatim via
`templatefile()` `file()`-reads — single source of truth):

- `tools/oracle/on_init/00_configure_vector_memory.sql` — **critical**
  (CLAUDE.md note #2): `ALTER SYSTEM SET vector_memory_size = 512M SCOPE=SPFILE;`
  then `SHUTDOWN IMMEDIATE` / `STARTUP`. Runs once on first DB creation, before
  any HNSW `ORGANIZATION INMEMORY NEIGHBOR GRAPH` index DDL. Free Edition rejects
  SGA overrides (ORA-56752); 512M fits the demo dataset.
- `tools/oracle/on_init/db_init.sql` — `ALTER SESSION SET CONTAINER=freepdb1;`
  + grants to `app` (CONNECT, RESOURCE, mining model, unlimited tablespace,
  create table/view/sequence/procedure, `DB_DEVELOPER_ROLE`).
- `tools/oracle/on_startup/00_verify_vector_memory.sql` — verifies the
  `V$SGAINFO` `Vector Memory` / `Vector Memory Area` row is non-zero on every
  start (warns if zero).
- `tools/oracle/on_startup/01_startup_test.sql` — `ALTER SESSION SET
  CONTAINER=freepdb1;` + a SYSDATE select.

App-side compatibility (no change needed): `src/app/lib/settings.py:91-113`
already reads `DATABASE_HOST/PORT/SERVICE_NAME/USER/PASSWORD` (defaults
`app`/`1521`/`freepdb1`), so Ch3 only sets `DATABASE_HOST=10.10.0.10`.

`make start-infra` (`Makefile:331-335`) calls `manage.py infra start --recreate
--skip-apex --skip-ords`; the local loop is unchanged by this chapter.

Greenfield: `tools/deploy/` currently holds only `docker/`. No `terraform/` or
`gcp/` directories and no Terraform `.gitignore` entries exist yet.

### External facts honored

- `gcloud compute instances create-with-container` is **deprecated** → use a
  cloud-init `docker run` on COS (research.md §A).
- COS runs cloud-init `write_files`/`runcmd` on **every boot**, not once → all
  startup logic must be **idempotent** (research.md §A "Gotcha").
- COS can mount a persistent disk into a container; ext4 or empty disk
  (research.md §A).
- COS has **no `gcloud`** binary → cloud-init reads Secret Manager via the
  metadata server token + the Secret Manager REST API (curl).

### Functional requirements

- **FR1 — VPC + subnets.** Custom-mode VPC `coffee-vpc`; subnet `coffee-subnet`
  `10.10.0.0/24` (DB) and `coffee-run-subnet` `10.10.1.0/24` (Cloud Run egress),
  both in `var.region`.
- **FR2 — Build-pool peering range.** Reserved global address
  `coffee-buildpool-range` `10.30.0.0/24`, `purpose=VPC_PEERING`, on `coffee-vpc`
  (consumed by Ch3's private pool; declared here so the firewall + network are
  complete).
- **FR3 — Static internal IP.** `coffee-db-ip` = `10.10.0.10`, address type
  `INTERNAL`, in `coffee-subnet`, assigned to the DB VM nic.
- **FR4 — Egress.** Cloud Router `coffee-router` + Cloud NAT `coffee-nat` on
  `coffee-vpc`/`var.region` so the `--no-address` VM can pull the gvenzl image
  and reach the Secret Manager API.
- **FR5 — Firewall.** `coffee-allow-iap-ssh`: ingress tcp:22 from
  `35.235.240.0/20` → target tag `coffee-db`. `coffee-allow-run-to-db`: ingress
  tcp:1521 from `10.10.1.0/24` **and** `10.30.0.0/24` → target tag `coffee-db`.
  No public ingress to the DB.
- **FR6 — Data disk.** `google_compute_disk` `coffee-db-data`, `pd-ssd`, 50 GB,
  `var.zone`. Attached to the VM with a stable device name `coffee-db-data` so it
  appears at `/dev/disk/by-id/google-coffee-db-data`.
- **FR7 — DB VM.** `google_compute_instance` `coffee-db`: COS `cos-stable` image
  family, `e2-standard-4`, **standard (NOT Spot)**, `--no-address` (no public
  IP), network tag `coffee-db`, static internal IP `coffee-db-ip`,
  `metadata.user-data` = the rendered cloud-init template. Dedicated SA
  `coffee-db-sa` with OAuth scope `cloud-platform`.
- **FR8 — Idempotent disk mount.** cloud-init `runcmd` formats the data disk with
  `mkfs.ext4` only if `blkid` reports no filesystem, then mounts it at
  `/mnt/disks/oradata` only if not already mounted (safe on every boot).
- **FR9 — Hooks on the VM.** cloud-init `write_files` writes the four hook SQL
  files to `/var/lib/oracle-hooks/on_init/` and `/var/lib/oracle-hooks/on_startup/`
  on the stateful partition; the bodies are injected by `templatefile()`
  `file()`-reading the repo's `tools/oracle/on_*/*.sql` (single source of truth).
- **FR10 — Oracle container.** cloud-init `runcmd` runs the gvenzl container
  guarded so reboots do not duplicate it: `gvenzl/oracle-free:latest`,
  `-p 1521:1521`, `-v /mnt/disks/oradata:/opt/oracle/oradata`, the two hook dirs
  bind-mounted to the entrypoint dirs, env `ORACLE_PASSWORD` / `APP_USER=app` /
  `APP_USER_PASSWORD`, `--restart always`.
- **FR11 — Secret at boot.** cloud-init reads `coffee-db-password:latest` from
  Secret Manager via metadata-token + REST API; on an empty/failed read it logs
  and **exits non-zero** (fail loud). No second password source / no fallback
  variable.
- **FR12 — IAM.** `coffee-db-sa` granted `roles/secretmanager.secretAccessor` on
  the `coffee-db-password` secret (resource created in Ch3, referenced here).
- **FR13 — Outputs.** `db_internal_ip`, `vpc_self_link`, `db_subnet_self_link`,
  `run_subnet_self_link`, `db_target_tag`, `db_service_account_email`.
- **FR14 — State hygiene.** `tools/deploy/terraform/.gitignore` ignores
  `.terraform/`, `*.tfstate*`, `*.tfvars` (state/vars can hold sensitive values).
- **FR15 — Local default state.** No remote backend block in Ch2 (PRD Open Items:
  local default; GCS is a Ch5 challenge).

### Non-functional requirements

- **NFR1 — Idempotency.** Every cloud-init action survives repeated boots
  (`blkid`-guarded format, mount-if-not-mounted, `docker rm -f`-then-run guard).
- **NFR2 — Privacy.** VM has `--no-address`; the only DB ingress is tcp:1521 from
  the run + build ranges; tcp:22 only from IAP. The DB is unreachable from the
  public internet by construction.
- **NFR3 — Durability.** Oracle data lives on the persistent disk; recreating the
  VM (disk retained) preserves the database.
- **NFR4 — Secret hygiene.** **Neither** the APP password nor the SYS/SYSTEM
  password is ever written to Terraform state, VM metadata (`user-data`), or
  logs; both are fetched at boot by the VM SA from Secret Manager. The rendered
  `user-data` contains only secret *ids* and env-var *names*.
- **NFR5 — Single source of truth.** Hook SQL is read from the repo files, not
  duplicated into the template.
- **NFR6 — House style.** Floor-only provider pins; no backwards-compat shims; no
  dual password paths.

### Cross-chapter coupling (shared Terraform root)

`db_vm.tf` references **two** Ch3-owned secrets — `coffee_db_password` (APP) and
`coffee_db_system_password` (SYS) — and adds a `secretAccessor` IAM binding on
each for `coffee-db-sa`. The instance's `depends_on` lists both secret
**versions** (the payloads) plus both IAM bindings, so the VM boots only after
the payloads exist and are readable (otherwise FR11's boot-time fetch hits the
fail-loud empty path). Both secrets + versions are created in Ch3's `secrets.tf`
**within the same root**; the two chapters share one `terraform apply`. Ch2's
HCL that touches the secrets is written now but only resolves once Ch3's
`secrets.tf` exists — these are forward references, not errors.

**New vs. PRD contract:** the PRD names a single secret `coffee-db-password`.
This chapter adds a second secret `coffee-db-system-password` for the Oracle
SYS/SYSTEM password so it is never templated into VM metadata (C2 fix). Flag
this to Ch3 planning: `secrets.tf` must create both secrets, and only the APP
secret feeds Cloud Run / the build migrate step (the SYS secret is DB-VM-only).

### API / DB surface

No application API or schema changes. The "API" of this chapter is the Oracle
listener at `10.10.0.10:1521`, PDB service `freepdb1`, app user `app` — consumed
by Ch3.

### Acceptance criteria

- **AC1** `terraform apply` (with Ch3's `secrets.tf` present, or both secrets
  `coffee-db-password` + `coffee-db-system-password` manually pre-created for
  standalone Ch2 testing) creates: `coffee-vpc`, both subnets,
  `coffee-router`/`coffee-nat`, `coffee-buildpool-range`,
  `coffee-db-ip`=`10.10.0.10`, both firewall rules, `coffee-db-data` disk,
  `coffee-db-sa`, the `coffee-db` VM.
- **AC2** `gcloud compute instances describe coffee-db` shows **no** external/NAT
  IP (`accessConfigs` empty) and `networkInterfaces[0].networkIP == 10.10.0.10`.
- **AC3** Over IAP SSH, `docker ps` shows one running `oracle-free` container and
  `docker inspect --format '{{.State.Health.Status}}' oracle-free` is `healthy`
  (requires the `--health-cmd healthcheck.sh` flags, M3).
- **AC4** `docker logs oracle-free` shows the init hooks ran (incl. the
  `00_configure_vector_memory.sql` `SHUTDOWN IMMEDIATE`/`STARTUP` bounce
  completing under `--restart always`, C3) and the on_startup verify printed a
  non-zero "Vector Memory pool: … MB allocated." line (vector memory configured
  before any index DDL — CLAUDE.md note #2).
- **AC5 (DB unreachable without VPC).** Three checks: (a) `coffee-db` has no
  external IP (`accessConfigs` empty) — no public path exists; (b) a probe VM in
  the **allowed** `coffee-run-subnet` connects to `10.10.0.10:1521`; (c) a probe
  in a range **not** in `coffee-allow-run-to-db` (e.g. a host in `coffee-subnet`
  `10.10.0.0/24`, which is intentionally NOT a source range) is **refused** on
  1521 — proving the firewall scoping, not merely the absence of a public IP.
- **AC6 (data survives VM recreate).** Create a marker table as `app`, run
  `terraform taint google_compute_instance.coffee_db` (disk retained) +
  `terraform apply`; after the VM reboots, the marker table still exists and the
  cloud-init log shows **no** "No filesystem on …" line (the disk was not
  reformatted).
- **AC7** `terraform output` returns `db_internal_ip=10.10.0.10`, the three
  self-links, `db_target_tag=coffee-db`, and `db_service_account_email`.
- **AC8** Rebooting the VM (`gcloud compute instances reset coffee-db`) does **not**
  create a duplicate container and does **not** reformat the data disk (idempotent
  cloud-init).

---

## Implementation Plan

> Conventions: every task names the exact file to CREATE and gives paste-ready
> HCL/YAML plus a concrete verification command. Provider HCL uses floor-only
> version pins (house style). `var.project_id` has no default; `region` /`zone`
> default to `us-central1` / `us-central1-c`. This is INFRA — TDD's "write a
> failing unit test first" does not apply; the test gates are `terraform
> validate`/`plan` and the live verification commands in each phase. No app
> source or pytest changes.

### Phase 1 — Terraform skeleton (providers, variables, gitignore)

- [ ] 1.1 Create `tools/deploy/terraform/providers.tf`.

  ```hcl
  terraform {
    required_version = ">= 1.7"
    required_providers {
      google = {
        source  = "hashicorp/google"
        version = ">= 5.0"
      }
    }
  }

  provider "google" {
    project = var.project_id
    region  = var.region
    zone    = var.zone
  }
  ```

  Verify: `cd tools/deploy/terraform && terraform init && terraform validate`
  (validate passes once 1.2 exists).

- [ ] 1.2 Create `tools/deploy/terraform/variables.tf`.

  ```hcl
  variable "project_id" {
    type        = string
    description = "GCP project ID for the lab."
  }

  variable "region" {
    type        = string
    default     = "us-central1"
    description = "Region for the VPC, subnets, router/NAT, and DB VM."
  }

  variable "zone" {
    type        = string
    default     = "us-central1-c"
    description = "Zone for the DB VM and its data disk."
  }

  variable "db_machine_type" {
    type        = string
    default     = "e2-standard-4"
    description = "Machine type for the coffee-db VM (standard, non-Spot)."
  }

  variable "db_data_disk_size_gb" {
    type        = number
    default     = 50
    description = "Size of the persistent pd-ssd Oracle data disk."
  }

  variable "cos_image_family" {
    type        = string
    default     = "cos-stable"
    description = "Container-Optimized OS image family for the DB VM."
  }

  variable "db_password_secret_id" {
    type        = string
    default     = "coffee-db-password"
    description = "Secret Manager secret holding the Oracle APP user password (created in Ch3)."
  }
  ```

  Verify: `terraform validate` passes. `terraform plan` errors only on the
  missing forward reference to the Ch3 secret (expected until Ch3 / a manual
  secret exists).

- [ ] 1.3 Create `tools/deploy/terraform/.gitignore`.

  ```gitignore
  # Terraform local state, plans, and provider plugins (may hold secrets)
  .terraform/
  *.tfstate
  *.tfstate.*
  *.tfvars
  crash.log
  ```

  Note: `.terraform.lock.hcl` is **committed** (not ignored) so provider
  versions are pinned for reproducible applies even though `required_providers`
  uses floor-only constraints (M4). Verify:
  `git -C tools/deploy/terraform check-ignore -v terraform.tfstate` prints a
  match; `git status` does not show `.terraform/` after `terraform init`;
  `.terraform.lock.hcl` IS tracked (`git status` shows it as a new file to add).

### Phase 2 — Network (VPC, subnets, router/NAT, peering range, firewall, static IP)

- [ ] 2.1 Create `tools/deploy/terraform/network.tf` — VPC + two subnets.

  ```hcl
  resource "google_compute_network" "coffee_vpc" {
    name                    = "coffee-vpc"
    auto_create_subnetworks = false
    routing_mode            = "REGIONAL"
  }

  resource "google_compute_subnetwork" "coffee_subnet" {
    name          = "coffee-subnet"
    ip_cidr_range = "10.10.0.0/24"
    region        = var.region
    network       = google_compute_network.coffee_vpc.id
  }

  resource "google_compute_subnetwork" "coffee_run_subnet" {
    name          = "coffee-run-subnet"
    ip_cidr_range = "10.10.1.0/24"
    region        = var.region
    network       = google_compute_network.coffee_vpc.id
  }
  ```

  Verify: `terraform plan` lists these three resources with the exact CIDRs.

- [ ] 2.2 Append the static internal IP + build-pool peering range to
  `network.tf`.

  ```hcl
  resource "google_compute_address" "coffee_db_ip" {
    name         = "coffee-db-ip"
    address_type = "INTERNAL"
    address      = "10.10.0.10"
    subnetwork   = google_compute_subnetwork.coffee_subnet.id
    region       = var.region
  }

  # Reserved range for the Ch3 Cloud Build private pool VPC peering.
  resource "google_compute_global_address" "coffee_buildpool_range" {
    name          = "coffee-buildpool-range"
    purpose       = "VPC_PEERING"
    address_type  = "INTERNAL"
    address       = "10.30.0.0"
    prefix_length = 24
    network       = google_compute_network.coffee_vpc.id
  }
  ```

  Verify: `terraform plan` shows `coffee-db-ip` with `address = 10.10.0.10` and
  the `/24` peering range `10.30.0.0/24`.

- [ ] 2.3 Append Cloud Router + Cloud NAT to `network.tf`.

  ```hcl
  resource "google_compute_router" "coffee_router" {
    name    = "coffee-router"
    region  = var.region
    network = google_compute_network.coffee_vpc.id
  }

  resource "google_compute_router_nat" "coffee_nat" {
    name                               = "coffee-nat"
    router                             = google_compute_router.coffee_router.name
    region                             = var.region
    nat_ip_allocate_option             = "AUTO_ONLY"
    source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  }
  ```

  Verify: `terraform plan` shows `coffee-router` + `coffee-nat`. (NAT lets the
  `--no-address` VM pull the gvenzl image and reach the Secret Manager API.)

- [ ] 2.4 Append the two firewall rules to `network.tf`.

  ```hcl
  resource "google_compute_firewall" "coffee_allow_iap_ssh" {
    name      = "coffee-allow-iap-ssh"
    network   = google_compute_network.coffee_vpc.id
    direction = "INGRESS"
    priority  = 1000

    allow {
      protocol = "tcp"
      ports    = ["22"]
    }

    source_ranges = ["35.235.240.0/20"] # Google IAP TCP-forwarding range
    target_tags   = ["coffee-db"]
  }

  resource "google_compute_firewall" "coffee_allow_run_to_db" {
    name      = "coffee-allow-run-to-db"
    network   = google_compute_network.coffee_vpc.id
    direction = "INGRESS"
    priority  = 1000

    allow {
      protocol = "tcp"
      ports    = ["1521"]
    }

    # Cloud Run Direct VPC egress range + Cloud Build private-pool peering range.
    source_ranges = ["10.10.1.0/24", "10.30.0.0/24"]
    target_tags   = ["coffee-db"]
  }
  ```

  Verify: `terraform plan` shows both rules with exact ports/ranges/target tag.
  Confirm there is **no** rule opening 1521 to `0.0.0.0/0`.

### Phase 3 — cloud-init template (disk mount, hooks, secret, container)

- [ ] 3.1 Create `tools/deploy/gcp/cloud-init-oracle.yaml.tftpl`. This is the
  COS cloud-config rendered by `templatefile()`. Template variables (passed from
  `db_vm.tf` in Phase 4): `app_user`, `app_password_secret_id`,
  `system_password_secret_id`, `project_id`, `oracle_image`, and the four hook
  SQL bodies (`init_vector_sql`, `init_db_sql`, `startup_verify_sql`,
  `startup_test_sql`). **Neither password is templated** — both are fetched from
  Secret Manager at boot (see C2 fix below). All `runcmd` steps are idempotent
  (COS runs them every boot).

  ```yaml
  #cloud-config
  # COS cloud-config for the Cymbal Coffee Oracle 26ai DB appliance.
  # Rendered by tools/deploy/terraform/db_vm.tf via templatefile().
  # COS runs write_files + runcmd on EVERY boot, so every step is idempotent.

  write_files:
    - path: /var/lib/oracle-hooks/on_init/00_configure_vector_memory.sql
      permissions: "0644"
      content: |
        ${indent(8, init_vector_sql)}
    - path: /var/lib/oracle-hooks/on_init/db_init.sql
      permissions: "0644"
      content: |
        ${indent(8, init_db_sql)}
    - path: /var/lib/oracle-hooks/on_startup/00_verify_vector_memory.sql
      permissions: "0644"
      content: |
        ${indent(8, startup_verify_sql)}
    - path: /var/lib/oracle-hooks/on_startup/01_startup_test.sql
      permissions: "0644"
      content: |
        ${indent(8, startup_test_sql)}

    # Script lives under /etc (exec-allowed). COS mounts /var noexec, so a
    # /var/lib script cannot be execve()'d directly (see C1). We also invoke it
    # via `bash <path>` from runcmd so the path is read, not executed.
    - path: /etc/oracle/start-oracle.sh
      permissions: "0755"
      content: |
        #!/bin/bash
        set -euo pipefail
        log() { echo "[start-oracle] $*"; }

        DISK_DEV="/dev/disk/by-id/google-coffee-db-data"
        MNT="/mnt/disks/oradata"
        CONTAINER="oracle-free"
        IMAGE="${oracle_image}"
        PROJECT="${project_id}"
        APP_SECRET_ID="${app_password_secret_id}"
        SYS_SECRET_ID="${system_password_secret_id}"

        # access_secret <secret-id> — read latest version via metadata token +
        # the Secret Manager REST API (COS has no gcloud). Extraction is anchored
        # to the JSON field names and base64-decoded; empty result is fatal.
        access_secret() {
          local sid="$1" token data
          token="$(curl -fsS -H 'Metadata-Flavor: Google' \
            'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token' \
            | grep -o '"access_token"[[:space:]]*:[[:space:]]*"[^"]*"' \
            | head -n1 | sed 's/.*"\([^"]*\)"$/\1/')"
          [ -n "$token" ] || { log "ERROR: no metadata access token."; return 1; }
          # The payload.data field is the base64 secret; dataCrc32c is a sibling.
          data="$(curl -fsS -H "Authorization: Bearer $token" \
            "https://secretmanager.googleapis.com/v1/projects/$PROJECT/secrets/$sid/versions/latest:access" \
            | grep -o '"data"[[:space:]]*:[[:space:]]*"[^"]*"' \
            | head -n1 | sed 's/.*"\([^"]*\)"$/\1/' | base64 -d)"
          [ -n "$data" ] || { log "ERROR: empty secret $sid."; return 1; }
          printf '%s' "$data"
        }

        # --- 1. Wait for the data disk device symlink (avoid mkfs race, I2) -----
        for i in $(seq 1 30); do
          [ -e "$DISK_DEV" ] && break
          log "Waiting for $DISK_DEV ($i/30)..."; sleep 2
        done
        [ -e "$DISK_DEV" ] || { log "ERROR: $DISK_DEV never appeared."; exit 1; }

        # --- 2. Idempotent format + mount (format ONLY if no filesystem) --------
        # No -F: refuse to clobber an existing fs. blkid is the format guard.
        if ! blkid "$DISK_DEV" >/dev/null 2>&1; then
          log "No filesystem on $DISK_DEV; creating ext4."
          mkfs.ext4 "$DISK_DEV"
        fi
        mkdir -p "$MNT"
        if ! mountpoint -q "$MNT"; then
          log "Mounting $DISK_DEV at $MNT."
          mount -o discard,defaults "$DISK_DEV" "$MNT"
        fi
        # gvenzl runs as the 'oracle' uid 54321; make oradata writable.
        chown -R 54321:54321 "$MNT" || true

        # --- 3. Fetch both passwords from Secret Manager (never templated) ------
        APP_USER_PASSWORD="$(access_secret "$APP_SECRET_ID")" \
          || { log "ERROR: could not read APP password."; exit 1; }
        ORACLE_PASSWORD="$(access_secret "$SYS_SECRET_ID")" \
          || { log "ERROR: could not read SYS password."; exit 1; }

        # --- 4. Run the Oracle container (idempotent: replace, never duplicate) -
        if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
          log "Removing existing $CONTAINER container before re-create."
          docker rm -f "$CONTAINER" || true
        fi
        log "Pulling $IMAGE."
        docker pull "$IMAGE"
        log "Starting $CONTAINER."
        docker run -d \
          --name "$CONTAINER" \
          --hostname coffee-db \
          --restart always \
          -p 1521:1521 \
          -e ORACLE_PASSWORD="$ORACLE_PASSWORD" \
          -e APP_USER='${app_user}' \
          -e APP_USER_PASSWORD="$APP_USER_PASSWORD" \
          -v "$MNT":/opt/oracle/oradata \
          -v /var/lib/oracle-hooks/on_init:/container-entrypoint-initdb.d \
          -v /var/lib/oracle-hooks/on_startup:/container-entrypoint-startdb.d \
          --health-cmd healthcheck.sh \
          --health-interval 10s \
          --health-timeout 5s \
          --health-retries 10 \
          --log-opt max-size=10m \
          --log-opt max-file=3 \
          "$IMAGE"
        log "Done."

  runcmd:
    - systemctl is-active docker || systemctl start docker
    # Invoke via bash so the /etc path is read, not execve'd (belt-and-braces
    # alongside placing the script on the exec-allowed /etc mount — C1).
    - ['bash', '/etc/oracle/start-oracle.sh']
  ```

  Notes for the executor:
  - **C1 (every boot, /var noexec):** COS mounts `/var` `noexec`, so the bring-up
    script lives under `/etc/oracle/` and is invoked as `['bash', '<path>']`
    (list form, no shell-string `execve`). Both placements are required.
  - **C2 (no templated passwords):** *Both* the gvenzl `ORACLE_PASSWORD`
    (SYS/SYSTEM) and `APP_USER_PASSWORD` are fetched from Secret Manager at boot
    via `access_secret`. Nothing secret is written to `user-data`, instance
    metadata, or Terraform state. The SYS secret id is `var.system_password_secret_id`
    (Phase 4); both secrets are created in Ch3 `secrets.tf` (shared root).
  - **M3 (healthcheck):** the gvenzl image defines no default `HEALTHCHECK`, so
    `--health-cmd healthcheck.sh` (+ interval/timeout/retries) is required or
    `docker inspect '{{.State.Health.Status}}'` returns `<no value>` and AC3
    cannot pass. `--log-opt` mirrors the local contract (database.py:441-445).
  - **M1 (`--hostname`):** matches the local contract's `--hostname` intent
    (database.py:422-423).
  - **I2 (mkfs race):** a bounded wait for `/dev/disk/by-id/google-coffee-db-data`
    precedes `blkid`; `mkfs.ext4` runs **without `-F`** so it never clobbers an
    existing filesystem (data-loss guard for AC6/NFR3).
  - **I1 (robust secret parse):** extraction is anchored to the JSON field names
    (`access_token`, `data`) with `grep -o ... | head -n1`, tolerant of proto3
    key ordering/whitespace; `curl -fsS` fails on non-2xx.
  - The `:z` SELinux relabel used locally is omitted: COS mounts the hook dirs
    read-write for `docker` already; do not add `:z`.
  - `${indent(8, ...)}` keeps the YAML block-scalar indentation correct when the
    SQL bodies are injected.

  Verify (render-only smoke, no apply): after Phase 4 wiring, dump a plan-time
  render and lint it:
  `terraform plan` then
  `python -c "import yaml; yaml.safe_load(open('rendered.yaml'))"` on the rendered
  `user-data`. Confirm no password literal appears anywhere in the render
  (`grep -i password rendered.yaml` shows only env-var *names* and secret *ids*).

### Phase 4 — DB VM + data disk + SA + secret IAM

- [ ] 4.1 Create `tools/deploy/terraform/db_vm.tf` — data disk + dedicated SA.

  ```hcl
  resource "google_compute_disk" "coffee_db_data" {
    name = "coffee-db-data"
    type = "pd-ssd"
    zone = var.zone
    size = var.db_data_disk_size_gb
  }

  resource "google_service_account" "coffee_db_sa" {
    account_id   = "coffee-db-sa"
    display_name = "Cymbal Coffee DB VM service account"
  }
  ```

  Verify: `terraform plan` shows the 50 GB `pd-ssd` disk and the SA.

- [ ] 4.2 Append the cloud-init rendering to `db_vm.tf`. **No password is
  templated** (C2): the template only carries secret *ids*; both passwords are
  fetched at boot. No `random` provider is needed.

  ```hcl
  locals {
    cloud_init = templatefile("${path.module}/../gcp/cloud-init-oracle.yaml.tftpl", {
      app_user                  = "app"
      app_password_secret_id    = var.db_password_secret_id        # coffee-db-password (Ch3)
      system_password_secret_id = var.system_password_secret_id    # coffee-db-system-password (Ch3)
      project_id                = var.project_id
      oracle_image              = "gvenzl/oracle-free:latest"
      init_vector_sql           = file("${path.module}/../../oracle/on_init/00_configure_vector_memory.sql")
      init_db_sql               = file("${path.module}/../../oracle/on_init/db_init.sql")
      startup_verify_sql        = file("${path.module}/../../oracle/on_startup/00_verify_vector_memory.sql")
      startup_test_sql          = file("${path.module}/../../oracle/on_startup/01_startup_test.sql")
    })
  }
  ```

  Add a `system_password_secret_id` variable to `variables.tf` (alongside
  `db_password_secret_id` from Phase 1.2):

  ```hcl
  variable "system_password_secret_id" {
    type        = string
    default     = "coffee-db-system-password"
    description = "Secret Manager secret holding the Oracle SYS/SYSTEM password (created in Ch3)."
  }
  ```

  Path note: from `tools/deploy/terraform/`, `../../oracle/on_init/...` resolves
  to `tools/oracle/on_init/...` (single source of truth — the repo hook SQL).
  Cross-chapter note: Ch3 `secrets.tf` must create **two** secrets —
  `coffee-db-password` (APP) and `coffee-db-system-password` (SYS) — plus their
  versions. The SYS secret is new vs. the PRD contract's single-secret note;
  flag this when Ch3 is planned so its `secrets.tf` and the build/run env wiring
  account for it.

  Verify: `terraform validate`; `terraform console` →
  `length(local.cloud_init) > 0` is `true`; the rendered string contains no
  password literal (only secret ids).

- [ ] 4.3 Append the `coffee-db` instance to `db_vm.tf`.

  ```hcl
  resource "google_compute_instance" "coffee_db" {
    name         = "coffee-db"
    machine_type = var.db_machine_type
    zone         = var.zone
    tags         = ["coffee-db"]

    # Standard (NOT Spot/preemptible) — this is the durable DB.
    scheduling {
      provisioning_model  = "STANDARD"
      preemptible         = false
      automatic_restart   = true
      on_host_maintenance = "MIGRATE"
    }

    boot_disk {
      initialize_params {
        image = "cos-cloud/${var.cos_image_family}"
        size  = 20
        type  = "pd-balanced"
      }
    }

    attached_disk {
      source      = google_compute_disk.coffee_db_data.id
      device_name = "coffee-db-data" # → /dev/disk/by-id/google-coffee-db-data
    }

    network_interface {
      subnetwork = google_compute_subnetwork.coffee_subnet.id
      network_ip = google_compute_address.coffee_db_ip.address
      # No access_config block => --no-address (no external IP).
    }

    service_account {
      email  = google_service_account.coffee_db_sa.email
      scopes = ["cloud-platform"] # required for the metadata-token Secret Manager read
    }

    metadata = {
      user-data                = local.cloud_init
      google-logging-enabled   = "true"
      google-monitoring-enabled = "true"
    }

    # Boot only after BOTH secret VERSIONS exist (payloads, not just the secret
    # resources) and the IAM bindings are in place (Ch3 secrets.tf, same root).
    # Depending on the *versions* guarantees the boot-time fetch (FR11) finds a
    # payload rather than hitting the fail-loud empty-read path.
    depends_on = [
      google_secret_manager_secret_iam_member.db_sa_app_secret_access,
      google_secret_manager_secret_iam_member.db_sa_system_secret_access,
      google_secret_manager_secret_version.coffee_db_password,
      google_secret_manager_secret_version.coffee_db_system_password,
    ]
  }
  ```

  Verify: `terraform plan` shows `coffee-db` with no `access_config`, tag
  `coffee-db`, `network_ip = 10.10.0.10`, scopes `cloud-platform`, COS image, and
  the attached `coffee-db-data` disk.

- [ ] 4.4 Append the secret-access IAM bindings to `db_vm.tf` (forward-reference
  the Ch3 secrets — resolve once `secrets.tf` exists in the shared root). One
  binding per secret (APP + SYS):

  ```hcl
  # Secrets + versions are created in Ch3 secrets.tf (same Terraform root).
  # These bindings let the VM SA read both at boot.
  resource "google_secret_manager_secret_iam_member" "db_sa_app_secret_access" {
    secret_id = google_secret_manager_secret.coffee_db_password.secret_id
    role      = "roles/secretmanager.secretAccessor"
    member    = "serviceAccount:${google_service_account.coffee_db_sa.email}"
  }

  resource "google_secret_manager_secret_iam_member" "db_sa_system_secret_access" {
    secret_id = google_secret_manager_secret.coffee_db_system_password.secret_id
    role      = "roles/secretmanager.secretAccessor"
    member    = "serviceAccount:${google_service_account.coffee_db_sa.email}"
  }
  ```

  Cross-chapter note: `google_secret_manager_secret.coffee_db_password`,
  `google_secret_manager_secret.coffee_db_system_password`, and their
  `_version` resources are defined in Ch3 `secrets.tf`. For **standalone Ch2
  verification**, pre-create both secrets manually
  (`gcloud secrets create coffee-db-password --replication-policy=automatic`,
  `gcloud secrets versions add coffee-db-password --data-file=-`, and the same
  for `coffee-db-system-password`) and temporarily point these bindings +
  `depends_on` at `data "google_secret_manager_secret"` lookups (drop the
  `_version` `depends_on` entries in that variant). The shared-root apply
  replaces them with the `resource` references. Record this in the task note; do
  not leave a permanent dual path.

  Verify: with Ch3 present (or the manual-secret + data-source variant),
  `terraform plan` resolves the references with no "undeclared resource" error.

### Phase 5 — outputs

- [ ] 5.1 Create `tools/deploy/terraform/outputs.tf`.

  ```hcl
  output "db_internal_ip" {
    value       = google_compute_address.coffee_db_ip.address
    description = "Static internal IP of the Oracle DB VM (DATABASE_HOST for Ch3)."
  }

  output "vpc_self_link" {
    value       = google_compute_network.coffee_vpc.self_link
    description = "Self-link of coffee-vpc (consumed by Ch3 Cloud Run + build pool)."
  }

  output "db_subnet_self_link" {
    value       = google_compute_subnetwork.coffee_subnet.self_link
    description = "Self-link of coffee-subnet (DB subnet)."
  }

  output "run_subnet_self_link" {
    value       = google_compute_subnetwork.coffee_run_subnet.self_link
    description = "Self-link of coffee-run-subnet (Cloud Run Direct VPC egress)."
  }

  output "db_target_tag" {
    value       = "coffee-db"
    description = "Network tag the firewall rules target."
  }

  output "db_service_account_email" {
    value       = google_service_account.coffee_db_sa.email
    description = "Email of the DB VM service account."
  }
  ```

  Verify: after apply, `terraform output db_internal_ip` prints `10.10.0.10` and
  the three self-links resolve.

### Phase 6 — live verification (private + durable)

> These run against a real project. For standalone Ch2, pre-create the
> `coffee-db-password` secret (Phase 4.4 note). Otherwise run after Ch3's
> `secrets.tf` is in the shared root.

- [ ] 6.1 Apply and confirm the appliance is private + healthy.

  ```bash
  cd tools/deploy/terraform
  terraform init && terraform apply -var="project_id=$PROJECT"

  # No external IP, correct internal IP (AC2):
  gcloud compute instances describe coffee-db --zone=us-central1-c \
    --format='value(networkInterfaces[0].networkIP, networkInterfaces[0].accessConfigs)'
  # Expect: 10.10.0.10  (and an EMPTY accessConfigs)

  # Container healthy + hooks ran (AC3/AC4):
  gcloud compute ssh coffee-db --zone=us-central1-c --tunnel-through-iap \
    --command='docker ps && docker inspect --format "{{.State.Health.Status}}" oracle-free && docker logs oracle-free 2>&1 | grep -E "Vector Memory pool|Startup script executed"'
  ```

  Verify: `docker ps` shows `oracle-free` Up; health `healthy`; logs include a
  non-zero "Vector Memory pool: … MB allocated." line.

- [ ] 6.2 Prove tcp:1521 reachability from the ALLOWED range, deny from a
  NON-allowed range, and no public path (AC5 a/b/c).

  ```bash
  # (b) ALLOWED: probe in coffee-run-subnet (10.10.1.0/24 is a source range):
  gcloud compute instances create coffee-probe-allow --zone=us-central1-c \
    --subnet=coffee-run-subnet --no-address \
    --image-family=cos-stable --image-project=cos-cloud
  gcloud compute ssh coffee-probe-allow --zone=us-central1-c --tunnel-through-iap \
    --command='timeout 5 bash -c "echo > /dev/tcp/10.10.0.10/1521 && echo OPEN_FROM_ALLOWED"'
  # Expect: OPEN_FROM_ALLOWED

  # (c) DENIED: probe in coffee-subnet (10.10.0.0/24 is intentionally NOT a
  #     source range in coffee-allow-run-to-db) — 1521 must be refused/time out:
  gcloud compute instances create coffee-probe-deny --zone=us-central1-c \
    --subnet=coffee-subnet --no-address \
    --image-family=cos-stable --image-project=cos-cloud
  gcloud compute ssh coffee-probe-deny --zone=us-central1-c --tunnel-through-iap \
    --command='timeout 5 bash -c "echo > /dev/tcp/10.10.0.10/1521 && echo UNEXPECTED_OPEN" || echo BLOCKED_FROM_DB_SUBNET'
  # Expect: BLOCKED_FROM_DB_SUBNET (the firewall scopes 1521 to run+build ranges)

  # (a) No public path: confirm the DB VM has no external IP:
  gcloud compute instances describe coffee-db --zone=us-central1-c \
    --format='value(networkInterfaces[0].accessConfigs)'   # expect EMPTY

  gcloud compute instances delete coffee-probe-allow coffee-probe-deny \
    --zone=us-central1-c --quiet
  ```

  Verify: `OPEN_FROM_ALLOWED` from the run-subnet probe; `BLOCKED_FROM_DB_SUBNET`
  from the db-subnet probe (proves firewall scoping, not just the missing public
  IP); `coffee-db` `accessConfigs` empty. Optionally
  `sqlplus app/<pwd>@10.10.0.10:1521/freepdb1` from the allowed probe (Instant
  Client) returns a row from `SELECT 1 FROM dual`.

- [ ] 6.3 Prove data durability across VM recreate (AC6) and reboot idempotency
  (AC8).

  ```bash
  # Seed a marker as the app user (from an in-VPC probe or via the DB VM toolbox):
  #   sqlplus app/<pwd>@10.10.0.10:1521/freepdb1 <<< "CREATE TABLE durable_marker(id NUMBER); INSERT INTO durable_marker VALUES (1); COMMIT;"

  # Recreate the VM, keeping the data disk:
  terraform taint google_compute_instance.coffee_db
  terraform apply -var="project_id=$PROJECT"

  # After reboot, marker survives + no duplicate container + disk not reformatted:
  gcloud compute ssh coffee-db --zone=us-central1-c --tunnel-through-iap \
    --command='docker ps -a --filter name=oracle-free --format "{{.Names}} {{.Status}}" | wc -l && docker logs oracle-free 2>&1 | grep -c "No filesystem on"'
  #   first number == 1 (exactly one container); the "No filesystem" count is 0 on a recreate (disk already formatted)
  ```

  Verify: `SELECT COUNT(*) FROM durable_marker` returns 1 after recreate; exactly
  one `oracle-free` container; cloud-init did not reformat the disk.

- [ ] 6.4 Confirm outputs (AC7).

  ```bash
  terraform output db_internal_ip db_target_tag db_service_account_email \
    vpc_self_link db_subnet_self_link run_subnet_self_link
  ```

  Verify: `db_internal_ip=10.10.0.10`, `db_target_tag=coffee-db`, the SA email,
  and three resolvable self-links.

---

## Notes for the executor

- Beads is the source of truth (backend Official). Record findings as
  `bd note <task-id> "..."`; sync markers after state changes.
- Do NOT run `coffee upgrade` / migrations here — that is Ch3 from the build pool.
- Do NOT add `:z` to the COS bind mounts.
- **Never template a password.** Both `ORACLE_PASSWORD` (SYS/SYSTEM) and the APP
  password are fetched from Secret Manager at boot (`coffee-db-system-password`
  and `coffee-db-password`). Nothing secret may appear in `user-data` or state.
- COS mounts `/var` `noexec`: keep the bring-up script under `/etc/oracle/` and
  invoke it as `['bash', '/etc/oracle/start-oracle.sh']` in `runcmd`.
- The gvenzl image has no default `HEALTHCHECK`; the `docker run` MUST pass
  `--health-cmd healthcheck.sh` or AC3's health check returns `<no value>`.
- Phase 4.4 forward-references Ch3's two secrets in the shared `secrets.tf`. If
  you implement Ch2 strictly before Ch3, use the documented manual-secret +
  data-source variant for verification, then revert to the `resource` references
  when Ch3 lands. No permanent dual path.
