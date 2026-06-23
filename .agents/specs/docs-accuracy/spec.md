# Flow: docs-accuracy

*Beads: oracledb-vertexai-mzm.1*

## Specification

The Cymbal Coffee docs and agent-context files drifted from the shipped code:
embedding instructions name an API parameter the code never uses, the model
literal and fixture counts are stale, and store/inventory/maps features that
have shipped are still described as "planned." This chapter brings every
tracked doc and `.agents` context file to 100% accuracy against current source
with zero outdated or hallucinated references. Editing `AGENTS.md` fixes
`CLAUDE.md` automatically because `CLAUDE.md` is a symlink to `AGENTS.md`.

### Requirements

* Replace every `task_type="RETRIEVAL_QUERY"/"RETRIEVAL_DOCUMENT"` *instruction*
  with the real mechanism: an `embedding_purpose="query"/"document"` argument
  whose value selects a text instruction prefix from
  `EMBEDDING_PURPOSE_INSTRUCTIONS`; the code sends no `task_type` parameter.
* Correct the embedding model literal from `gemini-embedding-2` to
  `gemini-embedding-2-preview` in every tracked doc and context file.
* Correct fixture counts from `122 products` / `16 stores` to the actual
  `130 products` / `17 stores`.
* Reframe store, inventory, and maps from "planned" to shipped, since the
  data, services, intent routes, and rendering exist in source.
* Fix the embedding-method reference in `docs/tour.md` from the non-existent
  `ProductService.embed_text` to `VertexAIService.get_text_embedding`.
* Fix `.agents/tech-stack.md` version/wording: `google-adk>=2.0.0` (not
  `2.2.0`), and stop conflating the `litestar-granian` plugin with the Granian
  server.
* Fix the service base class in `AGENTS.md` and `docs/reference/api.md` from
  `SQLSpecAsyncService[OracleAsyncDriver]` to `OracleAsyncService`.
* Fix the `512M` vector-memory attribution in `docs/reference/quickstart.md`
  to the `database.py` default, not `configure_vector_memory.sql` (which sets
  `4G`).
* Add the missing `PRODUCT_AVAILABILITY` label to the intent list in
  `.agents/knowledge/guides/adk-agent-patterns.md`.
* Leave the ADK migration source plan aspirational sections intact; only flag
  its two internal contradictions as plan-execution caveats (do not "correct"
  them to match the current stack).
* Do not touch `docs/_build/html/` (gitignored, out of scope).
* Docs/docstrings describe behavior only; no spec/phase/flow-ID references in
  any edited text.

### Code Analysis Summary

* `src/app/domain/products/services/services.py:35` — model literal
  `GEMINI_EMBEDDING_2_MODEL = "gemini-embedding-2-preview"`.
* `services.py:36-45` — `EMBEDDING_PURPOSE_INSTRUCTIONS` dict keyed by
  `"query"` / `"document"`; each value is an instruction string.
* `services.py:272-296` — `VertexAIService.get_text_embedding(text, *,
  embedding_purpose="document", ...)`; builds content via `_embedding_content`,
  calls `client.aio.models.embed_content(... config=EmbedContentConfig(
  output_dimensionality=self.embedding_dimensions))`. No `task_type`.
* `services.py:301-307` — `_embedding_content(model, text, embedding_purpose)`
  prepends the matching instruction only when the model contains
  `gemini-embedding-2-preview`.
* `services.py:48` — `class ProductService(OracleAsyncService)`. `ProductService`
  has no `embed_text` and no embedding call; embedding lives on `VertexAIService`.
* `services.py:321-322,380-381` — call sites use
  `get_text_embedding(query, embedding_purpose="query", ...)`.
* `src/app/lib/service.py:35` — `class OracleAsyncService(SQLSpecAsyncService[OracleAsyncDriver])`;
  exported in `__all__` (line 55).
* `src/app/lib/settings.py:349` — `EMBEDDING_MODEL` default
  `gemini-embedding-2-preview`; `:351-352` — `EMBEDDING_DIMENSIONS = 3072`.
* `tools/oracle/database.py:27` — `DEFAULT_VECTOR_MEMORY_SIZE = "512M"`; applied
  via `configure_vector_memory()` (`:42,210,232,465,485`). This is the source of
  the 512M default.
* `tools/oracle/configure_vector_memory.sql:26` — sets
  `vector_memory_size = 4G SCOPE = SPFILE` (larger-edition path, not 512M).
* `src/app/domain/chat/services/classifier.py:17-24` — `IntentLabel(StrEnum)`
  has 6 members: `PRODUCT_RAG`, `PRODUCT_AVAILABILITY`, `GENERAL_CONVERSATION`,
  `STORE_LOCATION`, `ORDER_STATUS` (plus the enum itself).
