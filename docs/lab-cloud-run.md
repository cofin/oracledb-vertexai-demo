# Hands-on Lab: Cymbal Coffee on Cloud Run — Private Oracle 26ai DB + Cloud Build

This is the **production-shaped** path: the **Litestar 2** web application (`coffee-app`, packaged as a distroless PyApp onefile container) and stateless **Oracle REST Data Services 26.3** (`coffee-ords`) run on Google Cloud Run, while the **Oracle AI Database 26ai** instance runs on a Container-Optimized OS Compute Engine virtual machine (`coffee-db`, `10.10.0.10:1521/freepdb1`) with a persistent SSD disk and no external IP address. A peered Cloud Build private worker pool builds the PyApp binary and distroless container, executes **SQLSpec `0.69.0`** database migrations, runs the packaged APEX CDN configuration (`src/app/db/sql/deploy/configure-apex-cdn.sql`), and deploys both Cloud Run services.

Welcome to the **Cymbal Coffee Cloud Run Hands-on Lab**. In this workshop, you will provision, deploy, and verify an AI-powered coffee recommendation and store-operations platform using Google Cloud Run, Direct VPC egress, Vertex AI (`gemini-embedding-2` + `gemini-3.8-flash`), and Oracle 26ai. For complete background concepts and reference material, visit the [Cymbal Coffee Documentation Site](https://cofin.github.io/oracledb-vertexai-demo/index.html).

This lab follows the [Single-VM GCE lab](lab-gce.md), where `make start-infra` runs `container-registry.oracle.com/database/adb-free:latest-26ai` (`cymbal-adb-free`, `.envs/tns` mTLS wallet, service `myatp_low` on TLS port `1522`, pre-bundled **Oracle APEX 26.1.5 + ORDS 26.3** at `https://localhost:8443/ords/apex`) alongside `uv run coffee run` on local HTTP port `8000`. Completing the Single-VM GCE lab first is recommended if you want to explore the codebase interactively before deploying the split Cloud Run topology.

---

## Prerequisites & Audience Expectations

- **GCP Knowledge**: Comfort with Google Cloud Platform, including Google Cloud Run, Cloud Build, Artifact Registry, Virtual Private Clouds (VPCs), Secret Manager, and Terraform.
- **ORDS & APEX**: Understanding how stateless Oracle REST Data Services (`ords:26.3`) on Cloud Run pairs with Oracle's public APEX CDN (`src/app/db/sql/deploy/configure-apex-cdn.sql`) and Oracle APEX 26.1 Vertex AI services (`COFFEE_VERTEX_AI`).
- **Tools Required**: A web browser and access to a Google Cloud Console account with billing or workshop credits enabled.

> **Note:** Unlike the Single-VM Spot GCE lab, this architecture provisions a persistent standard VM instance (`coffee-db`), a persistent `pd-ssd` disk, and regional networking services that do not scale to zero. Follow the cleanup instructions at the end of the lab to avoid ongoing charges.

---

## Step 1: Google Cloud Environment Setup

Initialize your cloud workspace and export the environment variables used across Terraform, Docker, and Cloud Build commands.

1. Log into the **Google Cloud Console** (`https://console.cloud.google.com`) using your workshop credentials.
2. In the top navigation bar, click the **Activate Cloud Shell** icon (a small terminal icon `>_`). Wait a few moments for the terminal environment to provision and connect.
3. Set your active project using the following command (replace `[YOUR-PROJECT-ID]` with your actual GCP project ID shown on your console dashboard):

   ```shell
   gcloud config set project [YOUR-PROJECT-ID]
   ```

4. Define the geographic deployment region and zone defaults:

   ```shell
   export REGION=us-central1
   export ZONE=us-central1-c
   export PROJECT_ID=$(gcloud config get-value project)

   gcloud config set compute/region $REGION
   gcloud config set compute/zone $ZONE
   ```

> **Note:** `$PROJECT_ID` is interpolated in Artifact Registry paths, Cloud Build substitutions, and worker pool resource names. Confirm `echo "$PROJECT_ID"` prints a non-empty project ID before continuing.

---

## Step 2: Enable Google Cloud APIs

Enable the Google Cloud APIs required to provision VPC peering, Compute Engine, Cloud Run, Cloud Build, Artifact Registry, Secret Manager, Identity-Aware Proxy, and Vertex AI.

1. Enable the required Google Cloud Services APIs:

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
     maps-embed-backend.googleapis.com
   ```

> **Note:** Enabling these APIs takes a minute or two. `servicenetworking.googleapis.com` peers the Cloud Build private worker pool (`coffee-build-pool`) into `coffee-vpc`, and `aiplatform.googleapis.com` allows `coffee-app` (and direct APEX 26.1 Generative AI Services) to invoke Vertex AI (`gemini-embedding-2` and `gemini-3.8-flash`).

---

## Step 3: Clone the Repository

Clone the Cymbal Coffee codebase and enter the Terraform infrastructure directory.

1. Clone the repository and move into `tools/deploy/terraform`:

   ```shell
   git clone https://github.com/cofin/oracledb-vertexai-demo.git
   cd oracledb-vertexai-demo/tools/deploy/terraform
   ```

> **Note:** Run all `terraform` commands from `tools/deploy/terraform`. When submitting Cloud Build from `tools/deploy/terraform`, pass the repository root (`../..`) or run `gcloud builds submit` from the repository root so Docker receives the full build context.

---

## Step 4: Configure Your Deployment Variables

Define your project variables in a local `terraform.tfvars` file inside `tools/deploy/terraform`.

1. Create `terraform.tfvars` using a shell heredoc:

   ```shell
   cat > terraform.tfvars <<EOF
   project_id          = "${PROJECT_ID}"
   region              = "us-central1"
   db_password         = "SuperSecret1"
   db_system_password  = "SuperSecretSYS1"
   EOF
   ```

> **Note:** `terraform.tfvars` is excluded by `.gitignore` so credentials are never committed to version control. Use cryptographically random passwords in non-lab environments.
>
> `db_password` populates the `coffee-db-password` Secret Manager secret (`DATABASE_PASSWORD` for the `APP` schema), consumed by `coffee-app`, the Cloud Build `migrate` step, and VM initialization. `db_system_password` populates `coffee-db-system-password`, consumed only by VM `cloud-init`, the Cloud Build `configure-apex` step (`DATABASE_SYSTEM_PASSWORD`), and `coffee-ords` (`ORACLE_PWD`) — never exposed to `coffee-app`.

---

## Step 5: Stand Up the Infrastructure with Terraform

Initialize the Terraform providers and apply the configuration to create the private VPC, Oracle 26ai VM, Artifact Registry repository, peered Cloud Build worker pool, Secret Manager secrets, IAM bindings, and placeholder Cloud Run services.

1. Initialize Terraform:

   ```shell
   terraform init
   ```

2. Apply the Terraform plan:

   ```shell
   terraform apply -auto-approve
   ```

Terraform provisions the following resources:

- **Networking (`network.tf`)** — Custom VPC `coffee-vpc` with database subnet `coffee-subnet` (`10.10.0.0/24`), Cloud Run Direct VPC egress subnet `coffee-run-subnet` (`10.10.1.0/24`), Cloud Router/NAT (`coffee-router` / `coffee-nat`), and reserved VPC peering range `coffee-buildpool-range` (`10.30.0.0/24`).
- **Database VM (`db_vm.tf`)** — Container-Optimized OS VM `coffee-db` at static internal IP `10.10.0.10` with a 50 GB `pd-ssd` persistent disk (`coffee-db-data`) mounted on the host at `/mnt/disks/oradata` and bind-mounted to `/opt/oracle/oradata` inside the `gvenzl/oracle-free:latest` container on port `1521` (`freepdb1`, `vector_memory_size = 512M`).
- **Artifact Registry & Build Pool (`registry.tf`, `buildpool.tf`)** — Regional Docker repository `coffee-artifacts` and private Cloud Build worker pool `coffee-build-pool` peered to `coffee-vpc`.
- **Secrets, IAM & Cloud Run (`secrets.tf`, `iam.tf`, `cloudrun.tf`, `ords.tf`)** — Secrets `coffee-db-password` and `coffee-db-system-password`, least-privilege service accounts (`coffee-db-sa`, `coffee-run-sa`, `coffee-ords-sa`, `coffee-build-sa`), and Cloud Run services `coffee-app` and `coffee-ords` (initialized with a bootstrap container image that Cloud Build replaces in Step 6).

> **Note:** `coffee-db` has no external IP address. Firewall rule `coffee-allow-run-to-db` permits `tcp:1521` solely from `10.10.1.0/24` (Cloud Run Direct VPC egress) and `10.30.0.0/24` (`coffee-build-pool`), while `coffee-allow-iap-ssh` permits `tcp:22` solely from Google's IAP range (`35.235.240.0/20`). Initial Oracle container startup and SPFILE vector-pool restart take roughly 3 to 5 minutes.

---

## Step 5b: Re-host the Oracle ORDS `26.3` Image to Artifact Registry

Cloud Run deploys container images from Google Artifact Registry (or Container Registry), so re-host the official **Oracle ORDS `26.3`** image into your project's `coffee-artifacts` repository (matching `_ORDS_TAG: "26.3"` in `tools/deploy/gcp/cloudbuild.yaml`).

1. Authenticate Docker with your regional Artifact Registry endpoint:

   ```shell
   gcloud auth configure-docker us-central1-docker.pkg.dev
   ```

2. Pull the official ORDS `26.3` image from Oracle Container Registry:

   ```shell
   docker pull container-registry.oracle.com/database/ords:26.3
   ```

3. Tag the image for your project's `coffee-artifacts` repository:

   ```shell
   docker tag container-registry.oracle.com/database/ords:26.3 \
     us-central1-docker.pkg.dev/${PROJECT_ID}/coffee-artifacts/ords:26.3
   ```

4. Push the tagged image to Artifact Registry:

   ```shell
   docker push us-central1-docker.pkg.dev/${PROJECT_ID}/coffee-artifacts/ords:26.3
   ```

---

## Step 6: Build and Deploy with Cloud Build

Move to the repository root and submit the build to the peered Cloud Build private worker pool (`coffee-build-pool`).

1. Run `gcloud builds submit` from the repository root (`oracledb-vertexai-demo/`):

   ```shell
   cd ../..
   gcloud builds submit \
     --config tools/deploy/gcp/cloudbuild.yaml \
     --region=$REGION \
     --substitutions=_PROJECT=$PROJECT_ID,_REGION=$REGION
   ```

The `tools/deploy/gcp/cloudbuild.yaml` pipeline executes these stages on `coffee-build-pool`:

- **`build-onefile`** — Installs Node.js 24 and `uv`, compiles the Vite frontend bundle (`uv run python manage.py assets build`), packages the Python wheel (including the packaged deployment SQL scripts at `src/app/db/sql/deploy/configure-apex-cdn.sql` and `src/app/db/sql/deploy/revert-apex-cdn.sql`), and compiles the self-contained PyApp binary (`dist/coffee-amd64-linux-gnu`).
- **`build`, `push-sha`, `push-latest`** — Packages the PyApp binary and Oracle Instant Client runtime libraries into `gcr.io/distroless/cc-debian12:nonroot` (`tools/deploy/docker/Dockerfile`, `ENTRYPOINT ["/usr/local/bin/tini", "--", "coffee"]`) and pushes `:${SHORT_SHA}` and `:latest` to `us-central1-docker.pkg.dev/$PROJECT_ID/coffee-artifacts/coffee-app`.
- **`migrate`** — Runs `coffee upgrade` inside the built distroless container over the peered VPC to `10.10.0.10:1521/freepdb1`, applying **SQLSpec `0.69.0`** migrations (`enable_session_tracing`, wire-level `sqlcommenter`, isolated `queue_db`) and loading committed 3072-dimensional vector fixtures (`src/app/db/fixtures/`).
- **`configure-apex`** — Runs `coffee configure-apex-cdn` inside the built container against `10.10.0.10:1521/freepdb1`, executing the wheel-packaged PL/SQL block at `src/app/db/sql/deploy/configure-apex-cdn.sql` (paired in the package with `src/app/db/sql/deploy/revert-apex-cdn.sql` for local `/i/` resets) so Oracle APEX points `IMAGE_PREFIX` to `https://static.oracle.com/cdn/apex/26.1.0/`.
- **`deploy-ords`** — Deploys `coffee-ords` (`ords:26.3`) on Cloud Run with Direct VPC egress (`PRIVATE_RANGES_ONLY`) targeting `10.10.0.10:1521/freepdb1`.
- **`deploy`** — Deploys `coffee-app` on Cloud Run with Direct VPC egress (`PRIVATE_RANGES_ONLY`), Secret Manager `coffee-db-password`, and Vertex AI (`gemini-embedding-2` + `gemini-3.8-flash`).

> **Note:** Because `src/app/db/fixtures/` contains pre-computed 3072-dimensional `gemini-embedding-2` embeddings and `src/app/db/sql/deploy/configure-apex-cdn.sql` is bundled directly inside the PyApp binary, both `migrate` and `configure-apex` run completely inside the peered build pool without external Vertex AI calls or loose SQL scripts.

---

## Step 7: Open Cymbal Coffee and Ask a Question

Retrieve your deployed Cloud Run URL, open the web frontend, and test conversational Hybrid RRF recommendations.

1. Retrieve the public HTTPS URL of `coffee-app`:

   ```shell
   export RUN_URL=$(gcloud run services describe coffee-app \
     --region=$REGION \
     --format='value(status.url)')
   echo "$RUN_URL"
   ```

2. Open the printed URL in a browser tab (and visit `$RUN_URL/explore` to inspect live Hybrid RRF and HNSW `VECTOR_DISTANCE(..., COSINE) FETCH APPROX` execution plans).
3. In the chat interface, enter a query such as:

   ```text
   I need something bold
   ```

4. Press Enter and confirm the assistant streams grounded Cymbal Coffee menu items retrieved from `10.10.0.10:1521/freepdb1` via Direct VPC egress and ranked with Vertex AI embeddings.

---

## Step 7b: Access Oracle REST Data Services (`ORDS 26.3`)

Verify that the stateless `coffee-ords` Cloud Run service reaches the private Oracle 26ai database over `coffee-vpc`.

1. Retrieve the public HTTPS endpoint URL of `coffee-ords` and verify the ORDS metadata catalog:

   ```shell
   export ORDS_URL=$(gcloud run services describe coffee-ords \
     --region=$REGION \
     --format='value(status.url)')

   curl -f -s "$ORDS_URL/ords/" | grep -o '"title":"Oracle REST Data Services"'
   ```

   Expected output:

   ```text
   "title":"Oracle REST Data Services"
   ```

2. When Oracle APEX 26.1 is installed in the target database, open the APEX Builder login screen at:

   ```text
   [YOUR-ORDS-URL]/ords/apex
   ```

   Because `coffee configure-apex-cdn` executed `src/app/db/sql/deploy/configure-apex-cdn.sql`, APEX loads all static assets from Oracle's public CDN while `coffee-ords` remains stateless and scales to zero.

---

## Step 7c: Oracle APEX 26.1 -> Vertex AI (`COFFEE_VERTEX_AI`) & Cymbal Coffee App (`App ID 100`)

> **Container Topology Note:** The Cloud Run lab's private `coffee-db` VM runs lightweight `gvenzl/oracle-free:latest` (`10.10.0.10:1521/freepdb1`). For an environment with **Oracle APEX 26.1.5 + ORDS 26.3** pre-bundled out of the box (workspace `COFFEE`, parsing schema `APP`, Database Actions at `https://localhost:8443/ords/sql-developer`, and mTLS wallet service `myatp_low` on TLS port `1522`), run `make start-infra` (`container-registry.oracle.com/database/adb-free:latest-26ai`, container `cymbal-adb-free`, volume `cymbal-adb-data`) locally or in the [Single-VM GCE lab](lab-gce.md), or connect against an APEX 26.1-enabled Oracle 26ai / Autonomous AI Database instance.

When running against an APEX 26.1 workspace (`COFFEE`, schema `APP`), Cymbal Coffee provides two methods to connect `APEX_AI.GENERATE` (`COFFEE_VERTEX_AI`) to Vertex AI, plus the full **Cymbal Coffee — Vertex AI & Operations** APEXlang application (`src/apex/cymbal-coffee-ops/`, `compatibilityMode: 26.1`, App ID `100`):

### 1. Connect Oracle APEX 26.1 to Vertex AI (`COFFEE_VERTEX_AI`)

- **Method 1 (Primary): Direct Vertex AI OpenAI-Compatible Endpoint**
  - **Base URL**: `https://aiplatform.googleapis.com/v1/projects/<VERTEX_AI_PROJECT_ID>/locations/<VERTEX_AI_LOCATION>/endpoints/openapi` (`location` defaults to `global`)
  - **AI Provider**: `OpenAI` (Generic OpenAI-compatible)
  - **Model**: `google/gemini-3.8-flash`
  - **Web Credential**: `VERTEX_AI_CRED` (`HTTP Header` `Authorization` = `Bearer <oauth2-access-token>`)
  - **Service Static ID**: `COFFEE_VERTEX_AI` (`Used by App Builder = Yes`)
  - **CLI Provisioning & Live `APEX_AI.GENERATE` Check**:

    ```shell
    uv run python manage.py infra apex configure-vertex \
      --mode direct \
      --project "$PROJECT_ID" \
      --verify
    ```

    Refresh the OAuth2 access token (~60-minute expiry) without recreating `DBMS_NETWORK_ACL_ADMIN` host ACEs:

    ```shell
    uv run python manage.py infra apex configure-vertex \
      --mode direct \
      --refresh-token \
      --verify
    ```

  - **Equivalent Manual APEX 26.1 Builder UI Steps**: Sign into Workspace `COFFEE` (`APP`) -> **App Builder** -> **Workspace Utilities** -> **Web Credentials** -> configure `VERTEX_AI_CRED` (`HTTP Header`, `Authorization: Bearer <oauth2-access-token>`) -> **Generative AI** -> configure `COFFEE_VERTEX_AI` (`OpenAI`, model `google/gemini-3.8-flash`, `Used by App Builder = Yes`, credential `VERTEX_AI_CRED`) -> click **Test Connection**.

- **Method 2 (Secondary / Zero-Expiry Local Dev, mTLS Workstations & Cloud Run Gateway): Litestar OpenAI-Compatible Gateway**
  - **Base URL**: `http://host.docker.internal:8000/api/apex/ai/v1` locally (or `$RUN_URL/api/apex/ai/v1` against your Cloud Run `coffee-app` deployment, backed by `ApexAIController` exposing `GET /api/apex/ai/v1/models` and `POST /api/apex/ai/v1/chat/completions` with optional `APEX_GATEWAY_API_KEY` Bearer token authentication)
  - **Model**: `gemini-3.8-flash`
  - **CLI Provisioning**:

    ```shell
    uv run python manage.py infra apex configure-vertex --mode gateway --verify
    ```

    (Pass `--gateway-url "$RUN_URL/api/apex/ai/v1"` when pointing a remote Oracle 26ai database at the Cloud Run `coffee-app` gateway.)

### 2. Validate, Import, and Run Cymbal Coffee APEX 26.1 (`src/apex/cymbal-coffee-ops/`, App ID `100`)

With Oracle SQLcl `26.1.2+` installed (`make install-sqlcl` / `uv run python manage.py install sqlcl`), validate, import, and export Application `100`:

```shell
uv run python manage.py infra apex validate --alias cymbal-coffee-ops
uv run python manage.py infra apex import --alias cymbal-coffee-ops --workspace COFFEE --schema APP --app-id 100
uv run python manage.py infra apex export --app-id 100 --alias cymbal-coffee-ops
```

Once imported, open `/ords/r/coffee/cymbal-coffee-ops/` to explore:

- **Page 6 — Vertex AI Coffee Concierge** (`/ords/r/coffee/cymbal-coffee-ops/vector-recommendations`): Invokes `APEX_AI.GENERATE(p_service_static_id => 'COFFEE_VERTEX_AI')` grounded on live in-stock `PRODUCT` rows alongside `HNSW Ready (3072d)` retrieval status.
- **Page 3 — DFW Store Directory** (`/ords/r/coffee/cymbal-coffee-ops/stores`): Generates keyless Google Maps search URLs purely from seeded `STORE` street addresses (`GET /api/apex/stores` contract) without collecting or persisting user browser coordinates.
- **Page 7 — 26ai & Vertex AI Health** (`/ords/r/coffee/cymbal-coffee-ops/integration-health`): Verifies `APEX_RELEASE`, `VERTEX_AI_CRED` / `COFFEE_VERTEX_AI`, `PRODUCT` 3072-dimensional `gemini-embedding-2` vector coverage, and `USER_ANNOTATIONS_USAGE` schema metadata.

---

## Advanced Challenge Tasks for Workshop Graduates

Once the Cloud Run deployment is live, challenge yourself with the following expansion exercises:

### Challenge 1: Wire a GitHub Push to a Cloud Build Trigger (Real CI/CD)

**Objective:** Automate the deployment pipeline so that pushing a commit to `main` triggers `tools/deploy/gcp/cloudbuild.yaml` on `coffee-build-pool`.

- **Step A: Connect the GitHub Repository to Cloud Build** — Initialize a regional GitHub connection resource:

  ```shell
  gcloud builds connections create github coffee-github \
    --region=$REGION
  ```

  > **Note:** Complete the OAuth handshake in the Google Cloud Console under **Cloud Build** -> **Repositories** -> **Connect Repository** -> `coffee-github`.

- **Step B: Create the Push Trigger** — Provision a trigger targeting your repository, branch, and build config:

  ```shell
  gcloud builds triggers create github \
    --name=coffee-deploy-on-push \
    --region=$REGION \
    --repository=projects/$PROJECT_ID/locations/$REGION/connections/coffee-github/repositories/oracledb-vertexai-demo \
    --branch-pattern='^main$' \
    --build-config=tools/deploy/gcp/cloudbuild.yaml \
    --substitutions=_PROJECT=$PROJECT_ID,_REGION=$REGION
  ```

- **Step C: Test the Trigger** — Commit and push a small documentation or template update to `main` on your fork and confirm the build starts under **Cloud Build** -> **History**.

---

### Challenge 2: Replace the Static Internal IP with a Cloud DNS Private Name

**Objective:** Front `coffee-db` (`10.10.0.10`) with a private Cloud DNS record (`db.coffee.internal`) inside `coffee-vpc`.

- **Step A: Create a Private DNS Zone**

  ```shell
  gcloud dns managed-zones create coffee-internal \
    --dns-name=coffee.internal. \
    --description="Private zone for Cymbal Coffee" \
    --visibility=private \
    --networks=coffee-vpc
  ```

- **Step B: Add an `A` Record for `coffee-db`**

  ```shell
  gcloud dns record-sets create db.coffee.internal. \
    --zone=coffee-internal \
    --type=A \
    --ttl=300 \
    --rrdatas=10.10.0.10
  ```

- **Step C: Update the Cloud Run Service Environment Variable**

  ```shell
  gcloud run services update coffee-app \
    --region=$REGION \
    --update-env-vars=DATABASE_HOST=db.coffee.internal
  ```

---

### Challenge 3: Move Terraform State to a GCS Backend

**Objective:** Migrate local `terraform.tfstate` to a versioned Google Cloud Storage bucket with state locking.

- **Step A: Create a Versioned Cloud Storage Bucket**

  ```shell
  gcloud storage buckets create gs://${PROJECT_ID}-coffee-tfstate \
    --location=us-central1 \
    --uniform-bucket-level-access
  gcloud storage buckets update gs://${PROJECT_ID}-coffee-tfstate --versioning
  ```

- **Step B: Configure the Remote Backend in Terraform** — Create a local `backend.tf` file inside `tools/deploy/terraform` (replacing `REPLACE_WITH_YOUR_PROJECT_ID` with your actual GCP project ID):

  ```hcl
  terraform {
    backend "gcs" {
      bucket = "REPLACE_WITH_YOUR_PROJECT_ID-coffee-tfstate"
      prefix = "coffee/state"
    }
  }
  ```

- **Step C: Migrate Local State to GCS**

  ```shell
  cd tools/deploy/terraform
  terraform init -migrate-state
  ```

---

## Verify your deployment

These checks prove two things at once: the app works end-to-end, and the Oracle database is private — reachable by Cloud Run over Direct VPC egress, never from the public internet (including Cloud Shell).

1. **Confirm Cloud Run is serving.** Capture the public service URL and request the home page:

   ```shell
   export RUN_URL=$(gcloud run services describe coffee-app \
     --region us-central1 \
     --format='value(status.url)')
   echo "$RUN_URL"
   curl -s -o /dev/null -w "%{http_code}\n" "$RUN_URL"
   ```

   Expected output:

   ```text
   https://coffee-app-xxxxxx-uc.a.run.app
   200
   ```

   A `200` response code confirms the Litestar app booted on Cloud Run and is reachable over HTTPS. (A first cold-start request can take ~30–60s while Direct VPC egress initializes — see Troubleshooting if it hangs.)

2. **Ask the app for a recommendation.** Note that `/api/chat/stream` enforces CSRF protection for browser form submissions; verify end-to-end Oracle + Vertex AI retrieval either by submitting a message in the browser UI from Step 7 or by querying the public catalog/health endpoints:

   ```shell
   curl -fsS "$RUN_URL/api/apex/vector/status"
   ```

   A `200` JSON payload reporting `"embeddingModel":"gemini-embedding-2"`, `"embeddingDimensions":3072`, and live `productCount` / `embeddedProductCount` totals from `10.10.0.10:1521/freepdb1` confirms `coffee-app` reached the private Oracle 26ai database over Direct VPC egress.

3. **Confirm the database VM has no public IP.** Query Compute Engine for the instance's external access configs:

   ```shell
   gcloud compute instances describe coffee-db \
     --zone us-central1-c \
     --format="value(networkInterfaces[0].accessConfigs)"
   ```

   The output is **empty**, confirming `coffee-db` has no external IP address.

4. **Confirm the database port is closed to the outside world.** From Cloud Shell — which lives **outside** `coffee-vpc` — test a TCP connection to `10.10.0.10:1521` with a short timeout:

   ```shell
   timeout 10 bash -c "</dev/tcp/10.10.0.10/1521" \
     && echo "REACHABLE (unexpected)" \
     || echo "BLOCKED as expected (no route / timeout)"
   ```

   This prints `BLOCKED as expected`. `10.10.0.10` is a private RFC1918 address inside `coffee-vpc`, and `coffee-allow-run-to-db` admits `tcp:1521` only from `10.10.1.0/24` (Cloud Run egress) and `10.30.0.0/24` (`coffee-build-pool`).

   Inspect the firewall rule directly:

   ```shell
   gcloud compute firewall-rules describe coffee-allow-run-to-db \
     --format="yaml(sourceRanges,allowed,targetTags)"
   ```

5. **Confirm migrations and APEX CDN configuration ran against the private database.** Inspect the most recent Cloud Build log:

   ```shell
   BUILD_ID=$(gcloud builds list --region us-central1 --limit=1 \
     --format='value(id)')
   gcloud builds log "$BUILD_ID" --region us-central1 \
     | grep -iE "Database Upgrade|APEX CDN|10\.10\.0\.10|SUCCESS" | head -20
   ```

   You should see `coffee upgrade` and `coffee configure-apex-cdn` completing against `10.10.0.10` from `coffee-build-pool`.

### Troubleshooting

If a check above failed, match the symptom below.

| Symptom | Likely cause | Fix |
|---|---|---|
| Cloud Run returns 5xx or the first request hangs ~1 min before succeeding | Direct VPC egress **cold-start connection delay** (~1 min while a new instance establishes its VPC path); `coffee-allow-run-to-db` missing `10.10.1.0/24`; or wrong `DATABASE_HOST` | Retry once the instance is warm. Verify the firewall: `gcloud compute firewall-rules describe coffee-allow-run-to-db --format="yaml(sourceRanges,allowed)"` must list `10.10.1.0/24` + `tcp:1521`. Verify env: `gcloud run services describe coffee-app --region us-central1 --format="value(spec.template.spec.containers[0].env)"` must show `DATABASE_HOST=10.10.0.10`. |
| `gcloud builds submit` `migrate` or `configure-apex` step hangs or fails to reach `10.10.0.10` | `coffee-db` still finishing initial 3–5 min Oracle boot, private pool not peered to `coffee-vpc`, or firewall missing `10.30.0.0/24` | Wait for `coffee-db` initialization, confirm `gcloud builds worker-pools describe coffee-build-pool --region us-central1`, and verify `coffee-allow-run-to-db` lists `10.30.0.0/24` and `gcloud services vpc-peerings list --network=coffee-vpc` shows an active peering. |
| `deploy-ords` fails with image not found (`ords:26.3`) | Step 5b was skipped or tagged with an older ORDS version | Re-run Step 5b to push `us-central1-docker.pkg.dev/${PROJECT_ID}/coffee-artifacts/ords:26.3`. |
| `Permission denied` during `gcloud run deploy` | Build SA missing `roles/run.admin` or `roles/iam.serviceAccountUser` | Grant on the project: `gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:coffee-build-sa@$PROJECT_ID.iam.gserviceaccount.com" --role="roles/run.admin"` and `--role="roles/iam.serviceAccountUser"`. |
| App or build step fails with a Secret Manager access-denied error | Run SA, ORDS SA, or Build SA missing `roles/secretmanager.secretAccessor`, or secret version missing | Grant `roles/secretmanager.secretAccessor` on `coffee-db-password` / `coffee-db-system-password` and confirm versions exist via `gcloud secrets versions list coffee-db-password`. |
| Chat returns a Vertex 503 / configuration error (app loads, recommendations fail) | `coffee-run-sa` missing `roles/aiplatform.user`, or `VERTEX_AI_PROJECT_ID` unset | Grant `roles/aiplatform.user` to `coffee-run-sa@$PROJECT_ID.iam.gserviceaccount.com` and verify `VERTEX_AI_PROJECT_ID=$PROJECT_ID` on `coffee-app`. |

## Clean up & costs

Cloud Run **scales to zero** — when idle, `coffee-app` and `coffee-ords` incur no compute charges. The ongoing cost in this lab is the private database VM (`coffee-db`, a standard `e2-standard-4`) and its 50 GB `pd-ssd` disk (`coffee-db-data`), plus Cloud NAT. If pausing between sessions, stop the VM to halt compute billing (disk storage continues to bill until destroyed):

```shell
gcloud compute instances stop coffee-db --zone us-central1-c
# Resume later with:
gcloud compute instances start coffee-db --zone us-central1-c
```

To stop **all** charges, destroy the stack completely:

1. **Review active services and builds:**

   ```shell
   gcloud run services list --region us-central1
   gcloud builds list --region us-central1 --limit=5
   ```

2. **Clear deletion protection on `coffee-db` if enabled:**

   ```shell
   gcloud compute instances update coffee-db \
     --zone us-central1-c --no-deletion-protection
   ```

3. **Destroy all Terraform-managed resources** (deletes `coffee-db-data` and all database contents):

   ```shell
   cd tools/deploy/terraform
   terraform destroy
   ```

   Review the plan and enter `yes`. Terraform destroys `coffee-app`, `coffee-ords`, `coffee-build-pool`, `coffee-db` and `coffee-db-data`, `coffee-artifacts`, `coffee-vpc` (subnets, firewall rules, router, NAT, `coffee-db-ip`, `coffee-buildpool-range`), service accounts, IAM bindings, and secrets (`coffee-db-password` and `coffee-db-system-password`).

4. **Sweep up any lingering resources created outside Terraform:**

   ```shell
   gcloud run services delete coffee-app --region us-central1 --quiet 2>/dev/null || true
   gcloud run services delete coffee-ords --region us-central1 --quiet 2>/dev/null || true
   gcloud iam service-accounts delete coffee-ords-sa@${PROJECT_ID}.iam.gserviceaccount.com --quiet 2>/dev/null || true
   gcloud artifacts repositories delete coffee-artifacts --location us-central1 --quiet 2>/dev/null || true
   gcloud compute addresses delete coffee-db-ip --region us-central1 --quiet 2>/dev/null || true
   gcloud compute addresses delete coffee-buildpool-range --global --quiet 2>/dev/null || true
   gcloud secrets delete coffee-db-password --quiet 2>/dev/null || true
   gcloud secrets delete coffee-db-system-password --quiet 2>/dev/null || true
   ```

5. **Confirm zero `coffee-*` resources remain:**

   ```shell
   gcloud compute instances list --filter="name~^coffee-"
   gcloud compute disks list --filter="name~^coffee-"
   gcloud compute addresses list --filter="name~^coffee-"
   gcloud compute networks list --filter="name~^coffee-"
   gcloud run services list --region us-central1 --filter="metadata.name~^coffee-"
   gcloud artifacts repositories list --location us-central1 --filter="name~coffee-"
   gcloud builds worker-pools list --region us-central1 --filter="name~coffee-"
   gcloud secrets list --filter="name~coffee-"
   ```

   Empty output across every command confirms the lab stack is completely torn down.
