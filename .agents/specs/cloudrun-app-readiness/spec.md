# Flow: cloudrun-app-readiness

> Parent PRD: `cloudrun-gce-lab` (`.agents/specs/cloudrun-gce-lab/prd.md`)
> Beads epic: `oracledb-vertexai-jw0.1`
> Type: feature · Status: planned · This is the ONLY app-code-touching chapter of the PRD.

## Specification

### Context

The PRD ships a new Cloud Run + GCE-Oracle lab. Cloud Run runs the Litestar webapp
as the existing distroless image and **injects a `PORT` environment variable**
(default `8080`) that the container process MUST bind. Today the image only works
on Cloud Run *by coincidence*: the Dockerfile `CMD` hardcodes `--port 8080`, which
happens to equal Cloud Run's default `PORT`. Because the `CMD` is **exec-form**, the
string `$PORT` would NOT shell-expand, so if Cloud Run ever injects a non-8080 port
(custom container port, or platform change) the app would bind the wrong port and the
deploy would fail the Cloud Run startup health check.

This chapter makes the container **honor `$PORT`** in a backward-compatible way and
carries the documented Cloud Run runtime env/secrets contract. **No new app feature
is added** — the app already supports remote Oracle via `DATABASE_HOST/PORT/SERVICE_NAME`
and Vertex via project-mode env. The work is hardening + correctness + documentation.

