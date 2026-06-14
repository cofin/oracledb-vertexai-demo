# Flow: maps-consolidation

*Beads: oracledb-vertexai-mzm.7*

## Specification

Make `src/app/domain/products/services/maps.py` the single no-key Google Maps
URL builder for the app, and wire it into chat grounding so each store/inventory
row emits BOTH a `search` and a `directions` map action. Delete the duplicate
inline URL builder that currently lives in `_adk_grounding.py`. Render the new
`directions` action in the chat UI alongside the existing "Open in Google Maps"
search link.

### Requirements

- One Maps URL builder module: `products/services/maps.py`. Grounding must hold
  no inline URL-building code after this flow.
- `_build_map_actions` returns, per store row, two actions: one `search` action
  (label "Open in Google Maps") and one `directions` action (label "Get
  directions"). Both URLs are no-key `https://www.google.com/maps/...` URLs.
- Preserve the existing action shape `{type, label, url}` and the existing
  `type: "search"` value so the frontend search-link path keeps working; add
  `type: "directions"`.
- Preserve coordinate privacy: directions URLs are built WITHOUT a browser
  `origin`. Browser coordinates must not be embedded in any persisted action,
  history entry, cache value, metric, or log. (Grounding has no per-request
  browser coordinates at `_build_map_actions` time — it only has store rows — so
  directions are destination-only.)
- Frontend renders the `directions` action through the same `safeMapsUrl`
  validation already used for `search` (host must stay `www.google.com`,
  path must start `/maps/`).
- Depends on Ch6 (`oracledb-vertexai-mzm.6`, adk-readability) landing first.

### Code Analysis Summary

- `src/app/domain/products/services/maps.py` — orphaned, more-capable builder.
  - `build_store_search_url(store: Store) -> str` (`:15`) → `/maps/search/` with
    `query` + optional `query_place_id`.
  - `build_store_directions_url(store: Store, origin=None) -> str` (`:23`) →
    `/maps/dir/` with `destination` + optional `destination_place_id` + optional
    `origin`.
  - `_store_query(store: Store)` (`:35`), `_maps_url(path, params)` (`:41`).
  - Only caller today is `src/tests/unit/app/domain/products/services/test_maps.py`.
    No production code imports it.
- `src/app/domain/chat/services/_adk_grounding.py` — duplicate inline builder.
  - `_store_query_parts(row: dict)` (`:174`) → `(name, query)` from raw dict keys
    `name`/`address`/`city`/`state`/`zip`/`google_place_id` with `store_*`
    fallbacks.
  - `_maps_search_url(query, place_id)` (`:186`) → `/maps/search/` only.
  - `_build_map_actions(rows: list[dict]) -> list[dict[str,str]]` (`:193`) →
    one `search` action per row.
  - `_store_query_parts` is ALSO used by `_format_store_location_answer` (`:222`)
    to derive the display `name` — that call site must keep a name source.
- `src/app/domain/chat/services/adk.py` — `_build_map_actions` is imported
  (`:25`) and called with plain dict rows: store rows at `:787`
  (`_store_location_event`) and inventory rows at `:870`
  (`_product_availability_event`). Rows are `_coerce_dict_rows(...)` output —
  serialized dicts, NOT `Store` structs.
- `src/app/domain/products/schemas/_products.py:32` — `Store` struct (camelized,
  `omit_defaults=True`): `name`, `address`, optional `city`/`state`/`zip`/
  `google_place_id`, etc.
- `src/resources/main.js`:
  - `safeMapsUrl(url)` (`:702`) — accepts `https:` + `www.google.com` +
    `pathname.startsWith("/maps/")`. `/maps/dir/` already passes.
  - `mapActionForRow(row, actions)` (`:714`) — finds ONE action by matching
    `action.label === store name`, falls back to `actions[0]`, validates URL.
    Returns a single `{...action, url}` or `null`.
  - `renderStoreCard(row, action)` (`:721`) — renders a single "Open in Google
    Maps" anchor at `:760-764` when `action` is truthy.
  - `renderStructuredResults` (`:769`) — maps each row through
    `mapActionForRow(row, actions)`.
  - Net: main.js currently renders a SINGLE action per row, matched by label.
    With two actions per store sharing the same label, the label-match must be
    replaced by per-row action grouping.

### Reconcile decision (type mismatch)

Grounding has raw dict rows; `maps.py` builders take a `Store`. `maps.py` is
orphaned (only tests import it), so the simpler, lower-risk path is to refactor
`maps.py` builders to accept the plain fields grounding already has, rather than
reconstructing a `Store` per row inside grounding.

Chosen approach: refactor `maps.py` to build from explicit primitive fields.

- Add field-based builders that take `name`, `address`, `city`, `state`, `zip`,
  `place_id` (the data grounding has):
  - `build_store_search_url(name, address, city, state, zip_code, place_id=None)`
  - `build_store_directions_url(name, address, city, state, zip_code, place_id=None, origin=None)`
- Keep behavior identical (same query assembly via a shared `_store_query(...)`
  on primitives, same `api=1`, same path/param names).
- Provide thin `Store`-typed adapters ONLY if a `Store`-typed caller exists. No
  production caller currently passes a `Store`; the existing `test_maps.py`
  constructs a `Store` and calls the builders, so update those tests to pass the
  store's fields (or keep one `Store` overload used solely by tests — prefer
  updating tests to the field-based signature to avoid a test-only wrapper).
