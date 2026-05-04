# API reference

Generated docstrings for the small set of classes that carry the demo's
behavior. The rest of the codebase — CLI commands, settings dataclasses,
plugin wiring, IoC providers — is intentionally out of scope; their
shapes are stable and reading the source is faster than reading
generated docs.

## ADK runner

The per-request chat runner that ties the Litestar chat controller to
Flash-Lite intent routing, deterministic grounded routes, Google ADK 2.0
fallbacks, and closure-bound tools.

```{eval-rst}
.. autoclass:: app.domain.chat.services.adk.ADKRunner
   :members:
```

## Services

`SQLSpecAsyncService` subclasses that own the named-SQL queries and result
mapping for products, the embedding/response caches, and the per-message
metrics surfaced on `/explore`.

```{eval-rst}
.. autoclass:: app.domain.products.services.services.ProductService
   :members:

.. autoclass:: app.domain.system.services.services.CacheService
   :members:

.. autoclass:: app.domain.system.services.services.MetricsService
   :members:
```

## Schemas

`msgspec.Struct` types used for request/response bodies, named-SQL row
mapping, and tool payloads.

```{eval-rst}
.. automodule:: app.domain.chat.schemas
   :members:

.. automodule:: app.domain.products.schemas
   :members:

.. automodule:: app.domain.system.schemas
   :members:
```
