# Research: Cloud Run + GCE-hosted Oracle DB + Cloud Build, on a private VPC (lab overhaul)

**Workspace**: `.agents/research/research_cloudrun_gce_lab_overhaul/`
**Status**: Complete
**Type**: Integration / Refactoring (deployment + lab architecture)
**Date**: 2026-06-23

## User Goal

Overhaul the hands-on lab into a more "real deployment" shape:

1. A **Cloud Run** service runs the Litestar webapp.
2. The **Oracle 26ai database runs on a GCE VM directly** (as a container).
3. The user runs **Cloud Build** to deploy changes (the "real deployment" loop).
4. A **private network** connects Cloud Run → GCE so the **DB is never publicly accessible**.

Framing from the user: *"this would be a lab overhaul"* and *"look at my old `cofin/spanner-mc` repo to see how cloudbuild configs were used."*

---

## Decisions (locked 2026-06-23)

These were confirmed with the user and supersede the corresponding Open Questions:

1. **Lab packaging — two separate labs.** Keep the current single-VM lab but **rename it** to signal it is the **GCE-only** path; author a **brand-new, separate lab module** for this Cloud Run + GCE-DB + Cloud Build + private-VPC architecture (it "follows" the GCE-only lab). Not a replacement, not an appended module — a distinct second lab.
2. **Migrations — Cloud Build private pool (preferred), Cloud Run Job w/ VPC egress (fallback).** Rationale (user's): a private pool lets us grant the extra DB-reaching / VPC privileges to the **Cloud Build config alone**, instead of the broadly-deployed Cloud Run service. Fall back to a Cloud Run Job with Direct VPC egress only if the private pool proves too difficult.
3. **Cloud Run → VPC — Direct VPC egress** (not the Serverless VPC connector spanner-mc used).
4. **DB VM OS — Container-Optimized OS**, with the Oracle container launched via cloud-init and a **persistent disk mounted into the container** for `/opt/oracle/oradata` durability.

---

## Executive Summary

- **Yes, a GCE VM can run a container directly — this is mature.** The single-flag command the user remembers (`gcloud compute instances create-with-container`, backed by the Container-Optimized OS "konlet" agent) **is now deprecated**. Google's current guidance is a **`cloud-init`/startup-script that runs `docker run`** on a Container-Optimized OS or Ubuntu VM. So the capability is real; the recommended mechanism has shifted to cloud-init.
- **The repo is already 80% ready.** It ships a production distroless image (`tools/deploy/docker/Dockerfile`, port 8080, Oracle Instant Client baked in) and settings already support a remote DB via `DATABASE_HOST/PORT/SERVICE_NAME/DSN` (`src/app/lib/settings.py:79-162`). No app code rewrite is required to point Cloud Run at a remote Oracle host.
- **spanner-mc is a near-exact template for steps 1+3.** `deploy/gcp/cloudbuild.deploy.yml` does: build → tag → push to Artifact Registry → **run `database upgrade`** → `gcloud run deploy ... --vpc-connector`. The overhaul reuses this pipeline almost verbatim, swapping `spannermc database upgrade` → `coffee upgrade` and the connector for the chosen VPC method.
- **The one genuinely hard part is the migration step against a *private* DB.** spanner-mc's migration step ran on the **default** Cloud Build pool, which works only because Spanner is a public Google-API endpoint. An Oracle DB on a **private internal IP is unreachable from default Cloud Build workers.** This forces a design choice: Cloud Build **private pool**, a **Cloud Run Job** with VPC egress, or running migrations **from the VM**. (See Risks + Recommended Approach.)
- **Private connectivity has a clear modern default: Direct VPC egress.** spanner-mc used a Serverless VPC Access **connector** (2023-era). For new work Google recommends **Direct VPC egress** — no connector VMs, lower latency, cheaper (egress only). The DB VM runs with `--no-address` + a static internal IP; a firewall rule allows `tcp:1521` only from the Cloud Run egress range.
- **Biggest non-technical risk: lab simplicity.** The current lab is a beginner-friendly ~7-step, single-VM flow (`docs/lab.md`). This overhaul adds Artifact Registry, Cloud Build, a VPC + egress config, a separate always-on DB VM with a persistent disk, and 2–3 service accounts. It is meaningfully more production-shaped — and meaningfully more failure surface for a "no GCP knowledge" audience. Recommend treating it as an **advanced / "Module 2" lab** rather than a replacement.

---

## Research Tasks Summary

| Task | Status | Key Findings |
|------|--------|--------------|
| Codebase: current deploy/infra inventory | Complete | Distroless image (8080), gvenzl Oracle local orchestration, settings already remote-DB-capable, single-VM lab |
| Platform: can GCE run a container directly | Complete | Yes; `create-with-container` deprecated → use cloud-init/startup `docker run`; COS can mount a persistent disk into a container |
| Platform: Cloud Run → VPC private DB | Complete | Direct VPC egress (recommended) vs Serverless VPC connector (spanner-mc used); both reach internal IPs |
| Platform: Cloud Build → private DB migrations | Complete | Default pool can't reach private IPs; need private pool, Cloud Run Job w/ VPC, or VM-side migrations |
| Prior art: spanner-mc cloudbuild | Complete | build→push→migrate→`run deploy --vpc-connector` is a reusable template |
| Risk assessment | Complete | Migration path, DB durability/Spot, lab complexity, cost, secrets, internal-IP stability |

---

## Codebase Analysis

### Key locations

| File | Lines | Purpose |
|------|-------|---------|
| `tools/deploy/docker/Dockerfile` | 1–92 | Production distroless image; PyApp `coffee` binary; `EXPOSE 8080`; `CMD ["run","--host","0.0.0.0","--port","8080"]` |
| `tools/oracle/database.py` | 34–86, 415–474 | Local Oracle orchestration: `gvenzl/oracle-free:latest`, `1521`, `freepdb1`, app user, `oracle-db-data` volume, entrypoint hooks |
| `tools/oracle/container.py` | 34–73 | Docker/Podman runtime auto-detection |
| `src/app/lib/settings.py` | 79–162 | `DatabaseSettings`: `DATABASE_HOST/PORT/SERVICE_NAME/DSN/USER/PASSWORD`, pool sizes, ADB wallet mode (`is_autonomous`) |
| `src/app/lib/settings.py` | 163–235 | SQLSpec `OracleAsyncConfig` build (local DSN vs ADB wallet) |
| `src/app/lib/settings.py` | 325–358 | Vertex AI: `VERTEX_AI_PROJECT_ID`, `VERTEX_AI_LOCATION` (default `us-central1`) |
| `src/app/cli/commands.py` | 69–86 | `coffee run` wraps `litestar_granian` run; `coffee upgrade` applies migrations + fixtures |
| `docs/lab.md` | 1–263 | Current single-VM IAP lab |
| `.github/workflows/release.yml` | ~130–143 | Existing container build (GitHub releases only — no Artifact Registry push) |

### Current deployment shape (what we are overhauling)

`docs/lab.md` provisions **one** `e2-standard-4` Ubuntu **Spot** VM (`--no-address`, IAP SSH, Cloud Router + NAT for egress). Both the **Oracle container and the webapp run on that single VM**. The user reaches the UI through `gcloud compute ssh ... -- -L8080:localhost:5006` and Cloud Shell **Web Preview**. There is **no Cloud Run, no Cloud Build, no Artifact Registry, and no app↔DB network isolation** (they share `localhost` on one box).

### What the app already supports (low-friction wins)

- **Remote DB is a config flip, not a code change.** `DATABASE_HOST/PORT/SERVICE_NAME` (or full `DATABASE_DSN`) already drive the connection (`settings.py:90-115`). Cloud Run just sets `DATABASE_HOST=<VM internal IP>`.
- **The image is Cloud Run-ready.** Distroless, single binary, listens on `0.0.0.0:8080`. Cloud Run sets `PORT=8080` by default, which matches; honoring `$PORT` explicitly is a nice-to-have (see Open Questions).
- **Oracle Instant Client is already in the image** (`Dockerfile:31-32`, `LD_LIBRARY_PATH=/opt/oracle/instantclient`), so the Cloud Run service can speak Oracle thick/thin to a remote host with no extra layers.

### Constraints discovered

- `coffee upgrade` does **both** migrations **and** fixture/embedding load — important for whoever runs it (it needs DB reachability *and* Vertex access for `bulk-embed`-style steps if invoked).
- The DB container relies on **entrypoint hooks** (`tools/oracle/on_init`, `on_startup`) mounted into `/container-entrypoint-initdb.d` and `/container-entrypoint-startdb.d`. A plain `docker run` on the VM must reproduce those mounts (or bake them in) to get the same APP user / grants bootstrap.

---

## Platform Documentation

### A. Running a container directly on a GCE VM (user's core question)

- **Supported, mature — but the one-flag path is deprecated.** `gcloud compute instances create-with-container` and the COS container-startup agent are **deprecated**; Google recommends **`docker run` in a startup script or a `cloud-init` cloud-config** on the VM metadata. ([Deploying containers on instances](https://cloud.google.com/compute/docs/containers/deploying-containers), [create-with-container reference](https://cloud.google.com/sdk/gcloud/reference/compute/instances/create-with-container))
- **Container-Optimized OS (COS)** ships Docker + a minimal, auto-updating OS; it can **mount a persistent disk into the container** (COS 69+, ext4 or empty disk) — the clean way to give Oracle durable storage. ([COS create/configure](https://cloud.google.com/container-optimized-os/docs/how-to/create-configure-instance), [run-container-instance](https://cloud.google.com/container-optimized-os/docs/how-to/run-container-instance))
- **Gotcha:** on COS, cloud-init `write_files`/`runcmd` run **on every boot**, not once — write idempotent startup logic.
- **Terraform option** exists if we want IaC: `terraform-google-modules/terraform-google-container-vm`.

### B. Cloud Run → VPC (private DB connectivity) — requirement #4

Two mechanisms, both reach an internal-IP VM ([Compare Direct VPC egress and connectors](https://docs.cloud.google.com/run/docs/configuring/connecting-vpc)):

| | **Direct VPC egress** (recommended) | **Serverless VPC Access connector** (spanner-mc used) |
|---|---|---|
| Cost | Egress only; **no connector VMs** | Pay for connector VMs **+** egress |
| Latency | Fewer hops, higher throughput | Extra proxy hop |
| Cold start | Connection setup can lag ~1 min on instance start; with Cloud NAT, 30s+ cold starts | With NAT, better startup behavior |
| Setup | Assign a subnet/range to the service | Create/maintain a connector resource |

Sources: [Direct VPC announcement](https://cloud.google.com/blog/products/serverless/announcing-direct-vpc-egress-for-cloud-run), [Direct VPC docs](https://docs.cloud.google.com/run/docs/configuring/vpc-direct-vpc), [VPC connectors docs](https://docs.cloud.google.com/run/docs/configuring/vpc-connectors).

**Recommendation:** Direct VPC egress for a fresh lab (cheaper, fewer moving parts). Keep the connector noted as the known-good fallback (and required for some Shared-VPC topologies).

### C. Cloud Build reaching a private DB (the migration step) — the subtle part

- **Default Cloud Build workers are not on your VPC** and cannot reach private internal IPs. ([Cloud Build in a private network](https://cloud.google.com/build/docs/private-pools/use-in-private-network))
- **Cloud Build private pools** are peered to your VPC and **can** reach private IPs (set `egressOption: NO_PUBLIC_EGRESS` to drop public egress). ([set-up private pool in VPC](https://docs.cloud.google.com/build/docs/private-pools/set-up-private-pool-to-use-in-vpc-network), [private pool Terraform module](https://registry.terraform.io/modules/GoogleCloudPlatform/secure-cicd/google/latest/submodules/cloudbuild-private-pool))
- **Cloud Run Jobs with Direct VPC** can egress to the VPC and run the migration using the *same image and same network path* as the service — often the most elegant fit. ([Direct VPC with a VPC network](https://docs.cloud.google.com/run/docs/configuring/vpc-direct-vpc))

---

## Prior Art

### Internal — `cofin/spanner-mc` (`deploy/gcp/cloudbuild.deploy.yml`)

The canonical pipeline (reusable almost verbatim):

```yaml
steps:
  - docker build -t $REGION-docker.pkg.dev/$PROJECT/.../$SERVICE:$BRANCH-$SHA --file deploy/docker/run/Dockerfile .
  - docker tag ... :latest
  - docker push  ...:$BRANCH-$SHA
  - docker push  ...:latest
  - # exec-wrapper runs the image to apply migrations:
    gcr.io/google-appengine/exec-wrapper -i ...:$BRANCH-$SHA -- spannermc database upgrade
  - gcloud beta run deploy $SERVICE --image ...:$BRANCH-$SHA --region $REGION \
      --service-account $SA --port 8000 --execution-environment gen2 \
      --no-cpu-throttling --vpc-connector projects/$PROJECT/locations/$REGION/connectors/$VPC
```

**What maps directly:** build/tag/push to Artifact Registry, the deploy step, `--service-account`, `--vpc-connector` (→ Direct VPC egress flags), substitution variables.
**What must change:** `spannermc database upgrade` → `coffee upgrade`; `--port 8000` → `8080`; **the migration step's network** (Spanner = public API; Oracle = private IP → see Recommended Approach); Dockerfile path → `tools/deploy/docker/Dockerfile`.

### Internal — current lab (`docs/lab.md`)

Establishes the lab's house style: `gcloud` imperative commands in Cloud Shell, IAP for SSH, Cloud Router + NAT for VM egress, Spot VM, Vertex IAM granted to the VM's default SA. The overhaul should **reuse these primitives** (IAP, NAT, the `aiplatform.user` grant — now applied to the **Cloud Run** SA instead of the VM).

### External patterns

- "Cloud Build with Compute Engine" continuous-delivery write-ups confirm build→deploy-to-VM patterns exist, but the cleaner split here is **Cloud Build → Cloud Run** (app) with the **VM as a stateful DB appliance**.

---

## Target Architecture (proposed)

```
                ┌─────────────────────────── VPC (private) ───────────────────────────┐
   Internet     │                                                                       │
   ───▶ Cloud Run service "coffee"   ──Direct VPC egress──▶   GCE VM "coffee-db"        │
        (webapp, :8080, scales to 0)        (tcp:1521)        Oracle 26ai container      │
          │  env: DATABASE_HOST=<VM static internal IP>        gvenzl/oracle-free        │
          │  Secret Manager: DB pwd, Vertex cfg                no external IP (--no-address)
          │  SA: roles/aiplatform.user                         static internal IP        │
          │                                                    persistent data disk      │
          ▼                                                    /opt/oracle/oradata        │
     Vertex AI (public Google API)        Cloud NAT ◀── VM egress (pull image) ──────────┘
                                          IAP ◀── admin SSH to VM
   Deploy loop:
     git push ─▶ Cloud Build: build ▶ Artifact Registry ▶ migrate ▶ gcloud run deploy
```

Firewall: ingress `tcp:1521` allowed **only** from the Cloud Run egress subnet/range (+ IAP `tcp:22` for admin). VM has **no public IP**; DB is unreachable from the internet by construction.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Migration step can't reach the private DB** (default Cloud Build pool has no VPC route) | High | High | Pick one: (a) **Cloud Run Job w/ Direct VPC** running `coffee upgrade` — same image+network as the service (recommended); (b) Cloud Build **private pool** peered to VPC; (c) run `coffee upgrade` **from the VM** via SSH/startup hook. Do **not** copy spanner-mc's default-pool migration step blindly. |
| **DB data loss on a Spot/preemptible VM** (current lab uses `--provisioning-model=SPOT`) | High | High | Use a **standard (non-Spot)** DB VM, or mount a **separate persistent disk** for `/opt/oracle/oradata` that survives VM recreation. Spot is fine for stateless app, dangerous for the only DB copy. |
| **Lab complexity explodes for a "no GCP knowledge" audience** | High | Med | Ship as **"Module 2 / advanced"** alongside the simple single-VM lab; provide a **one-shot bootstrap script** (or Terraform) so learners run ~3 commands, then *read* the pipeline rather than hand-typing every resource. |
| **Always-on DB VM cost** (Cloud Run scales to zero, the VM does not) | Med | Med | Right-size the DB VM (e2-standard-2/4); document teardown; consider stop-when-idle for lab accounts; note credits burn faster than the single-Spot-VM lab. |
| **Internal IP instability** (ephemeral internal IP changes on VM recreate, breaking Cloud Run env) | Med | Med | **Reserve a static internal IP** for the DB VM, or publish a **Cloud DNS private** record (e.g. `db.coffee.internal`) and point `DATABASE_HOST` at the name. |
| **Secret sprawl** (DB password / Vertex cfg currently `.env`) | Med | Med | Move DB password to **Secret Manager**, inject into Cloud Run (`--set-secrets`) and into Cloud Build's migration step; grant the Cloud Run SA `secretmanager.secretAccessor`. |
| **Vertex IAM moves** from VM SA → Cloud Run SA | Low | Med | Grant `roles/aiplatform.user` to the **Cloud Run** service account (the app now runs there, not on the VM). The VM no longer needs Vertex access. |
| **DB bootstrap hooks not reproduced** on the VM `docker run` | Med | Med | Bake the `tools/oracle/on_init` / `on_startup` SQL into the image, or mount them in the cloud-init `docker run` exactly as `tools/oracle/database.py:461-471` does. |
| **`coffee upgrade` also loads fixtures/embeddings** (needs Vertex + time) | Low | Med | Decide whether the deploy-time migration runs schema-only vs full seed; long seeds can exceed Cloud Build/Job timeouts. Split `migrate` from `seed` if needed. |

### Recovery strategy

- **Rollback (app):** Cloud Run keeps revisions — `gcloud run services update-traffic --to-revisions=PREV=100`. Images are immutable per `$SHA` tag.
- **Rollback (DB schema):** keep `python manage.py database downgrade` runnable via the same Job/VM path; persistent disk allows VM re-create without data loss.
- **Checkpoints:** (1) DB VM up + reachable on private IP; (2) Cloud Run hello reachable; (3) Cloud Run → DB connectivity proven; (4) Cloud Build green end-to-end. Validate each before the next.

---

## Recommended Approach

**Phase the overhaul; reuse what exists; isolate the one hard decision (migrations).**

1. **Network first.** Reserve a **static internal IP**; keep IAP + Cloud Router/NAT from the current lab. Firewall: `tcp:1521` from the Cloud Run egress range only.
2. **DB VM as a stateful appliance.** Standard (non-Spot) VM, `--no-address`, **separate persistent disk** mounted to `/opt/oracle/oradata`. Run `gvenzl/oracle-free` via **cloud-init `docker run`** (not the deprecated `create-with-container`), reproducing the `on_init`/`on_startup` hook mounts. (COS + persistent-disk mount is the tidy option; Ubuntu+Docker is closest to today's lab and most teachable.)
3. **App on Cloud Run via Cloud Build**, adapted from spanner-mc: build → Artifact Registry → **migrate** → `gcloud run deploy` with **Direct VPC egress**, `--port 8080`, `--service-account`, DB host/secret env. Grant the Cloud Run SA `aiplatform.user` + `secretmanager.secretAccessor`.
4. **Migrations (locked):** run `coffee upgrade` from a **Cloud Build private pool** peered to the VPC, so the extra DB-reaching/VPC privileges are scoped to the Cloud Build config rather than the deployed service. **Fallback:** a **Cloud Run Job with Direct VPC egress** (same image, same private path) if the private pool proves too fiddly for the lab.
5. **Secrets** to Secret Manager; **`DATABASE_HOST`** = the static internal IP (or a private DNS name).
6. **Lab packaging:** position as **advanced "Module 2"** beside the simple lab; provide a bootstrap script so learners spend their time *understanding* the architecture, not debugging 30 `gcloud` lines.

**Why this over alternatives:** It changes **zero application code** (settings already support remote DB), reuses the user's proven spanner-mc pipeline, adopts the *current* Google-recommended primitives (cloud-init, Direct VPC egress) instead of the deprecated ones, and confines the only genuinely novel problem (private-DB migrations) to a single, swappable step.

---

## Open Questions (for PRD / decisions)

> Resolved at research time and recorded in **Decisions (locked)** above: lab packaging (two separate labs, old one renamed), migration home (Cloud Build private pool → Cloud Run Job fallback), VPC method (Direct VPC egress), DB VM OS (Container-Optimized OS). Remaining:

1. **Old lab's new name/title.** What do we rename the current single-VM lab to (e.g. `docs/lab-gce.md` / "Cymbal Coffee on a single GCE VM") so the new Cloud Run lab can clearly "follow" it? New lab filename too (e.g. `docs/lab-cloudrun.md`).
2. **Migrate vs seed at deploy:** schema-only at deploy, with the (slow, Vertex-dependent) fixture/embedding seed run as a separate one-time step? (`coffee upgrade` does both today.)
3. **IaC:** imperative `gcloud` (current lab house style) vs **Terraform** for the new module (reproducible, but another tool for a beginner audience)?
4. **`$PORT` handling:** make the container honor Cloud Run's `$PORT` env instead of the hardcoded `--port 8080` in the Dockerfile CMD? (Defaults align today, but explicit is safer.)
5. **DB durability bar for a lab:** is the persistent disk enough, or do we want scheduled `expdp`/RMAN-to-GCS? (Likely persistent disk only for a lab.)
6. **Cloud Build trigger:** GitHub-push trigger vs manual `gcloud builds submit` for the "user runs Cloud Build to deploy changes" step.

---

## Research Outputs

**This research informs:**
- PRD: `.agents/specs/{prd_id}/prd.md` (when created)
- Flow: `.agents/specs/{flow_id}/` (when created)

**Primary sources**
- [Deploying containers on instances and MIGs](https://cloud.google.com/compute/docs/containers/deploying-containers) · [create-with-container (deprecated)](https://cloud.google.com/sdk/gcloud/reference/compute/instances/create-with-container) · [COS create/configure](https://cloud.google.com/container-optimized-os/docs/how-to/create-configure-instance) · [COS run container](https://cloud.google.com/container-optimized-os/docs/how-to/run-container-instance)
- [Compare Direct VPC egress vs connectors](https://docs.cloud.google.com/run/docs/configuring/connecting-vpc) · [Direct VPC with a VPC network](https://docs.cloud.google.com/run/docs/configuring/vpc-direct-vpc) · [Direct VPC egress announcement](https://cloud.google.com/blog/products/serverless/announcing-direct-vpc-egress-for-cloud-run) · [VPC connectors](https://docs.cloud.google.com/run/docs/configuring/vpc-connectors)
- [Cloud Build in a private network](https://cloud.google.com/build/docs/private-pools/use-in-private-network) · [Set up private pool in VPC](https://docs.cloud.google.com/build/docs/private-pools/set-up-private-pool-to-use-in-vpc-network) · [Private pool Terraform module](https://registry.terraform.io/modules/GoogleCloudPlatform/secure-cicd/google/latest/submodules/cloudbuild-private-pool)
- Internal: `cofin/spanner-mc` `deploy/gcp/cloudbuild.deploy.yml`; this repo `tools/deploy/docker/Dockerfile`, `tools/oracle/database.py`, `src/app/lib/settings.py`, `docs/lab.md`
