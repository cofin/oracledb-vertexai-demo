# Flow: Store Intent Routing (store-intent-routing_20260501)

*Chapter 3 of [store-location-inventory-chat_20260501](../store-location-inventory-chat_20260501/prd.md)*
*Beads: TBD*

---

## Objective

Make store and store-inventory chat intents deterministic and grounded, matching the current product RAG path rather than relying on the model to choose a store tool.

---

## Dependencies

- Requires `store-data-foundation_20260501`.
- Requires `store-query-services_20260501`.
- Builds on the completed ADK 2 runner and classifier-first architecture.

---

## Scope

### Classifier

- Add `PRODUCT_AVAILABILITY` to `IntentLabel`.
- Expand examples with the richer original `main` store-location patterns:
  - location
  - hours
  - directions
  - city/state/zip
  - availability near a location
  - typo/casual variants
- Keep `ORDER_STATUS`, but route it to an explicit unsupported-demo response.

### Request Context

Accept and validate optional location context:

- city/state/zip from the message or fallback UI
- store name hints
- browser latitude/longitude/accuracy only when `location_consent=true`

Do not persist raw browser coordinates.

### Runner Routes

- `STORE_LOCATION` returns a grounded store answer from store service data.
- `PRODUCT_AVAILABILITY` resolves product + inventory + store facts before answering.
- `ORDER_STATUS` returns a grounded unsupported response.
- `PRODUCT_RAG` continues to use the existing product path.
- General conversation remains unchanged.

### Response Payload

Extend chat final payload with:

- `store_results`
- `inventory_results`
- `map_actions`
- non-sensitive `location_context`

Browser-coordinate requests should bypass response caching unless a rounded-location cache strategy is explicitly reviewed.

---

## Tests

- Classifier tests for `STORE_LOCATION`, `PRODUCT_AVAILABILITY`, `PRODUCT_RAG`, `GENERAL_CONVERSATION`, and `ORDER_STATUS`.
- ADK runner tests for deterministic store path, product availability path, and unsupported order status.
- Controller tests for location consent and coordinate validation.
- Cache tests proving raw coordinates are not in cache keys/payloads.

---

## Acceptance Criteria

- "Where is your Seattle store?" returns Seattle address, hours, phone, and map action.
- "Find a store near Dallas" returns the new Dallas store.
- "Where can I pick up cold brew near me?" returns product, inventory, store, and distance ranking after opt-in.
- Product RAG behavior is not regressed.
- Order-status prompts do not invent order data.
- Raw coordinates are not stored in display history, response cache, metrics, or logs.
