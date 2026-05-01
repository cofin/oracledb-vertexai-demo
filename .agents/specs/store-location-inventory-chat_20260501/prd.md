# Master PRD: Store-Aware Chat, Inventory, and Maps

*PRD ID: `store-location-inventory-chat_20260501`*
*Created: 2026-05-01*
*Status: Accepted - ready for implementation planning*
*Beads: pending tracker creation*

---

## North Star

Restore and extend the store-aware chat behavior that existed in `main`, then make it useful in the current ADK 2 + HTMX chat surface.

The end state is a chat experience that can answer store location, hours, directions, and store-level product availability questions from grounded local data. Browser location can be used only after explicit user consent. Google Maps integration starts with safe Maps URLs that need no API key, with embedded maps available later behind explicit configuration and restricted Google Maps keys.

This PRD allows store, product, and inventory data-structure changes. Implementation planning is complete; source changes remain out of scope until a chapter is claimed.

---

## Current Findings

### Current branch

- `IntentLabel` already has `PRODUCT_RAG`, `GENERAL_CONVERSATION`, `STORE_LOCATION`, and `ORDER_STATUS`.
- The classifier instruction already mentions location, hours, nearest cafe, pickup location, and directions.
- Only `PRODUCT_RAG` has a deterministic grounded route in `ADKRunner.stream_request`.
- `STORE_LOCATION` currently falls through to the general ADK workflow and depends on the model choosing `get_all_store_locations`.
- `AgentToolsService` currently exposes only three chat tool factories: `search_products_by_vector`, `get_product_details`, and `get_all_store_locations`.
- `StoreService` supports all stores, city, state, and id lookups. It does not expose zip search, hours lookup, nearest-store ranking, inventory lookup, or product-availability-by-store.
- The chat controller and frontend do not accept browser location context and do not render store cards, inventory cards, or map actions.
- No current CSP or Permissions-Policy header path was found in `src/app`; adding embedded maps or browser geolocation needs an explicit security-header plan.

### `main` branch behavior to recover

The old code had richer store intent examples and tools:

- `app/services/_intent.py` had `STORE_LOCATION` examples for directions, hours, city/state questions, address/contact questions, typos, and availability-style prompts.
- `app/services/_adk/tool_service.py` exposed `find_stores_by_location(city=None, state=None)` and `get_store_hours(store_id)`.
- `app/services/_adk/tools.py` exported module-level `get_store_locations`, `find_stores_by_location`, and `get_store_hours`.
- `app/services/_adk/runner.py` streamed store function responses as `type: "stores"` with store metadata.
- `app/services/_store.py` had `search_stores_by_zip`, but it used inline SQL. The current branch requires named SQL under `src/app/db/sql/*.sql`.

### Fixture data

Store fixture:

- `src/app/db/fixtures/store.json.gz` contains 15 stores.
- Fields are `id`, `name`, `address`, `city`, `state`, `zip`, `phone`, `hours`, `metadata`, `created_at`, and `updated_at`.
- `hours` is present for each day.
- Metadata includes useful display attributes such as wifi, seating, drive through, meeting rooms, late night, rooftop terrace, bike parking, student discounts, beach view, and similar local features.
- The fixture does not currently include a Dallas-area store. The implementation must add one so location prompts from Dallas can produce a nearby match.
- Missing for maps and nearest-store behavior: `latitude`, `longitude`, `timezone`, and optional `google_place_id`.

Product fixture:

- `src/app/db/fixtures/product.json.gz` contains 122 products.
- Product categories are cappuccino, chocolate, coffee, cold-brew, espresso, frappuccino, latte, macchiato, and tea.
- Every fixture row has `in_stock: null`. The loader drops nulls, so the database default currently makes products globally in stock, but this is ambiguous and does not model store-level inventory.
- Missing for availability prompts: a store-product inventory fixture and table.

---

## External API Findings

Use these as implementation constraints:

- Google Maps URLs can launch search and directions across platforms and do not require a Google API key. This is the required baseline.
- Maps Embed API can render an interactive map in an iframe, but 2026 Google docs still require a valid Google Cloud API key and billing-enabled project for every Maps Embed request. It must be optional and key-restricted.
- Google Maps Platform guidance says API keys must be restricted by application and API. The demo must not ship or document an unrestricted key.
- Browser geolocation requires a secure context and explicit user permission when calling `getCurrentPosition()` or `watchPosition()`. Access is also affected by the `Permissions-Policy: geolocation` directive.

