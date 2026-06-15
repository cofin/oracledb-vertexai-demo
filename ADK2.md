# ADK 2.2 / SQLSpec 0.50 Migration Plan

This document captures every code change required to align the
`oracledb-vertexai-demo` with the **SQLSpec ADK clean-break schema** and
Google ADK 2.2. The plan assumes a destructive cutover. SQLSpec 0.50
ships a first-party cutover migration (`0002_reset_adk_tables.py`) that
drops the legacy/configured ADK tables and creates the current schema;
the demo runs it via the existing `make migrate` target. No demo-side
migration scripts are required.

> **Plan-execution caveat (not a correction).** The memory-embedding preset
> rows below are forward-looking and do not match the current shipped stack.
> They reference `gemini-embedding-002` at 1536-dim (the `1536-dim` helper, the
> `ADK_EMBEDDING_PRESET = "gemini-embedding-002"` setting, and the
> `embedding_preset: gemini-embedding-002` wiring step) and a
> `RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY` memory-embedding helper. The running
> demo uses `gemini-embedding-2-preview` at 3072 dimensions and selects
> query-vs-document intent through an instruction-prefix `embedding_purpose`,
> sending no `task_type` parameter. Anyone executing this plan should reconcile
> the memory-embedding preset and dimensionality with the shipped embedding
> contract before wiring it. The aspirational rows are left intact below.

## Snapshot — what's already correct

| Aspect | Status |
| --- | --- |
| Direct use of deprecated `event_json` column | Not present |
| Custom `BaseAsyncADKStore` subclass | Not present (uses stock `OracleAsyncADKStore`) |
| `owner_id_column` integration | Not present (no change required) |
| Direct calls to `upsert_app_state` / `upsert_user_state` | Not present |
| Session identity bridge (`src/app/domain/chat/session.py`) | Compatible — no change |
| Litestar `_chat.py` controllers / routes | Compatible — no change |
| Workflow + classifier (`workflow.py`, `classifier.py`) | Compatible — no change |
| `_adk_telemetry.py`, `_adk_grounding.py`, `_adk_history.py` | Compatible — no change |

The demo is in good shape. The bulk of the work is **dependency bumps**,
**one config decision** (memory store), and **one atomic-write
refactor** in `ADKRunner`.

---

## 1. Dependency bumps

**File:** `pyproject.toml`

```diff
  "sqlspec[adk,mypyc,oracledb,performance]==0.50.0",
- "google-adk>=2.0.0b1",
+ "google-adk>=2.2.0",
```

Run `uv lock --upgrade-package sqlspec --upgrade-package google-adk` after the
edit.

> Why: SQLSpec 0.50 introduces the atomic `append_event_and_update_state`
> kwargs (now `(event_record, app_name, user_id, session_id, state, *,
> app_state=None, user_state=None)`), the `event_json` → `event_data`
> column rename, the scoped-state tables
> (`adk_app_state`, `adk_user_state`, `adk_internal_metadata`), and the
> `0001` no-op + `0002_reset_adk_tables.py` cutover migration that lands
> the new schema via `make migrate`. Google ADK 2.2 adds the current
> service surface SQLSpec implements, including `BaseSessionService.get_user_state`.

---

## 2. Memory store: wire it for "agent remembers past orders"

