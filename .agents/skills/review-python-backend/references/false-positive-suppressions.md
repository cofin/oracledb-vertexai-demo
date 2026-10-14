# Python Backend False-Positive Suppressions

DO NOT FLAG any of the following deliberate architectural patterns:

## `FP-PY-01` — Absence of `from __future__ import annotations` in `src/app/ioc/`

- **DO NOT FLAG** missing `from __future__ import annotations` in `src/app/ioc/_database.py`, `src/app/ioc/_ai.py`, or `src/app/ioc/_domain.py`.
- **Rationale**: Dishka introspects provider parameter and return annotations at runtime to build the dependency graph. Stringified annotations break Dishka provider resolution.

## `FP-PY-02` — Absence of `@inject` Decorators on Litestar Route Handlers

- **DO NOT FLAG** Litestar route handlers that use `Inject[Service]` (`FromDishka[Service]`) without `@inject`.
- **Rationale**: `AutowirePlugin(AutowireConfig(domain_packages=["app.domain"], integrations=["dishka", "queues"]))` in `src/app/server/plugins.py` wraps controllers in `DishkaRouter` automatically.

## `FP-PY-03` — `auth = exclude()` on `PublicController` Subclasses with Cookie-Session `POST` Routes

- **DO NOT FLAG** `auth: ClassVar[AuthenticationPolicy] = exclude()` combined with `opt={"exclude_from_csrf": False}` in `src/app/domain/chat/controllers/_chat.py` or `src/app/domain/products/controllers/_vector.py`.
- **Rationale**: In `litestar-security` 0.6.0, `public()` sets `csrf="exclude"` and rejects `opt={"exclude_from_csrf": False}`. Setting `auth = exclude()` allows public cookie-session `POST` routes to enforce Litestar's native CSRF middleware.
