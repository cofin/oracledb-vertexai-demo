# Learnings: APEX ORDS Sidecar

## 2026-06-23 - Infra Status Integration

- **Implemented:** `infra status --verbose` reports the ORDS sidecar container, image, status, and exposed ports alongside the Oracle database lifecycle status.
- **Files changed:** `tools/oracle/cli/database.py`, `src/tests/unit/tools/oracle/test_apex_ords.py`.
- **Commands:** `uv run pytest src/tests/unit/tools/oracle/test_apex_ords.py -q`; included in the broader focused unit bundle.
- **Gotchas:** ORDS lifecycle integration already existed for start/stop/remove/status paths through the database infra CLI. The remaining standalone `infra ords start|stop|status|logs` subgroup belongs to `oracledb-vertexai-apxg.3.5`, not the 3.4 lifecycle-status task.