* `src/app/db/migrations/0001_cymball_coffee_products.sql` — contains store
  coordinates, `store_product_inventory`, and stock booleans (store/inventory
  shipped, not planned).
* `src/app/domain/products/services/maps.py` and `_location.py` exist (maps and
  nearest-store ranking shipped).
* `src/app/ioc.py:38,61,105` — three providers
  (`LitestarPersistenceProvider`, `IntegrationsProvider`, `DomainServiceProvider`);
  AGENTS.md "three app providers" is accurate, leave it.
* Fixture counts (verified by gunzip + len): `product.json.gz` = 130,
  `store.json.gz` = 17, `store_product_inventory.json.gz` = 1700.
* `pyproject.toml:25` — `google-adk>=2.0.0`; `:20` — `litestar-granian[uvloop]`
  (plugin dep, distinct from the Granian server).
* `.agents/specs/adk2-sqlspec-migration/source-plan.md:1` — "ADK 2.2 /
  SQLSpec 0.50 Migration Plan" (forward-looking). Contradictions to flag, not
  fix: `:558` (1536-dim), `:609` / `:717` (`gemini-embedding-002`), `:719`
  (`RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY`).
* `CLAUDE.md` is a symlink -> `AGENTS.md` (verified `ls -la`); never edit
  `CLAUDE.md` directly.

### Accuracy facts the implementer must NOT change

* `.agents/patterns.md:118-119` already says "Do not send the old embedding
  `task_type` API parameter" — accurate, keep the prose; only fix the
  `gemini-embedding-2` model literal on line 29 and 118.
* `docs/tour.md:97-99` already says Gemini Embedding 2 "does not use the old
  embedding `task_type` API parameter" — accurate, keep. Only fix the model
  literal (`:78,:96`) and the `embed_text`/owning-class error (`:95`).

### Files verified clean (no change; record as verified)

`docs/maps.md`, `docs/concepts/agent-flow.md`, `docs/concepts/rag.md`,
`docs/reference/developers.md`, `CONTRIBUTING.md`, `.agents/index.md`.

## Implementation Plan

### Phase 1: AGENTS.md core (also fixes CLAUDE.md via symlink)

- [ ] 1.1 `AGENTS.md:17` — change "`gemini-embedding-2` embeddings" to
  "`gemini-embedding-2-preview` embeddings".
- [ ] 1.2 `AGENTS.md:20-22` — rewrite the "**Planned components**" bullet so
  store coordinates/inventory, deterministic store and product-availability
  routes, browser location opt-in, and no-key Maps URLs are described as
  shipped; keep only genuinely forward-looking items (e.g. optional Maps Embed,
  settings cleanup) as such, matching the actual `0001` migration, `maps.py`,
  `_location.py`, and `classifier.py`.
- [ ] 1.3 `AGENTS.md:127` — change the import line
  `from app.lib.service import SQLSpecAsyncService` to
  `from app.lib.service import OracleAsyncService`.
- [ ] 1.4 `AGENTS.md:130` — change
  `class ProductService(SQLSpecAsyncService[OracleAsyncDriver]):` to
  `class ProductService(OracleAsyncService):` (drop the now-unused
  `OracleAsyncDriver` reference from the snippet).
- [ ] 1.5 `AGENTS.md:161-163` (the `### Vertex AI` block) — replace the
  `task_type="RETRIEVAL_QUERY"`/`task_type="RETRIEVAL_DOCUMENT"` instruction
  with the real mechanism: pass `embedding_purpose="query"` for user search
  queries and `embedding_purpose="document"` for product/document embeddings,
  which selects a text instruction prefix from `EMBEDDING_PURPOSE_INSTRUCTIONS`;
  no `task_type` parameter is sent. Update the model literal in the same block
  to `gemini-embedding-2-preview` and keep `EMBEDDING_DIMENSIONS = 3072`.
- [ ] 1.6 `AGENTS.md:175-181` (`### Store, Inventory, And Maps`) — reframe
  "Planned data changes belong in the baseline `0001` migration" as shipped in
  the `0001` migration; keep the typed-service/named-SQL guidance.

### Phase 2: README and docs/

- [ ] 2.1 `README.md:37` — change "122 Cymbal Coffee products, 16 stores, and
  committed `gemini-embedding-2` fixtures" to "130 Cymbal Coffee products, 17
  stores, and committed `gemini-embedding-2-preview` fixtures".
- [ ] 2.2 `docs/index.md:31` — change `gemini-embedding-2` to
  `gemini-embedding-2-preview`.
- [ ] 2.3 `docs/tour.md:78` — change the model literal to
  `gemini-embedding-2-preview`.