Primary docs:

- Google Maps URLs: <https://developers.google.com/maps/documentation/urls/get-started>
- Maps Embed API: <https://developers.google.com/maps/documentation/embed/get-started>
- Maps Embed quickstart: <https://developers.google.com/maps/documentation/embed/quickstart>
- Google Maps API key security: <https://developers.google.com/maps/api-security-best-practices>
- MDN Geolocation API: <https://developer.mozilla.org/en-US/docs/Web/API/Geolocation_API>

### Access Decision

We can support directions and store-location actions without any Google Maps API key by using Maps URLs:

- This covers "Open in Google Maps", directions, search, and mobile handoff.
- This should be the default and the only required map integration for the first implementation.
- It also keeps the chat feature independent from Gemini or Vertex credentials.

We cannot embed an interactive Google map inside the chat window without a Google Maps Platform API key. If in-chat iframe maps are accepted for a later chapter, create a separate Maps Embed key. Do not reuse any Gemini, Vertex, or general Google API key.

Recommended environment names:

- `GOOGLE_MAPS_EMBED_API_KEY` for Maps Embed only
- `MAPS_ENABLE_EMBED=false` by default

The Maps key is optional and separate from any Gemini key. Gemini is not required for this store/maps feature.

Recommended setup commands for optional embed support:

```bash
export GOOGLE_CLOUD_PROJECT="<project-id>"

gcloud services enable \
  --project "${GOOGLE_CLOUD_PROJECT}" \
  "maps-embed-backend.googleapis.com"

gcloud services api-keys create \
  --project "${GOOGLE_CLOUD_PROJECT}" \
  --display-name "oracledb-vertexai-demo-maps-embed" \
  --api-target=service=maps-embed-backend.googleapis.com \
  --allowed-referrers="http://localhost:8000/*,http://127.0.0.1:8000/*,https://<your-demo-host>/*"
```

After creation, fetch the key string from the returned key resource and set it outside source control:

```bash
gcloud services api-keys get-key-string \
  "projects/${GOOGLE_CLOUD_PROJECT}/locations/global/keys/<KEY_ID>"

export GOOGLE_MAPS_EMBED_API_KEY="<returned-key-string>"
export MAPS_ENABLE_EMBED="true"
```

Implementation docs should instruct users to replace `<your-demo-host>` and `<KEY_ID>`, and to verify the key has exactly:

- application restriction: allowed HTTP referrers for the local/demo hosts
- API restriction: `maps-embed-backend.googleapis.com`

### Optional Scripted Key Setup

Yes, the Maps Embed key setup should be scriptable. Add a helper in the implementation:

- Path: `tools/scripts/create-maps-embed-key.sh`
- Purpose: enable Maps Embed API, create a separate restricted Maps Embed key, and print the environment exports needed by the app.
- Required inputs:
  - `--project <project-id>` or `GOOGLE_CLOUD_PROJECT`
  - one or more `--referrer <pattern>` values
- Defaults:
  - display name: `oracledb-vertexai-demo-maps-embed`
  - API target: `maps-embed-backend.googleapis.com`
  - local referrers: `http://localhost:8000/*` and `http://127.0.0.1:8000/*`
- Optional inputs:
  - `--display-name <name>`
  - `--dry-run`
  - `--env-file <path>` to append local exports only when explicitly requested
  - `--reuse-existing` to reuse an existing key with the same display name instead of creating another one

Recommended usage:

```bash
tools/scripts/create-maps-embed-key.sh \
  --project "${GOOGLE_CLOUD_PROJECT}" \
  --referrer "http://localhost:8000/*" \
  --referrer "http://127.0.0.1:8000/*" \
  --referrer "https://<your-demo-host>/*"
```

Recommended script behavior:

1. Fail if `gcloud` is not installed.
2. Fail if no project is provided.
3. Show the active `gcloud` account and project before creating anything.
4. Enable `maps-embed-backend.googleapis.com`.
5. Create or reuse a key with:
   - `--api-target=service=maps-embed-backend.googleapis.com`
   - restricted `--allowed-referrers`
