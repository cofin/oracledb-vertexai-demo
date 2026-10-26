---
type: Guide
title: General Styleguide
description: Repository-wide conventions for naming, SPDX licensing, single canonical contracts, documentation, and privacy
tags:
  - styleguide
  - general
---

# General Code Style Principles

These principles apply across every language, template, SQL asset, and configuration file in the Cymbal Coffee repository.

## Clarity and Domain Naming

- Prefer straightforward, readable control flow over clever or compressed constructs.
- Name modules, classes, functions, CSS hooks, and SQL queries after the domain concept they represent (`ProductService`, `StoreService`, `SearchMetrics`, `build_oracle_text_query`) rather than implementation mechanics or temporary refactoring history.
- Keep formatting consistent with automated repository linters (`make lint`, `make format`, `make frontend-typecheck`).

## Single Canonical Implementation

- Maintain one canonical implementation per domain concern.
- When refactoring a schema, service, CLI command, or helper, update all callers and tests directly instead of leaving backward-compatibility aliases, re-export shims, deprecated flags, or fallback wrappers behind.
- Keep modules focused on a single cohesive responsibility and avoid speculative abstractions.

## License Headers and File Hygiene

- Begin every source-owned code, script, stylesheet, SQL, and Jinja2 template file with the project SPDX license header (`SPDX-FileCopyrightText: 2026 Google LLC` and `SPDX-License-Identifier: Apache-2.0`), enforced and maintained by `tools/license_headers.py` (`uv run python tools/license_headers.py --fix`).
- Encode all text files as UTF-8 without a byte-order mark, strip trailing whitespace on lines, and terminate every file with a single trailing newline.
- Never commit generated build outputs (`dist/`, `.venv/`, `src/resources/node_modules/`, or generated Vite bundle artifacts under `src/resources/public/`) that are excluded by `.gitignore` or managed by `manage.py assets build`.

## Documentation and Prose Hygiene

- Document *why* a design choice, constraint, or edge case exists rather than restating *what* obvious statements do.
- In Python files (`src/app/`, `src/tests/`, `tools/`, `manage.py`), never write inline `#` comments; place explanations in module, class, and function Google-style docstrings.
- Keep documentation, docstrings, UI copy, and error messages calm, direct, and matter-of-fact: avoid exclamation marks, promotional filler, and artificial count-prefixed labels.
- Keep knowledge files (`.agents/bundles/knowledge/`), public docs (`docs/`, `README.md`), and tests synchronized whenever public APIs, CLI commands, settings, or database contracts change.

## Privacy and Secret Hygiene

- Never commit credentials, wallets, `.env` files, API keys, or workstation-specific absolute paths.
- Treat browser geolocation coordinates (`latitude`, `longitude`, `accuracy_meters`, `radius_miles`) as ephemeral, opt-in request inputs: never persist them to database tables, caches, telemetry rows, or application logs.

## Language-Specific Guides

- [Python Styleguide](python.md)
- [Bash Styleguide](bash.md)
- [HTML and CSS Styleguide](html-css.md)
- [TypeScript Styleguide](typescript.md)