**Decision made: enable the memory store and use it.** This turns the demo
into a more compelling agent showcase — after a customer places an order
the agent can recall that order on a later visit ("I'll get your usual
oat milk latte?").

SQLSpec 0.50 memory configuration is table/search oriented. There is no
`EMBEDDING_PRESETS`, `EmbeddingPreset`, `register_embedding_preset`, or
`resolve_embedding_config` API in this branch. Treat embeddings as
demo-owned metadata only if you choose to add a future vector recall
path; the Oracle memory store searches `content_text` with Oracle Text
(`CONTAINS`) when `memory_use_fts=True`, otherwise it falls back to a
case-insensitive lexical match.

### 2a. Wire the memory settings

```diff
# src/app/lib/settings.py — Database / ADK defaults
  ADK_ENABLE_MEMORY: bool = True
  ADK_IN_MEMORY: bool = True
+ ADK_MEMORY_USE_FTS: bool = True
+ ADK_MEMORY_MAX_RESULTS: int = 20
+ ADK_MEMORY_RETENTION_DAYS: int = 365                  # 1-year window
```

```python
# extension_config["adk"] block in config.py / settings.py
"adk": {
    "enable_memory": True,
    "include_memory_migration": True,
    "in_memory": True,            # Oracle-specific SQLSpec INMEMORY DDL option
    "memory_use_fts": True,       # Oracle Text search over content_text
    "memory_max_results": 20,
}
```

Remove the old table-name overrides unless you intentionally want custom
names. With no overrides, SQLSpec creates the clean-break defaults:
`adk_session`, `adk_event`, `adk_app_state`, `adk_user_state`,
`adk_internal_metadata`, and `adk_memory`.

If you keep the demo's current overrides (`adk_sessions`, `adk_events`,
`adk_memory_entries`), the reset migration will drop legacy/default
tables and then recreate those configured plural names. That is valid,
but it is a customization rather than the clean-break default.

### 2b. Wire DI for the memory store

**File:** `src/app/ioc.py`

```diff
- from sqlspec.adapters.oracledb.adk.store import OracleAsyncADKStore
+ from sqlspec.adapters.oracledb.adk import OracleAsyncADKMemoryStore, OracleAsyncADKStore

  class IntegrationsProvider(Provider):
      @provide(scope=Scope.APP)
      def provide_adk_store(self, config: OracleAsyncConfig) -> OracleAsyncADKStore:
          return OracleAsyncADKStore(config=config)

+     @provide(scope=Scope.APP)
+     def provide_adk_memory_store(self, config: OracleAsyncConfig) -> OracleAsyncADKMemoryStore:
+         return OracleAsyncADKMemoryStore(config=config)
+
      @provide(scope=Scope.APP)
      def provide_session_service(self, store: OracleAsyncADKStore) -> SQLSpecSessionService:
          return SQLSpecSessionService(store)
```

The memory store is the recall surface: it owns insert / search / delete
APIs over `adk_memory` by default. The session store and memory store
share the same Oracle config (and pool) so there's no extra connection
cost.

### 2c. Write a memory entry when an order completes

In `AgentToolsService` (or wherever order completion lives — the demo
currently doesn't persist orders, but you have intent routes for
PRODUCT_RAG / store_location / etc.), add a helper that writes to memory
after a successful interaction:

```python
# src/app/domain/chat/services/adk.py — inside AgentToolsService

from datetime import datetime, timezone
from uuid import uuid4

from sqlspec.adapters.oracledb.adk import OracleAsyncADKMemoryStore
from sqlspec.extensions.adk import MemoryRecord


async def remember_order(
    self,
    *,
    memory_store: OracleAsyncADKMemoryStore,
    app_name: str,
    user_id: str,
    session_id: str,
    event_id: str,
    summary: str,                       # e.g. "Ordered oat milk latte, 12oz, no sugar"
    metadata: "dict[str, object] | None" = None,
) -> None:
    """Persist a one-line natural-language memory of what just happened."""
    now = datetime.now(timezone.utc)
    record: MemoryRecord = {
        "id": str(uuid4()),
        "session_id": session_id,
        "app_name": app_name,
        "user_id": user_id,
        "event_id": event_id,
        "author": "system",
        "timestamp": now,
        "content_json": {"parts": [{"text": summary}]},
        "content_text": summary,
        "metadata_json": metadata or {},
        "inserted_at": now,
    }
    await memory_store.insert_memory_entries([record])
```

Call sites: after the deterministic order-placement event in
`stream_request`, or after a PRODUCT_RAG turn that resolves a purchase
intent. Wire the new `memory_store` dependency via the existing Dishka
container.

### 2d. Recall past orders at the start of a turn

Add a tool on `AgentToolsService` so the LLM can call it (or invoke it
unconditionally on every turn for short context windows):

