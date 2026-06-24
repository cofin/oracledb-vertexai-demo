# Flow Spec: ords-lab-walkthrough

*Beads: `oracledb-vertexai-ords.5`*
*Parent PRD: [../cloudrun-ords-deploy/prd.md](../cloudrun-ords-deploy/prd.md)*
*Depends on: `ords-pipeline`*
*Status: Planned*

---

## Context
Update the hands-on Cloud Run lab walkthrough (`docs/lab-cloud-run.md`) to document the ORDS deployment, image re-hosting steps, and verification.

---

## Requirements

1.  **Walkthrough Updates** in `docs/lab-cloud-run.md`:
    *   **Prerequisites**: Mention that deploying ORDS is part of the lab.
    *   **Step 5b (New)**: `Step 5b: Re-host the Oracle ORDS Image to Artifact Registry`.
        - Add step-by-step commands to pull the official ORDS 26.1.2 image, tag it, and push it to the project's private GCP Artifact Registry.
    *   **Step 6**: Explain that the Cloud Build pipeline now deploys the `coffee-ords` service and configures the APEX CDN in the DB.
    *   **Step 7b (New)**: `Step 7b: Access the Oracle REST Data Services (ORDS)`.
        - Explain how to retrieve the ORDS URL using `gcloud run services describe coffee-ords`.
        - Provide a verification command (e.g. curling the URL).
    *   **Teardown**: Update cleanup commands to delete `coffee-ords` Cloud Run service and its service account.
2.  **Verification**:
    *   Run `make docs` to ensure the Sphinx build runs without warnings or errors.

---

## Implementation Tasks

- [ ] Edit `docs/lab-cloud-run.md` to insert the new steps and update existing sections.
- [ ] Run `make docs` (or the Sphinx build command) to verify the build passes.
- [ ] Verify that no markdown link errors are introduced.

---

## Verification

### Documentation Build
1.  Run the Sphinx build:
    ```bash
    uv run --group docs sphinx-build -W --keep-going -b html docs docs/_build/html
    ```
    Ensure it exits with `0` and no warnings are generated.

---

## Done
*   `docs/lab-cloud-run.md` is updated.
*   Sphinx docs build completes successfully with no warnings.
