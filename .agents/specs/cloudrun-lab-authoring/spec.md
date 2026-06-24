# Flow: cloudrun-lab-authoring

> Parent PRD: `cloudrun-gce-lab` (`.agents/specs/cloudrun-gce-lab/prd.md`)
> Beads epic: `oracledb-vertexai-jw0.5`
> Type: docs · Status: planned
> Depends on: Ch2 `gce-oracle-appliance` (`jw0.2`), Ch3 `cloudbuild-cloudrun-pipeline` (`jw0.3`), Ch4 `lab-gce-rename` (`jw0.4`)
> Owns: the **body** of `docs/lab-cloud-run.md` (the full end-to-end walkthrough + challenges).
> Does NOT own: the `{toctree}` entry or the file's existence (Ch4), nor the
> `## Verify your deployment` / `## Clean up & costs` section bodies (Ch6).

## Specification

### Context

The PRD ships a **second, separate** hands-on lab beside the existing single-VM
lab. Where `docs/lab.md` (which Ch4 renames to `docs/lab-gce.md`) co-locates the
Oracle container and the webapp on one Spot VM reached over an IAP SSH tunnel +
Cloud Shell Web Preview, this new lab deploys Cymbal Coffee as the
**production-shaped** architecture:

- The **Litestar webapp runs on Cloud Run** (`coffee-app`, scales to zero, public HTTPS, port 8080).
- The **Oracle 26ai database runs on a Container-Optimized OS GCE VM** (`coffee-db`),
  launched by cloud-init with a persistent disk and **no external IP**, reachable
  only on its static internal IP `10.10.0.10:1521/freepdb1`.
- A **Cloud Build pipeline** (`tools/deploy/gcp/cloudbuild.yaml`) does
  build → push → `coffee upgrade` (migrate + committed-embedding fixtures) → `gcloud run deploy`,
  triggered manually with `gcloud builds submit`.
- A **private VPC** (`coffee-vpc`) with **Direct VPC egress** lets Cloud Run reach
  the DB on its internal IP; the DB is never reachable from the public internet.
- All infrastructure is **Terraform** under `tools/deploy/terraform/`; the lab
  teaches `terraform apply` to stand the stack up, then explains how each module is wired.

This chapter is **documentation-only (Sphinx/MyST)**. It writes the prose and the
paste-ready shell commands for `docs/lab-cloud-run.md`. It modifies **no source,
no Terraform, no cloudbuild config** — those artifacts are authored by Ch2/Ch3 and
are referenced by path. Every resource name, CIDR, env var, IAM role, image path,
and command embedded in the lab is governed by the PRD **Architecture Contract**
(`.agents/specs/cloudrun-gce-lab/prd.md:89-148`), which is LAW.

### Dependency & ownership boundaries (binding)

- **Ch4 (`lab-gce-rename`) creates the file and the toctree entry.** Ch4 renames
  `docs/lab.md`→`docs/lab-gce.md`, turns `docs/lab.md` into a "choose your path"
  index, registers `lab-cloud-run` in the `:caption: Lab` `{toctree}`, and writes a
  **minimal stub** `docs/lab-cloud-run.md` so `sphinx-build -W --keep-going` stays
  green. **This chapter REPLACES that stub body** with the full walkthrough. This
  chapter does **not** edit any `{toctree}` and does **not** create the file from
  scratch — it overwrites the stub's content. (If, at implementation time, the stub
  does not yet exist because Ch4 has not landed, that is a blocked-dependency
  condition: Ch4 must land first; do not invent the toctree entry here.)
- **Ch6 (`cloudrun-lab-verification-teardown`) owns the verification, troubleshooting,
  cost, and teardown content.** This chapter leaves exactly two placeholder headers,
  last and in this order, with empty bodies: `## Verify your deployment` then
  `## Clean up & costs`. Do not author any verification/troubleshooting/cost/`terraform
  destroy` prose here.
