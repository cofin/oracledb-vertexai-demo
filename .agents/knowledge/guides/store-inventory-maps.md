# Store, Inventory, and Maps Guide

This guide details store location management, inventory tracking, browser geolocation integration, and Google Maps services.

## Architecture & Domain

Store, location, and inventory services reside in the **products domain** rather than a separate domain package.
- Seed data and configuration live in the products domain.
- Domain services are request-scoped and resolve facts using Oracle named SQL.

## Data Foundation

The baseline database migration (`0001_cymball_coffee_products.sql`) and fixtures ship:
- **Stores:** Latitude, longitude, timezone, name, phone, address, hours, and optional Google Place IDs.
- **Inventory:** Normalized `store_product_inventory` table linking products to stores with a `quantity` and `in_stock` boolean.
- **Dallas Arts District store:** The default seeded demo store.

## Query Services & Mechanics

### 1. Nearest Store (Haversine)
Nearest-store lookup is calculated on the database or using a Python helper (`src/app/domain/products/services/_location.py`).
- It uses the Haversine formula (`haversine_miles`) based on the database coordinates.
- **Do not** call Google Geocoding, Places, Distance Matrix, or Routes APIs to compute nearest stores.

### 2. Product Availability Lookups
Product availability queries (`find_product_availability`) resolve target products in three steps:
1. **Exact Match:** Attempt to match name, SKU, or ID directly in Oracle.
2. **Pronoun Resolution:** If the query lacks a specific product name (e.g. "Is it in stock?"), resolve the target using the `last_products` list stored in the ADK session state.
3. **Vector Fallback:** If direct match fails, generate a query embedding and execute a vector search against products (threshold 0.6) to identify the closest match (e.g. "Gemini" -> "Gemini Rush").

## ADK Integration & Intent

The chat runner handles store/availability requests deterministically via intent classification:
- `STORE_LOCATION`: returns closest store, store card, hours, phone, and address.
- `PRODUCT_AVAILABILITY`: returns stock status for the resolved product at the nearest or specified store.
- `ORDER_STATUS`: explicitly recognized but unsupported until order data structures exist.

Timings and store search counts are captured in `search_metrics`.

## Geolocation & Privacy

We enforce a strict privacy boundary for user location data:
- **Opt-in Only:** Location tracking must require explicit user action (clicking a "Share Location" button in the browser), never on page load.
- **In-Memory:** Latitude and longitude remain in browser memory for the session.
- **No Persistence:** **NEVER** save, cache, log, or persist raw user coordinates in database tables, response caches, telemetry, or server logs.
- **Cache Bypassing:** Vary or bypass response cache reads when location context is present to avoid serving store-specific answers to the wrong user.

## Google Maps Integration

### 1. No-Key URLs (Default)
Standard Google Maps links are the default integration and require no API keys:
- Search URL: `https://www.google.com/maps/search/?api=1&query={query}`
- Directions URL: `https://www.google.com/maps/dir/?api=1&destination={latitude},{longitude}&destination_place_id={place_id}`

### 2. Maps Embed (Optional)
Embedded map iframes are optional and disabled by default:
- Requires `MAPS_ENABLE_EMBED=true` and a separate `GOOGLE_MAPS_EMBED_API_KEY`.
- The key must be restricted in the Google Cloud Console and must be distinct from Gemini/Vertex AI credentials.
- In Litestar, the CSP header (`frame-src`) is modified dynamically by `build_security_headers` only when maps embed is active.
- Always send `Permissions-Policy: geolocation=(self)` to prevent the maps iframe from accessing browser location.
