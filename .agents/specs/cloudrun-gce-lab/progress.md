# Progress: cloudrun-gce-lab

*PRD: `cloudrun-gce-lab` · Beads master: `oracledb-vertexai-jw0`*
*Updated: 2026-06-23*

| # | Chapter | flow_id | Beads | Status | Spec |
|---|---------|---------|-------|--------|------|
| 1 | Cloud Run app/image readiness | `cloudrun-app-readiness` | `oracledb-vertexai-jw0.1` | Planned | [spec](../cloudrun-app-readiness/spec.md) |
| 2 | GCE Oracle DB appliance | `gce-oracle-appliance` | `oracledb-vertexai-jw0.2` | Planned | [spec](../gce-oracle-appliance/spec.md) |
| 3 | Cloud Build + Cloud Run pipeline | `cloudbuild-cloudrun-pipeline` | `oracledb-vertexai-jw0.3` | Planned | [spec](../cloudbuild-cloudrun-pipeline/spec.md) |
| 4 | Lab docs restructure (GCE-only) | `lab-gce-rename` | `oracledb-vertexai-jw0.4` | Planned | [spec](../lab-gce-rename/spec.md) |
| 5 | Author new Cloud Run lab | `cloudrun-lab-authoring` | `oracledb-vertexai-jw0.5` | Planned | [spec](../cloudrun-lab-authoring/spec.md) |
| 6 | Cloud Run lab verification + teardown | `cloudrun-lab-verification-teardown` | `oracledb-vertexai-jw0.6` | Planned | [spec](../cloudrun-lab-verification-teardown/spec.md) |

**Execution order:** 1 → 2 → 3 → 4 → 5 → 6 (1, 2, 4 parallelizable).

Legend: Planned · In progress · Done · Blocked
