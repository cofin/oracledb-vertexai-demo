# Python Backend Review Checklist

## Litestar 2, Dishka DI, Immutable Schemas & Code Hygiene

1. **Controllers & Private `_*` Domain Module Layout**:
   - Domain packages implement logic in private `_*` modules re-exported through package `__init__.py` facades:
     - Products controllers (`src/app/domain/products/controllers/_products.py`, `src/app/domain/products/controllers/_vector.py`, `src/app/domain/products/controllers/_apex.py` `ApexController`, `src/app/domain/products/controllers/_apex_ai.py` `ApexAIController`) and services (`src/app/domain/products/services/_products.py` `ProductService`, `src/app/domain/products/services/_stores.py` `StoreService`, `src/app/domain/products/services/_vector.py` `OracleVectorSearchService`, `src/app/domain/products/services/_embedding.py` `VertexAIService`, `src/app/domain/products/services/_maps.py`, `src/app/domain/products/services/_location.py`).
     - System controllers (`src/app/domain/system/controllers/_system.py` `SystemController`, `src/app/domain/system/controllers/_metrics.py` `MetricsController`) and services (`src/app/domain/system/services/_cache.py` `CacheService`, `src/app/domain/system/services/_metrics.py` `MetricsService`, `src/app/domain/system/services/_personas.py` `PersonaManager`).
     - Chat (`src/app/domain/chat/controllers/_chat.py`, `src/app/domain/chat/services/_router.py`, `src/app/domain/chat/services/_grounded.py`, `src/app/domain/chat/services/_composers.py`, `src/app/domain/chat/services/_telemetry.py`) and web (`src/app/domain/web/controllers/_pages.py` `PageController`).
   - Every HTTP controller must inherit from `PublicController`, `SecureController`, `SkillController`, or `PromptController` (enforced by `tools/ci/check_litestar_security.py`; never raw `litestar.Controller`).
   - Cookie-session `POST` endpoints on `PublicController` subclasses must set `auth = exclude()` on the controller and `opt={"exclude_from_csrf": False}` on the handler so CSRF stays active, whereas stateless server-to-server endpoints such as `ApexAIController` (`src/app/domain/products/controllers/_apex_ai.py`) explicitly set `opt={"exclude_from_csrf": True}`.
   - Never name a Python handler parameter `query` for a URL query string (`query` is a reserved Litestar handler kwarg that receives `MultiDict` and raises `ImproperlyConfiguredException` if annotated with `QueryParameter` or `Parameter`); use a non-reserved parameter name such as `q` or `search_query` with `Annotated[..., QueryParameter(name="query")]` or `Parameter(query="query")`.
2. **Immutable Schemas & Serialization (`src/app/lib/schema.py`, `src/app/utils/serialization.py`)**:
   - Domain and wire schemas inherit from `FrozenBaseStruct` or `CamelizedFrozenStruct` (`msgspec.Struct(..., frozen=True, gc=False, omit_defaults=True)` in `src/app/lib/schema.py`).
   - Route JSON encoding and decoding through centralized utilities in `src/app/utils/serialization.py` (`encode_json`, `format_json`, `decode_json`, `sanitize_for_json`).
3. **Dishka Container & Providers (`src/app/ioc/__init__.py`)**:
   - Container wiring uses `create_container()` and `get_providers()` in `src/app/ioc/__init__.py`, assembling `ConfigProvider` (`src/app/ioc/_config.py`), `DBProvider` (`src/app/ioc/_database.py`), `AIProvider` (`src/app/ioc/_ai.py`), and `DomainServiceProvider` (`src/app/ioc/_domain.py`).
   - Modules under `src/app/ioc/` (`src/app/ioc/__init__.py`, `src/app/ioc/_config.py`, `src/app/ioc/_database.py`, `src/app/ioc/_ai.py`, `src/app/ioc/_domain.py`) must never include `from __future__ import annotations` because Dishka evaluates provider type annotations at runtime.
   - Never import `app.config` inside `src/app/domain/`, `src/app/ioc/`, or `src/app/lib/`; consume `Settings` via Dishka or `Settings.from_env()`.
   - Route handlers use `Inject[T]` (`FromDishka[T]`) with `AutowirePlugin` rather than `@inject` decorators.
4. **AST & Token Code Hygiene (`tools/ci/check_code_hygiene.py`, `src/tests/unit/test_test_suite_guards.py`)**:
   - `tools/ci/check_code_hygiene.py` (across `src/app/`, `tools/` including `tools/demos/` and `tools/oracle/`, and `manage.py`) together with `src/tests/unit/test_test_suite_guards.py` (across `src/app/` and `src/tests/`) and Ruff (`RUF022`) enforce repository-wide hygiene:
     - Zero non-directive inline `#` comments in `.py` files (all explanations belong in Google-style docstrings).
     - Zero function-scoped imports (except lazy CLI subcommand callbacks in `src/app/cli/main.py` and `src/app/cli/commands.py`).
     - Top-level module docstring, sorted `__all__` (required on every non-`__init__.py` module under `src/app/`), and public symbols defined strictly before private `_...` helpers.
     - Class member ordering (`class attributes` -> `__init__` -> `@property` -> `public methods` -> `private _... methods` on `src/app/` classes) and `@dataclass(slots=True)` on every dataclass.
