# Learnings: apex-ops-app

- SQLcl 26.1.2 can validate APEXlang `restDataSource` components that reference
  a `restDataSourceServer`, but the local APEX 26.1 import path rolled back
  with `WWV_WEBSRC_MODULE_RSERVER_FK` for those sources.
- Pre-creating workspace remote servers with both `litestar-api` and
  `litestar_api` static IDs and calling
  `APEX_APPLICATION_INSTALL.SET_REMOTE_SERVER` did not satisfy the import FK.
- Keep the operations console importable with SQL-backed interactive reports
  until a generated App Builder round trip or Oracle patch provides a
  source-controlled REST Data Source import shape that imports cleanly.
- Treat SQLcl stdout markers `APEXLang Compile Errors:` and
  `APEXLang Import Errors:` as fatal even when SQLcl exits with status 0.
- Completion evidence for the importable SQL-backed app leaf: `uv run pytest
  src/tests/unit/tools/oracle -q` passed with 149 tests, SQLcl validate/import
  and export passed for app 100, `git diff --check` passed, `make lint` passed,
  and `make test` passed with 378 tests.
