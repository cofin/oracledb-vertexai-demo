# Learnings: Oracle APEX Integration

## 2026-06-13 20:40 - Flow Refresh Beads Alignment

- **Changed:** Created the missing `oracledb-vertexai-apex` Beads graph and synchronized metadata/spec status.
- **Why:** Code for the ADB container/settings/doctor path was already present in commit `f360c2f`, but the spec still read like planning-only work and no Beads records existed locally.
- **Files changed:** `.agents/flows.md`, `.agents/specs/oracle-apex-integration/{metadata.json,prd.md,spec.md}`.
- **Commands:** focused unit refresh tests covering settings, doctor, Oracle database helpers, inventory data, grounding, and store service behavior.
- **Gotchas:** Runtime container/APEX verification remains a separate open task because this refresh did not run `make start-infra` or browser/manual ORDS checks.

## 2026-06-13 21:31 - Runtime Infra Verification

- **Changed:** Closed `oracledb-vertexai-apex` after verifying the managed ADB Free lifecycle end to end.
- **Why:** The runtime path needed real container validation after cross-machine spec/code updates. The fixes aligned host paths, wallet configuration, app credentials, and idempotent cleanup.
- **Files changed:** `tools/oracle/database.py`, `tools/oracle/cli/database.py`, `tools/oracle/connection.py`, `tools/lib/utils.py`, `src/app/lib/settings.py`, and focused tests.
- **Commands:** `make start-infra`, `uv run coffee upgrade`, `uv run python manage.py database connect test`, `make test`, `make stop-infra`, `make wipe-infra`, repeated `make wipe-infra`.
- **Gotchas:** ADB Free needs both `/u01/data` and `/u01/app/oracle/oradata` on writable host storage here; `/dev/shm` avoided the read-only/full `/var/tmp` and overlay-backed ORA-65169 failures. Thin-mode wallet clients need `config_dir` as well as `wallet_location`.