- **Ch2/Ch3 own the referenced artifacts.** `tools/deploy/terraform/` (VPC, COS DB VM,
  cloud-init, Artifact Registry, build pool, Cloud Run, IAM, secret) and
  `tools/deploy/gcp/cloudbuild.yaml` are authored there. This chapter references them by
  the exact contract paths and must **reconcile** the `terraform.tfvars` variable names
  and the `gcloud builds submit --substitutions` keys against the authored files
  (see Q3/Q4 resolutions below). Locked at planning time:
  - `terraform.tfvars` keys = `project_id`, `region`, `db_password` (Ch3 `variables.tf`).
  - Deploy command =
    `gcloud builds submit --config ../gcp/cloudbuild.yaml --substitutions=_REGION=us-central1 --worker-pool=projects/$PROJECT_ID/locations/$REGION/workerPools/coffee-build-pool`
    (run from `tools/deploy/terraform/`); substitution keys must match
    `tools/deploy/gcp/cloudbuild.yaml`.

### House-style analysis (`docs/lab.md` — these are LAW for voice)

The new lab must read as a **sibling** of `docs/lab.md`. Observed conventions (with
line references) that the worksheet reproduces:

- **Title**: H1 sentence-style with the Cymbal Coffee + Oracle/Vertex framing
  (`docs/lab.md:1`: `# Hands-on Lab: Cymbal Coffee — Oracle 26ai + Vertex AI ...`).
  `docs/index.md:1` confirms sentence-style H1s. Note the literal `\+` escape used in
  the existing title is a MyST artifact; the new title uses a plain `+`.
- **Intro paragraph** linking the docs site + naming the stack
  (`docs/lab.md:3-5`).
- **`## Prerequisites & Audience Expectations`** bullet block with **GCP Knowledge**
  / **Tools Required** (`docs/lab.md:9-13`). The new lab adjusts audience to
  "comfortable with the GCE-only lab" and adds a "billing enabled" note.
- **Numbered `## Step N: <Title>`** sections, each opening with a one-sentence "in
  this step you will…" framing, then **numbered sub-steps** with paste-ready fenced
  ```` ```shell ```` blocks (`docs/lab.md:16-48` Step 1 is the template for Step 1
  of the new lab).
- **Step 1 idioms to mirror exactly** (`docs/lab.md:20-48`): "Activate Cloud Shell",
  `gcloud config set project [YOUR-PROJECT-ID]`, then
  `export REGION=us-central1` / `export ZONE=us-central1-c` /
  `export PROJECT_ID=$(gcloud config get-value project)` /
  `gcloud config set compute/region $REGION` / `gcloud config set compute/zone $ZONE`,
  then a `gcloud services enable ...` block (line-continued with `\`).
- **API-enable block style**: one `gcloud services enable` with backslash line
  continuation, one API per line (`docs/lab.md:43-48`).
- **Callouts**: blockquote `> **Note:** …` (`docs/lab.md:435`), **not** MyST
  `{note}` admonitions. The new lab uses `> **Note:**` for every aside (why the DB is
  private, why `terraform.tfvars` is gitignored, why no Vertex at build time).
- **`---` horizontal rules** between top-level steps (`docs/lab.md:50, 91, 124, ...`).
- **Advanced challenges**: a final `## Advanced Challenge Tasks for Workshop Graduates`
  section (`docs/lab.md:267-269`) containing `### Challenge N: <Title>` blocks, each
  with an **Objective** line and `* **Step A:** … ` / `* **Step B:** …` substructure
  carrying paste-ready fenced blocks (`docs/lab.md:271-441`). The new lab reproduces
  this exact shape for its three challenges.
- **Code-fence languages**: `shell` for commands, `` ``` `` (plain) for `.env`/file
  snippets, `hcl`/`yaml` for IaC excerpts when shown (the lab shows commands, not full
  IaC files — those live in `tools/deploy/`).

### Requirements

**Functional (FR)**

- FR1. `docs/lab-cloud-run.md` body presents the eight-part story as numbered
  `## Step N` sections in this order: (1) Cloud Shell + project/region/zone;
  (2) Enable APIs; (3) Clone repo + `cd tools/deploy/terraform`; (4) Create
  `terraform.tfvars`; (5) `terraform init && terraform apply` (+ what/why explanation);
  (6) Deploy via `gcloud builds submit`; (7) Get the Cloud Run URL, open it, send a
  chat query, confirm a grounded recommendation; (8) `## Advanced Challenge Tasks …`
  with three challenges.