```python
# src/app/domain/chat/services/adk.py — inside AgentToolsService

async def recall_recent_history(
    self,
    *,
    memory_store: OracleAsyncADKMemoryStore,
    app_name: str,
    user_id: str,
    query: str,
    limit: int = 5,
) -> "list[str]":
    """Return short natural-language strings of the user's recent relevant history."""
    results = await memory_store.search_entries(query=query, app_name=app_name, user_id=user_id, limit=limit)
    return [entry["content_text"] for entry in results if entry.get("content_text")]
```

Then in the workflow / runner, before composing the prompt:

```python
recall = await tools.recall_recent_history(
    memory_store=memory_store,
    app_name=_APP_NAME,
    user_id=user_id,
    query=user_message,
    limit=5,
)
if recall:
    prompt_context += "\n\nThings I remember about this customer:\n" + "\n".join(f"- {r}" for r in recall)
```

The Oracle memory store uses Oracle Text full-text indexes on
`content_text` for retrieval. Anything in `content_json["embedding"]`
is stored but not yet queried for search (vector path is pending in a
future sqlspec release). For the "the usual?" demo, lexical recall on
`content_text` is enough.

### 2e. Retention housekeeping (optional but recommended for a demo)

To keep memory bounded so the demo doesn't grow unbounded over a public
deployment, schedule a periodic cleanup. The store exposes
`delete_entries_older_than(days: int)`:

```python
# src/app/cli/commands.py
@click.command("adk-memory-prune")
@click.option("--days", type=int, default=365)
def adk_memory_prune(days: int) -> None:
    """Delete ADK memory entries older than --days."""
    import anyio
    from sqlspec.adapters.oracledb.adk import OracleAsyncADKMemoryStore
    from app.config import db

    async def _run() -> None:
        store = OracleAsyncADKMemoryStore(config=db)
        removed = await store.delete_entries_older_than(days)
        click.echo(f"Removed {removed} memory entries older than {days} days.")

    anyio.run(_run)
```

---

## 3. Atomic state updates in `ADKRunner`

**File:** `src/app/domain/chat/services/adk.py`
**Function:** `_append_display_history` (~lines 523–552)

Today this helper reaches through the service to call
`store.update_session_state` directly:

```python
update_state = getattr(getattr(self._session_service, "store", None), "update_session_state", None)
if callable(update_state):
    result = update_state(session_id, state)
    if isawaitable(result):
        await result
```

SQLSpec 0.50 keeps `update_session_state` working, but the current
signature is `(app_name, user_id, session_id, state)`. The demo's
two-argument shim is therefore broken after the upgrade. The preferred
ADK 2.x pattern is to fold the durable state mutation into the event
that caused it. That lets `SQLSpecSessionService.append_event` call
`append_event_and_update_state(...)` so the event insert, session
UPDATE, and optional `app_state` / `user_state` UPSERTs share one store
operation.

There are two scenarios to fix:

### 3a. Where an event already triggered the update — fold state_delta into the event

If `_append_display_history` is called immediately after the assistant
produces an event (it is — see `stream_request` and `process_request`,
~lines 864–1041), refactor so the persisted event carries the
`display_history` and `intent` updates in `event.actions.state_delta`:

```python
# adk.py — replace _append_display_history-then-append_event sequence with:
from google.adk.events.event_actions import EventActions

event = Event(
    invocation_id=invocation_id,
    author="model",
    content=response_content,
    actions=EventActions(state_delta={
        "display_history": history_messages,   # full list, not the diff
        "intent": effective_intent,
    }),
)
await self._session_service.append_event(session, event)
```

Why: `SQLSpecSessionService.append_event` calls
`store.append_event_and_update_state(...)` under the hood, which now
takes the state snapshot plus optional `app_state` / `user_state` kwargs
and persists everything in one transaction. No more silent-divergence
window between the event row and the session-state row.

### 3b. Where there is no triggering event — keep `update_session_state`, drop the `getattr` shim AND fix the signature

Per the SQLSpec 0.50 service contract, `SQLSpecSessionService.store` is a
real attribute (not optional) and every retained adapter implements
`update_session_state`. **But the signature changed** — it now
takes `(app_name, user_id, session_id, state)` (four args), not the
older `(session_id, state)`. The demo's current shim passes only two
args and **will break on upgrade**. The `getattr` chain collapses and
the call must be widened:

```diff
- update_state = getattr(getattr(self._session_service, "store", None), "update_session_state", None)
- if callable(update_state):
-     result = update_state(session_id, state)
-     if isawaitable(result):
-         await result
+ await self._session_service.store.update_session_state(
+     _APP_NAME, user_id, session_id, state,
+ )
```

`_append_display_history` already has `user_id` and `session_id` in
scope, and `_APP_NAME` is a module-level constant in `adk.py`.

Pick whichever shape applies at each call site — most uses in this demo
follow path 3a (an event is being produced anyway, and 3a sidesteps the
signature change entirely). The exception is the intent-classification
merge in `workflow.py:75-79` (writes `ctx.state["intent"]`), which the
ADK workflow handles internally and does not need to change.

> **Recommendation:** adopt path 3a everywhere `_append_display_history`
> is invoked. It eliminates the only signature drift you'd otherwise
> have to manage, and it gets you the atomic event-plus-state write in
> a single transaction for free.

---

## 4. Drop the deprecated-pattern grep guards locally

SQLspec 2.0 ships
`tests/unit/extensions/test_adk/test_clean_break_guards.py` that fails
CI if `event_json`, `backwards_compat`, `legacy_`, or `# DEPRECATED`
markers reappear in the SQLspec source tree. **Nothing in the demo
violates these**, but if you copy SQLspec test patterns into the demo
later, mirror the guards in `src/tests/unit/` to keep your own ADK
extensions clean.

This step is optional — only add the guards if you grow your own
ADK helpers in `src/app/domain/chat/services/`.

---

## 5. Database lifecycle — run `make migrate`

**SQLspec ships a first-party cutover migration.** No new CLI is
required. The ADK extension's migration directory now contains two
files:

- `0001_create_adk_tables.py` — reduced to a no-op (`up()` and `down()`
  both return `[]`). Installs that already applied it keep their
  tracking-table row.
- `0002_reset_adk_tables.py` — unconditionally drops legacy ADK tables
  (`adk_sessions`, `adk_events`, plus the memory table if any adapter
  ships one), then creates the new 2.0 schema (`adk_session`,
  `adk_event`, `adk_app_state`, `adk_user_state`, `adk_internal_metadata`,
  and the memory table when `enable_memory=True`) and seeds
  `schema_version=1`. Memory drop is unconditional so users moving from
  `enable_memory=True` to `enable_memory=False` get cleanup; memory
  create is gated on the current config.

To run the cutover:

```bash
make migrate          # already wired to `uv run python manage.py database upgrade --no-prompt`
```

That's it. The migrations runner picks up `0002`, executes it inside a
transaction (atomic on Oracle), and the database is on the 2.0 schema.

**Existing data:** the migration **drops** the legacy `sessions` /
`events` rows. The 2.0 events-table delta (new `id` PK, removed
`author`, renamed `event_json` → `event_data`) cannot be ALTER-ed
non-destructively, and the demo confirmed migrations are not a concern.
If you ever need to keep historical data, export at the application
level before running the migration.

**Programmatic alternative (test fixtures, ad-hoc resets):** the
`store.recreate_tables()` lifecycle helper on `BaseAsyncADKStore` is
retained and useful — but only operates on the **session-store tables**
(`adk_session`, `adk_event`, `adk_app_state`, `adk_user_state`,
`adk_internal_metadata`). The memory store has only `create_tables()` /
`ensure_tables()` and **no public `drop_tables()` or
`recreate_tables()`**, so programmatic memory resets either go through
the migration or call the private `_get_drop_memory_table_sql()`. Prefer
the migration.

---

## 6. Scoped state — nothing to do today, but be aware

The demo's session state is a plain dict containing `display_history`
and `intent`. Neither key uses the new `app:` / `user:` / `temp:`
prefixes, so the service-level routing in 2.0 is a no-op for this
codebase.