**Hard constraint (PRD Global Constraint #1):** the local developer loop must remain
byte-for-byte unchanged — `make start-infra` + `uv run coffee run` against local
`gvenzl/oracle-free`, served at `http://localhost:5006/` (because `.env` sets
`LITESTAR_PORT=5006`), and bare `coffee run` with no env still defaults to `8000`.

### Code-analysis summary (file:line — these are LAW)

**Port resolution chain (the heart of this chapter):**

- `src/app/cli/commands.py:69-86` — `_create_run_command()` builds the `coffee run`
  command by copying `litestar_granian.cli.run_command`'s params verbatim
  (`new_command.params = original_command.params.copy()`, line 85) and wrapping its
  callback. `wrapped_run` (lines 73-82) forwards `**kwargs` straight to granian's
  callback, so `port`/`host` arrive **already resolved by Click**.
- `src/app/cli/commands.py:208` — `cli.add_command(_create_run_command())` registers it.
- `.venv/.../litestar_granian/cli.py:78-79` — the copied options:
  - `--host` → `default="127.0.0.1"`, `envvar="LITESTAR_HOST"`
  - `--port` → `type=int, default=8000, envvar="LITESTAR_PORT"`
  - granian callback signature `run_command(app, host: str, port: int, ...)`
    (`.venv/.../litestar_granian/cli.py:518-521`).
- **Click precedence for `--port`:** explicit CLI flag > `LITESTAR_PORT` env > default `8000`.
  Granian reads **`LITESTAR_PORT`**, NOT Cloud Run's **`PORT`**. Cloud Run does not set
  `LITESTAR_PORT`, so without a change granian never sees Cloud Run's `$PORT`.
- `tools/deploy/docker/Dockerfile:82` — `EXPOSE 8080`.
- `tools/deploy/docker/Dockerfile:85-86` — `ENTRYPOINT ["/usr/local/bin/tini","--","coffee"]`
  then `CMD ["run","--host","0.0.0.0","--port","8080"]`. The literal `--port 8080` is a
  CLI flag → **highest precedence**, overriding any env. Exec-form → no `$PORT` expansion.
- `.env:15-16` — local dev sets `LITESTAR_HOST=0.0.0.0` and `LITESTAR_PORT=5006`. The
  app's `Settings.from_env` uses `load_dotenv(..., override=False)` (`settings.py:472`),
  so a shell-exported value wins over `.env`. **Do NOT touch `.env`.**
- `src/app/lib/settings.py:437-444` — `setup_litestar_env()` derives `APP_URL` from
  `LITESTAR_PORT` (default `8000`). It does **not** read `PORT` and is unrelated to the
  bound listen port (it only sets `APP_URL`); we leave it unchanged so dev `APP_URL`
  stays `http://localhost:5006` / `http://localhost:8000`.

**`is_autonomous` / DSN path (requirement #2):**

- `src/app/lib/settings.py:137-139` — `is_autonomous` returns True **only** when
  `self.URL is not None and self.WALLET_PASSWORD is not None`, i.e. when both
  `DATABASE_URL` AND `WALLET_PASSWORD` are set.
- `src/app/lib/settings.py:83,85` — `URL = os.getenv("DATABASE_URL")`,
  `WALLET_PASSWORD = os.getenv("WALLET_PASSWORD")`; both default to `None`.
- `src/app/lib/settings.py:98-115` — `HOST`/`PORT`/`SERVICE_NAME` default
  `localhost`/`1521`/`freepdb1`; `DSN` is built as `HOST:PORT/SERVICE_NAME` when
  `DATABASE_DSN` is unset.
- `src/app/lib/settings.py:157-161,203-211` — when `is_autonomous` is False,
  `get_connection_params()` returns `{user, password, dsn}` and `create_config()` uses
  the local/standard pool config (no wallet).
- **Conclusion:** The Cloud Run env (`DATABASE_HOST=10.10.0.10`, `DATABASE_PORT=1521`,
  `DATABASE_SERVICE_NAME=freepdb1`, `DATABASE_USER=app`, `DATABASE_PASSWORD` via secret,
  and **no** `DATABASE_URL`, **no** `WALLET_PASSWORD`) ⇒ `is_autonomous == False` ⇒
  standard DSN `10.10.0.10:1521/freepdb1`. This is already supported; this chapter only
  documents it (a test asserts it).

**Vertex / GenAI env (documentation only):**

- `src/app/lib/settings.py:328-339` — `AISettings.project_id` reads `VERTEX_AI_PROJECT_ID`
  (or `GOOGLE_CLOUD_PROJECT`); `location` reads `VERTEX_AI_LOCATION` (default `us-central1`).
- `src/app/lib/settings.py:446-459` — `configure_genai_env()` sets
  `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`
  whenever a project id is present. The Cloud Run contract sets these explicitly; the app
  already wires them.

### Requirements

**Functional**

- FR1. When the process starts with `PORT` set in the environment (Cloud Run), the
  Granian server MUST bind that port, regardless of `LITESTAR_PORT`.
- FR2. When `PORT` is **unset** (local dev, CI, tests), behavior MUST be identical to
  today: `LITESTAR_PORT` (5006 from `.env`) is honored, and bare `coffee run` defaults
  to `8000`.
- FR3. An explicit `--port N` flag MUST still override everything (CLI-flag precedence
  preserved) so `coffee run --port 1234` works unchanged.
- FR4. The container, run with `docker run -e PORT=9090 ...`, MUST listen on `9090`.
- FR5. The container, run with no `PORT` (e.g. `docker run` locally), MUST listen on
  `8080` (matching `EXPOSE 8080` and Cloud Run's default).

**Non-functional / constraints**

- NFR1 (no-regression). No change to `.env`, `setup_litestar_env()`, or
  `DatabaseSettings`. The dev URL stays `http://localhost:5006/`.
- NFR2 (no shims). No backwards-compat re-export or facade module (repo convention).
- NFR3 (one approach). Implement exactly Approach A below; do not add an entrypoint
  wrapper script (Approach B is rejected).

**Documentation carried by this spec (no code):** a "Cloud Run runtime env & secrets"
subsection (below) mirroring the PRD Architecture Contract.

### Decision — recommended approach (A); rejected alternative (B)

**Approach A (RECOMMENDED — implement this): make the `run` command's `--port` default
resolve `PORT` → `LITESTAR_PORT` → 8000, and drop the hardcoded `--port 8080` from the
Dockerfile CMD.**

- In `_create_run_command()` (`commands.py`), after copying granian's params, mutate the
  copied `--port` option so its `default` is a callable that reads
  `os.getenv("PORT")` first, then falls back to granian's existing env-driven default.
  Because Click evaluates `default` only when neither the CLI flag nor `LITESTAR_PORT`
  envvar is supplied, this is purely additive: it inserts `PORT` *below* an explicit
  `--port` flag and *below* `LITESTAR_PORT`, and *above* the literal `8000`.
- Drop `--port 8080` (and the now-redundant explicit value) from the Dockerfile `CMD` so
  the new default actually takes effect inside the container. Keep `--host 0.0.0.0`
  (containers must bind all interfaces; granian's default is `127.0.0.1`).
- Net effect:
  - Cloud Run sets `PORT=8080` → binds 8080 (unchanged behavior, now *correct* not coincidental).
  - Cloud Run sets `PORT=9090` → binds 9090 (the bug today; fixed).
  - Local `coffee run`: `PORT` unset, `.env` `LITESTAR_PORT=5006` → binds 5006 (unchanged).
  - Bare `coffee run` (no `.env`/env): `PORT` and `LITESTAR_PORT` unset → 8000 (unchanged).
  - `coffee run --port 1234`: 1234 (CLI flag still wins; unchanged).
  - `docker run` with no `PORT`: default callable returns `8000`? **No** — the Dockerfile
    CMD keeps an explicit fallback so the container default is `8080` (see Task 2.1; we
    pass `--port "${PORT:-8080}"`-equivalent by keeping `PORT` env defaulted in the image,
    detailed in the worksheet). FR5 is satisfied via `ENV PORT=8080` in the image.

  **Regression risk (called out explicitly):** the only risk is the precedence ordering.
  If `PORT` were placed *above* an explicit `--port` flag it would break `coffee run
  --port 1234`; and if `PORT` were read *above* `LITESTAR_PORT` it could hijack a
  developer who has `PORT` exported for an unrelated tool. Approach A avoids both: it only
  changes the **default factory**, which Click consults *after* both the CLI flag and the
  `LITESTAR_PORT` envvar, so local dev (`LITESTAR_PORT=5006`) is untouched. The Dockerfile
  edit is the second half — without dropping the literal `--port 8080`, the env-honoring
  default would be shadowed by the CLI flag inside the container.

**Approach B (REJECTED): add a shell/exec entrypoint wrapper that expands `${PORT:-8080}`.**

- Rejected because: (1) the base image is `gcr.io/distroless/cc-debian12:nonroot` —
  **there is no shell** in the runtime stage (`Dockerfile:56`), so a `sh -c` wrapper would
  require adding a shell or a static helper binary, enlarging the distroless image and
  breaking its single-binary contract (`Dockerfile:8-9`); (2) it pushes port logic into an
  untested shell file instead of the Python CLI the rest of the app already owns; (3) it
  duplicates the `LITESTAR_PORT` precedence granian already implements. Approach A reuses
  the existing, tested Click/granian machinery and adds zero new files.

### Acceptance criteria

- AC1. `python -c` / unit test: with `PORT=9090` and no `--port` flag, the resolved
  `coffee run` port is `9090`.
- AC2. Unit test: with `PORT` unset and `LITESTAR_PORT=5006`, resolved port is `5006`.
- AC3. Unit test: with `PORT` unset and `LITESTAR_PORT` unset, resolved port is `8000`.
- AC4. Unit test: `coffee run --port 1234` with `PORT=9090` set resolves to `1234`
  (CLI flag wins).
- AC5. Unit test: with only `DATABASE_HOST/PORT/SERVICE_NAME/USER/PASSWORD` set (no
  `DATABASE_URL`, no `WALLET_PASSWORD`), `DatabaseSettings().is_autonomous is False` and
  `get_connection_params()["dsn"] == "10.10.0.10:1521/freepdb1"`.
- AC6. Container smoke (manual/CI): `docker run -e PORT=9090 -p 9090:9090 <image>` →
  `curl -fsS http://localhost:9090/` returns 200; `docker run -p 8080:8080 <image>` (no
  `PORT`) → `curl -fsS http://localhost:8080/` returns 200.
- AC7. `make lint` and `make test` pass.
- AC8. Local-loop check: `uv run coffee run` (with repo `.env`) still serves
  `http://localhost:5006/`. No diff to `.env`.

### Backward-compat constraint (restated, binding)

- Do NOT edit `.env`, `src/app/lib/settings.py:437-444` (`setup_litestar_env`), or
  `DatabaseSettings`. The only source edits are `src/app/cli/commands.py:69-86` and
  `tools/deploy/docker/Dockerfile:84-86`. The settings change for AC5 is **test-only**.

---

## Cloud Run runtime env & secrets (documentation this spec carries)

This mirrors the PRD "Cloud Run service" + "Secret Manager" sections. The app already
supports every value below; Chapter 3 (`cloudbuild-cloudrun-pipeline`) wires them on the
`gcloud run deploy`. No code in *this* chapter is required to make them work — they are
recorded here so the deploy chapter and the lab docs have a single source of truth.

**`gcloud run deploy coffee-app` plain env (`--set-env-vars`):**

| Variable | Value | App reader (file:line) |
|---|---|---|
| `PORT` | injected by Cloud Run (default `8080`) | `coffee run` `--port` default (Task 1.2) |
| `DATABASE_HOST` | `10.10.0.10` (DB VM static internal IP) | `settings.py:98-100` |
| `DATABASE_PORT` | `1521` | `settings.py:102-104` |
| `DATABASE_SERVICE_NAME` | `freepdb1` | `settings.py:106-108` |
| `DATABASE_USER` | `app` | `settings.py:90-92` |
| `VERTEX_AI_PROJECT_ID` | `$PROJECT` | `settings.py:328-330` |
| `VERTEX_AI_LOCATION` | `us-central1` | `settings.py:332-339` |
| `GOOGLE_GENAI_USE_VERTEXAI` | `true` | also force-set by `configure_genai_env` (`settings.py:457`) |
| `ORACLE_ADK_IN_MEMORY` | `true` | `settings.py:121` |
| `ORACLE_LITESTAR_SESSION_IN_MEMORY` | `true` | `settings.py:125-127` |

**Secrets (`--set-secrets`):**

| Variable | Secret | App reader |
|---|---|---|
| `DATABASE_PASSWORD` | `coffee-db-password:latest` | `settings.py:94-96` |

**Deliberately UNSET on Cloud Run** (so the standard DSN path is taken, not ADB wallet):
`DATABASE_URL`, `WALLET_PASSWORD`, `WALLET_LOCATION`, `TNS_ADMIN`, `DATABASE_DSN`. With
these unset, `is_autonomous` is False (`settings.py:137-139`) and the connection DSN is
`DATABASE_HOST:DATABASE_PORT/DATABASE_SERVICE_NAME` (`settings.py:110-115`). See AC5.

---

## Implementation Plan

> TDD: each feature task writes tests first, then the minimal implementation. Run focused
> tests while editing; run `make lint` and `make test` before claiming completion.

### Phase 1: Honor `$PORT` in the `coffee run` command

- [ ] **1.1 Write the failing port-resolution tests.**
  - File: `src/tests/unit/cli/test_commands.py` (create if absent; add an SPDX-bearing
    `__init__.py` in any new `src/tests/unit/cli/` package dir per patterns.md testing
    rules). If a CLI test module already exists under `src/tests/unit/cli/`, add cases there.
  - Test the command produced by `_create_run_command()` via Click's `CliRunner` with a
    callback stub, asserting the resolved `port` kwarg. Use `monkeypatch.setenv/delenv`
    for `PORT` and `LITESTAR_PORT`.
  - Idiomatic test snippet:

    ```python
    # SPDX-FileCopyrightText: 2026 Google LLC
    # SPDX-License-Identifier: Apache-2.0
    """Behavioral tests for the ``coffee run`` command's port resolution."""

    import pytest
    from click.testing import CliRunner

    from app.cli.commands import _create_run_command


    def _resolve_port(monkeypatch: pytest.MonkeyPatch, args: list[str], env: dict[str, str | None]) -> int:
        captured: dict[str, int] = {}

        def fake_callback(**kwargs: object) -> None:  # granian callback stand-in
            captured["port"] = int(kwargs["port"])  # type: ignore[arg-type]

        # The wrapped command forwards to granian's callback via original_command.callback.
        monkeypatch.setattr("app.cli.commands.litestar_run_command.callback", fake_callback)
        # Avoid building the real Litestar app/env during the resolution test.
        monkeypatch.setattr("app.server.asgi.create_app", lambda: object())
        monkeypatch.setattr("litestar.cli._utils.LitestarEnv.from_env", classmethod(lambda cls, _p: type("E", (), {"app": None})()))
        for key, value in env.items():
            if value is None:
                monkeypatch.delenv(key, raising=False)
            else:
                monkeypatch.setenv(key, value)
        result = CliRunner().invoke(_create_run_command(), args, standalone_mode=False)
        assert result.exit_code == 0, result.output
        return captured["port"]


    @pytest.mark.parametrize(
        ("args", "env", "expected"),
        [
            ([], {"PORT": "9090", "LITESTAR_PORT": None}, 9090),          # AC1 Cloud Run
            ([], {"PORT": None, "LITESTAR_PORT": "5006"}, 5006),          # AC2 local .env
            ([], {"PORT": None, "LITESTAR_PORT": None}, 8000),            # AC3 bare default
            (["--port", "1234"], {"PORT": "9090", "LITESTAR_PORT": None}, 1234),  # AC4 flag wins
        ],
    )
    def test_run_port_resolution(monkeypatch, args, env, expected):
        assert _resolve_port(monkeypatch, args, env) == expected
    ```

  - Verify it FAILS first (current code ignores `PORT`):
    `uv run pytest src/tests/unit/cli/test_commands.py -q` → the `PORT=9090` case yields
    `8000`, not `9090`.

- [ ] **1.2 Implement `$PORT` honoring in `_create_run_command()`.**
  - File: `src/app/cli/commands.py:69-86` (inside `_create_run_command`, after line 85's
    `new_command.params = original_command.params.copy()` and before `return new_command`
    at line 86).
  - Add a module-level `import os` at the top of the file if not already present
    (check imports block lines 11-39; add `import os` near the stdlib imports).
  - After copying params, locate the copied `--port` option and replace its `default` with
    a factory that reads `PORT` then falls back to the existing env-driven default. Because
    Click only consults `default` when neither the `--port` flag nor the `LITESTAR_PORT`
    envvar is provided, this preserves all higher-precedence sources.
  - Idiomatic implementation snippet (insert between current lines 85 and 86):

    ```python
    new_command.params = original_command.params.copy()
    # Cloud Run injects ``$PORT`` (default 8080). Granian's ``--port`` reads
    # ``LITESTAR_PORT``/8000, not ``PORT``; thread ``PORT`` in *below* an explicit
    # ``--port`` flag and ``LITESTAR_PORT`` so the container binds Cloud Run's port
    # while local ``coffee run`` (LITESTAR_PORT=5006) is unchanged.
    for param in new_command.params:
        if isinstance(param, click.Option) and "--port" in param.opts:
            granian_default = param.default  # 8000 (granian's literal default)
            param.default = lambda _d=granian_default: int(os.getenv("PORT") or _d)
            break
    return new_command
    ```

  - Note: Click consults `envvar` (`LITESTAR_PORT`) before `default`, so a set
    `LITESTAR_PORT` still wins over the `PORT` factory — exactly the desired ordering.
  - Verify the Phase-1 tests now PASS:
    `uv run pytest src/tests/unit/cli/test_commands.py -q`.
  - Local-loop guard: run `LITESTAR_PORT=5006 uv run coffee run --help` to confirm the
    command still loads, and (if Oracle is up) `uv run coffee run` still serves
    `http://localhost:5006/` (AC8). Do NOT change `.env`.

### Phase 2: Make the container bind `$PORT` (Dockerfile)

- [ ] **2.1 Edit the Dockerfile CMD/ENV so `$PORT` drives the bound port.**
  - File: `tools/deploy/docker/Dockerfile:84-86`.
  - Add `PORT=8080` to the runtime `ENV` block so the image has a self-contained default
    (FR5) that the Task 1.2 factory reads when Cloud Run is absent, and drop the literal
    `--port 8080` (CLI flag) from `CMD` so the factory is not shadowed. Keep
    `--host 0.0.0.0`.
  - Exact edits:
    - Extend the `ENV` block. Change line 64 from:

      ```dockerfile
          TMPDIR=/tmp
      ```

      to:

      ```dockerfile
          TMPDIR=/tmp \
          PORT=8080
      ```

      (Append `PORT=8080` as the final entry of the `ENV` block that starts at line 58.
      `ENV PORT=8080` is an image default only; Cloud Run overrides it at runtime.)
    - Change the `CMD` at line 86 from:

      ```dockerfile
      CMD ["run", "--host", "0.0.0.0", "--port", "8080"]
      ```

      to:

      ```dockerfile
      CMD ["run", "--host", "0.0.0.0"]
      ```

      Now no `--port` flag is passed, so the Task 1.2 default factory resolves the port:
      `PORT` (8080 from `ENV`, or Cloud Run's injected value) → falls back to `LITESTAR_PORT`/8000.
  - Leave `EXPOSE 8080` (line 82) as documentation of the image default. Leave the
    `ENTRYPOINT` (line 85) unchanged.

- [ ] **2.2 Verify the container honors `$PORT` (build + smoke).**
  - This is infra verification, not a `src/tests` unit (patterns.md forbids tests whose
    subject is Dockerfile text). Run it as a manual/CI smoke per the acceptance criteria.
  - The image wraps the prebuilt onefile (`Dockerfile:44`), so build needs
    `dist/coffee-<arch>-linux-gnu` present (`make build-onefile` first if absent).
  - Commands:

    ```bash
    # Build (from repo root; requires dist/coffee-<arch>-linux-gnu to exist)
    docker build -f tools/deploy/docker/Dockerfile -t coffee-app:portcheck .

    # FR4 / AC6: Cloud Run-style non-default port
    docker run --rm -d --name pc9090 -e PORT=9090 -p 9090:9090 coffee-app:portcheck
    sleep 5 && curl -fsS http://localhost:9090/ >/dev/null && echo "PORT=9090 OK"
    docker rm -f pc9090

    # FR5 / AC6: no PORT → image default 8080
    docker run --rm -d --name pc8080 -p 8080:8080 coffee-app:portcheck
    sleep 5 && curl -fsS http://localhost:8080/ >/dev/null && echo "default 8080 OK"
    docker rm -f pc8080
    ```

  - Note: the smoke only proves the *bind port*; a full request needs a reachable Oracle.
    A startup-only check (process binds the port, health endpoint or `curl` connects) is
    sufficient for this chapter. If `/` requires DB, target a lightweight route or accept a
    connection-level 200/redirect; the binding is what AC6 validates.

### Phase 3: Lock the `is_autonomous` / DSN contract with a test (no app change)

- [ ] **3.1 Write the `is_autonomous`/DSN settings test (AC5).**
  - File: add to the existing settings test module under
    `src/tests/unit/lib/test_settings.py` (find the existing settings test file first per
    patterns.md; if a `DatabaseSettings` test section exists, extend it — do not create a
    one-issue file).
  - Construct `DatabaseSettings` with the Cloud Run env applied via `monkeypatch` and
    assert the standard DSN path. This is a guard test proving the documented Cloud Run
    config drives the non-autonomous path; it requires **no source change**.
  - Idiomatic snippet:

    ```python
    import pytest

    from app.lib.settings import DatabaseSettings


    @pytest.mark.parametrize("unset", ["DATABASE_URL", "WALLET_PASSWORD"])
    def test_cloud_run_env_uses_standard_dsn(monkeypatch, unset):
        for key, value in {
            "DATABASE_HOST": "10.10.0.10",
            "DATABASE_PORT": "1521",
            "DATABASE_SERVICE_NAME": "freepdb1",
            "DATABASE_USER": "app",
            "DATABASE_PASSWORD": "secret-from-secret-manager",
        }.items():
            monkeypatch.setenv(key, value)
        # Cloud Run deliberately leaves these unset → not autonomous.
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("WALLET_PASSWORD", raising=False)
        monkeypatch.delenv("DATABASE_DSN", raising=False)

        settings = DatabaseSettings()

        assert settings.is_autonomous is False
        params = settings.get_connection_params()
        assert params["dsn"] == "10.10.0.10:1521/freepdb1"
        assert params["user"] == "app"
        assert "wallet_password" not in params
    ```

  - Verify it PASSES against current source (no implementation step follows — the behavior
    already exists; this only freezes it):
    `uv run pytest src/tests/unit/lib/test_settings.py -q`.

### Phase 4: Verify the whole change + no regression

- [ ] **4.1 Run focused tests, then the aggregate gates.**
  - `uv run pytest src/tests/unit/cli/test_commands.py src/tests/unit/lib/test_settings.py -q`
  - `make lint`
  - `make test`
  - Confirm AC7 (gates green) and AC8 (no `.env` diff: `git diff --stat .env` is empty).
  - Confirm the only source files changed are `src/app/cli/commands.py` and
    `tools/deploy/docker/Dockerfile` (plus test files):
    `git diff --stat` should not list `.env`, `settings.py`, or any new shim module.
