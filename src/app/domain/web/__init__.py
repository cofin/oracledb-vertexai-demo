# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
"""Web domain — Jinja templates and the litestar-vite bundle output for the
HTMX frontend.

The package marker turns ``domain/web`` into a peer-domain alongside
``chat``/``products``/``system``:

* ``templates/`` — Jinja2 sources resolved by Litestar's ``TemplateConfig``.
* ``static/dist/`` — Vite bundle output (gitignored). ``manage.py assets
  build`` writes ``manifest.json`` + hashed bundles here.
* ``controllers/`` — page-level route handlers that render those templates.
"""