6. Fetch the key string with `gcloud services api-keys get-key-string`.
7. Print these exports to stdout:

```bash
export GOOGLE_MAPS_EMBED_API_KEY="<returned-key-string>"
export MAPS_ENABLE_EMBED="true"
```

Safeguards:

- The script must never ask for, read, or reuse a Gemini/Vertex key.
- The script must never create an unrestricted Maps key.
- The script must not write secrets to tracked files.
- If `--env-file` is used, the target path must be ignored by git or the script must refuse to write.
- `--dry-run` must show the exact `gcloud` operations without creating a key.
- The implementation should verify the exact `gcloud services api-keys create --format=...` output shape against the installed Cloud SDK. If the create command returns operation metadata instead of a key resource name, resolve the key by display name before calling `get-key-string`.

---

## Product Decisions

1. Make grounded store answers deterministic like product RAG.
   - `STORE_LOCATION` should not rely on the model deciding to call a tool.
   - The runner should gather store facts first, build a grounded answer, and return structured store metadata.

2. Add a new intent for store-level inventory.
   - Recommended label: `PRODUCT_AVAILABILITY`.
   - It covers prompts like "where can I get cold brew near me" and "is the mocha muffin available in Seattle".
   - This keeps product discovery, store lookup, and inventory lookup from being overloaded into one broad `PRODUCT_RAG` path.

3. Keep `ORDER_STATUS` explicit but unsupported unless order data is added.
   - The current app has no order fixture or order service.
   - `ORDER_STATUS` should return a grounded "order lookup is not available in this demo" response instead of hallucinating an order state.

4. Use Maps URLs for the first implementation.
   - They require no key.
   - They keep Google Maps outside the chat app unless the user clicks.
   - They support directions from browser coordinates when the user has opted in.

5. Treat embedded maps as optional.
   - Gate with settings such as `MAPS_ENABLE_EMBED=false` and `GOOGLE_MAPS_EMBED_API_KEY`.
   - Require HTTP referrer restrictions and API restrictions for the key.
   - Add CSP frame allowances only when embed is enabled.

6. Browser location must be opt-in and request-scoped.
   - Never prompt on page load.
   - Call `navigator.geolocation.getCurrentPosition()` only from a user action.
   - Do not persist raw latitude/longitude in the database, response cache, chat display history, SQL metrics, or logs.
   - If coordinates are sent to the server, use them only for the current request and omit exact values from telemetry.

7. Do not use live geocoding during chat.
   - Seed store coordinates in fixtures or metadata ahead of time.
   - Do not call Google Geocoding, Places, or Google Maps Geolocation APIs from chat turns.
   - This keeps chat latency, cost, and key exposure lower.

8. Model store inventory explicitly.
   - Add normalized store-product inventory rather than hiding inventory in JSON metadata.
   - Keep `product.in_stock` as catalog/global availability only, and fix product fixture nulls to a clear boolean if the field stays.

9. Preserve current repo patterns.
   - Named SQL belongs under `src/app/db/sql/*.sql`.
   - Service code calls `db_manager.get_sql(...)`.
   - Chat data uses existing serialization helpers and existing ADK service boundaries.
   - Frontend stays HTMX/Jinja plus `src/resources/main.js`, not a new SPA or frontend framework.

10. Modify only the baseline migration for schema changes.
    - This branch will drop and recreate the database.
    - Do not add a timestamped forward migration for this feature.
    - All schema changes belong in `src/app/db/migrations/0001_cymball_coffee_products.sql`.

11. Use curated inventory fixture coverage.
    - Do not seed all 122 products across every store.
    - Seed enough inventory for deterministic Dallas, Seattle, Berkeley, and near-me examples.

---

## Existing Plan Alignment

All current `.agents/specs` folders were reviewed on 2026-05-01. The alignment record is [alignment.md](./alignment.md).

This PRD is a follow-on to the reset work. It depends on the completed ADK 2 runner, named SQL extraction, HTMX/Vite frontend, and test-suite reorganization. It does not reopen React, inline SQL, or timestamped migration strategies.

---

## Data Model

### Store

Add fields:

- `latitude NUMBER(9,6) NULL`
- `longitude NUMBER(9,6) NULL`
- `timezone VARCHAR2(64) NULL`
- `google_place_id VARCHAR2(255) NULL`
- Optional generated/display-only field in schema: `maps_search_url` or `maps_directions_url`.

Update:

- `src/app/db/migrations/0001_cymball_coffee_products.sql`
- `src/app/db/fixtures/store.json.gz`
- `src/app/domain/products/schemas/_products.py`
- `src/app/db/sql/stores.sql`
- related generated OpenAPI/types after implementation

Migration strategy:

- Update the baseline migration and fixtures together.
- Modify only `src/app/db/migrations/0001_cymball_coffee_products.sql`.
- Do not add a timestamped forward migration.
- Verification should drop and recreate the local database before applying the updated baseline.

### Inventory

Add a new table:

- `store_product_inventory`
- `id VARCHAR2(36) PRIMARY KEY`
- `store_id VARCHAR2(36) NOT NULL REFERENCES store(id)`
- `product_id VARCHAR2(36) NOT NULL REFERENCES product(id)`
- `quantity_available NUMBER(10) DEFAULT 0 NOT NULL`
- `stock_status VARCHAR2(32) NOT NULL`
- `pickup_available BOOLEAN DEFAULT TRUE NOT NULL`
- `updated_at TIMESTAMP WITH TIME ZONE NOT NULL`
- unique constraint on `(store_id, product_id)`
- indexes on `store_id`, `product_id`, `stock_status`, and `(product_id, stock_status)`

Recommended stock statuses:

- `IN_STOCK`
- `LOW_STOCK`
- `OUT_OF_STOCK`

Add fixtures:

- `src/app/db/fixtures/store_product_inventory.json.gz`
- Fixture volume should be enough for deterministic examples, not an exhaustive retail catalog.
- Seed inventory for a curated subset of products across the existing stores plus Dallas, with mixed in-stock, low-stock, and out-of-stock cases.
- Include specific rows that exercise "near me" and city-specific availability tests.

Add a Dallas-area store fixture:

- Recommended name: `Cymbal Coffee Dallas Arts District`
- Recommended city/state/zip: `Dallas`, `TX`, `75201`
- Recommended timezone: `America/Chicago`
- Recommended approximate coordinates: `32.7876`, `-96.7994`
- Recommended metadata: wifi, seating, meeting rooms, early hours, local art
- Include normal weekday/weekend hours and a phone number consistent with the existing fictional fixture style.
- Seed inventory rows for this store so "near me" and Dallas availability prompts can return both a location and at least one available product.

---

## API and Response Shape

Extend chat responses with structured store facts:

```json
{
  "intent_detected": "STORE_LOCATION",
  "store_results": [
    {
      "id": "store-001",
      "name": "Cymbal Coffee Palo Alto",
      "address": "...",
      "city": "Palo Alto",
      "state": "CA",
      "zip": "94301",
      "phone": "...",
      "hours": {},
      "distance_miles": 2.4,
      "maps_url": "https://www.google.com/maps/dir/?api=1&destination=..."
    }
  ],
  "inventory_results": [],
  "location_context": {
    "source": "browser",
    "used_for_ranking": true,
    "accuracy_meters": 120
  },
  "map_actions": [
    {
      "label": "Directions",
      "url": "https://www.google.com/maps/dir/?api=1&origin=...&destination=..."
    }
  ]
}
```

Rules:

- `location_context` may say browser/city/zip/none, but must not echo exact coordinates back to the UI unless there is a specific display reason.
- `store_results` and `inventory_results` must be built from database rows, not model text.
- Coordinates must not become part of cache keys unless rounded and intentionally documented. MVP should disable response caching for browser-coordinate requests.
- `map_actions` should be deterministic URL actions generated by application code.

---

## Browser Location

Add a browser-side location state in `src/resources/main.js`:

- User clicks "Use my location" or a store/directions prompt offers it.
- JS calls `navigator.geolocation.getCurrentPosition(...)`.
- Suggested options:
  - `enableHighAccuracy: false`
  - `timeout: 8000`
  - `maximumAge: 300000`