- Grounding extracts the same fields it reads today and calls the maps builders;
  delete `_maps_search_url` and `_store_query_parts` from grounding.

## Implementation Plan

### Phase 1: Single field-based Maps builder
- [ ] 1.1 In `src/app/domain/products/services/maps.py`, change `_store_query` to
      operate on primitive fields: `_store_query(name, address, city, state, zip_code) -> str`
      (same assembly: `name, address, "city, state zip"`).
- [ ] 1.2 Change `build_store_search_url` (`maps.py:15`) to signature
      `build_store_search_url(name, address, city, state, zip_code, place_id=None)`;
      keep `/maps/search/`, `api=1`, `query`, and `query_place_id` (set only when
      `place_id`).
- [ ] 1.3 Change `build_store_directions_url` (`maps.py:23`) to signature
      `build_store_directions_url(name, address, city, state, zip_code, place_id=None, origin=None)`;
      keep `/maps/dir/`, `api=1`, `destination`, `destination_place_id`, and the
      optional `origin` formatting (tuple → `"{lat:.6f},{lon:.6f}"`, else string).
- [ ] 1.4 Drop the `Store` import / `TYPE_CHECKING` block if no longer referenced.
      Keep behavior-only docstrings (no spec/phase references).

### Phase 2: Wire grounding to the single builder + dual actions
- [ ] 2.1 In `_adk_grounding.py`, add a small row→fields reader (reuse the
      existing `name`/`address`/`city`/`state`/`zip` + `store_*` fallback logic
      that lives in `_store_query_parts`) so `_build_map_actions` can pull the
      primitives and `google_place_id`.
- [ ] 2.2 Rewrite `_build_map_actions(rows)` (`_adk_grounding.py:193`) to emit two
      actions per row: a `search` action `{type:"search", label:"Open in Google
      Maps", url: build_store_search_url(...)}` and a `directions` action
      `{type:"directions", label:"Get directions", url: build_store_directions_url(...)}`.
      Import both builders from `app.domain.products.services.maps`.
      Note: labels change from the store name to fixed action labels because the
      frontend match-by-label path is being replaced (Phase 4); confirm no other
      consumer depends on label == store name.
- [ ] 2.3 Preserve a store-name source for `_format_store_location_answer`
      (`_adk_grounding.py:222`): it calls `_store_query_parts(first)` only for the
      name. Replace with an inline name read (`row.get("name") or row.get("store_name") or "Cymbal Coffee"`)
      or a tiny `_store_name(row)` helper; do not retain `_store_query_parts`
      solely for this.