- FR2. Every embedded resource name/path/value matches the PRD Architecture Contract
  verbatim: VPC `coffee-vpc`; subnets `coffee-subnet` (`10.10.0.0/24`),
  `coffee-run-subnet` (`10.10.1.0/24`); build-pool range `coffee-buildpool-range`
  (`10.30.0.0/24`); DB IP `coffee-db-ip` = `10.10.0.10`; DB VM `coffee-db`;
  PDB `freepdb1`; app user `app`; Cloud Run service `coffee-app`;
  Artifact Registry `coffee-artifacts`; image
  `us-central1-docker.pkg.dev/$PROJECT_ID/coffee-artifacts/coffee-app`;
  private pool `coffee-build-pool`; secret `coffee-db-password`; Terraform root
  `tools/deploy/terraform/`; cloudbuild `tools/deploy/gcp/cloudbuild.yaml`;
  region `us-central1`; zone `us-central1-c`.
- FR3. The API-enable step enables exactly the services the lab needs:
  `compute`, `run`, `cloudbuild`, `artifactregistry`, `secretmanager`, `aiplatform`,
  `servicenetworking`, `iap`, `osconfig`, and `maps-backend` (`.googleapis.com`).
- FR4. Step 4 instructs the learner to create `terraform.tfvars` with keys
  `project_id`, `region`, `db_password`, and carries a `> **Note:**` that the file is
  **gitignored** (lab-only secret hygiene) and should never be committed.
- FR5. Step 5 runs `terraform init && terraform apply`, then briefly explains, per
  Terraform module/resource, **what** was created and **why the DB is private**
  (no external IP, Direct VPC egress, firewall allows tcp:1521 only from the run +
  build-pool ranges).
- FR6. Step 6 is exactly:
  `gcloud builds submit --config ../gcp/cloudbuild.yaml --substitutions=_REGION=us-central1 --worker-pool=projects/$PROJECT_ID/locations/$REGION/workerPools/coffee-build-pool`
  (run from `tools/deploy/terraform/`), followed by an explanation that the migration
  (`coffee upgrade`) runs **from the private pool** because the pool is peered to
  `coffee-vpc` and can reach `10.10.0.10`, and that **committed-embedding fixtures mean
  no Vertex is needed at build time**. Includes a one-line reconcile note pointing at
  `tools/deploy/gcp/cloudbuild.yaml` for the authoritative substitution keys.
- FR7. Step 7 retrieves the URL with
  `gcloud run services describe coffee-app --region=$REGION --format='value(status.url)'`,
  has the learner open it, send a chat query (e.g. *"I need something bold"*), and
  confirm a grounded coffee recommendation — explicitly framed as proof that the
  **public Cloud Run webapp reached the PRIVATE Oracle DB and Vertex AI**.
- FR8. Step 8 authors three `### Challenge N` blocks in the existing lab's challenge
  format: (1) GitHub push → Cloud Build trigger (real CI/CD); (2) swap the static
  internal IP for a Cloud DNS private name; (3) move Terraform state to a GCS backend.
- FR9. The body ends with exactly two placeholder section headers, last and in this
  order, with empty bodies: `## Verify your deployment` then `## Clean up & costs`
  (Ch6 fills them).

**Non-functional / constraints (NFR)**

- NFR1 (voice). Reads as a sibling of `docs/lab.md`: numbered steps, `shell` fences,
  `> **Note:**` callouts, `---` rules, the `## Advanced Challenge Tasks …` format.
- NFR2 (no source/IaC edits). This chapter writes **only** `docs/lab-cloud-run.md`.
  No edits to `tools/deploy/**`, `src/**`, `docs/conf.py`, any `{toctree}`, or `.env`.
- NFR3 (Sphinx `-W` clean). The body must build clean under
  `sphinx-build -W --keep-going` (patterns.md docs gate): valid MyST, no broken
  intra-doc anchors, no orphaned-doc warning (the toctree entry is Ch4's, already
  present per the dependency). Heading depth ≤ 3 (matches `myst_heading_anchors = 3`).
- NFR4 (Ch6 boundary). No verification/troubleshooting/cost/teardown prose — only the
  two empty placeholder headers.
