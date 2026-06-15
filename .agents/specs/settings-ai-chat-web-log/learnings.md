# Learnings: settings-ai-chat-web-log (mzm.8)

## Settings env mutation must move out of `__post_init__` for frozen dataclasses
`VertexAISettings.__post_init__` mutated `os.environ` and nulled `API_KEY` during
construction. Relocated to `Settings.configure_genai_env()` called from
`Settings.from_env()` (alongside `setup_litestar_env()`). The dataclass stays
effectively immutable; `ioc.provide_genai_client` already branches on
`project_id` (Vertex path ignores `api_key`), so nulling the field on the
instance was unnecessary once the env vars are cleared at startup.

## Renaming `Settings.vertex_ai` -> `Settings.ai` is contained, not high-churn
Consumers were ioc.py (genai client, intent classifier, vertex service),
cli/commands.py (model-info), adk.py (credential guard + workflow model), plus
two unit tests and one integration test that stub settings. The PRD flagged this
as "deferrable/high-churn"; in practice it was a clean rename. Lowercase fields:
`project_id/location/api_key/chat_model/intent_model_override` + derived
`intent_model` property + `embedding_model/embedding_dimensions`.

## ChatSettings is the single source for chat-workflow constants
`adk.py` no longer hardcodes `_APP_NAME`, `_CHAT_CACHE_VERSION`, `ttl_minutes=60`,
`history[-40:]`, or the closure tool's `limit=5`/`threshold=0.7`. All read from
`get_settings().chat`. Closure-tool defaults bind `chat.product_search_limit`/
`product_search_threshold` at factory-build time; `AgentToolsService.search_*`
resolves `None` defaults to settings so explicit caller args still win.
The data-layer `ProductService.search_by_vector` keeps its own `0.7`/`5` literal
defaults (not a duplicated chat constant — the chat layer owns ChatSettings).

## Typing the embedding-cache read makes `EmbeddingCache` live
Widened `get-cached-embedding` named SQL to the full row and mapped via
`schema_type=EmbeddingCache` in `CacheService.get_embedding`; return
`cached.embedding`. Public contract (`list[float] | None`) and hit_count/
last_accessed bump unchanged. Symmetric with `ResponseCache`.

## Tests stubbing `get_settings()` must mirror the new namespace shape
Any test that monkeypatches `adk_module.get_settings` to a MagicMock/
SimpleNamespace must now provide `ai.*` AND a full `chat.*` namespace, because
session lookups, cache key/TTL, and display-history truncation all read
`get_settings().chat`. Missing attrs surface as AttributeError at runtime, not
import time.
