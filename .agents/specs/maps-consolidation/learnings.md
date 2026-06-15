# Learnings: maps-consolidation

## oracledb-vertexai-mzm.7 — Ch7: Maps consolidation + directions [c3f5704]

### Reconcile decision (Store struct vs. dict rows)

`products/services/maps.py` was orphaned (only `test_maps.py` imported it) and its
builders took a `Store` struct, but chat grounding works on raw serialized dict
rows (`_coerce_dict_rows` output), not `Store` structs. Chose the simpler,
lower-risk path: refactor the builders to accept primitive fields
(`name`, `address`, `city`, `state`, `zip_code`, `place_id`) rather than
reconstructing a `Store` per row inside grounding. `_store_query` now operates on
primitives. `test_maps.py` updated to pass the store's fields directly (no
test-only `Store` wrapper retained).

### `_store_query_parts` had a second caller

`_store_query_parts` was used both by `_build_map_actions` (for name + query) and
by `_format_store_location_answer` (which only needed the display name). Before
deleting it, extracted a tiny `_store_name(row)` helper
(`row.get("name") or row.get("store_name") or "Cymbal Coffee"`) and pointed the
store-location answer at it, so deleting the duplicate builder did not break
store-location replies.

### Dual map actions + privacy

`_build_map_actions` now emits TWO actions per store row in row order (search then
directions), both no-key `www.google.com/maps/` URLs, preserving the
`{type, label, url}` shape and the `type: "search"` value, adding
`type: "directions"`. Directions are destination-only — grounding has no
per-request browser coordinates at action-build time, so no `origin` is embedded
(coordinate privacy preserved). Deleted `_maps_search_url` + `_store_query_parts`
and the now-unused `urlencode`/`urlunsplit` imports from grounding.

### Type-checking primitive-field unpacking

Unpacking a row-derived dict with `**fields` into the builders failed mypy because
a plain `dict[str, str | None]` is incompatible with `str` params. Fixed by
declaring a `_StoreFields` `TypedDict` with precise per-key types
(`name`/`address`/`city`/`state`/`zip_code: str`, `place_id: str | None`), which
makes the unpack type-check cleanly.

### main.js per-row action grouping

The old `mapActionForRow` matched a single action by `label === store name`. With
two actions per store sharing fixed labels ("Open in Google Maps" / "Get
directions"), replaced the label-match with per-row index grouping: row `i` maps
to `actions[i*2]` (search) and `actions[i*2+1]` (directions), each validated via
the existing `safeMapsUrl` (no validator change needed — it already accepts
`/maps/dir/` via the `/maps/` prefix check). `renderStoreCard` renders both
anchors with the same classes, `target="_blank"`, `rel="noopener noreferrer"`.

### Built assets are gitignored

`src/app/domain/web/static` is gitignored (`.gitignore:160`). The Vite build
(`cd src/resources && npm run build`) regenerates the bundle (verified "Get
directions" present in `static/assets/main-*.js`), but there are no asset files to
stage — only the Vite source `src/resources/main.js` is tracked.
