# Learnings: APEXlang Source

## 2026-06-23 - SQLcl APEXlang Wrapper

- **Implemented:** SQLcl 26.1.2+ capability detection, an `ApexLang` wrapper that runs SQLcl with `/nolog` and sends the database connection through stdin, and `infra apex generate|export|validate|import` commands rooted under `src/apex/<alias>/`.
- **Files changed:** `tools/oracle/apex_lang.py`, `tools/oracle/sqlcl_installer.py`, `tools/oracle/cli/apex.py`, `tools/oracle/__init__.py`, `src/apex/README.md`, and focused unit tests.
- **Commands:** `uv run pytest src/tests/unit/tools/oracle/test_sqlcl_installer.py src/tests/unit/tools/oracle/test_apex_lang.py src/tests/unit/tools/oracle/test_apex_install.py -q`; `uv run mypy src/app tools manage.py`; `uv run pyright src/app tools manage.py`; `uv run ruff check src/app tools src/tests/unit`.
- **Gotchas:** Keep the SQLcl password out of argv; use `/nolog` plus stdin connection text. APEXlang needs SQLcl/APEX 26.1.2+ support, so command handlers should fail with install/upgrade guidance instead of trying to run older SQLcl binaries.