- NFR5 (privacy). The lab does not introduce browser-geolocation persistence and keeps
  no-key Maps behavior intact (PRD Global Constraint #5); `maps-backend` is enabled
  only because the app's Maps URL features may be exercised, not to persist coordinates.
- NFR6 (contract drift guard). Where a value is owned by Ch2/Ch3 artifacts
  (`terraform.tfvars` keys, `--substitutions` keys), the doc carries a one-line
  reconcile note rather than silently hardcoding a guess.

### Acceptance criteria

- AC1. `docs/lab-cloud-run.md` contains all eight `## Step`/challenge sections in the
  FR1 order, each with paste-ready `shell` blocks.
- AC2. Every name/CIDR/path/image/secret/IAM value in the doc matches the PRD
  Architecture Contract (FR2) — a reviewer diffing the doc's literals against
  `prd.md:89-148` finds zero mismatches.
- AC3. Step 6's command string equals FR6 verbatim; Step 7's describe command equals
  FR7 verbatim.
- AC4. The doc ends with `## Verify your deployment` immediately followed by
  `## Clean up & costs`, both with empty bodies, and they are the **last two**
  headers in the file.
- AC5. `make docs` (i.e. `sphinx-build -W --keep-going`) builds with no new warnings
  or errors attributable to `lab-cloud-run.md`.
- AC6. House-style check: the doc uses `> **Note:**` blockquotes (not `{note}`),
  `## Step N:` numbered headers, and a `## Advanced Challenge Tasks for Workshop
  Graduates` section with `### Challenge N:` blocks — matching `docs/lab.md`.
- AC7. A reviewer with a fresh GCP project can follow Steps 1→7 end-to-end and reach a
  grounded chat recommendation (manual/judgment acceptance; the commands are
  copy-paste runnable given Ch2/Ch3 artifacts exist).
- AC8. `git diff --stat` after implementation lists only `docs/lab-cloud-run.md`
  (no `tools/**`, `src/**`, `docs/conf.py`, other `docs/*.md`, or `.env`).

---

## Implementation Plan

> Docs-only, no TDD code cycle. "Verification" for each phase = the paste-ready
> command block is contract-accurate and the section renders under `sphinx-build -W`.
> The worksheet below **is** the section-by-section outline of `docs/lab-cloud-run.md`
> with the exact text/commands to embed. Author top-to-bottom; the file is a single
> overwrite of Ch4's stub.

### Phase 0: Pre-flight (dependency + contract confirmation)

- [ ] **0.1 Confirm dependencies landed and the stub exists.**
  - Confirm Ch4 landed: `docs/lab-cloud-run.md` exists as a stub and is registered in
    the `:caption: Lab` `{toctree}` (in `docs/lab.md` or whatever index Ch4 produced).
    Command: `ls docs/lab-cloud-run.md && grep -rn "lab-cloud-run" docs/*.md`.
  - Confirm Ch2/Ch3 artifact paths exist (so referenced commands are real):
    `ls tools/deploy/terraform/ tools/deploy/gcp/cloudbuild.yaml`.
  - Read `tools/deploy/terraform/variables.tf` and confirm the variable names are
    `project_id`, `region`, `db_password`; read `tools/deploy/gcp/cloudbuild.yaml` and
    confirm the substitution key(s) (expecting `_REGION`). If either differs from the
    locked values, **update the doc's literals to match the authored artifacts** (the
    artifacts win; the doc reconciles).
  - If the stub or artifacts are absent: STOP — this is a blocked dependency
    (Ch2/Ch3/Ch4 must land first). Do not fabricate the toctree or the artifacts.

### Phase 1: Title, intro, prerequisites

- [ ] **1.1 Write the H1 title + intro paragraph.**
  - Replace the entire stub body. Begin with an H1 sentence-style title that signals
    the production-shaped path and names the cloud services, e.g.:
    `# Hands-on Lab: Cymbal Coffee on Cloud Run — Private Oracle 26ai DB + Cloud Build`.
  - One intro paragraph (mirroring `docs/lab.md:3-5`): explain this lab deploys the
    same app as the GCE-only lab but as a **real GCP architecture** — Cloud Run webapp
    + private GCE Oracle DB + Cloud Build, all via Terraform — and link the docs site
    (`https://cofin.github.io/oracledb-vertexai-demo/index.html`). One sentence noting
    it "follows" the GCE-only lab (`lab-gce`).
  - Add a `> **Note:**` that this is the advanced "Module 2" path; the simpler
    single-VM lab is `lab-gce` (link via MyST doc ref or plain text).
  - Then a `---` rule.

