# APEXlang Source

This directory is the source-controlled root for Oracle APEX 26.1 APEXlang
applications.

Use SQLcl 26.1.2 or newer through the local infra CLI:

```bash
uv run python manage.py infra apex generate --alias cymbal-coffee-ops
uv run python manage.py infra apex export --app-id 100 --alias cymbal-coffee-ops
uv run python manage.py infra apex validate --alias cymbal-coffee-ops
uv run python manage.py infra apex import --alias cymbal-coffee-ops
```

Generated applications should live under `src/apex/<alias>/`. SQLcl 26.1.2
generates names such as `application.apx`, `pages/`, `shared-components/`,
`supporting-objects/`, `deployments/`, and `.apex/`.

The current Cymbal Coffee Operations Console uses importable APEX interactive
reports over local Oracle tables and keeps the `/api/apex` endpoint bridge
visible in page regions. APEX 26.1 validates app-level `restDataSource`
APEXlang, but local import rolls back with
`WWV_WEBSRC_MODULE_RSERVER_FK` when those sources reference a REST Data Source
Server; do not mark REST Source Catalog wiring complete until that import path
round-trips.
