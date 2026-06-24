# PRD: cloudrun-ords-deploy

*Link: [./specs/cloudrun-ords-deploy/](./specs/cloudrun-ords-deploy/)*
*Beads: oracledb-vertexai-ords (master epic)*
*Research: [../research/research_ords_cloudrun_deploy/](../research/research_ords_cloudrun_deploy/)*

Deploy Oracle REST Data Services (ORDS) on Google Cloud Run to provide a scalable, serverless HTTP front-end for the GCE database, enabling Oracle APEX applications and REST APIs.

## North Star Goal
Deploy ORDS as a serverless Cloud Run service (`coffee-ords`) peered to the private GCE database VPC via Direct VPC egress, using Secret Manager for secure credential access, and Oracle CDN for APEX static assets to maintain a stateless container profile.

---

## Scope & Requirements

### 1. Image Management
*   Cloud Run cannot pull directly from the authenticated Oracle Container Registry.
*   We must re-host the official ORDS image `container-registry.oracle.com/database/ords:26.1.2` inside the project's private Google Artifact Registry (`coffee-artifacts/ords:26.1.2`).

### 2. Network & Connectivity
*   ORDS runs in Cloud Run with Direct VPC egress enabled, using `coffee-vpc` and `coffee-run-subnet`.
*   Connects to the GCE DB internal IP `10.10.0.10:1521/freepdb1`.
*   Firewall rules (`coffee-allow-run-to-db`) must admit traffic from ORDS Cloud Run egress.

### 3. Credential Security
*   The database administrative password (`SYS/system`) is required for ORDS to perform startup configuration checks.
*   This password must be injected from Secret Manager (`coffee-db-system-password`) into the container environment variable `ORACLE_PWD`.

### 4. Stateless APEX Static Assets
*   Instead of hosting static assets locally or mounting FUSE storage, APEX must be configured to load all system assets (CSS, JS, images) from Oracle's public CDN: `https://static.oracle.com/cdn/apex/26.1.0/` (or matching APEX version).
*   A post-migration SQL script must run to set the `IMAGE_PREFIX` parameter in the database.

---

## Architecture Contract

| Item | Value |
|---|---|
| Cloud Run Service | `coffee-ords` (port `8080`, gen2, Direct VPC egress) |
| Image | `us-central1-docker.pkg.dev/$PROJECT/coffee-artifacts/ords:26.1.2` |
| VPC & Subnet | `coffee-vpc` / `coffee-run-subnet` |
| Secret env | `ORACLE_PWD=coffee-db-system-password:latest` |
| Connectivity | target `10.10.0.10:1521/freepdb1` |
| APEX CDN | `https://static.oracle.com/cdn/apex/26.1.0/` |

---

## Sagas / Chapters

### Chapter 1: Image Re-hosting and script prep (`ords-image-prep`)
*   **Objective**: Stage the ORDS image in Artifact Registry and create the CDN configuration SQL script.
*   **Deliverables**:
    *   Command documentation for pulling, tagging, and pushing ORDS image.
    *   `tools/deploy/gcp/configure-apex-cdn.sql` script to update `IMAGE_PREFIX` in the DB.
*   **Beads**: `oracledb-vertexai-ords.1`

### Chapter 2: Terraform Infrastructure (`ords-terraform`)
*   **Objective**: Add ORDS Cloud Run service to the Terraform stack.
*   **Deliverables**:
    *   `tools/deploy/terraform/ords.tf` containing `google_cloud_run_v2_service` for ORDS, IAM bindings, and Secret Manager accessor bindings.
    *   Updated `network.tf` to ensure ORDS subnet egress is admitted by the firewall.
*   **Beads**: `oracledb-vertexai-ords.2`

### Chapter 3: Pipeline Integration (`ords-pipeline`)
*   **Objective**: Automate the CDN configuration as part of the Cloud Build deployment.
*   **Deliverables**:
    *   Updated `tools/deploy/gcp/cloudbuild.yaml` to execute `configure-apex-cdn.sql` using SQLcl/sqlplus (or `coffee` runner) inside the peered private pool after the migration step.
*   **Beads**: `oracledb-vertexai-ords.3`

### Chapter 4: Lab Walkthrough & Verification (`ords-lab-walkthrough`)
*   **Objective**: Update the hands-on lab with ORDS instructions.
*   **Deliverables**:
    *   New sections in `docs/lab-cloud-run.md` guiding the student through ORDS setup, accessing the APEX workspace, and verifying the deployment.
*   **Beads**: `oracledb-vertexai-ords.4`
