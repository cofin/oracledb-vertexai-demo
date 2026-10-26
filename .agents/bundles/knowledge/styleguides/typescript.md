---
type: Guide
title: TypeScript Styleguide
description: TypeScript 7 and ES2022 client module conventions for Vite 8, HTMX 2.x event delegation, SSE streaming, and coordinate privacy
tags:
  - styleguide
  - typescript
---

# TypeScript and Client Module Style Guide

Conventions for TypeScript configuration and ES2022 browser modules under `src/resources/`.

## Frontend Toolchain (`src/resources/`)

The frontend bundle is built from `src/resources/` without a client SPA framework:

- **Bundler**: Vite 8 (`src/resources/vite.config.ts`) integrated with `litestar-vite-plugin` and `@tailwindcss/vite`.
- **Typechecker**: TypeScript 7 (`src/resources/tsconfig.json`) targeting `ES2022` with `DOM` and `DOM.Iterable` libraries, invoked via `make frontend-typecheck` (included in `make lint`).
- **Client Modules**: `src/resources/main.js` (HTMX registration and event delegation), `src/resources/chat-stream.js` (SSE chat reader and structured store cards), `src/resources/geolocation.js` (opt-in browser location), `src/resources/telemetry.js` (SQL and score inspection popover), `src/resources/charts.js` (ApexCharts telemetry), `src/resources/vector-calculator.js` (vector footprint and SGA Vector Pool sizing calculator), `src/resources/easter-egg.js`, and `src/resources/util.js`.

## License Headers

Every `.ts` and `.js` source file under `src/resources/` starts with the SPDX header enforced by `tools/license_headers.py`:

```typescript
// SPDX-FileCopyrightText: 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0
```

## Strict Compiler Configuration (`src/resources/tsconfig.json`)

Keep strict checks enabled in `src/resources/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "moduleResolution": "bundler",
    "noEmit": true,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  }
}
```

## Declarations, Naming, and Exports

| Construct | Convention | Example |
| :--- | :--- | :--- |
| Interfaces & Type Aliases | `PascalCase` | `StreamEvent`, `MapAction` |
| Functions & Methods | `camelCase` | `handleChatSubmit`, `requestBrowserLocation` |
| Local Variables | `camelCase` | `formData`, `stockStatus` |
| Module Constants | `SCREAMING_SNAKE_CASE` | `GEOLOCATION_OPTIONS` |

- Default to `const`; use `let` only when reassignment is required (such as SSE stream buffers), and never use `var`.
- Use named exports (`export const ...`, `export function ...`, `export type { ... }`) across client modules. Reserve `export default` exclusively for framework configuration files that mandate it (`src/resources/vite.config.ts`).

## Type Narrowing and Safe DOM Access

- Prefer `unknown` with explicit runtime checks over `any` or unvalidated `as` type assertions.
- Narrow DOM nodes with `instanceof` (`Element`, `HTMLElement`, `HTMLFormElement`, `HTMLInputElement`, `HTMLButtonElement`, `HTMLTemplateElement`) rather than non-null postfix operators:

```typescript
// SPDX-FileCopyrightText: 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

export function readPersonaSelection(picker: ParentNode): string {
  const selected = picker.querySelector('[data-persona-option][aria-pressed="true"]');
  if (selected instanceof HTMLElement && selected.dataset.personaOption) {
    return selected.dataset.personaOption;
  }
  return "barista";
}
```

## HTMX-Safe Event Delegation (`src/resources/main.js`)

Because HTMX replaces DOM subtrees during partial swaps, avoid binding one-off listeners directly to replaceable elements on initial page load. Delegate `click` and `submit` listeners from `document.body` using `data-*` selectors and `Element.closest(...)`:

```typescript
// SPDX-FileCopyrightText: 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

document.body.addEventListener("click", (event: MouseEvent): void => {
  if (!(event.target instanceof Element)) {
    return;
  }
  const trigger = event.target.closest("[data-use-location]");
  if (trigger instanceof HTMLButtonElement && trigger.form instanceof HTMLFormElement) {
    requestBrowserLocation(trigger.form, trigger);
  }
});
```

When inserting new HTMX-annotated nodes outside normal HTMX swaps, run `processHtmxDom()` (`src/resources/util.js`) so `htmx.process(...)` wires the new subtree.

## Forms, SSE Streaming, and HTML Escaping (`src/resources/chat-stream.js`)

1. **Capture `FormData` Before Disabling Controls**: Always construct `new FormData(form)` before calling `control.disabled = true` on inputs; disabled form controls are omitted from `FormData` per the HTML specification.
2. **CSRF Token Propagation**: Read `<meta name="csrf-token">` and pass `{"x-csrftoken": token}` on `fetch` POST requests (`/api/chat/stream`, `/api/chat/session/clear`).
3. **XSS and URL Validation**: Write plain text via `element.textContent` or escape dynamic strings with `escapeHtml(...)` (`src/resources/util.js`) before inserting HTML templates. Validate external map action URLs (`https://www.google.com/maps/...`) via `new URL(url)` before rendering anchor tags.

```typescript
// SPDX-FileCopyrightText: 2026 Google LLC
// SPDX-License-Identifier: Apache-2.0

export async function submitChatForm(form: HTMLFormElement): Promise<void> {
  const input = form.elements.namedItem("message");
  if (!(input instanceof HTMLInputElement)) {
    return;
  }
  const message = input.value.trim();
  if (!message) {
    return;
  }

  const formData = new FormData(form);
  formData.set("message", message);
  input.disabled = true;

  try {
    const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content");
    const headers: Record<string, string> = { Accept: "text/event-stream" };
    if (token) {
      headers["x-csrftoken"] = token;
    }
    const response = await fetch(form.action, { method: "POST", body: formData, headers });
    if (!response.ok) {
      throw new Error(`Chat request failed with status ${response.status}`);
    }
  } finally {
    input.disabled = false;
  }
}
```

## Opt-In Browser Geolocation (`src/resources/geolocation.js`)

- Call `navigator.geolocation.getCurrentPosition(...)` only in response to an explicit user click on `[data-use-location]`.
- Populate request-scoped hidden form fields (`[data-location-consent]`, `[data-location-latitude]`, `[data-location-longitude]`, `[data-location-accuracy]`) in memory only; never persist raw coordinates in `localStorage`, `sessionStorage`, cookies, or URL query strings.
- Clear all coordinate fields whenever geolocation is unsupported, denied, or times out.

## Build and Verification Commands

```bash
uv run python manage.py assets install
uv run python manage.py assets build
make frontend-typecheck
make lint
```
