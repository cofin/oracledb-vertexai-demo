# Flow Spec: ords-image-prep

*Beads: `oracledb-vertexai-ords.2`*
*Parent PRD: [../cloudrun-ords-deploy/prd.md](../cloudrun-ords-deploy/prd.md)*
*Depends on: none*
*Status: Completed*

---

## Context
Before deploying ORDS to Cloud Run, we need to prepare the container image and database configuration.
1.  **Image Prep**: Pull the official ORDS image from Oracle Container Registry, tag it, and push it to Google Artifact Registry. This is required because Cloud Run cannot authenticate to Oracle Registry at deployment runtime.
2.  **APEX CDN Config**: Create a SQL script that updates APEX to use Oracle's CDN for static files, keeping the ORDS deployment stateless.

---

## Architecture/Prose

### Image Re-hosting to Google Artifact Registry

Cloud Run cannot directly authenticate with the Oracle Container Registry to pull container images. Therefore, the official ORDS image must be re-hosted in the project's private Google Artifact Registry.

Follow these commands to pull, tag, and push the image:

1. **Authenticate to Oracle Container Registry**:
   ```bash
   docker login container-registry.oracle.com
   ```
   *Note: Provide your Oracle Single Sign-On (SSO) credentials when prompted.*

2. **Pull the official ORDS 26.1.2 image**:
   ```bash
   docker pull container-registry.oracle.com/database/ords:26.1.2
   ```

3. **Authenticate Docker to Google Artifact Registry**:
   ```bash
   gcloud auth configure-docker us-central1-docker.pkg.dev
   ```

4. **Tag the image for Google Artifact Registry**:
   ```bash
   # Replace $PROJECT_ID with your active GCP project ID
   docker tag container-registry.oracle.com/database/ords:26.1.2 us-central1-docker.pkg.dev/$PROJECT_ID/coffee-artifacts/ords:26.1.2
   ```

5. **Push the image to Artifact Registry**:
   ```bash
   docker push us-central1-docker.pkg.dev/$PROJECT_ID/coffee-artifacts/ords:26.1.2
   ```

---

## Requirements

1.  **Image Re-hosting Instructions**:
    *   Document the exact commands to pull `container-registry.oracle.com/database/ords:26.1.2`, tag, and push to `us-central1-docker.pkg.dev/$PROJECT_ID/coffee-artifacts/ords:26.1.2`.
2.  **APEX CDN SQL Script**:
    *   Path: `tools/deploy/gcp/configure-apex-cdn.sql`
    *   Content: A PL/SQL block executing `apex_instance_admin.set_parameter('IMAGE_PREFIX', 'https://static.oracle.com/cdn/apex/26.1.0/')` and committing.
    *   Must run safely as `SYSDBA` (using SQLcl or sqlplus).
    *   Must be idempotent (subsequent runs are no-ops).

---

## Implementation Tasks

- [x] Document image re-hosting commands in this spec (under Architecture/Prose).
- [x] Create `tools/deploy/gcp/configure-apex-cdn.sql` with the PL/SQL block.
- [x] Add a local developer verification script or instructions to test APEX CDN updates locally (with options to revert to `/i/`).

---

## Verification

### Local Verification
1.  Run the CDN config script locally on the container using OS authentication:
    ```bash
    # Run the SQL script on local DB container
    docker exec -i oracle-free-db sqlplus -S / as sysdba < tools/deploy/gcp/configure-apex-cdn.sql
    ```
2.  Open APEX Builder or the APEX app locally (`http://localhost:8181/ords/`) and verify:
    *   The page loads correctly.
    *   Using Browser Developer Tools (Network tab), check that static assets (`desktop.min.js`, `theme.min.css`, etc.) are loaded from `https://static.oracle.com/cdn/apex/...` instead of `http://localhost:8181/i/...`.
3.  Revert the changes locally to avoid breaking offline development:
    ```bash
    # Run the revert SQL script on local DB container
    docker exec -i oracle-free-db sqlplus -S / as sysdba < tools/deploy/gcp/revert-apex-cdn.sql
    ```

---

## Done

*   `tools/deploy/gcp/configure-apex-cdn.sql` exists and contains correct PL/SQL.
*   Image re-hosting commands are documented.
*   Verification steps pass on local Oracle DB instance.