- Store coordinates only in memory for the current page session.
- Submit `latitude`, `longitude`, `accuracy_meters`, and an explicit `location_consent=true` field with the chat request only after opt-in.
- If denied/unavailable, do not retry automatically. Offer city/zip fallback.

Add server-side validation:

- Latitude must be between -90 and 90.
- Longitude must be between -180 and 180.
- Accuracy must be non-negative and capped to a reasonable max.
- Reject or ignore coordinates unless `location_consent=true`.
- Never log raw coordinates.

Add security headers:

- At minimum: `Permissions-Policy: geolocation=(self)`.
- If map embeds are disabled, no third-party geolocation delegation is needed.
- If embed is enabled, do not grant geolocation to the Google iframe; the app should compute direction URLs from the user-approved origin.

---

## Maps Integration

### Required: Maps URLs

Generate links such as:

- Store search: `https://www.google.com/maps/search/?api=1&query=<encoded address or lat,lng>`
- Directions without browser location: `https://www.google.com/maps/dir/?api=1&destination=<encoded address>`
- Directions with browser location: `https://www.google.com/maps/dir/?api=1&origin=<lat,lng>&destination=<encoded address>`

Implementation notes:

- Use structured URL builders, not ad hoc concatenation.
- Encode destination from known store address or seeded coordinates.
- Keep these links safe to render in chat cards as normal anchors.
- This should be the default and required scope.

### Optional: Maps Embed API

Enable only when:

- `MAPS_ENABLE_EMBED=true`
- `GOOGLE_MAPS_EMBED_API_KEY` is configured
- the key has website restrictions for the app host
- the key is restricted to Maps Embed API
- CSP allows the iframe source

Implementation notes:

- Do not store the API key in source, fixtures, or generated frontend assets.
- Do not reuse Gemini, Vertex, or general Google API keys for Maps Embed.
- Do not put map embed URLs into response cache.
- Render one selected-store iframe at a time, not an iframe for every store result.
- If the key is absent or disabled, UI should silently fall back to Maps URLs.

### Chat UI Mockup

The UI should stay in the existing chat surface. Store results should appear as grounded chat output, with one selected map panel only when Maps Embed is enabled.

Default no-key state:

```text
+---------------------------------------------------------------+
| Cymbal Coffee Assistant                                  [new] |
+---------------------------------------------------------------+
| User                                                          |
| Find a store near Dallas                                     |
|                                                               |
| Assistant                                                     |
| The nearest Cymbal Coffee location I found is in Dallas.      |
|                                                               |
| +---------------------------------------------------------+   |
| | Cymbal Coffee Dallas Arts District                      |   |
| | 1722 Routh St, Dallas, TX 75201                         |   |
| | Today: 6:30 AM - 8:00 PM          1.8 mi away           |   |
| | Phone: (214) 555-0184                                  |   |
| |                                                         |   |
| | [Directions] [Open in Google Maps] [View hours]         |   |
| +---------------------------------------------------------+   |
|                                                               |
| Assistant                                                     |
| I can use your browser location to rank stores more exactly.  |
| [Use my location] [Enter city or ZIP]                         |
+---------------------------------------------------------------+
| Message Cymbal Coffee...                                [send] |
+---------------------------------------------------------------+
```

Optional embedded map state:

```text
+---------------------------------------------------------------+
| Cymbal Coffee Assistant                                  [new] |
+---------------------------------------------------------------+
| User                                                          |
| Directions to the Dallas store                               |
|                                                               |
| Assistant                                                     |
| Here is the Dallas Arts District location.                    |
|                                                               |
| +---------------------------------------------------------+   |
| | Cymbal Coffee Dallas Arts District                      |   |
| | 1722 Routh St, Dallas, TX 75201                         |   |
| | Today: 6:30 AM - 8:00 PM                                |   |
| | [Directions] [Open in Google Maps] [Hide map]            |   |
| +---------------------------------------------------------+   |
|                                                               |
| +---------------------------------------------------------+   |
| |                                                         |   |
| |                    GOOGLE MAP IFRAME                    |   |
| |              single selected store/directions           |   |
| |                                                         |   |
| +---------------------------------------------------------+   |
+---------------------------------------------------------------+
| Message Cymbal Coffee...                                [send] |
+---------------------------------------------------------------+
```

