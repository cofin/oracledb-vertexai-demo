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

## Clean up & costs
