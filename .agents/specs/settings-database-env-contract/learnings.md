# Learnings: settings-database-env-contract

*Beads: oracledb-vertexai-mzm.4 (closed, commit 31485ce)*

## Drift found

The Oracle connection env contract was parsed in three places with divergent
names/defaults:

1. **Internal inconsistency inside `DatabaseSettings`** (`src/app/lib/settings.py`):
   the `SERVICE_NAME` field defaulted to `freepdb1`, but the `DSN` default derived
   its service from `myatp_low`. The class disagreed with itself.
2. **`ConnectionConfig.from_env()`** (`tools/oracle/connection.py`): managed
   service default `myatp_low`, external default `ORCL` (no app concept), plus
   `ORACLE_USER`/`ORACLE_PASSWORD` and `ORACLE26AI_PORT`/`ORACLE23AI_PORT`
   fallbacks the app path never shared.
3. **`.env` generation** (`tools/lib/utils.py`): managed block emits a wallet-style
   contract; external standard block emits host/port/service.

## Key realization: two service names, both valid

- `freepdb1` is the gvenzl container's **physical PDB** and the actual
  managed/local/standard connection target — used by `tools/oracle/database.py`
  (`PDB_SERVICE_NAME`, `get_connection_info` -> `localhost:port/freepdb1`) and by
  `src/tests/integration/conftest.py` (standard-mode connection).
- `myatp_low` is only a **wallet/TNS alias** in the dev `.env` `DATABASE_URL`,
  resolved via `tnsnames.ora` under `TNS_ADMIN=.envs/tns`. It comes from
  `DATABASE_URL` parsing, never from the `SERVICE_NAME` default.

The spec's premise that the managed default should be `myatp_low` was stale.
Flipping the no-env default to `myatp_low` would point the standard local path at
a wallet-only alias and break the gvenzl integration path. The correct unified
managed/local default is `freepdb1`; the wallet path keeps `myatp_low` because it
genuinely connects via the wallet.

## Unified contract (managed/local default)

`DATABASE_USER=app`, `DATABASE_PASSWORD=SuperSecret1`, `DATABASE_HOST=localhost`,
`DATABASE_PORT=1521`, `DATABASE_SERVICE_NAME=freepdb1`,
`DATABASE_DSN=localhost:1521/freepdb1`, pool `min=5`/`max=20`. Wallet/autonomous
via `DATABASE_URL` + `WALLET_PASSWORD` + `WALLET_LOCATION`(=`TNS_ADMIN`).

## Pattern: separate connection config from lifecycle config

App **connection** config (`DatabaseSettings`, `ConnectionConfig.from_env()`) and
container **lifecycle** config (`tools/oracle/database.py` `DatabaseConfig`) are
intentionally separate. The lifecycle config legitimately keeps its own
`ORACLE26AI_PORT`/`ORACLE23AI_PORT` host-port knobs and `ORACLE_PASSWORD` (SYS
password for the container) — those were NOT removed. Only the app **connection**
readers were unified onto `DATABASE_*`.

## Verification that mattered

`coffee model-info` only proves the AI client; it does not prove the DB. For an
env-contract change, verify the DB path directly: `create_config().provide_session()`
running `SELECT 1` (exercises the live wallet path), plus the chat workflow
integration test (real gvenzl container, Oracle-backed RAG). Both passed.

## Follow-up: the `.env` generator was the un-aligned third reader

Phase 4.1 originally concluded "no change required" for `tools/lib/utils.py`
`create_env_interactive()` because the generated managed `.env` matched the author's
live wallet `.env`. That was wrong: the managed block kept emitting the wallet-style
contract (`DATABASE_URL=…@myatp_low` + `WALLET_PASSWORD` + `TNS_ADMIN=.envs/tns` +
`DATABASE_SERVICE_NAME=myatp_low`) — directly contradicting the unified managed/local
default above. Because `DatabaseSettings.is_autonomous` is True whenever both
`DATABASE_URL` and `WALLET_PASSWORD` are present, that `.env` routes the app down the
wallet/SSL branch (`settings.py:166`), so a fresh `make start-infra` setup could not
connect to the gvenzl `localhost:1521/freepdb1` container.

Fix: managed mode now emits `DATABASE_USER/PASSWORD/HOST/PORT/SERVICE_NAME` for
`localhost:1521/freepdb1` and emits NO `DATABASE_URL`/`WALLET_PASSWORD`/`TNS_ADMIN`,
so `is_autonomous` stays False. `test_env_utils.py` now asserts the local contract
(and the absence of the wallet keys). Lesson: "matches my live `.env`" is not a
correctness check when the live `.env` is a different deployment mode than the one
being generated — verify the generated `.env` against a clean local container.

## Process note

An external hook auto-committed the work bundled with three unrelated dirty files
(`tools/oracle/cli/database.py`, `test_apex_install.py`, `test_apex_ords.py`). The
fix: `git reset --soft` the auto-commit, `git restore --staged` the three dirty
files (returning them to their original unstaged state), then commit only the four
chapter files. Always verify `git show --name-only <sha>` excludes forbidden files
after committing when hooks are in play.