- [ ] 2.4 `docs/tour.md:95-96` — rewrite "`ProductService` is a SQLSpec async
  service. Its `embed_text` method is the wrapper around Vertex AI's
  `gemini-embedding-2` call" so the embedding wrapper is named
  `VertexAIService.get_text_embedding` and the model literal is
  `gemini-embedding-2-preview`. Keep the cache-check-in-front detail.
- [ ] 2.5 `docs/tour.md:97-99` — leave the "does not use the old embedding
  `task_type` API parameter" sentence as-is (already accurate).
- [ ] 2.6 `docs/concepts/vector-search.md:19` — change the "Embedding model"
  table value to `gemini-embedding-2-preview`.
- [ ] 2.7 `docs/concepts/vector-search.md:70` — change "122 product vectors" to
  "130 product vectors".
- [ ] 2.8 `docs/reference/internals.md:98` — change "122 committed product
  vectors" to "130 committed product vectors".
- [ ] 2.9 `docs/reference/api.md:22` — change the base-class reference from
  "`SQLSpecAsyncService` subclasses" to "`OracleAsyncService` subclasses".
- [ ] 2.10 `docs/reference/quickstart.md:46-49` — fix the `512M` attribution so
  the 512M default is credited to the managed container default in
  `tools/oracle/database.py` (`DEFAULT_VECTOR_MEMORY_SIZE`), and clarify that
  `tools/oracle/configure_vector_memory.sql` is the manual fallback that targets
  `4G`; do not imply the `.sql` file produces the 512M value.
- [ ] 2.11 `docs/reference/quickstart.md:50` — change the `gemini-embedding-2
  404` gotcha label to `gemini-embedding-2-preview`.
- [ ] 2.12 `docs/reference/cli.md:12` — change "Generate `gemini-embedding-2`
  embeddings" to `gemini-embedding-2-preview`.

### Phase 3: .agents knowledge and context files

- [ ] 3.1 `.agents/patterns.md:29` — change `gemini-embedding-2` to
  `gemini-embedding-2-preview`.
- [ ] 3.2 `.agents/patterns.md:118` — change the `gemini-embedding-2` model
  literal to `gemini-embedding-2-preview`; keep line 119's "do not send the old
  `task_type` API parameter" prose unchanged.
- [ ] 3.3 `.agents/knowledge/project-guide.md:106` — change the
  `gemini-embedding-2` model literal to `gemini-embedding-2-preview`.
- [ ] 3.4 `.agents/knowledge/project-guide.md:16,28-29,53-80,170-173` — reframe
  the "active planning"/"planned component" framing for store, inventory, maps,
  and intent routes as shipped where the code confirms it (migration `0001`,
  `maps.py`, `_location.py`, `classifier.py`); keep optional Maps Embed and
  settings cleanup as forward-looking only if still unimplemented.
- [ ] 3.5 `.agents/knowledge/guides/architecture.md:197` — change
  `gemini-embedding-2` to `gemini-embedding-2-preview`.
- [ ] 3.6 `.agents/knowledge/guides/architecture.md:164-182` (`## Store,
  Inventory, And Maps Expansion`) — reframe "Active store-aware chat planning"
  / "planned components" as shipped components, matching the migration and
  services; keep only genuinely future items as future.
- [ ] 3.7 `.agents/knowledge/guides/oracle-vector-search.md:9` — change "Model:
  `gemini-embedding-2`" to `gemini-embedding-2-preview`. (Working tree has one
  occurrence on line 9; re-grep before editing in case the modified file shifts
  lines or contains additional occurrences.)
- [ ] 3.8 `.agents/knowledge/guides/adk-agent-patterns.md:182-185` — add
  `PRODUCT_AVAILABILITY` to the intent-label list so it matches the
  `classifier.py` `IntentLabel` enum (`PRODUCT_RAG`, `PRODUCT_AVAILABILITY`,
  `GENERAL_CONVERSATION`, `STORE_LOCATION`, `ORDER_STATUS`).
- [ ] 3.9 `.agents/knowledge/cymbal-coffee-reset_20260429.md:42` — change the
  `gemini-embedding-2` model literal to `gemini-embedding-2-preview` (tracked
  knowledge note; in scope for the model-literal sweep).
- [ ] 3.10 `.agents/tech-stack.md:8` — reword so "Litestar-granian" is described
  as the plugin/integration and the runtime ASGI server is named "Granian",
  removing the conflation.
- [ ] 3.11 `.agents/tech-stack.md:10` — change "Google ADK 2.2.0" to match the
  `pyproject.toml` pin `google-adk>=2.0.0` (e.g. "Google ADK 2 (>=2.0.0)").

### Phase 4: tools-tree tracked docs (counts and model sweep)

- [ ] 4.1 `tools/scripts/lab.md:5` — change `gemini-embedding-2` to
  `gemini-embedding-2-preview`; verify the ADK version wording (`Google ADK
  2.0`) is acceptable or align it with `>=2.0.0b1`.
