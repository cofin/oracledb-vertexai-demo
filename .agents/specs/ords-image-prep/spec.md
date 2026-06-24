# Flow Spec: ords-image-prep

*Beads: `oracledb-vertexai-ords.2`*
*Parent PRD: [../cloudrun-ords-deploy/prd.md](../cloudrun-ords-deploy/prd.md)*
*Depends on: none*
*Status: Planned*

---

## Context
Before deploying ORDS to Cloud Run, we need to prepare the container image and database configuration.
1.  **Image Prep**: Pull the official ORDS image from Oracle Container Registry, tag it, and push it to Google Artifact Registry. This is required because Cloud Run cannot authenticate to Oracle Registry at deployment runtime.
2.  **APEX CDN Config**: Create a SQL script that updates APEX to use Oracle's CDN for static files, keeping the ORDS deployment stateless.

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

- [ ] Document image re-hosting commands in this spec (under Architecture/Prose).
- [ ] Create `tools/deploy/gcp/configure-apex-cdn.sql` with the PL/SQL block.
- [ ] Add a local developer verification script or instructions to test APEX CDN updates locally (with options to revert to `/i/`).

---

## Verification

### Local Verification
1.  Run the CDN config script locally on the infra container:
    ```bash
    # Run the SQL script on local DB container
    docker exec -i coffee-db sqlplus sys/Admin123@freepdb1 as sysdba < tools/deploy/gcp/configure-apex-cdn.sql
    ```
2.  Open APEX Builder or the APEX app locally (`http://localhost:8181/ords/`) and verify:
    *   The page loads correctly.
    *   Using Browser Developer Tools (Network tab), check that static assets (`desktop.min.js`, `theme.min.css`, etc.) are loaded from `https://static.oracle.com/cdn/apex/...` instead of `http://localhost:8181/i/...`.
3.  Revert the changes locally to avoid breaking offline development:
    ```sql
    -- Revert script content
    BEGIN
        apex_instance_admin.set_parameter('IMAGE_PREFIX', '/i/');
        COMMIT;
    END;
    /
    ```

---

## Done
*   `tools/deploy/gcp/configure-apex-cdn.sql` exists and contains correct PL/SQL.
*   Image re-hosting commands are documented.
*   Verification steps pass on local Oracle DB instance.