Product availability state:

```text
+---------------------------------------------------------------+
| User                                                          |
| Is cold brew available in Dallas?                            |
|                                                               |
| Assistant                                                     |
| Yes. These Dallas pickup options have cold brew available.    |
|                                                               |
| +--------------------------+  +----------------------------+  |
| | Classic Cold Brew        |  | Dallas Arts District       |  |
| | In stock                 |  | 1722 Routh St              |  |
| | Pickup available today   |  | [Directions] [Map]         |  |
| +--------------------------+  +----------------------------+  |
+---------------------------------------------------------------+
```

Interaction rules:

- The map panel must be collapsed by default unless the user asks for directions or clicks "Map".
- Only one iframe should render at a time.
- When `MAPS_ENABLE_EMBED=false` or the key is missing, the "Map" action should become "Open in Google Maps".
- Browser location prompt should be a user-click action, never an automatic page-load prompt.
- Store cards must be grounded from `store_results`, not generated from freeform model text.

### Deferred: Maps JavaScript API and Places

Do not include in the first implementation:

- Places autocomplete
- live Google geocoding
- distance matrix calls
- route optimization
- interactive store-locator map with markers

Those require more API surface, CSP, billing, and key-management work than this chat enhancement needs.

---

## Roadmap

### Chapter 1 - `store-data-foundation_20260501`

Goal: make the local dataset capable of answering store, directions, nearest-store, and inventory questions.

Deliverables:

- Add store coordinate/timezone/place-id fields to schema and fixtures.
- Add normalized `store_product_inventory` schema, fixture, and indexes.
- Clarify product-level `in_stock` semantics and fixture values.
- Update product/store schemas to include new fields and inventory objects.
- Update fixture loading order so inventory loads after stores and products.
- Update named SQL files for widened store selection and inventory joins.

Acceptance:

- All existing store fixtures plus the new Dallas-area store have lat/lng, timezone, and realistic directions-ready addresses.
- The Dallas-area store is present in the loaded database and can be found by city, state, zip, and nearest-store ranking.
- `0001_cymball_coffee_products.sql` is the only migration file changed; no timestamped migration is added.
- Product fixture `in_stock` is no longer semantically ambiguous.
- At least one deterministic fixture proves each inventory status: in stock, low stock, and out of stock.
- The database can be reset and loaded without FK ordering failures.
- No chat behavior changes are required in this chapter.

Primary files:

- `src/app/db/migrations/0001_cymball_coffee_products.sql`
- `src/app/db/fixtures/store.json.gz`
- `src/app/db/fixtures/product.json.gz`
- `src/app/db/fixtures/store_product_inventory.json.gz`
- `src/app/utils/fixtures.py`
- `src/app/domain/products/schemas/_products.py`
- `src/app/db/sql/stores.sql`
- new `src/app/db/sql/inventory.sql`

### Chapter 2 - `store-query-services_20260501`

Goal: expose grounded store and inventory query primitives through the service layer and ADK tool service.

Deliverables:

- Add `StoreService.get_store_hours`.
- Add `StoreService.search_stores_by_zip`.
- Add `StoreService.find_nearest_stores(latitude, longitude, limit=5)`.
- Add inventory service methods:
  - `get_store_inventory(store_id)`
  - `find_stores_with_product(product_id, latitude=None, longitude=None)`
  - `find_product_availability(query, location_hint=None, coordinates=None)`
- Add tool service methods:
  - `find_stores_by_location(city=None, state=None, zip_code=None)`
  - `get_store_hours(store_id)`
  - `find_nearest_stores(latitude, longitude)`
  - `find_stores_with_product(product_query, latitude=None, longitude=None)`
- Generate map URL actions from app code.
- Keep all database access through named SQL.

Acceptance:

- Store lookups by city, state, zip, id, and nearest coordinates are covered by unit tests.
- Inventory lookups return product, store, quantity/status, and pickup availability.
- Nearest-store ranking uses seeded store coordinates and never calls external geocoding.
- Tool-factory tests are updated for the expanded tool set.
- SQL telemetry continues to report named SQL phases without raw coordinates.

Primary files:

