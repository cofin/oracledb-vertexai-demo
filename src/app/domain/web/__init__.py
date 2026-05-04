# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Web domain — Jinja templates and the litestar-vite bundle output for the
HTMX frontend.

The package marker turns ``domain/web`` into a peer-domain alongside
``chat``/``products``/``system``:

* ``templates/`` — Jinja2 sources resolved by Litestar's ``TemplateConfig``.
* ``static/`` — Vite bundle output (gitignored). ``manage.py assets
  build`` writes ``manifest.json`` + hashed bundles here.
* ``controllers/`` — page-level route handlers that render those templates.
"""
