# Research: Deploying Oracle REST Data Services (ORDS) on Google Cloud Run

**Research ID**: `research_ords_cloudrun_deploy`
**Topic**: Deploying ORDS on Cloud Run, scalability, connection pooling, and APEX static asset serving.
**Status**: Complete
**Created**: 2026-06-24

---

## Executive Summary

1.  **Feasibility**: Deploying ORDS on Cloud Run is highly feasible and recommended. ORDS is a stateless, Java-based servlet runner that scales to zero and scales up dynamically, making it a perfect fit for Cloud Run.
2.  **Database Connectivity**: Connection to the private GCE Oracle DB is established over **Direct VPC egress** (using the same `coffee-vpc` and `coffee-run-subnet` as the python app), targeting the static internal IP `10.10.0.10:1521/freepdb1`.
3.  **Secret Management**: The database administrative password (SYS/SYSTEM) is required for ORDS initialization. It is securely injected via Secret Manager as `ORACLE_PWD` at runtime, avoiding plain-text exposure in configuration files or deployment logs.
4.  **Static Asset Serving (APEX /i/)**: To run APEX, ORDS requires static files. The recommended serverless pattern is to **use Oracle's public CDN** (`https://static.oracle.com/cdn/apex/...`) by updating the `IMAGE_PREFIX` parameter in the database instance admin settings. This avoids baking 200MB+ of assets into the Docker image or mounting FUSE storage.
5.  **Image Registry gotcha**: Oracle Container Registry requires authentication. To deploy on Cloud Run, the ORDS image must be pulled locally once (or in a secure builder stage), tagged, and pushed to the project's private GCP Artifact Registry (`coffee-artifacts/ords:26.1.2`), allowing Cloud Run to pull it without external credentials.

---

## Codebase Analysis

### Existing Local Setup
*   **Source File**: `tools/oracle/ords.py`
*   **Local Container Run**: Runs `container-registry.oracle.com/database/ords:26.1.2` as a sidecar container.
*   **Local Configuration**:
    *   Envs passed: `DBHOST`, `DBPORT`, `DBSERVICENAME`, and `ORACLE_PWD`.
    *   Volume mount: Mounts local APEX images (`/opt/oracle/apex/images`) to container `/opt/oracle/apex/images` to serve static assets at `/i/`.
    *   Port mapping: Maps host `8443` (HTTPS) and `8181` (HTTP).

### GCE VM Stack (Ch2)
*   The DB VM runs `gvenzl/oracle-free:latest` which does **not** have APEX/ORDS pre-installed.
*   If ORDS is deployed to Cloud Run, it will run the initial database registration (`ords install`) on its very first boot, utilizing the `ORACLE_PWD` credentials. Once registered, subsequent container cold starts only verify the schema and boot.

---

## Technology & Documentation Analysis

### 1. Stateless ORDS Configuration
ORDS requires a configuration directory (`/etc/ords/config`) to operate.
*   **Cold Start behavior**: In a serverless environment like Cloud Run, the container starts fresh on cold starts. Because the `/etc/ords/config` is ephemeral, the container entrypoint script runs `ords install` validation on every boot.
*   **Database Schema Registry**: Since the database is persistent (on GCE), the ORDS schema is already installed after the first container boots. On subsequent cold starts, ORDS detects the schema is present, generates the configuration in memory, and starts the servlet.
*   **Latency**: The installation check and configuration generation add a minor delay (estimated 5-10s) to cold starts. This is acceptable for a demo but would require pre-baked config files or FUSE volume mounting for production-grade latency.

### 2. Connectivity & Security
*   **VPC Peering**: Cloud Run communicates with the private GCE VM (`10.10.0.10`) via Direct VPC egress. The firewall rule `coffee-allow-run-to-db` must be updated to allow traffic from the ORDS Cloud Run service account/subnet.
*   **Secret Manager Integration**: Cloud Run supports mapping Secret Manager secret versions directly to environment variables. The `coffee-db-system-password` (SYS password) is mapped to `ORACLE_PWD` for the ORDS service.

### 3. APEX Static Assets (`IMAGE_PREFIX`)
APEX applications load JavaScript, CSS, and images from the URL prefix defined by `IMAGE_PREFIX`.
*   **Default**: `/i/` (requires ORDS to serve them locally).
*   **CDN Pattern**: We can change this prefix to Oracle's CDN. For example, for APEX 26.1:
    ```sql
    BEGIN
        apex_instance_admin.set_parameter(
            p_parameter => 'IMAGE_PREFIX',
            p_value     => 'https://static.oracle.com/cdn/apex/26.1.0/'
        );
        COMMIT;
    END;
    /
    ```
*   **Deployment Integration**: This SQL block can be executed during the `coffee upgrade` migration step (conditional on environment) or as a post-deployment database configuration script in the Cloud Build pipeline.
*   **Local Development**: Local dev continues to use the offline `/i/` mount to ensure offline capability.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|:---|:---|:---|:---|
| **Cold Start Latency** | High | Medium | Acceptable for demo. Can be optimized by pre-configuring ORDS and copying the config directory into a custom Docker image. |
| **SYS Password Exposure** | Medium | Low | Limit IAM access to `coffee-db-system-password` secret strictly to the ORDS Cloud Run service identity. The DB is private and unreachable from the public internet. |
| **Oracle Registry Credentials** | High | High | Re-host the image in GCP Artifact Registry. Pull `container-registry.oracle.com/database/ords:26.1.2` locally, tag it, and push it to `us-central1-docker.pkg.dev/$PROJECT/coffee-artifacts/ords:26.1.2`. |
| **Database Connection Limits** | Low | Medium | ORDS scales dynamically. If Cloud Run scales up ORDS instances, they could exhaust database sessions. Configure `jdbc.MaxLimit` or set concurrency limits on the Cloud Run service. |

---

## Recommended Approach

1.  **Registry Hosting**: Add a step to the lab (or setup instructions) to pull the official ORDS image locally and push it to the project's GCP Artifact Registry:
    ```shell
    docker pull container-registry.oracle.com/database/ords:26.1.2
    docker tag container-registry.oracle.com/database/ords:26.1.2 us-central1-docker.pkg.dev/$PROJECT_ID/coffee-artifacts/ords:26.1.2
    docker push us-central1-docker.pkg.dev/$PROJECT_ID/coffee-artifacts/ords:26.1.2
    ```
2.  **Terraform Configuration**:
    *   Declare a new Cloud Run service `coffee-ords` running the re-hosted image.
    *   Configure Direct VPC egress pointing to `coffee-vpc` and `coffee-run-subnet`.
    *   Map the environment variables:
        *   `DBHOST = "10.10.0.10"`
        *   `DBPORT = 1521`
        *   `DBSERVICENAME = "freepdb1"`
    *   Wire the secret `coffee-db-system-password` to the `ORACLE_PWD` env var.
3.  **Database Configuration (CDN)**:
    *   Create a post-setup script `tools/deploy/gcp/configure-apex-cdn.sql` containing the PL/SQL block to set `IMAGE_PREFIX` to Oracle's CDN.
    *   Execute this script in the Cloud Build pipeline using a peered private build pool runner after database migration.
4.  **Lab Walkthrough Updates**:
    *   Add a new section in the lab explaining ORDS deployment and how to test it (e.g. accessing `https://<ords-url>/ords/apex`).
