# Web & HTMX False-Positive Suppressions

DO NOT FLAG any of the following deliberate web and HTMX patterns:

## `FP-WEB-01` — `ViteConfig(types=False)` in `src/app/lib/settings/_server.py`

- **DO NOT FLAG** `types=False` in `ViteSettings.get_config()` (`src/app/lib/settings/_server.py`).
- **Rationale**: The frontend uses server-rendered Jinja2 templates with vanilla JavaScript and HTMX rather than generated TypeScript OpenAPI/AsyncAPI clients. Setting `types=False` disables unused `litestar-asyncapi` codegen warnings during asset builds.

## `FP-WEB-02` — `hx-ext="ignore:litestar"` on HTML Fragment Forms

- **DO NOT FLAG** `hx-ext="ignore:litestar"` on HTMX form containers in `src/app/domain/web/templates/`.
- **Rationale**: The application registers `hx-ext="litestar"` on the root shell for JSON routes, so HTML fragment panels use `hx-ext="ignore:litestar"` to receive server-rendered HTML partials cleanly.

## `FP-WEB-03` — Keyless Google Maps URLs in `src/app/domain/products/services/_maps.py` and `src/apex/cymbal-coffee-ops/pages/p00003-stores.apx`

- **DO NOT FLAG** `build_store_search_url` / `build_store_directions_url` in `src/app/domain/products/services/_maps.py` or `utl_url.escape(...)` `google_maps_url` expressions in `src/apex/cymbal-coffee-ops/pages/p00003-stores.apx` for omitting a Google Maps API key.
- **Rationale**: Google Maps Universal Cross-Platform URLs (`/maps/search/?api=1` and `/maps/dir/?api=1`) are officially keyless deep links constructed purely from seeded `STORE` street addresses while preserving browser-coordinate privacy.
