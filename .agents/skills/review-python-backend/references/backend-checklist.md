# Python Backend Review Checklist

## Litestar 2, Dishka DI & Security

1. **Controllers (`src/app/domain/*/controllers/`)**:
   - Every HTTP controller must inherit from `PublicController`, `SecureController`, `SkillController`, or `PromptController` (never raw `litestar.Controller`).
   - Cookie-session `POST` endpoints on `PublicController` subclasses must set `auth = exclude()` on the controller and `opt={"exclude_from_csrf": False}` on the handler so CSRF stays active.
   - Never name a query parameter argument `query` without `Parameter(query="query")` (`query` is a reserved Litestar handler kwarg that receives `MultiDict`).
2. **Dishka Providers (`src/app/ioc/`)**:
   - Provider modules (`src/app/ioc/_database.py`, `src/app/ioc/_ai.py`, `src/app/ioc/_domain.py`) must never include `from __future__ import annotations` because Dishka evaluates provider type annotations at runtime.
   - Route handlers use `Inject[T]` (`FromDishka[T]`) with `AutowirePlugin` rather than `@inject` decorators.
3. **Code Hygiene**:
   - Zero non-pragma inline `#` comments in `.py` files (all explanations belong in Google-style docstrings).
   - Zero function-scoped imports (except lazy CLI subcommand callbacks in `src/app/cli/main.py` and `src/app/cli/commands.py`).
   - Every non-`__init__.py` module in `src/app/` defines a module docstring and `__all__`.
   - Class methods follow strict ordering: `__init__` -> `@property` -> public methods -> private `_...` methods.