- `src/app/domain/products/services/services.py`
- `src/app/domain/chat/services/adk.py`
- `src/app/domain/system/services/services.py`
- `src/app/db/sql/stores.sql`
- `src/app/db/sql/inventory.sql`
- `src/tests/unit/app/domain/products/services/`
- `src/tests/unit/app/domain/chat/services/test_adk.py`

### Chapter 3 - `store-intent-routing_20260501`

Goal: make store and inventory intents deterministic and grounded in the current chat runner.

Deliverables:

- Expand `IntentLabel` with `PRODUCT_AVAILABILITY`.
- Update classifier instructions and examples using the richer `main` examples.
- Add request parsing for location hints:
  - city
  - state
  - zip
  - store name
  - browser coordinates if present and consented
- Route `STORE_LOCATION` to a direct grounded store-answer path.
- Route `PRODUCT_AVAILABILITY` to a product + inventory + store-answer path.
- Route `ORDER_STATUS` to an explicit unsupported-demo response.
- Extend chat response payload with `store_results`, `inventory_results`, `map_actions`, and non-sensitive `location_context`.
- Disable response cache for browser-coordinate requests unless a reviewed rounded-location cache strategy is added.

Acceptance:

- "Where is your Seattle store?" returns the Seattle store, hours, address, phone, and map action.
- "Are you open near me?" asks for browser location or city/zip when no location context exists.
- "Where can I pick up cold brew near me?" returns matching products plus store inventory and distance ranking after opt-in.
- Product RAG prompts still use the existing grounded product path.
- General conversation prompts do not include store payloads.
- Order-status prompts do not invent order data.

Primary files:

- `src/app/domain/chat/services/classifier.py`
- `src/app/domain/chat/services/adk.py`
- `src/app/domain/chat/controllers/_chat.py`
- `src/app/domain/system/services/services.py`
- `src/app/domain/chat/schemas/` if a response schema split exists or is added
- `src/tests/unit/app/domain/chat/services/test_classifier.py`
- `src/tests/unit/app/domain/chat/services/test_adk.py`
- `src/tests/integration/app/domain/chat/controllers/test_chat_http.py`

### Chapter 4 - `browser-location-maps-ui_20260501`

Goal: render store-aware chat interactions in the current HTMX/Jinja frontend.

Deliverables:

- Add a location opt-in control to the chat UI.
- Add browser geolocation handling in `src/resources/main.js`.
- Submit location context with chat requests only after explicit opt-in.
- Render store result cards with:
  - name
  - address
  - phone
  - current/open hours summary
  - distance if available
  - inventory status if applicable
  - Directions/Open in Google Maps action
- Add city/zip fallback when browser location is denied or unsupported.
- Add optional single-store map embed only if enabled in settings.
- Match the PRD mockup states for no-key store result, optional embedded map, and product availability.
- Keep the UI compact and work-focused, consistent with the existing chat.

Acceptance:

- The browser does not ask for location on page load.
- Clicking the opt-in control prompts for permission once and handles grant, denial, timeout, and unsupported states.
- Chat still works when geolocation is unavailable.
- Maps URL actions work without a Google key.
- Embedded maps are absent unless explicitly configured.
- The rendered UI matches the mockup behavior: store cards first, one optional selected map panel, and no page-load geolocation prompt.
- Frontend tests cover the new request fields and result rendering.

Primary files:

- `src/app/domain/web/templates/pages/chat.html.j2`
- `src/resources/main.js`
- `src/app/domain/chat/controllers/_chat.py`
- `src/tests/unit/src/resources/test_chat_frontend.py`
- browser/manual smoke tests if Playwright exists in the repo

### Chapter 5 - `store-maps-security-docs_20260501`

Goal: harden, document, and verify the complete store/maps feature.

Deliverables:

- Add settings for optional maps embed behavior.
- Add `tools/scripts/create-maps-embed-key.sh` for separate Maps Embed key setup:
  - enable `maps-embed-backend.googleapis.com`
  - create `oracledb-vertexai-demo-maps-embed`
  - restrict it to allowed HTTP referrers
  - restrict it to Maps Embed API only
  - store it as `GOOGLE_MAPS_EMBED_API_KEY`, never as a Gemini key
