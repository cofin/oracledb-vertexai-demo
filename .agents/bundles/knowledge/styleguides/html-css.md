---
type: Guide
title: HTML and CSS Styleguide
description: Jinja2 HTML templates, HTMX 2.x fragment contracts, data-* hooks, and Tailwind CSS v4 theme conventions
tags:
  - styleguide
  - html
  - css
---

# HTML, Jinja2, HTMX, and Tailwind CSS Guide

Conventions for server-rendered Jinja2 templates (`src/app/domain/web/templates/`) and Tailwind CSS v4 stylesheets (`src/resources/styles.css`).

## License Headers

Every `.html.j2` template and `.css` file starts with the SPDX header enforced by `tools/license_headers.py`:

```html
{#
SPDX-FileCopyrightText: 2026 Google LLC
SPDX-License-Identifier: Apache-2.0
#}
```

```css
/*
 * SPDX-FileCopyrightText: 2026 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */
```

## Jinja2 Template Architecture (`src/app/domain/web/templates/`)

- **Layout Hierarchy**: Full pages (`src/app/domain/web/templates/pages/chat.html.j2`, `src/app/domain/web/templates/pages/explore.html.j2`) extend `src/app/domain/web/templates/base.html.j2` and override `title`, `page_kicker`, `page_heading`, `page_subheading`, and `content` blocks.
- **Partials**: HTMX fragment targets and shared chrome live under `src/app/domain/web/templates/partials/` and `src/app/domain/web/templates/_nav.html.j2`.
- **Vite and CSRF Integration**: `src/app/domain/web/templates/base.html.j2` injects `<meta name="csrf-token" content="{{ csrf_token() }}">` alongside `{{ vite_hmr() | safe }}` and `{{ vite(['styles.css', 'main.js']) | safe }}`.
- **Auto-Escaping**: Keep Jinja2 auto-escaping active for all user, model, and database strings. Reserve `| safe` strictly for trusted framework asset helpers (`vite_hmr()`, `vite(...)`), and escape JSON attributes with `| e` (`data-telemetry-detail="{{ hybrid_detail_json | e }}"`).
- **Dynamic Entity Options**: Populate `<select>` menus and filter pills from live service data passed in template context (for example, `StoreService` in `src/app/domain/products/services/_stores.py`) rather than hardcoding database primary keys that can shift across seeds.

```html
<!DOCTYPE html>
<html lang="en" class="bg-canvas">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="csrf-token" content="{{ csrf_token() }}">
  <title>{% block title %}Cymbal Coffee{% endblock %}</title>
  {{ vite_hmr() | safe }}
  {{ vite(['styles.css', 'main.js']) | safe }}
</head>
<body hx-ext="litestar" data-app-shell="true" class="app-shell font-sans text-strong antialiased">
  <main class="app-main">
    {% block content %}{% endblock %}
  </main>
</body>
</html>
```

## Semantic HTML, Accessibility, and External Links

- Indent HTML and Jinja2 blocks by 2 spaces with double-quoted attribute values.
- Use semantic landmarks (`<header>`, `<nav>`, `<main>`, `<section>`, `<article>`) and associate every form control with an explicit `<label for="...">` or `aria-label`.
- Keep interactive state accessible (`aria-pressed` on toggle pills, `aria-live` regions for streamed chat updates, `alt` attributes on images with `aria-hidden="true"` on decorative icons).
- Add `rel="noopener noreferrer"` to external `target="_blank"` anchors, and restrict Google Maps links to keyless `https://www.google.com/maps/...` URLs.

## HTMX 2.x and Behavior Hooks

- **Litestar HTMX Extension Scoping**: `src/app/domain/web/templates/base.html.j2` sets `hx-ext="litestar"` on `<body>` for CSRF header injection and JSON payload support. When an HTMX form posts standard form-encoded fields and expects an HTML partial response (`HTMXTemplate` from `litestar_htmx`, imported from `litestar_htmx` rather than `litestar.plugins.htmx`), wrap the panel or form with `hx-ext="ignore:litestar"` as in `src/app/domain/web/templates/pages/explore.html.j2`:

```html
<section id="panel-vector-search" data-ui-panel="vector-search" hx-ext="ignore:litestar" class="ui-panel p-4">
  <form id="explore-search-form" hx-post="/api/vector-demo"
    hx-trigger="submit, keyup changed delay:300ms"
    hx-target="#search-results" hx-swap="outerHTML">
    <label for="explore-query" class="mb-1 block text-xs font-semibold uppercase text-muted">Search the menu</label>
    <input id="explore-query" type="search" name="query" value="{{ query }}" autocomplete="off" required>
  </form>
  <div id="search-results" class="mt-3 min-h-28 space-y-2"></div>
</section>
```

- **Decoupled `data-*` Hooks**: Attach JavaScript event listeners via `data-*` attributes (`data-chat-form="true"`, `data-use-location`, `data-clear-chat`, `data-telemetry-detail`, `data-persona-picker`) instead of styling classes so visual refactors never break client behavior.

## Tailwind CSS v4 (`src/resources/styles.css`)

`src/resources/styles.css` uses Tailwind CSS v4 CSS-first configuration compiled by `@tailwindcss/vite`:

- **Template Scanning**: `@import "tailwindcss";` followed by `@source "../app/domain/web/templates";` ensures utility classes in every `.html.j2` template are discovered during Vite builds.
- **Semantic Design Tokens (`@theme`)**: Define palette and typography tokens inside `@theme` (`--color-canvas`, `--color-deep`, `--color-surface`, `--color-surface-strong`, `--color-border`, `--color-strong`, `--color-base`, `--color-muted`, `--color-accent`, `--color-accent-strong`, `--color-accent-soft`, `--color-success`, `--color-danger`, `--color-sage`, `--color-sky`, `--font-sans`) and reference them through utility classes (`bg-surface`, `text-strong`, `text-muted`, `border-border`, `bg-accent-soft`).
- **Component Layer (`@layer components`)**: Extract multi-property layout chrome and repeated interactive surfaces (`.app-shell`, `.app-header`, `.ui-panel`, `.telemetry-chip`, `.message-row`) into `@layer components` in `src/resources/styles.css`.
- **Specificity Discipline**: Avoid inline `style="..."` attributes, ID-based CSS selectors, and CSS importance overrides; control cascade order through `@layer components` and semantic utility classes.
- **Overflow Safety**: Include `min-w-0` on flex and CSS Grid children that wrap long SQL plans, telemetry badges, or streamed text so panels never overflow mobile viewports.