- [ ] **1.2 Write `## Prerequisites & Audience Expectations`.**
  - Mirror `docs/lab.md:9-13` bullet shape:
    - **GCP Knowledge**: comfortable with the GCE-only lab; this one adds Cloud Run,
      Cloud Build, Artifact Registry, a private VPC, and Terraform.
    - **Tools Required**: a browser + a Google Cloud project with **billing/credits
      enabled** (this lab provisions an always-on DB VM — see `## Clean up & costs`).
    - **Cost note** as a `> **Note:**`: the DB VM does not scale to zero; tear the
      stack down when finished (forward-reference `## Clean up & costs`, Ch6).
  - End with a `---` rule.
  - Verification: bullets render; the cost note is a blockquote.

### Phase 2: Step 1 — Cloud Shell, project, region/zone

- [ ] **2.1 Write `## Step 1: Google Cloud Environment Setup`.**
  - Mirror `docs/lab.md:16-38`. One-sentence framing, then numbered sub-steps:
    1. Activate Cloud Shell (terminal icon `>_`).
    2. Set the project (paste-ready):

       ```shell
       gcloud config set project [YOUR-PROJECT-ID]
       ```

    3. Export region/zone/project and set gcloud defaults:

       ```shell
       export REGION=us-central1
       export ZONE=us-central1-c
       export PROJECT_ID=$(gcloud config get-value project)

       gcloud config set compute/region $REGION
       gcloud config set compute/zone $ZONE
       ```

  - `> **Note:**` that `$PROJECT_ID` is reused throughout (Cloud Run env, image path,
    worker-pool path) so these exports must succeed before continuing.
  - End with `---`.

### Phase 3: Step 2 — Enable APIs

- [ ] **3.1 Write `## Step 2: Enable Google Cloud APIs`.**
  - One-sentence framing (these power Compute, Cloud Run, Cloud Build, Artifact
    Registry, Secret Manager, Vertex AI, private service networking, IAP, OS Config,
    and Maps). Then the paste-ready block (one API per line, backslash continuation,
    matching `docs/lab.md:43-48` style):

    ```shell
    gcloud services enable \
      compute.googleapis.com \
      run.googleapis.com \
      cloudbuild.googleapis.com \
      artifactregistry.googleapis.com \
      secretmanager.googleapis.com \
      aiplatform.googleapis.com \
      servicenetworking.googleapis.com \
      iap.googleapis.com \
      osconfig.googleapis.com \
      maps-backend.googleapis.com
    ```

  - `> **Note:**` that enabling APIs can take a minute or two; `servicenetworking` is
    required for the Cloud Build private-pool VPC peering and `aiplatform` for Vertex
    AI embeddings/chat at runtime.
  - End with `---`.

### Phase 4: Step 3 — Clone the repo

- [ ] **4.1 Write `## Step 3: Clone the Repository`.**
  - One-sentence framing. Numbered sub-steps mirroring `docs/lab.md:193-200`:
    1. Clone + cd into the Terraform root (paste-ready):

       ```shell
       git clone https://github.com/cofin/oracledb-vertexai-demo.git
       cd oracledb-vertexai-demo/tools/deploy/terraform
       ```

  - `> **Note:**` that all `terraform` commands in this lab run from
    `tools/deploy/terraform/`, and the Cloud Build config lives one directory over at
    `../gcp/cloudbuild.yaml` (referenced in Step 6).
  - End with `---`.

### Phase 5: Step 4 — terraform.tfvars

- [ ] **5.1 Write `## Step 4: Configure Your Deployment Variables`.**
  - One-sentence framing (Terraform reads a `terraform.tfvars` file for your
    project-specific values). Numbered sub-steps:
    1. Create `terraform.tfvars` (paste-ready heredoc so the learner can run it
       directly; the `db_password` is the Oracle `app` user password stored in Secret
       Manager `coffee-db-password`):

       ```shell
       cat > terraform.tfvars <<EOF
       project_id  = "${PROJECT_ID}"
       region      = "us-central1"
       db_password = "SuperSecret1"
       EOF
       ```

  - `> **Note:**` (FR4): `terraform.tfvars` is **gitignored** by the repo — it holds a
    lab-only secret (`db_password`) and must never be committed. For a real deployment
    you would generate a strong password and let Terraform write it straight into
    Secret Manager (`coffee-db-password`).
  - Reconcile note (one line, can be a second `> **Note:**` or inline comment): the
    variable names (`project_id`, `region`, `db_password`) are defined in
    `tools/deploy/terraform/variables.tf`; if you customized that file, match these keys.
  - End with `---`.
  - Verification: keys exactly `project_id`, `region`, `db_password`; password default
    matches the GCE-only lab's `SuperSecret1` convention (`docs/lab.md:215`).

