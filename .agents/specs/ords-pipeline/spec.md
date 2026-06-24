# Flow Spec: ords-pipeline

*Beads: `oracledb-vertexai-ords.4`*
*Parent PRD: [../cloudrun-ords-deploy/prd.md](../cloudrun-ords-deploy/prd.md)*
*Depends on: `ords-terraform`*
*Status: Planned*

---

## Context
Integrate the ORDS service deployment and the APEX CDN configuration into the Cloud Build deployment pipeline.
We will:
1.  Add a CLI command `coffee configure-apex-cdn` to the application CLI. This command reads `tools/deploy/gcp/configure-apex-cdn.sql`, connects to the database as `SYSDBA` using the `DATABASE_SYSTEM_PASSWORD` secret env, and runs the PL/SQL configuration.
2.  Update `tools/deploy/gcp/cloudbuild.yaml` to deploy `coffee-ords` and run the configuration command.

---

## Requirements

1.  **Application CLI Command**:
    *   Command: `coffee configure-apex-cdn`
    *   Description: Run the APEX CDN configuration script against the database as SYSDBA.
    *   It must read `tools/deploy/gcp/configure-apex-cdn.sql`, parse the PL/SQL block, connect using `mode=oracledb.AUTH_MODE_SYSDBA` using `DATABASE_SYSTEM_PASSWORD` as the password, and execute the block.
    *   It should capture and print `dbms_output` logs to stdout.
2.  **Cloud Build Pipeline (`cloudbuild.yaml`)**:
    *   **Secrets**: Map `projects/$PROJECT_ID/secrets/coffee-db-system-password/versions/latest` to the environment variable `DATABASE_SYSTEM_PASSWORD` in `availableSecrets`.
    *   **Deploy ORDS Step**: Add a step named `deploy-ords` using `gcr.io/cloud-builders/gcloud` to deploy `coffee-ords` Cloud Run service using the image `${_REGION}-docker.pkg.dev/${_PROJECT}/${_AR}/ords:26.1.2` (re-hosted in Ch 1).
        *   Configuration matching Chapter 2: gen2, Direct VPC egress, private ranges only, allow unauthenticated.
    *   **Configure APEX CDN Step**: Add a step named `configure-apex` that runs `coffee configure-apex-cdn` using the newly built application container.
        *   Pass envs: `DATABASE_HOST=10.10.0.10`, `DATABASE_PORT=1521`, `DATABASE_SERVICE_NAME=freepdb1`, and secretEnv: `DATABASE_SYSTEM_PASSWORD`.
        *   Run this step after the `migrate` step.

---

## Implementation Tasks

- [ ] Add the `configure-apex-cdn` command to `src/app/cli/commands.py` (and any helper functions in `src/app/cli/_helpers/` or a new helper file).
- [ ] Update `tools/deploy/gcp/cloudbuild.yaml` to add secret binding, `deploy-ords` step, and `configure-apex` step.
- [ ] Run `make lint` and verify tests pass.

---

## Verification

### Local CLI Verification
1.  Run the CLI command locally using the docker network:
    ```bash
    # Run the python CLI command targeting the local DB container
    # We must provide the system password (Admin123) as env
    DATABASE_SYSTEM_PASSWORD=Admin123 uv run coffee configure-apex-cdn
    ```
    Verify it prints:
    `[DBMS_OUTPUT] APEX IMAGE_PREFIX successfully updated to CDN...` (or already set).
2.  Run the revert script to restore local environment (or run local setup again).

---

## Done
*   `coffee configure-apex-cdn` command exists and runs successfully against local database.
*   `tools/deploy/gcp/cloudbuild.yaml` contains the new secret, `deploy-ords` step, and `configure-apex` step.
*   `make lint` passes.
