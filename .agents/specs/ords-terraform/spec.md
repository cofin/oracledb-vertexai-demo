# Flow Spec: ords-terraform

*Beads: `oracledb-vertexai-ords.3`*
*Parent PRD: [../cloudrun-ords-deploy/prd.md](../cloudrun-ords-deploy/prd.md)*
*Depends on: `ords-image-prep`*
*Status: Planned*

---

## Context
Deploy the ORDS service `coffee-ords` as a serverless Cloud Run instance, peered into the VPC network via Direct VPC egress to communicate with the GCE database.

---

## Requirements

1.  **Service Account**:
    *   Create a dedicated service account `coffee-ords-sa` for the ORDS service.
2.  **IAM Permissions**:
    *   Grant `coffee-ords-sa` secret accessor role on `coffee-db-system-password` secret in Secret Manager.
    *   Grant the Cloud Build service account (`coffee-build-sa`) secret accessor role on `coffee-db-system-password` (needed for Chapter 3 configuration step).
3.  **Cloud Run Service (`coffee-ords`)**:
    *   Name: `coffee-ords`
    *   Image: Use bootstrap `us-docker.pkg.dev/cloudrun/container/hello` to avoid dependency loop, but configure lifecycle to ignore image updates (cloudbuild will manage the real image).
    *   Direct VPC Access: Peer with `coffee-vpc` and `coffee-run-subnet`.
    *   Egress: `PRIVATE_RANGES_ONLY` (to route DB traffic over VPC).
    *   Environment Variables:
        *   `DBHOST` = `"10.10.0.10"`
        *   `DBPORT` = `"1521"`
        *   `DBSERVICENAME` = `"freepdb1"`
        *   `ORACLE_PWD` = Map from Secret Manager `coffee-db-system-password` version `latest`.
    *   Ingress: `INGRESS_TRAFFIC_ALL` (allow public web access to the APEX URLs).
    *   IAM: Allow unauthenticated users (`allUsers`) to invoke the service (roles/run.invoker).
4.  **Outputs**:
    *   Output `coffee_ords_url` containing the URI of the deployed Cloud Run service.

---

## Implementation Tasks

- [ ] Create `tools/deploy/terraform/ords.tf` containing the new resources:
    - Service account `coffee_ords_sa`.
    - Secret IAM binding for `coffee_ords_sa`.
    - Secret IAM binding for `coffee_build_sa` (SYS secret accessor).
    - Cloud Run service `coffee_ords` (bootstrap config + lifecycle ignore).
    - Public IAM invoker binding for `coffee_ords`.
    - Output `coffee_ords_url`.
- [ ] Run `terraform validate` under `tools/deploy/terraform/` to ensure syntax validity.
- [ ] Run `terraform fmt` to format the code.

---

## Verification

### Static Verification
1.  Run validation:
    ```bash
    cd tools/deploy/terraform && terraform init -backend=false && terraform validate
    ```
    Ensure no errors are returned.
2.  Format check:
    ```bash
    cd tools/deploy/terraform && terraform fmt -check
    ```

---

## Done
*   `tools/deploy/terraform/ords.tf` exists.
*   `terraform validate` passes with no errors.
*   IAM policies strictly limit `coffee-db-system-password` to the ORDS and Build SAs.