### Phase 6: Step 5 — terraform init && apply (+ what/why)

- [ ] **6.1 Write `## Step 5: Stand Up the Infrastructure with Terraform`.**
  - One-sentence framing. Numbered sub-steps:
    1. Initialize providers/modules:

       ```shell
       terraform init
       ```

    2. Review and apply (auto-approve acceptable for the lab; the learner can drop
       `-auto-approve` to inspect the plan first):

       ```shell
       terraform apply -auto-approve
       ```

  - Then a short **"What Terraform just created"** prose block (bulleted, FR5),
    grouped by the Ch2/Ch3 modules and tying each to its contract name:
    - **Network** — `coffee-vpc` with `coffee-subnet` (`10.10.0.0/24`, DB VM) and
      `coffee-run-subnet` (`10.10.1.0/24`, Cloud Run Direct VPC egress range);
      `coffee-router` + `coffee-nat` for outbound image pulls; the reserved
      `coffee-buildpool-range` (`10.30.0.0/24`) for Cloud Build private-pool peering.
    - **Database VM** — `coffee-db` (COS, `e2-standard-4`, **standard, not Spot**,
      `--no-address`), static internal IP `coffee-db-ip` = `10.10.0.10`, a persistent
      data disk mounted to `/opt/oracle/oradata`, running `gvenzl/oracle-free` on
      `1521`, PDB `freepdb1`, app user `app`.
    - **Registry + build pool** — Artifact Registry `coffee-artifacts`; Cloud Build
      private pool `coffee-build-pool` peered to `coffee-vpc`.
    - **Cloud Run + IAM + secret** — the `coffee-app` service (bootstrap image to
      start), the `coffee-run-sa` / `coffee-build-sa` / VM service accounts with their
      roles, and Secret Manager `coffee-db-password`.
  - **Why the DB is private** `> **Note:**` (FR5): the VM has no external IP
    (`--no-address`); the only ingress to `1521` is firewall rule `coffee-allow-run-to-db`
    from the Cloud Run egress range (`10.10.1.0/24`) **and** the build-pool range
    (`10.30.0.0/24`); SSH is IAP-only (`coffee-allow-iap-ssh`, `35.235.240.0/20`). The
    public internet cannot reach the database by construction.
  - `> **Note:**` that `terraform apply` may take several minutes (the COS VM boots,
    runs cloud-init, pulls and starts the Oracle container, and initializes
    `freepdb1`); the Cloud Run service comes up on a bootstrap image and is replaced by
    the real image in Step 6.
  - End with `---`.

### Phase 7: Step 6 — Deploy via Cloud Build

- [ ] **7.1 Write `## Step 6: Build and Deploy with Cloud Build`.**
  - One-sentence framing (one command builds the image, pushes it, migrates the
    private DB, and rolls out Cloud Run). Numbered sub-steps:
    1. Submit the build (paste-ready, run from `tools/deploy/terraform/`) — FR6 verbatim:

       ```shell
       gcloud builds submit \
         --config ../gcp/cloudbuild.yaml \
         --substitutions=_REGION=us-central1 \
         --worker-pool=projects/$PROJECT_ID/locations/$REGION/workerPools/coffee-build-pool
       ```

  - **What this pipeline does** prose (bulleted), tied to `tools/deploy/gcp/cloudbuild.yaml`:
    1. `docker build` the image from `tools/deploy/docker/Dockerfile`, tag
       `:$SHORT_SHA` and `:latest`, push both to
       `us-central1-docker.pkg.dev/$PROJECT_ID/coffee-artifacts/coffee-app`.
    2. **Migrate** — run the image entrypoint `coffee upgrade` with
       `DATABASE_HOST=10.10.0.10`, `DATABASE_PORT=1521`,
       `DATABASE_SERVICE_NAME=freepdb1`, `DATABASE_USER=app`, and `DATABASE_PASSWORD`
       from the `coffee-db-password` secret.
    3. `gcloud run deploy coffee-app` with Direct VPC egress
       (`--network=coffee-vpc --subnet=coffee-run-subnet --vpc-egress=private-ranges-only`),
       port 8080, `--execution-environment gen2`, the `coffee-run-sa` service account,
       the DB/Vertex env, and `--set-secrets=DATABASE_PASSWORD=coffee-db-password:latest`.
  - **Why migration reaches a private DB** `> **Note:**` (chapter goal): the migration
    runs **on the Cloud Build private pool** (`coffee-build-pool`), which is **peered to
    `coffee-vpc`**, so it can reach the DB on its internal IP `10.10.0.10` — default
    Cloud Build workers cannot. And because the committed fixtures already carry their
    embedding vectors (`product.json.gz` ships `"embedding":[...]`), `coffee upgrade`
    loads them **without any Vertex AI call at build time**; only the running Cloud Run
    service needs Vertex (for live query embeddings).
  - Reconcile note (one line, FR6): the exact substitution keys are defined in
    `tools/deploy/gcp/cloudbuild.yaml`; if it declares additional `_`-prefixed
    substitutions, pass them here too.
  - `> **Note:**` that the build streams logs in Cloud Shell; a green build ends with
    the new Cloud Run revision serving 100% of traffic.
  - End with `---`.