- [ ] 2.4 Delete `_maps_search_url` (`_adk_grounding.py:186`) and
      `_store_query_parts` (`:174`). Confirm no other references remain
      (`grep -rn "_maps_search_url\|_store_query_parts" src/`).
- [ ] 2.5 Confirm `adk.py` call sites (`:787`, `:870`) need no change — they pass
      the same dict rows; only the returned action list grows. The `urlencode`/
      `urlunsplit` imports in `_adk_grounding.py` become unused → remove them.

### Phase 3: Backend tests
- [ ] 3.1 Update `src/tests/unit/app/domain/products/services/test_maps.py` to the
      field-based signatures (pass the store's fields instead of a `Store`). Keep
      the existing assertions: no-key, `api=1`, `query`/`destination` encoding,
      `*_place_id`, `origin` formatting, `key=` absent.
- [ ] 3.2 In `src/tests/unit/app/domain/chat/services/test_adk_grounding.py`, add a
      test asserting `_build_map_actions([store_row])` returns exactly two actions:
      one `type=="search"` and one `type=="directions"`, both with URLs starting
      `https://www.google.com/maps/`, both with `api=1`, neither containing
      `origin=` or `key=`.

### Phase 4: Render the directions action
- [ ] 4.1 In `src/resources/main.js`, replace `mapActionForRow(row, actions)`
      (`:714`) with a function that returns the row's validated search + directions
      actions. Since two actions now share the search-link rendering surface and the
      old code matched by `label === store name`, group actions per row: each
      `find_stores_*` event returns actions in row order (2 per row), or filter by
      `type`. Validate each URL with `safeMapsUrl` (`:702`); drop any that fail.
- [ ] 4.2 In `renderStoreCard(row, action)` (`:721`), accept the search +
      directions pair and render both links in the actions row (`:753-765`):
      keep the existing "Open in Google Maps" anchor for the `search` action; add a
      sibling anchor labeled "Get directions" for the `directions` action, using the
      same classes, `target="_blank"`, and `rel="noopener noreferrer"`.
- [ ] 4.3 Update `renderStructuredResults` (`:769`) to pass the per-row action pair
      to `renderStoreCard`. Keep the `slice(0, 3)` cap.
- [ ] 4.4 Do NOT hand-edit generated bundles under
      `src/app/domain/web/static/assets/main-*.js`; they regenerate from the build.

### Phase 5: Build + verify
- [ ] 5.1 `cd src/resources && npm run build` succeeds.
- [ ] 5.2 `uv run pytest src/tests/unit/app/domain/products/services/test_maps.py src/tests/unit/app/domain/chat/services/test_adk_grounding.py`
      passes.
- [ ] 5.3 `make lint` and `make test` green.

## Acceptance

- [ ] `products/services/maps.py` is the only Maps URL builder; it builds both
      search and directions URLs from primitive fields.
- [ ] `_adk_grounding.py` contains no inline URL builder (`_maps_search_url` and
      `_store_query_parts` deleted; `urlencode`/`urlunsplit` imports removed).
- [ ] `_build_map_actions` returns one `search` action and one `directions`
      action per store row, with valid no-key `www.google.com/maps/` URLs and no
      `origin`/`key`.
- [ ] Chat store/availability replies render BOTH "Open in Google Maps" and
      "Get directions" links, each through `safeMapsUrl`.
- [ ] No dead maps function remains anywhere (grep clean).
- [ ] `make test` and `cd src/resources && npm run build` are green.

## Verification

```bash
grep -rn "_maps_search_url\|_store_query_parts" src/            # expect: no matches
grep -rn "from app.domain.products.services.maps" src/app       # grounding now imports the builder
cd src/resources && npm run build
uv run pytest src/tests/unit/app/domain/products/services/test_maps.py \
              src/tests/unit/app/domain/chat/services/test_adk_grounding.py
make lint
make test
```
