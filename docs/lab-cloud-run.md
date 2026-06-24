# Hands-on Lab: Cymbal Coffee on Cloud Run — Private Oracle 26ai DB + Cloud Build

This is the **production-shaped** path: the Litestar web application runs on Google Cloud Run, while the Oracle 26ai database runs on a Container-Optimized OS Compute Engine virtual machine with a persistent disk and no external IP address, completely isolated from the public internet. A Cloud Build pipeline handles the automated build, database migration, and service deployment.

Welcome to the **Cymbal Coffee Cloud Run Hands-on Lab**. In this workshop, you will step-by-step deploy, configure, and run a premium next-generation AI-powered coffee recommendation application using real Google Cloud and Oracle resources. For complete background concepts and documentation material, please visit the official [Cymbal Coffee Documentation Site](https://cofin.github.io/oracledb-vertexai-demo/index.html).

This lab is advanced and follows the [Single-VM GCE lab](lab-gce.md). We recommend completing the single-VM lab first to familiarize yourself with the application codebase and basic operation.

---

## Prerequisites & Audience Expectations

- **GCP Knowledge**: Comfort with Google Cloud Platform, including basic familiarity with Google Cloud Run, Cloud Build, Artifact Registry, virtual private clouds (VPCs), and Terraform.
- **Tools Required**: A web browser and access to a Google Cloud Console account with billing or credits enabled.

> **Note:** Unlike the single-VM lab, this architecture provisions a persistent, standard VM instance and regional networking services that do not scale to zero. Be sure to follow the cleanup instructions at the end of the lab to avoid ongoing charges.

---

## Step 1: Google Cloud Environment Setup

In this first step, you will initialize your cloud workspace and export the environment variables required for the deployment commands.

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

> **Note:** The `$PROJECT_ID` environment variable is reused dynamically in build pipelines, container image paths, and worker pool resource paths. Ensure it is correctly resolved before continuing.

---

## Step 2: Enable Google Cloud APIs

In this step, you will enable the necessary Google Cloud APIs required to orchestrate networking, compute, containers, security, database storage, and Vertex AI.

1. Enable the Google Cloud Services APIs with the following command:

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

> **Note:** Enabling these APIs can take a minute or two. The `servicenetworking` API is required to peer the Cloud Build private pool with your VPC subnet, and the `aiplatform` API enables the Litestar application to communicate with Google Vertex AI for text embeddings and chat orchestration at runtime.

---

## Step 3: Clone the Repository

In this step, you will clone the Cymbal Coffee application codebase and navigate to the Terraform infrastructure directory.

1. Clone the project repository and move into the deployment directory:

```shell
git clone https://github.com/cofin/oracledb-vertexai-demo.git
cd oracledb-vertexai-demo/tools/deploy/terraform
```

> **Note:** All subsequent `terraform` commands must be run from the `tools/deploy/terraform` directory. The Cloud Build pipeline configuration is located in the sibling directory at `../gcp/cloudbuild.yaml`.

---

## Step 4: Configure Your Deployment Variables

Before running Terraform, you must define your local project variables by writing them to a `terraform.tfvars` file.

1. Create a `terraform.tfvars` file using a shell heredoc:

```shell
cat > terraform.tfvars <<EOF
project_id          = "${PROJECT_ID}"
region              = "us-central1"
db_password         = "SuperSecret1"
db_system_password  = "SuperSecretSYS1"
EOF
```

> **Note:** The `terraform.tfvars` file is explicitly ignored by version control (.gitignore) to prevent sensitive secrets from being committed to public repositories. In a production environment, you should use cryptographically secure passwords.

> **Note:** `db_password` represents the Oracle application user password (`DATABASE_PASSWORD`) which will be accessed by Cloud Run, the build pool migration step, and the VM container initialization. `db_system_password` represents the Oracle administrative SYS/SYSTEM password, which is consumed only by the GCE VM cloud-init process at boot.

---

## Step 5: Stand Up the Infrastructure with Terraform

In this step, you will initialize the Terraform providers and apply the configuration to build your private VPC, VM instance, Artifact Registry, worker pool, and access control policies.

1. Initialize the Terraform backend and plugins:

```shell
terraform init
```

2. Review and apply the configuration:

```shell
terraform apply -auto-approve
```

Once the application of the infrastructure finishes, Terraform will have provisioned the following resources:
- **Networking** — A custom VPC (`coffee-vpc`) with a subnet for the DB VM (`coffee-subnet`, `10.10.0.0/24`), a subnet for Cloud Run egress (`coffee-run-subnet`, `10.10.1.0/24`), a Cloud Router/NAT for internet access, and a peered range (`10.30.0.0/24`) for the Cloud Build private pool.
- **Database VM** — A Container-Optimized OS VM (`coffee-db`) with a static internal IP (`10.10.0.10`) and a persistent data disk mounted at `/opt/oracle/oradata`. It runs the `gvenzl/oracle-free` database image container on port 1521.
- **Artifact Registry & Build Pool** — A Docker repository (`coffee-artifacts`) and a Cloud Build private worker pool (`coffee-build-pool`) peered to the custom VPC.
- **Secrets & IAM** — The `coffee-db-password` secret in Secret Manager and service accounts with minimal necessary permissions.

> **Note:** The Oracle database VM is private by design. It does not possess a public external IP. Ingress is restricted via firewall rules (`coffee-allow-run-to-db`) to only allow traffic on port 1521 from the Cloud Run egress subnet (`10.10.1.0/24`) and the Cloud Build private pool range (`10.30.0.0/24`). SSH access is allowed only via Identity-Aware Proxy (IAP) tunnels.

> **Note:** The initial boot of the Oracle DB container can take 3 to 5 minutes as it sets up the container entrypoints and mounts the persistent disk.

---

## Step 6: Build and Deploy with Cloud Build

In this step, you will submit your build to the Cloud Build private pool. The build pipeline compiles the application Docker image, pushes it to your Artifact Registry, executes database migrations, and deploys the Cloud Run service.

1. Run the build submission from the `tools/deploy/terraform` directory:

```shell
gcloud builds submit \
  --config ../gcp/cloudbuild.yaml \
  --region=$REGION \
  --substitutions=_PROJECT=$PROJECT_ID,_REGION=$REGION
```

The pipeline operates in three stages:
1. **Build and Push** — Builds the app container image and pushes tags for both the Git SHA and `:latest` to `us-central1-docker.pkg.dev/$PROJECT_ID/coffee-artifacts/coffee-app`.
2. **Migrate** — Spawns the container on the peered private pool and runs `coffee upgrade` to apply database migrations and load committed-embedding fixtures.
3. **Deploy** — Configures the Cloud Run service (`coffee-app`) with Direct VPC egress, wires Secret Manager credentials, and connects it to the Vertex AI platform.

> **Note:** The migration step successfully reaches the private database because it runs on the peered regional worker pool (`coffee-build-pool`) rather than the default public Google shared builders. Because our committed fixtures under `src/app/db/fixtures/` already contain pre-calculated vector embeddings, database migration executes immediately without requiring any external Vertex AI API calls at build time.

---

## Step 7: Open Cymbal Coffee and Ask a Question

In this step, you will locate your newly deployed Cloud Run URL, access the live frontend, and test the multi-agent chat interface.

1. Retrieve the public HTTPS endpoint URL of your service:

```shell
gcloud run services describe coffee-app \
  --region=$REGION \
  --format='value(status.url)'
```

2. Open the printed URL in a new browser tab.
3. In the chat interface, enter a query such as:
   ```
   I need something bold
   ```
4. Press Enter. Confirm that the application returns a response containing specific coffee suggestions (like a French Roast or Dark Roast Espresso) from the database.

> **Note:** The successful response proves that the public-facing Cloud Run service successfully routed requests through its Direct VPC egress interface to query the private database at `10.10.0.10:1521/freepdb1` and leveraged Vertex AI to embed your chat search query.

---

## Advanced Challenge Tasks for Workshop Graduates

Once the core application is up and running, challenge yourself or your participants with the following real-world architectural expansion exercises:

### Challenge 1: Wire a GitHub Push to a Cloud Build Trigger (Real CI/CD)

**Objective:** Automate the deployment pipeline so that pushing a code update to your `main` branch automatically triggers the Cloud Build flow on your private pool.

- **Step A: Connect the GitHub Repository to Cloud Build** Run the command to initialize a regional GitHub connection resource:

```shell
gcloud builds connections create github coffee-github \
  --region=$REGION
```

> **Note:** This command initiates a connection resource. To complete the authentication, you must open the Google Cloud Console, navigate to **Cloud Build** -> **Repositories**, click **Connect Repository**, select `coffee-github`, and authorize access via GitHub OAuth.

- **Step B: Create the Push Trigger** Provision a trigger that targets your repository, branch, and private pool:

```shell
gcloud builds triggers create github \
  --name=coffee-deploy-on-push \
  --region=$REGION \
  --repository=projects/$PROJECT_ID/locations/$REGION/connections/coffee-github/repositories/oracledb-vertexai-demo \
  --branch-pattern='^main$' \
  --build-config=tools/deploy/gcp/cloudbuild.yaml \
  --substitutions=_PROJECT=$PROJECT_ID,_REGION=$REGION
```

- **Step C: Test the Trigger** Make a minor change (e.g., in a documentation file or template), commit it, and push it to the `main` branch of your fork. Verify that the build starts automatically under **Cloud Build** -> **History** in the Google Cloud Console.

---

### Challenge 2: Replace the Static Internal IP with a Cloud DNS Private Name

**Objective:** Abstract the database host configuration by fronting the VM with a stable, private DNS name (such as `db.coffee.internal`) rather than pointing directly to the IP address.

- **Step A: Create a Private DNS Zone** Provision a DNS zone visible only inside the custom VPC network:

```shell
gcloud dns managed-zones create coffee-internal \
  --dns-name=coffee.internal. \
  --description="Private zone for Cymbal Coffee" \
  --visibility=private \
  --networks=coffee-vpc
```

- **Step B: Add an A Record for the Database VM** Add a DNS record resolving `db.coffee.internal` to the database VM internal IP (`10.10.0.10`):

```shell
gcloud dns record-sets create db.coffee.internal. \
  --zone=coffee-internal \
  --type=A \
  --ttl=300 \
  --rrdatas=10.10.0.10
```

- **Step C: Update the Cloud Run Service Configuration** Re-configure the Cloud Run service environment variables to target the private DNS hostname:

```shell
gcloud run services update coffee-app \
  --region=$REGION \
  --update-env-vars=DATABASE_HOST=db.coffee.internal
```

---

### Challenge 3: Move Terraform State to a GCS Backend

**Objective:** Replace the local state file backend (`terraform.tfstate`) with a versioned Google Cloud Storage bucket backend to support state locking and multi-developer collaboration.

- **Step A: Create a Versioned Cloud Storage Bucket** Provision a bucket with object versioning enabled to store state history:

```shell
gcloud storage buckets create gs://${PROJECT_ID}-coffee-tfstate \
  --location=us-central1 \
  --uniform-bucket-level-access
gcloud storage buckets update gs://${PROJECT_ID}-coffee-tfstate --versioning
```

- **Step B: Configure the Remote Backend in Terraform** Create a file named `backend.tf` in the `tools/deploy/terraform` directory (replace `REPLACE_WITH_YOUR_PROJECT_ID` with your actual GCP project ID):

```hcl
terraform {
  backend "gcs" {
    bucket = "REPLACE_WITH_YOUR_PROJECT_ID-coffee-tfstate"
    prefix = "coffee/state"
  }
}
```

- **Step C: Migrate the Local State to GCS** Run the initialization command and authorize state migration:

```shell
terraform init -migrate-state
```

---

<!-- Owned by Ch6 (cloudrun-lab-verification-teardown): do not author here. -->
## Verify your deployment

These checks prove two things at once: the app works end-to-end, and the Oracle database is private — reachable by Cloud Run but not by the public internet (including this Cloud Shell).

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

   A `200` response code means the Litestar app booted on Cloud Run and is publicly reachable over HTTPS. (A first request may take ~30-60s while a cold instance starts and establishes its Direct VPC egress path — see Troubleshooting if it hangs.)

2. **Ask the app for a recommendation.** This single request proves the full private path works — Cloud Run reaching the **private** Oracle DB at `10.10.0.10:1521` for vector search and Vertex AI for embeddings, then rendering a grounded answer from Oracle rows:

   ```shell
   curl -sN "$RUN_URL/api/chat/stream" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     --data-urlencode "message=Recommend a smooth cold brew" \
     --data-urlencode "persona=enthusiast" \
     | head -40
   ```

   You should see Server-Sent Event lines (`event: ...` / `data: ...`) ending in a `final` event whose payload names a real Cymbal Coffee product. A grounded product name (e.g. a real menu item with a price) confirms the app reached the private Oracle DB **and** Vertex — if either were unreachable the stream would emit an `error` event instead.

3. **Confirm the database VM has no public IP.** Ask Compute Engine for the instance's external access configs:

   ```shell
   gcloud compute instances describe coffee-db \
     --zone us-central1-c \
     --format="value(networkInterfaces[0].accessConfigs)"
   ```

   The output is **empty**. An empty `accessConfigs` means `coffee-db` has no external IP at all — there is no public address the internet could dial.

   Expected output:
   ```text

   ```

4. **Confirm the database port is closed to the outside world.** From Cloud Shell — which lives **outside** `coffee-vpc` — try to open a TCP connection to the database's private IP and port, with a short timeout:

   ```shell
   timeout 10 bash -c "</dev/tcp/10.10.0.10/1521" \
     && echo "REACHABLE (unexpected!)" \
     || echo "BLOCKED as expected (no route / timeout)"
   ```

   This prints `BLOCKED as expected`. `10.10.0.10` is a **private** address inside `coffee-vpc`; Cloud Shell has no route to it, and even with a route the `coffee-allow-run-to-db` firewall rule admits `tcp:1521` **only** from the Cloud Run egress range `10.10.1.0/24` and the build-pool range `10.30.0.0/24` — nothing else. The database is private by construction.

   You can optionally inspect the rule to see the two admitted ranges and the `coffee-db` target tag:

   ```shell
   gcloud compute firewall-rules describe coffee-allow-run-to-db \
     --format="yaml(sourceRanges,allowed,targetTags)"
   ```

5. **Confirm migrations ran against the private database.** The deploy pipeline's migrate step ran `coffee upgrade` from the **private build pool** (`coffee-build-pool`), the only Cloud Build path peered into `coffee-vpc`. Inspect the most recent build's log:

   ```shell
   BUILD_ID=$(gcloud builds list --region us-central1 --limit=1 \
     --format='value(id)')
   gcloud builds log "$BUILD_ID" --region us-central1 \
     | grep -iE "coffee upgrade|migration|10\.10\.0\.10|SUCCESS" | head -20
   ```

   You should see the `coffee upgrade` step connecting to `10.10.0.10` and a `SUCCESS` status for the build. This proves the schema + committed-embedding fixtures were applied to the private DB from inside the VPC — no public DB exposure was needed.

### Troubleshooting

If a check above failed, find the symptom below.

| Symptom | Likely cause | Fix |
|---|---|---|
| Cloud Run returns 5xx or the request hangs ~1 min, then the chat stream errors connecting to the DB | Direct VPC egress **cold-start connection delay** (~1 min while a new instance establishes its VPC path); or `coffee-allow-run-to-db` not admitting `10.10.1.0/24`; or wrong `DATABASE_HOST` env | Retry once the instance is warm. Verify the firewall: `gcloud compute firewall-rules describe coffee-allow-run-to-db --format="yaml(sourceRanges,allowed)"` must list `10.10.1.0/24` + `tcp:1521`. Verify env: `gcloud run services describe coffee-app --region us-central1 --format="value(spec.template.spec.containers[0].env)"` must show `DATABASE_HOST=10.10.0.10`. |
| `gcloud builds submit` migrate step hangs or fails to reach the DB | Private pool **not peered** to `coffee-vpc`, missing `servicenetworking` connection, or firewall not admitting the build-pool range `10.30.0.0/24` | Confirm the pool: `gcloud builds worker-pools describe coffee-build-pool --region us-central1`. Confirm the firewall admits the pool range (`coffee-allow-run-to-db` lists `10.30.0.0/24`). Confirm the reserved peering range `coffee-buildpool-range` and the servicenetworking peering exist (`gcloud compute addresses describe coffee-buildpool-range --global` / `gcloud services vpc-peerings list --network=coffee-vpc`). |
| `Permission denied` during `gcloud run deploy` (the deploy step of the build) | Build SA missing `roles/run.admin` or `roles/iam.serviceAccountUser` (needed to act-as the run SA) | Grant on the project: `gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:coffee-build-sa@$PROJECT_ID.iam.gserviceaccount.com" --role="roles/run.admin"` and again with `--role="roles/iam.serviceAccountUser"`. |
| App or build step fails with a Secret Manager access-denied error | Run SA or build SA missing `roles/secretmanager.secretAccessor`, or the `coffee-db-password` secret has no version | Grant accessor to the failing SA (`coffee-run-sa@...` and/or `coffee-build-sa@...`) on the secret: `gcloud secrets add-iam-policy-binding coffee-db-password --member="serviceAccount:coffee-run-sa@$PROJECT_ID.iam.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"`. Confirm a version exists: `gcloud secrets versions list coffee-db-password`. |
| Chat returns a Vertex 503 / permission error (app loads but recommendations fail) | Run SA missing `roles/aiplatform.user`, or `VERTEX_AI_PROJECT_ID` unset/placeholder on the service | Grant: `gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:coffee-run-sa@$PROJECT_ID.iam.gserviceaccount.com" --role="roles/aiplatform.user"`. Verify env: the run service must set `VERTEX_AI_PROJECT_ID=$PROJECT_ID` and `VERTEX_AI_LOCATION=us-central1` (check via `gcloud run services describe coffee-app --region us-central1 --format="value(spec.template.spec.containers[0].env)"`). |
| Image pull fails / `gcloud run deploy` cannot find the image / push fails | Artifact Registry API not enabled, repo `coffee-artifacts` missing, or build SA missing `roles/artifactregistry.writer` | Enable + verify: `gcloud services enable artifactregistry.googleapis.com`; `gcloud artifacts repositories describe coffee-artifacts --location us-central1`; grant `gcloud artifacts repositories add-iam-policy-binding coffee-artifacts --location us-central1 --member="serviceAccount:coffee-build-sa@$PROJECT_ID.iam.gserviceaccount.com" --role="roles/artifactregistry.writer"`. |

Most failures are IAM or firewall scope, not app code. The app itself is unchanged from the local loop (only `DATABASE_HOST` and Vertex env differ). Cold-start connection delay (T1) is expected behavior during initial routing setup over Direct VPC egress, not a system failure.

## Clean up & costs

Cloud Run **scales to zero** — when no one is using `coffee-app`, it costs nothing. The dominant cost in this lab is the database: the `coffee-db` VM (an always-on `e2-standard-4`) and its attached persistent disk (`coffee-db-data`, a 50GB pd-ssd) bill **continuously**, whether or not anyone is using the app. Because that VM never scales to zero, **this lab burns credits faster than the single-Spot-VM GCE-only lab.** If you are pausing between sessions, stop the VM to cut compute cost (the disk still bills for storage):

```shell
gcloud compute instances stop coffee-db --zone us-central1-c
# ...resume later with:
gcloud compute instances start coffee-db --zone us-central1-c
```

For a smaller footprint you can right-size the VM (e.g. a smaller machine type) in `tools/deploy/terraform/` and re-apply. To stop **all** charges, tear the stack down completely with the steps below.

1. **Stop new traffic and note the deploy artifacts.** Cloud Run revisions and finished builds do not bill for compute once idle, but `terraform destroy` removes the service for you. There is nothing to stop manually for Cloud Build (builds are ephemeral). You can review what exists before destroying:

   ```shell
   gcloud run services list --region us-central1
   gcloud builds list --region us-central1 --limit=5
   ```

2. **Clear delete protection so the stack can be destroyed.** The database VM and disk may be guarded against accidental deletion. If the Terraform config sets `deletion_protection = true` on `coffee-db` or a `prevent_destroy` lifecycle on the disk/addresses, remove or set those to `false` in `tools/deploy/terraform/` and re-apply once, or clear protection directly:

   ```shell
   gcloud compute instances update coffee-db \
     --zone us-central1-c --no-deletion-protection
   ```

   (If no protection was set, this is a harmless no-op.)

3. **Destroy the whole stack.** From the Terraform root, destroy every managed resource. **This deletes the persistent disk `coffee-db-data` and all database data** — that data loss is intended at teardown:

   ```shell
   cd tools/deploy/terraform
   terraform destroy
   ```

   Review the plan and confirm with `yes`. Terraform removes, in dependency order: the Cloud Run service `coffee-app`, the Cloud Build private pool `coffee-build-pool`, the `coffee-db` VM and its `coffee-db-data` disk, the Artifact Registry repo `coffee-artifacts` (and the images in it), the VPC `coffee-vpc` with its subnets/firewall/router/NAT, the reserved internal IP `coffee-db-ip` and peering range `coffee-buildpool-range`, the IAM bindings, and the `coffee-db-password` secret.

4. **Sweep up anything Terraform left behind.** Most resources are gone after `terraform destroy`. A few can linger if they were created outside Terraform or guarded — delete them explicitly so nothing keeps billing:

   ```shell
   # Artifact Registry images (if the repo or images outlived the repo resource)
   gcloud artifacts repositories delete coffee-artifacts \
     --location us-central1 --quiet 2>/dev/null || true

   # Reserved addresses (regional internal IP + global peering range)
   gcloud compute addresses delete coffee-db-ip \
     --region us-central1 --quiet 2>/dev/null || true
   gcloud compute addresses delete coffee-buildpool-range \
     --global --quiet 2>/dev/null || true

   # The DB password secret
   gcloud secrets delete coffee-db-password --quiet 2>/dev/null || true
   ```

5. **Confirm nothing is left.** Each command below should return **no `coffee-*` rows**:

   ```shell
   gcloud compute instances list        --filter="name~^coffee-"
   gcloud compute disks list            --filter="name~^coffee-"
   gcloud compute addresses list        --filter="name~^coffee-"
   gcloud compute networks list         --filter="name~^coffee-"
   gcloud run services list --region us-central1 --filter="metadata.name~^coffee-"
   gcloud artifacts repositories list --location us-central1 --filter="name~coffee-"
   gcloud builds worker-pools list --region us-central1 --filter="name~coffee-"
   gcloud secrets list --filter="name~coffee-"
   ```

   Empty output across the board means the stack is fully torn down and nothing is billing. You can now safely close the lab.