### Phase 8: Step 7 — Open the app and prove the path

- [ ] **8.1 Write `## Step 7: Open Cymbal Coffee and Ask a Question`.**
  - One-sentence framing. Numbered sub-steps:
    1. Get the public URL (paste-ready) — FR7 verbatim:

       ```shell
       gcloud run services describe coffee-app \
         --region=$REGION \
         --format='value(status.url)'
       ```

    2. Open the printed `https://coffee-app-….run.app` URL in a new browser tab.
    3. In the chat box, send a query such as *"I need something bold"* (the same idiom
       used in the docs hero, `docs/index.md:6-10`), and confirm a **grounded coffee
       recommendation** with real menu rows renders.
  - **What this proves** `> **Note:**` (FR7): a grounded answer means the **public
    Cloud Run service reached the PRIVATE Oracle DB** at `10.10.0.10:1521/freepdb1`
    over Direct VPC egress **and** called **Vertex AI** to embed your query — the full
    production-shaped path is working end to end. (Detailed verification — checking the
    revision, the DB connection, and that the DB is unreachable publicly — is in
    `## Verify your deployment` below.)
  - End with `---`.

### Phase 9: Step 8 — Advanced Challenge Tasks

- [ ] **9.1 Write `## Advanced Challenge Tasks for Workshop Graduates` + intro.**
  - Reuse the exact section title and one-paragraph framing shape from
    `docs/lab.md:267-269` ("Once the core deployment is live, challenge yourself…").

- [ ] **9.2 Write `### Challenge 1: Wire a GitHub Push to a Cloud Build Trigger (Real CI/CD)`.**
  - **Objective** line: turn the manual `gcloud builds submit` into a push-triggered
    deploy so every commit to `main` redeploys Cloud Run.
  - `* **Step A:**` connect the GitHub repo to Cloud Build (paste-ready, note the
    one-time browser OAuth in **Cloud Build → Repositories → Connect**):

    ```shell
    gcloud builds connections create github coffee-github \
      --region=$REGION
    ```

    (with a `> **Note:**` that completing the GitHub OAuth/install is an interactive
    browser step in the console).
  - `* **Step B:**` create the trigger bound to the existing private pool +
    `cloudbuild.yaml` (paste-ready):

    ```shell
    gcloud builds triggers create github \
      --name=coffee-deploy-on-push \
      --region=$REGION \
      --repository=projects/$PROJECT_ID/locations/$REGION/connections/coffee-github/repositories/oracledb-vertexai-demo \
      --branch-pattern='^main$' \
      --build-config=tools/deploy/gcp/cloudbuild.yaml \
      --substitutions=_REGION=us-central1
    ```

  - `* **Step C:**` test it: push a trivial commit to `main` and watch the build start
    automatically in **Cloud Build → History**.
  - `> **Note:**` that the trigger reuses the same `cloudbuild.yaml`, so the build
    still migrates the private DB and deploys with Direct VPC egress — the only change
    is *what kicks it off*.

