# Migrating to the SQLSpec ADK 2.0 Store

This app currently pins `sqlspec[adk,mypyc,oracledb,performance]==0.50.0` and
`google-adk>=2.0.0` (running 2.3.0). SQLSpec's next release rebuilds the ADK
session store around the ADK 2.x contract. This guide covers what changes for
this app and what to do.

## TL;DR

- **The `google-adk` bump is a non-event.** The session and memory base-service
  contracts are byte-identical between 2.2.0 (what SQLSpec tests against) and
  2.3.0 (what this app runs); the artifact base differs only by an unused
  import. This app already uses the ADK 2.x agent API (`Runner(node=...)`,
  `Workflow`). No code change is required for the ADK version itself.
- **One hard breaking change** comes from the new SQLSpec store: the store-level
  `update_session_state(...)` signature changed. This app reaches through to it
  in `_append_display_history` and must be updated.
- Two small cleanups: drop a now-stale warning filter, and bump the `sqlspec`
  pin.

## 1. The breaking change: `update_session_state`

`src/app/domain/chat/services/adk.py` persists chat display history by reaching
*past* `SQLSpecSessionService` into its private `.store`:

```python
# adk.py:592 — current (sqlspec 0.50.0)
result = self._session_service.store.update_session_state(session_id, state)
if isawaitable(result):
    await result
```

The new store keys every session operation by `(app_name, user_id, session_id)`,
so the method signature became:

```python
# sqlspec 0.50.0
update_session_state(session_id, state)
# new store
update_session_state(app_name, user_id, session_id, state)
```

The current 2-arg call will raise `TypeError` at runtime on the new store.

## 2. The fix: write state through `append_event`

Rather than re-add the two arguments and keep reaching into the private `.store`,
route durable state through ADK's official `append_event` API. `append_event` is
part of `BaseSessionService` and its `(session, event)` signature is stable
across ADK versions and SQLSpec releases — it merges an event's
`actions.state_delta` into session state and persists it via the store with the
correct keying. This removes the fragile `.store` reach-through entirely.

```python
from google.adk.events import Event, EventActions  # add to imports

async def _append_display_history(
    self,
    *,
    user_id: str,
    session_id: str,
    query: str,
    answer: str,
    intent_detected: str | None = None,
    last_products: list[str] | None = None,
) -> None:
    app_name = get_settings().chat.session_app_name
    session = await self._session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    if not session:
        return

    existing = _coerce_history_messages(
        (getattr(session, "state", None) or {}).get(_DISPLAY_HISTORY_STATE_KEY)
    )
    history = [
        *[{"source": m.source, "message": m.message} for m in existing],
        {"source": "human", "message": query},
        {"source": "ai", "message": answer},
    ][-get_settings().chat.display_history_limit :]

    state_delta: dict[str, Any] = {_DISPLAY_HISTORY_STATE_KEY: history}
    if intent_detected:
        state_delta["intent"] = intent_detected
    if last_products is not None:
        state_delta["last_products"] = last_products

    await self._session_service.append_event(
        session,
        Event(
            author="system",
            invocation_id=f"display-{uuid.uuid4().hex}",
            actions=EventActions(state_delta=state_delta),
        ),
    )
```

Notes:

- The state keys (`display_history`, `intent`, `last_products`) are unprefixed,
  so ADK treats them as session-scoped durable state — exactly the previous
  behavior. (`app:`/`user:` would route to the new scoped-state tables;
  `temp:` would be dropped before persistence.)
- The `isawaitable` hedge is no longer needed — `SQLSpecSessionService.append_event`
  is always a coroutine.
- **Behavior change to be aware of:** this writes one lightweight state-delta
  event row per turn (in addition to the runner's own events). That is the
  idiomatic ADK approach. If you specifically want to avoid the extra event row,
  the minimal alternative is to keep the reach-through and just pass the four
  arguments: `await self._session_service.store.update_session_state(app_name, user_id, session_id, state)`.
  The `append_event` path is recommended because it does not depend on a private
  attribute and survives future store-contract changes.
- Update the unit test that asserts the old call. `src/tests/unit/app/domain/chat/services/test_adk.py`
  currently asserts `store.update_session_state(session_id, state)` is invoked
  with truncated `display_history`; after this change it should assert
  `append_event` is called with the expected `state_delta`.

## 3. Drop the stale `throw()` warning filter

`pyproject.toml` filters a SQLSpec deprecation warning:

```toml
# sqlspec's ADK store uses the 3-arg generator throw() (deprecated in Python 3.12).
"ignore:.*the \\(type, exc, tb\\) signature of throw\\(\\).*:DeprecationWarning:sqlspec.*",
```

Current SQLSpec source contains **no** 3-arg `throw()` usage (verified: zero
occurrences in the package). Remove this filter once on the new release and
confirm the test suite stays warning-clean. Keep the `google-adk` /
`BaseAgentConfig` filters — those are ADK noise, not SQLSpec.

## 4. Bump the pin

```toml
# pyproject.toml
"sqlspec[adk,mypyc,oracledb,performance]>=0.51.0",  # the release carrying the ADK 2.0 store
```

`google-adk>=2.0.0` already resolves to 2.3.0 and needs no change.

## 5. Migrations are a destructive clean break

The new release ships migration `0001_create_adk_tables` as a no-op and a new
`0002_reset_adk_tables` that **drops** legacy ADK tables (across all historical
name profiles, e.g. `adk_sessions`/`adk_events`) and recreates the new schema:
singular `adk_session`/`adk_event` plus new scoped-state tables
(`adk_app_state`, `adk_user_state`, `adk_internal_metadata`).

- Running migrations **drops existing ADK session data.** Acceptable for this
  demo's ephemeral chat sessions; export first in any non-demo deployment.
- Review the `extension_config["adk"]` table-name overrides in
  `src/app/lib/settings.py` against the new defaults. The scoped-state tables
  are created automatically regardless of the session/event table names.

## What does *not* change

- **DI wiring (`src/app/ioc.py`)** — the `OracleAsyncADKStore(config=...)` and
  `SQLSpecSessionService(store)` constructors are unchanged, so the Dishka
  providers work without edits.
- **Session service API** — `get_session` / `create_session` / `delete_session`
  keep their keyword-only `(app_name=, user_id=, session_id=)` signatures, so the
  8 call sites in `adk.py` are unaffected.
- **`Runner` / `Workflow` / `LlmAgent`** — pure ADK surface, already on 2.x.

## Verification checklist

- [ ] `_append_display_history` no longer calls the 2-arg `store.update_session_state`
- [ ] `test_adk.py` updated to assert the `append_event` state-delta path
- [ ] stale `throw()` warning filter removed; `uv run pytest` is warning-clean
- [ ] migrations run clean against Oracle; ADK tables recreated
- [ ] chat round-trip: history persists across turns and `session.state["intent"]`
      round-trips (see `src/tests/integration/.../test_chat_workflow.py`)
