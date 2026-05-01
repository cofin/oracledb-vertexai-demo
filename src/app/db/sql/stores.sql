-- Copyright 2026 Google LLC
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

-- name: find-stores-by-city
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
WHERE LOWER(city) = LOWER(:city)
ORDER BY name;

-- name: find-stores-by-state
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
WHERE UPPER(state) = UPPER(:state)
ORDER BY city, name;

-- name: find-stores-by-zip
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
WHERE zip = :zip_code
ORDER BY name;

-- name: rank-stores-by-distance
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
       updated_at,
       (POWER(latitude - :latitude, 2) + POWER(longitude - :longitude, 2)) AS distance_score
FROM store
WHERE latitude IS NOT NULL
  AND longitude IS NOT NULL
ORDER BY distance_score
FETCH FIRST :limit ROWS ONLY;