- [ ] **9.3 Write `### Challenge 2: Replace the Static Internal IP with a Cloud DNS Private Name`.**
  - **Objective** line: front the DB with a stable private DNS name
    (e.g. `coffee-db.internal`) so `DATABASE_HOST` no longer hardcodes `10.10.0.10`.
  - `* **Step A:**` create a private DNS managed zone bound to `coffee-vpc` (paste-ready):

    ```shell
    gcloud dns managed-zones create coffee-internal \
      --dns-name=coffee.internal. \
      --description="Private zone for Cymbal Coffee" \
      --visibility=private \
      --networks=coffee-vpc
    ```

  - `* **Step B:**` add an A record pointing the name at the DB's internal IP
    (paste-ready):

    ```shell
    gcloud dns record-sets create db.coffee.internal. \
      --zone=coffee-internal \
      --type=A \
      --ttl=300 \
      --rrdatas=10.10.0.10
    ```

  - `* **Step C:**` update Cloud Run to use the DNS name instead of the IP (paste-ready):

    ```shell
    gcloud run services update coffee-app \
      --region=$REGION \
      --update-env-vars=DATABASE_HOST=db.coffee.internal
    ```

  - `> **Note:**` that for a permanent change you would set `DATABASE_HOST` in the
    Terraform/`cloudbuild.yaml` so it survives the next deploy; the `gcloud run
    services update` above is a live override for the challenge.

- [ ] **9.4 Write `### Challenge 3: Move Terraform State to a GCS Backend`.**
  - **Objective** line: move the local `terraform.tfstate` into a versioned GCS bucket
    so the stack is reproducible and shareable (the lab default is local state).
  - `* **Step A:**` create a versioned state bucket (paste-ready):

    ```shell
    gcloud storage buckets create gs://${PROJECT_ID}-coffee-tfstate \
      --location=us-central1 \
      --uniform-bucket-level-access
    gcloud storage buckets update gs://${PROJECT_ID}-coffee-tfstate --versioning
    ```

  - `* **Step B:**` add a `backend "gcs"` block to the Terraform config (shown as an
    `hcl` snippet the learner adds to `tools/deploy/terraform/`, e.g. a new
    `backend.tf`):

    ```hcl
    terraform {
      backend "gcs" {
        bucket = "REPLACE_WITH_PROJECT_ID-coffee-tfstate"
        prefix = "coffee/state"
      }
    }
    ```

  - `* **Step C:**` migrate the existing local state into the bucket (paste-ready):

    ```shell
    terraform init -migrate-state
    ```

  - `> **Note:**` that GCS object versioning gives state history/rollback, and a remote
    backend is what lets a team apply the same stack safely.
  - End the challenges section with `---`.

### Phase 10: Ch6 placeholders (empty bodies)

- [ ] **10.1 Append the two Ch6 placeholder headers, last and in order (FR9, AC4).**
  - After the challenges' closing `---`, add exactly:

    ```markdown
    ## Verify your deployment

    ## Clean up & costs
    ```

  - Leave both bodies **empty** (Ch6 fills them). Do not add a trailing `---` after
    `## Clean up & costs`; it is the final section. Add an HTML comment marker above
    them so the boundary is unmistakable, e.g.
    `<!-- Owned by Ch6 (cloudrun-lab-verification-teardown): do not author here. -->`.

### Phase 11: Build + house-style verification

- [ ] **11.1 Build the docs and confirm a clean `-W` build.**
  - Run `make docs` (or the project's `sphinx-build -W --keep-going` invocation;
    confirm the exact target from the Makefile first). Confirm no new warnings/errors
    reference `lab-cloud-run.md` (AC5). Fix any MyST issues (heading depth ≤ 3, valid
    fences, no broken anchors).
- [ ] **11.2 House-style + contract self-review.**
  - Confirm AC2 by diffing the doc's literal names/values against
    `.agents/specs/cloudrun-gce-lab/prd.md:89-148` — zero mismatches.
  - Confirm AC3 (Step 6 + Step 7 command strings verbatim), AC4 (last two headers),
    AC6 (`> **Note:**` blockquotes, `## Step N:` headers, challenge format).
  - Confirm AC8: `git diff --stat` lists only `docs/lab-cloud-run.md`.
  - (Optional) Dispatch `flow:code-reviewer` on the drafted doc against `docs/lab.md`
    for voice/contract validation before marking complete.
