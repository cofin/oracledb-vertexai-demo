# Flow Spec: apex-runtime-hardening

*Beads: `oracledb-vertexai-apxo.1`*
*Parent PRD: [../apex-ops-console/prd.md](../apex-ops-console/prd.md)*
*Related PRD: [../apex-gvenzl-install/prd.md](../apex-gvenzl-install/prd.md)*
*Status: Planned - implementation-ready after old open tasks are reconciled*

---

## Context

The repo already has opt-in APEX/ORDS work from `apex-gvenzl-install`, but the
current implementation still needs a June 2026 refresh before an official lab
can depend on it.

Current anchors:

- `make start-infra` remains DB-only through `--skip-apex --skip-ords`.
- `make apex` starts DB + APEX + ORDS.
- `tools/oracle/ords.py` defaults to
  `container-registry.oracle.com/database/ords:latest`.
- `tools/oracle/ords.py` readiness checks container state, not HTTP service
  readiness.
- `tools/oracle/cli/database.py` starts ORDS as part of DB startup, but ORDS
  does not yet have its own nested `infra ords` lifecycle group.
- `tools/oracle/cli/apex.py` exposes install/upgrade/status only.

Official Oracle guidance to use:

- Oracle Skills `db` domain:
  - `db/ords/ords-installation.md`
  - `db/ords/ords-monitoring.md`
  - `db/ords/ords-security.md`
  - `db/containers/ords.md`
  - `db/containers/container-selection-matrix.md`
- Oracle APEX 26.1 release notes and known issues.
- ORDS 26.1 download and developer guide changes.

## Requirements

- Keep APEX optional. Do not make `make start-infra` install or start APEX/ORDS.
- Replace silent `:latest` assumptions with an explicit ORDS version target or
  a runtime version probe that fails clearly when the container is below ORDS
  26.1.1.
- Prefer ORDS 26.1.2 where the container tag is available and verified.
- Add HTTP readiness checks for `/ords/` and static APEX image serving under
  `/i/`.
- Add an explicit ORDS lifecycle CLI:
  `manage.py infra ords start|stop|restart|status|logs|remove`.
- Surface APEX 26.1 public media state, APEX 26.1.1 optional MOS patch state,
  and ORDS runtime version in status output where practical.
- Reconcile `apex-gvenzl-install` open chapters before implementing overlapping
  new work.

## Proposed Changes

### Flow Reconciliation

- Read the old open specs:
  - `apex-ords-sidecar`
  - `apexlang-source`
  - `apex-verify-docs`
- Decide whether each old Bead is superseded, absorbed, or still executable.
- Update Beads notes before implementation starts so no one works stale tasks.

### ORDS Runtime

- Update `OrdsConfig` in `tools/oracle/ords.py`:
  - add `minimum_version = "26.1.1"`
  - add a verified image selection policy
  - keep `ORDS_IMAGE` env override
  - expose HTTP and static image readiness URLs
- Extend `OrdsSidecar.wait_for_healthy()`:
  - poll `/ords/`
  - verify `/i/` responds with an expected HTTP outcome
  - treat container-running as insufficient
- Add a version probe:
  - prefer a container command or ORDS endpoint if available
  - otherwise parse logs only as a fallback
  - record an inconclusive probe as warning, not success

### CLI

- Create `tools/oracle/cli/ords.py` with standalone lifecycle commands.
- Wire it through `manage.py`.
- Keep existing `tools/oracle/cli/database.py` orchestration, but make the ORDS
  step call the same reusable sidecar service used by `infra ords`.

## Implementation Tasks

- [ ] Reconcile old `apex-gvenzl-install` open chapters and Beads notes.
- [ ] Update ORDS image/version policy and add focused tests for default,
  override, and minimum-version behavior.
- [ ] Add HTTP readiness probes for `/ords/` and `/i/`.
- [ ] Add `infra ords` lifecycle commands and Click tests.
- [ ] Update APEX/ORDS status output with version and patch-state details.
- [ ] Document the runtime policy in implementation notes for Ch6 docs.

## Verification

Automated:

```bash
uv run pytest src/tests/unit/tools/oracle/test_apex_ords.py
uv run pytest src/tests/unit/tools/oracle/test_ords_cli.py
make lint
```

Manual, when local Oracle runtime is available:

```bash
make apex
curl -fsS http://localhost:8181/ords/
curl -fsS http://localhost:8181/i/
uv run python manage.py infra ords status
uv run python manage.py infra ords logs --tail 100
```

## Done

- Optional APEX path starts with verified APEX/ORDS runtime state.
- ORDS readiness means the HTTP endpoints respond, not just that a container
  exists.
- ORDS lifecycle can be managed independently from the DB.
- Old Flow tasks are reconciled so this PRD is the current source of truth.