If you later add cross-session preferences (e.g. "user prefers oat
milk"), use the `user:` prefix:

```python
EventActions(state_delta={
    "user:preferred_milk": "oat",       # persisted in adk_user_states
    "app:active_promotion": "fall24",   # persisted in adk_app_states
    "temp:transient_token": "...",      # stripped before persistence
    "display_history": [...],           # persisted in adk_sessions.state
})
```

The 2.0 service strips `temp:*` keys before write and merges
`app:*` / `user:*` keys on read, so `session.state` looks identical to
callers regardless of the underlying split.

---

## 7. Tests to update

### 7a. `test_adk.py` — runner unit tests

If you adopt the **option 3a** refactor (fold state into events), the
mocked `session_service` in `src/tests/unit/app/domain/chat/services/test_adk.py`
needs to assert against `append_event` calls carrying the expected
`state_delta`, instead of asserting on `store.update_session_state`
calls.

Search for `update_session_state` in the test file and replace
expectations:

```python
# BEFORE
mock_store.update_session_state.assert_awaited_once_with(session_id, expected_state)

# AFTER
service.append_event.assert_awaited_once()
event = service.append_event.await_args.args[1]
assert event.actions.state_delta["display_history"] == expected_history
assert event.actions.state_delta["intent"] == expected_intent
```

If you keep `update_session_state` (path 3b), only drop the `getattr`
shim assertions if any exist.

### 7b. `test_chat_workflow.py` — integration

The integration fixtures can keep relying on the auto-applied
migrations runner — `0002_reset_adk_tables.py` handles the schema swap
the first time the suite runs against an old database. No fixture
change is strictly required.

If you want belt-and-braces freshness per session (recommended for
parallel-friendly suites), call the programmatic helper instead of
running the migration twice:

```python
# tests/integration/conftest.py
@pytest.fixture(scope="session")
async def adk_store(oracle_async_config):
    store = OracleAsyncADKStore(config=oracle_async_config)
    await store.recreate_tables()   # session-store tables only
    yield store
```

This only touches the five session-store tables. If the memory store is
also enabled in the suite, drive that one through the migration runner
or call `await memory_store.create_tables()` (idempotent) — there is no
public `recreate_tables()` on the memory store.

### 7c. New: memory recall integration test (recommended)

Add a focused integration test that proves the round-trip end-to-end:
write a memory entry as user `alice` in session A, start session B (same
user, fresh session), call `recall_recent_history`, and assert the entry
comes back. This is the test that catches embedding-dimension
mismatches, FTS index misconfiguration, and `app_name` / `user_id`
scoping bugs all at once.

```python
# src/tests/integration/app/domain/chat/services/test_chat_memory.py  (NEW)
import pytest
from sqlspec.adapters.oracledb.adk import OracleAsyncADKMemoryStore

from app.domain.chat.services.adk import AgentToolsService
from app.domain.chat.services._adk_memory_embedding import embed_memory_text

pytestmark = [pytest.mark.integration, pytest.mark.oracledb]


async def test_memory_round_trip_across_sessions(
    oracle_async_config, fake_genai_client, tools_service: AgentToolsService
) -> None:
    """A memory written in session A is recallable in session B for the same user."""
    memory_store = OracleAsyncADKMemoryStore(config=oracle_async_config)
    await memory_store.create_tables()   # idempotent CREATE IF NOT EXISTS

    # Session A: place an order
    await tools_service.remember_order(
        memory_store=memory_store,
        genai_client=fake_genai_client,
        app_name="cymbal-coffee",
        user_id="web:alice",
        session_id="session-A",
        event_id="evt-1",
        summary="Ordered oat milk latte, 12oz, no sugar",
        metadata={"source": "test"},
    )

    # Session B: fresh session, same user
    recall = await tools_service.recall_recent_history(
        memory_store=memory_store,
        app_name="cymbal-coffee",
        user_id="web:alice",
        query="latte",
        limit=5,
    )

    assert any("oat milk latte" in line for line in recall)


async def test_memory_is_scoped_per_user(
    oracle_async_config, fake_genai_client, tools_service: AgentToolsService
) -> None:
    """A memory written for alice is invisible to bob."""
    memory_store = OracleAsyncADKMemoryStore(config=oracle_async_config)
    await memory_store.create_tables()

    await tools_service.remember_order(
        memory_store=memory_store,
        genai_client=fake_genai_client,
        app_name="cymbal-coffee",
        user_id="web:alice",
        session_id="session-A",
        event_id="evt-1",
        summary="Ordered double shot espresso",
    )

    bob_recall = await tools_service.recall_recent_history(
        memory_store=memory_store,
        app_name="cymbal-coffee",
        user_id="web:bob",
        query="espresso",
        limit=5,
    )

    assert bob_recall == []
```

`fake_genai_client` is the existing stub from `test_chat_workflow.py` —
return a deterministic 1536-dim vector for any text. Reuse it.

### 7d. New: contract parity (optional)

SQLspec 2.0 ships shared contract helpers in
`tests/integration/adapters/_adk_contract_helpers.py` (in the SQLspec
repo). The demo doesn't need to copy them, but if you want belt-and-
braces coverage for the Oracle store you can add one test that wires
in:

```python
from sqlspec.adapters.oracledb.adk import OracleAsyncADKStore

async def test_oracle_adk_atomic_scoped_state(oracle_async_config) -> None:
    store = OracleAsyncADKStore(config=oracle_async_config)
    await store.recreate_tables()

    session = await store.create_session("test-session", "demo", "alice", {})
    event_record = {
        "session_id": "test-session",
        "invocation_id": "inv-1",
        "author": "user",
        "timestamp": datetime.now(timezone.utc),
        "event_data": {"id": "event-1", "actions": {"state_delta": {"turn": 1}}},
    }
    updated = await store.append_event_and_update_state(
        event_record=event_record,
        app_name="demo",
        user_id="alice",
        session_id="test-session",
        state={"turn": 1},
        app_state={"app:active_promo": "fall24"},
        user_state={"user:milk_pref": "oat"},
    )
    assert updated["state"] == {"turn": 1}
    assert await store.get_app_state("demo") == {"app:active_promo": "fall24"}
    assert await store.get_user_state("demo", "alice") == {"user:milk_pref": "oat"}
```

---

## 8. Settings module — final shape

After the bumps + memory wiring, the relevant slice of
`src/app/lib/settings.py` should look like:

```python
# DatabaseSettings — extension_config slice
class DatabaseSettings(BaseSettings):
    ADK_ENABLE_MEMORY: bool = True
    ADK_IN_MEMORY: bool = True
    ADK_EMBEDDING_PRESET: str = "gemini-embedding-002"  # 1536-dim for ADK memory
    ADK_MEMORY_RETENTION_DAYS: int = 365

    def create_config(self) -> OracleAsyncConfig:
        adk_config: dict[str, Any] = {
            "session_table": "adk_sessions",
            "events_table": "adk_events",
            "app_state_table": "adk_app_states",        # default is singular "adk_app_state"
            "user_state_table": "adk_user_states",      # default is singular "adk_user_state"
            "metadata_table": "adk_internal_metadata",
            "memory_table": "adk_memory_entries",
            "enable_memory": self.ADK_ENABLE_MEMORY,
            "include_memory_migration": self.ADK_ENABLE_MEMORY,
            "in_memory": self.ADK_IN_MEMORY,            # demo-internal; sqlspec ignores it
            "memory": {
                "embedding_preset": self.ADK_EMBEDDING_PRESET,
            },
        }
        return OracleAsyncConfig(
            pool_config=...,
            extension_config={
                "adk": adk_config,
                "litestar": {...},
            },
        )
```

---

## 9. Verification checklist

Run these in order after applying the changes:

1. `uv lock --upgrade-package sqlspec --upgrade-package google-adk`
2. `uv sync`
3. `make migrate` — runs `0001` (no-op) then `0002_reset_adk_tables.py`, which drops legacy ADK tables and creates the 2.0 schema in one transaction
4. `uv run pytest src/tests/unit/app/domain/chat/services/test_adk.py -x`
5. `uv run pytest src/tests/integration/app/domain/chat/services/test_chat_workflow.py -x`
6. `make lint` (or your equivalent — ruff / mypy / pyright)
7. **Memory smoke test**: start the app as user `alice`, send
   `POST /api/chat` "I'll have an oat milk latte" — confirm the
   `remember_order` helper inserted a row into `ADK_MEMORY_ENTRIES`:
   ```sql
   SELECT user_id, content_text, inserted_at
     FROM adk_memory_entries
    WHERE user_id = 'web:<session_uuid>'
    ORDER BY inserted_at DESC FETCH FIRST 5 ROWS ONLY;
   ```
   Then start a **new** browser session as the same user, send a
   conversational prompt ("the usual?") and confirm `recall_recent_history`
   surfaces the latte memory in the prompt context.
8. Standard session test: send a `POST /api/chat` request, then a
   follow-up to the same session and confirm `display_history` carries
   forward.

Optional but recommended:

9. Confirm via SQL that the schema looks right:
   ```sql
   SELECT table_name FROM user_tables WHERE table_name LIKE 'ADK_%';
   -- Expect: ADK_SESSIONS, ADK_EVENTS, ADK_APP_STATES, ADK_USER_STATES,
   --         ADK_INTERNAL_METADATA, ADK_MEMORY_ENTRIES
   ```

10. Confirm Oracle Text index on memory content:
    ```sql
    SELECT index_name, index_type FROM user_indexes
     WHERE table_name = 'ADK_MEMORY_ENTRIES';
    -- Expect a CTXSYS.CONTEXT (Oracle Text) index on content_text.
    ```

---

## 10. Out-of-scope (intentionally deferred)

The SQLspec 2.0 release ships a catalog of latency-oriented variations
(V1 NULL-encoded empty state, V2 skip-no-op session UPDATE, V3
generated columns, V4 event partitioning, V5 covering indexes, V8
AlloyDB columnar autopromote) gated behind
`ADKOptimizationConfig`. None are wired up in this demo yet — they
require per-driver capability detection that is still in flight (tracked
in `sqlspec-badb`). When that work lands, the demo can opt in with:

```python
"adk": {
    ...,
    "optimizations": {
        "null_encoded_empty_state": True,
        "skip_noop_session_update": True,
    },
}
```

Until then, the demo runs on the default 2.0 schema and gets the
correctness wins (atomic scoped-state writes, clean-break event_data
column, single-table-per-scope routing) without the latency
variations.

---

## TL;DR

The demo upgrade is **one destructive cutover** plus a **new agent
capability** (long-term memory of customer interactions):

| Step | File | Effort |
| --- | --- | --- |
| 1. Bump SQLspec + google-adk versions | `pyproject.toml` | trivial |
| 2. Wire `embedding_preset: gemini-embedding-002` | `src/app/lib/settings.py` | small |
| 3. Provide `OracleAsyncADKMemoryStore` in DI | `src/app/ioc.py` | small |
| 4. Add memory embedding helper (RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY) | `_adk_memory_embedding.py` (new) | small |
| 5. Add `remember_order` + `recall_recent_history` tools on `AgentToolsService` | `src/app/domain/chat/services/adk.py` | medium |
| 6. Fold `update_session_state` into `append_event` | `src/app/domain/chat/services/adk.py` | one helper |
| 7. Add `adk-memory-prune` CLI command (optional retention helper) | `src/app/cli/commands.py` | small |
| 8. Run `make migrate` — `0002_reset_adk_tables.py` handles drop + create automatically | (runtime) | one command |
| 9. Update mocks in `test_adk.py` to assert on `append_event` | `src/tests/unit/.../test_adk.py` | medium |
| 10. Add a memory recall integration test | `src/tests/integration/.../test_chat_memory.py` (new) | medium |

Total estimated change: **~250 lines of code touched + ~80 lines of new
memory helpers and tests**, no demo-side migration script (sqlspec ships
the cutover via `0002_reset_adk_tables.py`), no controller / route
changes.

The user-visible win is the demo can now answer "the usual?" — a
believable Vertex-AI-on-Oracle showcase that previously was just chat
without persistence beyond a single session.
