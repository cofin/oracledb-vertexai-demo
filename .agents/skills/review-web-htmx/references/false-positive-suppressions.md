# Web & HTMX False-Positive Suppressions

DO NOT FLAG any of the following deliberate web and HTMX patterns:

## `FP-WEB-01` — `ViteConfig(types=False)` in `src/app/lib/settings/_server.py`

- **DO NOT FLAG** `types=False` in `ViteSettings.get_config()` (`src/app/lib/settings/_server.py`).
- **Rationale**: The frontend uses server-rendered Jinja2 templates with vanilla JavaScript and HTMX rather than generated TypeScript OpenAPI/AsyncAPI clients. Setting `types=False` disables unused `litestar-asyncapi` codegen warnings during asset builds.

## `FP-WEB-02` — `hx-ext="ignore:litestar"` on HTML Fragment Forms

- **DO NOT FLAG** `hx-ext="ignore:litestar"` on HTMX form containers in `src/app/domain/web/templates/`.
- **Rationale**: The application registers `hx-ext="litestar"` on the root shell for JSON routes, so HTML fragment panels use `hx-ext="ignore:litestar"` to receive server-rendered HTML partials cleanly.