- [ ] 4.2 `tools/scripts/lab.md:233` — change "122 coffee items, 16 premium
  store locations" to "130 coffee items, 17 premium store locations".
- [ ] 4.3 `src/app/db/migrations/README.md:102` — change "122 committed product
  vectors" to "130 committed product vectors". (File is already modified in the
  working tree; re-grep for the exact current line before editing.)

### Phase 5: ADK migration source-plan caveat flags (no content correction)

- [ ] 5.1 `.agents/specs/adk2-sqlspec-migration/source-plan.md` — add a short
  plan-execution caveat (near the snapshot/top or beside the affected rows)
  noting that its memory-embedding preset references —
  `gemini-embedding-002` / 1536-dim (`:558,:609,:717`) and
  `RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY` (`:719`) — conflict with the current
  shipped stack (`gemini-embedding-2-preview`, 3072-dim, instruction-prefix
  embedding purpose, no `task_type`). Do NOT rewrite the aspirational rows
  themselves.

### Product RAG guard addendum

The `fix/product-improve` branch changes Product RAG wording behavior. Docs
must not claim the model writes final customer-facing product copy safely. The
accurate contract is: Product RAG may use Gemini structured output to select
retrieved product ids, Python validates those ids, and Python renders names,
prices, and descriptions from Oracle rows. Grep active docs and guides for
phrases such as "Gemini for the answer", "formats the final answer", and
"deterministic Product RAG" to verify they do not imply either a fully model-
authored product answer or no model call at all.

### Phase 6: Verification grep sweep

- [ ] 6.1 Re-grep the whole tree (excluding gitignored `docs/_build`) to prove
  no stale `task_type` instruction, no non-preview `gemini-embedding-2` literal,
  and no `122`/`16 store` counts remain outside the ADK migration source plan's
  flagged aspirational rows.

## Acceptance

- [ ] No tracked file outside `.agents/specs/adk2-sqlspec-migration/source-plan.md`
  (and outside gitignored `docs/_build`) instructs the use of `task_type` for
  embeddings; the only surviving mentions describe NOT using it
  (`.agents/patterns.md`, `docs/tour.md`) or are flagged source-plan rows.
- [ ] No tracked Markdown contains a bare `gemini-embedding-2` model literal
  (i.e. `gemini-embedding-2` not immediately followed by `-preview`), except the
  source-plan `gemini-embedding-002` lines flagged as caveats.
- [ ] No tracked doc states `122` products or `16 stores`; all read `130`
  products / `17 stores`.
- [ ] `AGENTS.md` and `docs/reference/api.md` reference `OracleAsyncService` as
  the service base; no `SQLSpecAsyncService[OracleAsyncDriver]` base-class claim
  remains in those docs.
- [ ] `docs/tour.md` names `VertexAIService.get_text_embedding` and no longer
  references `ProductService.embed_text`.
- [ ] `.agents/knowledge/guides/adk-agent-patterns.md` intent list includes
  `PRODUCT_AVAILABILITY`.
- [ ] `.agents/tech-stack.md` matches `google-adk>=2.0.0` and distinguishes the
  `litestar-granian` plugin from the Granian server.
- [ ] Store/inventory/maps are described as shipped (not "planned") in
  `AGENTS.md`, `.agents/knowledge/project-guide.md`, and
  `.agents/knowledge/guides/architecture.md`.
- [ ] The ADK migration source-plan aspirational sections are unchanged except
  for the added caveat.
- [ ] `docs/_build/` is untouched.

## Verification

- `grep -rn "task_type" --include="*.md" . | grep -v docs/_build | grep -v .agents/specs/adk2-sqlspec-migration/source-plan.md`
  — only "do not / does not use" prose should remain.
- `grep -rnE "gemini-embedding-2([^-]|$)" --include="*.md" . | grep -v docs/_build | grep -v .agents/specs/adk2-sqlspec-migration/source-plan.md`
  — expect zero hits.
- `grep -rnE "\b122\b|16 stores?\b" --include="*.md" . | grep -v docs/_build`
  — expect zero product/store-count hits.
- `grep -rn "SQLSpecAsyncService\[OracleAsyncDriver\]" AGENTS.md docs/reference/api.md`
  — expect zero hits.
- `grep -rn "embed_text" docs/` — expect zero hits.
- `grep -n "PRODUCT_AVAILABILITY" .agents/knowledge/guides/adk-agent-patterns.md`
  — expect at least one hit.
- `grep -n "2.2.0\|google-adk" .agents/tech-stack.md` — version matches `>=2.0.0b1`.
- `git diff --stat` — confirm `CLAUDE.md` shows no separate diff (symlink to
  `AGENTS.md`) and no file under `docs/_build/` is modified.
- `make lint` — docs/markdown lint gate passes.
