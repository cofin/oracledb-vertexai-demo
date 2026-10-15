-- SPDX-FileCopyrightText: 2026 Google LLC
-- SPDX-License-Identifier: Apache-2.0

-- name: list-stores
SELECT id,
       name,
       address,
       city,
       state,
       zip,
       phone,
       latitude,
       longitude,
       timezone,
       google_place_id,
       hours,
       metadata,
       created_at,
       updated_at
FROM store;

-- name: get-store-by-id
SELECT id,
       name,
       address,
       city,
       state,
       zip,
       phone,
       latitude,
       longitude,
       timezone,
       google_place_id,
       hours,
       metadata,
       created_at,
       updated_at
FROM store
WHERE id = :id;

-- name: find-stores-by-location
SELECT id,
       name,
       address,
       city,
       state,
       zip,
       phone,
       latitude,
       longitude,
       timezone,
       google_place_id,
       hours,
       metadata,
       created_at,
       updated_at
FROM store
WHERE (:city IS NULL OR LOWER(city) = LOWER(:city))
  AND (:state IS NULL OR UPPER(state) = UPPER(:state))
  AND (:zip_code IS NULL OR zip = :zip_code)
ORDER BY city, name;