- Document the scripted and manual Maps Embed setup paths.
- Add or update security headers:
  - `Permissions-Policy: geolocation=(self)`
  - CSP frame allowances only when maps embed is enabled
- Add docs for:
  - no-key Maps URL baseline
  - optional Maps Embed setup
  - Google Cloud key restrictions
  - privacy behavior for browser location
  - manual demo prompts
- Add regression tests around:
  - no raw coordinates in logs/cache payloads
  - cache disabled or scoped for browser-location requests
  - missing embed key falls back to links
  - configured embed key does not appear when embed disabled

Acceptance:

- A developer can run the feature with no Google Maps API key and still get directions links.
- A developer can enable embedded maps only through explicit env/settings and a separate restricted Maps Embed key.
- `tools/scripts/create-maps-embed-key.sh --dry-run` shows the intended API enablement and restricted key creation commands.
- `tools/scripts/create-maps-embed-key.sh` refuses to create an unrestricted key and refuses to write key material to a tracked file.
- Docs state that unrestricted Google Maps keys are not acceptable.
- Docs state that Gemini keys are not required for Maps URLs or Maps Embed.
- Tests prove browser coordinates are not persisted to chat history/cache/search metrics.
- `make lint` and `make test` are the final implementation gates.

Primary files:

- `src/app/config/` or current settings module
- app middleware/bootstrap file that owns response headers
- `docs/` or README section for maps/location setup
- `src/tests/unit/`
- `src/tests/integration/`

---

## Test Plan

Chapter-level tests:

- Classifier examples for `STORE_LOCATION`, `PRODUCT_AVAILABILITY`, `PRODUCT_RAG`, `GENERAL_CONVERSATION`, and `ORDER_STATUS`.
- Store service tests for city/state/zip/id/hours/nearest.
- Inventory service tests for product availability by store and nearest matching store.
- Chat runner tests for deterministic store paths and unsupported order status.
- Chat controller tests for validating browser coordinates and consent.
- Frontend tests for geolocation opt-in, fallback, map action rendering, and no automatic prompt.

End-to-end manual prompts:

- "Where is your Seattle store?"
- "What time is the Mission store open today?"
- "Directions to Cymbal Coffee Palo Alto"
- "Use my location to find the nearest store"
- "Find a store near Dallas"
- "Where can I pick up cold brew near me?"
- "Is the mocha muffin available in Berkeley?"
- "Is cold brew available in Dallas?"
- "Track order 12345"

Final gates after implementation:

```bash
make lint
make test
```

---

## Risks and Mitigations

Risk: Browser location creates privacy concerns.

Mitigation: explicit user action, request-scoped use, no persistence, no raw-coordinate logs, and clear fallback.

Risk: Google Maps API key leakage or abuse.

Mitigation: Maps URLs are baseline; embed is optional, env-gated, and requires restricted keys.

Risk: Store availability questions require both product matching and inventory matching.

Mitigation: add a distinct `PRODUCT_AVAILABILITY` intent and deterministic direct route.

Risk: The current data model cannot answer nearest-store or inventory questions.

Mitigation: add store coordinates and a normalized inventory table with focused fixture data.

Risk: Fixture changes make reset/load workflows brittle.

Mitigation: update fixture order and add reset/load tests before chat behavior depends on the new data.

Risk: Existing tests pin the old three-tool factory set.

Mitigation: update tests with intentional new tool names and add behavior tests for the new direct paths.

---

## Non-Goals

- Live Google Places search.
- Live geocoding during chat turns.
- Google Distance Matrix or Routes API calls.
- Full ecommerce order tracking.
- Background location tracking.
- Storing customer coordinates.
- A standalone SPA or new frontend framework.
- A map-first store locator page.

---

## Resolved Decisions

1. MVP map scope: store cards and no-key Google Maps URLs are required; embedded maps are optional and env-gated.
2. Inventory fixtures: use a curated subset that supports deterministic demos, including Dallas.
3. Product availability: keep `product.in_stock` as a catalog flag; store-level availability belongs to `store_product_inventory`.
4. Migration approach: modify only `0001_cymball_coffee_products.sql`; this environment will drop and recreate the database.
5. Maps key setup: provide a scriptable helper for a separate restricted Maps Embed key; Gemini/Vertex keys are not involved.
