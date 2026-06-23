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

Generated applications should live under `src/apex/<alias>/`. Oracle's APEXlang
layout uses names such as `application.apx`, `pages/`, `shared_components/`,
`supporting_objects/`, `deployments/`, and `.apex/`.
