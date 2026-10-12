# API reference

Generated docstrings for the core orchestration, hybrid routing, and database
services that power the demo.

## Agent orchestration & hybrid router

The native `google-genai` turn orchestrator and single-query Oracle 26ai
Hybrid RRF router that tie the Litestar chat controller to grounded
row-rendered routes, closure-bound tools, and multi-step `AgentRuntime`
conversations.

```{eval-rst}
.. autoclass:: app.domain.ai.services.AgentOrchestrationService
   :members:

.. autoclass:: app.domain.chat.services.HybridRouteResolver
   :members:
```

## Services

`OracleAsyncService` subclasses that own the named-SQL queries and result
mapping for products, hybrid search, the embedding/response caches, and the
per-message metrics surfaced on `/explore`.

```{eval-rst}
.. autoclass:: app.domain.products.services.ProductService
   :members:

.. autoclass:: app.domain.system.services.CacheService
   :members:

.. autoclass:: app.domain.system.services.MetricsService
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
