# Flow Spec: apex-ords-sidecar (Chapter 3)

*Beads: `oracledb-vertexai-apxg.3` (chapter epic)*
*Parent PRD: [../apex-gvenzl-install/prd.md](../apex-gvenzl-install/prd.md)*
*Depends on: Ch1 (staged `apex/images`), Ch2 (APEX schema + REST users in `FREEPDB1`)*
*Status: Drafted — needs full refresh before implementation (see contract update)*

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

## 3.0 Proposed Changes

### Component: ORDS sidecar (`tools/oracle/`)

#### [CREATE] `tools/oracle/ords.py`
- `@dataclass OrdsConfig`: `image` (official `database/ords` tag pinned for 26.1),
  `container_name = "oracle-ords"`, `network = "oracle-net"`, `db_container`, `pdb = "FREEPDB1"`,
  `host_https_port = 8443`, `host_http_port = 8080`, `apex_images_path` (from Ch1 `images_dir`),
  connection user/password (APEX_PUBLIC_USER/ORDS_PUBLIC_USER from Ch2). `from_env()` for overrides.
- `class OrdsSidecar(runtime, config)`:
  - `ensure_network()` — create the shared docker network if absent (idempotent).
  - `start(*, recreate=False)` — `docker run -d` the ORDS image on the network, env/args for the DB
    connection, bind-mount `apex/images` to the ORDS `/i/` location, expose ports, health-cmd.
  - `stop()`, `remove()`, `status()`, `logs()` — mirror `OracleDatabase` lifecycle ergonomics.
  - `wait_for_healthy()` — poll `/ords/` until ready.

### Component: infra lifecycle integration (`tools/oracle/`)

#### [MODIFY] `tools/oracle/database.py`
- Join the DB container to the shared `oracle-net` network (so ORDS can reach it) in `_build_run_command()`.

#### [MODIFY] `tools/oracle/cli/database.py` (+ `manage.py infra` wiring)
- `infra start` → after DB healthy + APEX installed (Ch2), `OrdsSidecar.start()`.
- `infra stop` / `infra remove` / `infra status` → include the ORDS container.
- Add `infra ords start | stop | status | logs` for direct control.

---

## 4.0 Implementation Plan (TDD)

- [ ] **Task 3.1** — `OrdsConfig` + `OrdsSidecar` run-command builder (image, network, ports, env,
  image bind-mount). Unit tests assert the `docker run` argv shape.
- [ ] **Task 3.2** — ORDS configured against `FREEPDB1` with Ch2 REST users; `/i/` served from Ch1
  `images_dir`. Unit tests assert connection args + image mount.
- [ ] **Task 3.3** — `ensure_network()` + DB↔ORDS connectivity + `wait_for_healthy()` polling.
  Unit tests for network-create idempotency + health poll (mock runtime).
- [ ] **Task 3.4** — Integrate ORDS into `infra start/stop/remove/status`. Unit tests assert ORDS is
  started after DB+APEX and torn down with the DB.
- [ ] **Task 3.5** — `infra ords` direct CLI commands. Unit tests via Click runner (mock `OrdsSidecar`).

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
