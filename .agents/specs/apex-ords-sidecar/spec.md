# Flow Spec: apex-ords-sidecar (Chapter 3)

*Beads: `oracledb-vertexai-apxg.3` (chapter epic)*
*Parent PRD: [../apex-gvenzl-install/prd.md](../apex-gvenzl-install/prd.md)*
*Depends on: Ch1 (staged `apex/images`), Ch2 (APEX schema + REST users in `FREEPDB1`)*
*Status: Refreshed 2026-06-14 (host-gateway, freepdb1, no database.py edit) — implementation-ready*

---

> **⚠ Contract update (2026-06-14) — refresh fully before implementing.**
> Written against the `adb-free` draft; the landed gvenzl base changes several assumptions. Apply these
> when this chapter comes up (after Ch2):
> - **Service/PDB:** `freepdb1` (gvenzl `PDB_SERVICE_NAME`), container `oracle-free-db`, DB port `1521`.
> - **DB↔ORDS connectivity (avoid a `database.py` edit):** prefer ORDS reaching the DB via the host
>   gateway (`--add-host=host.docker.internal:host-gateway`, connect `host.docker.internal:1521/freepdb1`)
>   instead of adding `--network oracle-net` to `_build_run_command()` (which would re-touch the
>   just-reverted lifecycle class and require a DB recreate). If a shared network is preferred, treat the
>   `database.py` `--network` edit as an explicit, separate decision.
> - **Images at `/i/`:** bind-mount Ch1 `ApexMedia.paths().images_dir` into the ORDS container (the ORDS
>   container, not the DB) — `container_mounts(ords_images_target=…)` returns the spec.
> - **REST users** come from Ch2's non-interactive PL/SQL (no interactive `apex_rest_config.sql`).
> - **Lifecycle integration** belongs in `cli/database.py` (the flat `infra` group in `manage.py`), not
>   in `OracleDatabase`. Add `infra ords …` as its own subgroup like `infra apex`.

## 1.0 Context

`gvenzl/oracle-free` ships no ORDS, so APEX has no HTTP front end until one is added. Per the locked
decision, ORDS runs as a **sidecar container launched by the Python infra CLI** (`docker run`, not
compose-primary — consistent with the project's "CLI owns infra" rule). The sidecar connects to the
gvenzl DB's `FREEPDB1`, serves `/ords` (incl. `/ords/apex`, Database Actions) and the APEX static images
at `/i/` from the media staged in Ch1, and is wired into the `infra` lifecycle so `make start-infra`
brings up DB + ORDS together.

---

## 2.0 Requirements

- Run the official ORDS image as a sidecar via the Python CLI; pin a tag compatible with APEX 26.1
  (the running container already validated ORDS `26.1.0`; reuse that line).
- Put DB + ORDS on a shared container network so ORDS reaches the DB by name (no host-port hops).
- Configure ORDS against `FREEPDB1` using the APEX REST/listener users created in Ch2
  (`apex_rest_config.sql`); serve APEX images at `/i/` from Ch1's `images_dir`.
- Expose HTTPS (and/or HTTP) on a stable host port; health-check `/ords/`.
- Integrate ORDS into `infra start | stop | remove | status`; idempotent and re-runnable.
- No secrets persisted to logs; demo credentials only.

---

## 3.0 Proposed Changes (refreshed to host-gateway; no `database.py` edit)

### Component: ORDS sidecar (`tools/oracle/`)

#### [CREATE] `tools/oracle/ords.py`
- `@dataclass OrdsConfig`: `image` (official `container-registry.oracle.com/database/ords:latest`,
  overridable via `ORDS_IMAGE`), `container_name = "oracle-ords"`, `db_container = "oracle-free-db"`,
  `service_name = "freepdb1"`, `db_host = "host.docker.internal"`, `db_port = 1521`,
  `host_https_port = 8443`, `host_http_port = 8181`, `apex_images_path` (host path from Ch1
  `ApexMedia.paths().images_dir`), `images_url_path = "/i/"`, connection user/password (app/ORDS pool).
  `from_env()` for overrides.
- `class OrdsSidecar(runtime, config, console=None)`:
  - `_build_run_command()` — `docker run -d --name oracle-ords --add-host=host.docker.internal:host-gateway`
    (DB reachable over the published host port — **no shared network, no DB recreate**), `-p` HTTPS/HTTP,
    `-v {images_dir}:{container images dir}:z` for `/i/`, ORDS connection env, the image. Returns argv.
  - `start(*, recreate=False)`, `stop()`, `remove()`, `status()`, `logs()` — mirror `OracleDatabase`
    lifecycle ergonomics using `ContainerRuntime`.
  - `wait_for_healthy()` — poll `/ords/` readiness.

### Component: infra lifecycle integration (`tools/oracle/cli/`)

> **No `tools/oracle/database.py` change.** ORDS reaches the DB via `host.docker.internal:1521/freepdb1`
> (host gateway), so the lifecycle class stays untouched, consistent with Ch2.

#### [MODIFY] `tools/oracle/cli/database.py`
- After `db.start()` + `_auto_install_apex()` (unless `--skip-apex`), start the ORDS sidecar (add
  `--skip-ords`). `infra wipe`/`stop`/`status` also act on the ORDS container.

#### [CREATE] `tools/oracle/cli/ords.py` (+ `__init__`/`manage.py` wiring)
- `ords_group` with `start | stop | status | logs`; mounted as `infra ords …` (like `infra apex`).

---

## 4.0 Implementation Plan (TDD)

- [ ] **Task 3.1** — `OrdsConfig` + `OrdsSidecar._build_run_command()` (image, `--add-host` gateway,
  ports, `/i/` image bind-mount, ORDS env). Unit tests assert the `docker run` argv shape.
- [ ] **Task 3.2** — ORDS connection against `freepdb1` over the host gateway + `/i/` served from Ch1
  `images_dir`. Unit tests assert connection env + image mount (`:z`).
- [ ] **Task 3.3** — `start/stop/remove/status/logs` lifecycle + `wait_for_healthy()` poll.
  Unit tests for idempotent start (already-running) + health poll (mock runtime).
- [ ] **Task 3.4** — Integrate ORDS into `infra start` (after APEX) + `stop`/`wipe`/`status`
  (`--skip-ords`). Unit tests assert ORDS started after APEX and torn down with the DB.
- [ ] **Task 3.5** — `tools/oracle/cli/ords.py` `infra ords start|stop|status|logs` + wiring.
  Unit tests via Click `CliRunner` (mock `OrdsSidecar`).

---

## 5.0 Verification Plan

### Automated
```bash
uv run pytest src/tests/unit/tools/oracle/test_apex_ords.py
make lint
```

### Manual (real, after Ch1+Ch2)
```bash
make start-infra            # DB + APEX install + ORDS sidecar
curl -ksS https://localhost:8443/ords/ | head
# open https://localhost:8443/ords/apex  -> APEX login renders; /i/ images load
```

---

## 6.0 Definition of Done

- `make start-infra` brings up gvenzl DB **and** ORDS; `/ords/apex` renders with `/i/` images.
- ORDS reaches `FREEPDB1` over the shared network; health-check passes.
- `infra stop/remove/status` manage both containers; `infra ords …` works standalone; all idempotent.
- `make lint` and the new unit tests pass.

---

## Open Questions
- Exact ORDS image tag paired with APEX 26.1 (validate against `database/ords` releases; the running
  stack proved ORDS `26.1.0.r0791128` works with the APEX line).
- HTTPS-only vs HTTP+HTTPS for the local demo (recommend HTTPS on 8443 to mirror prior URLs).
