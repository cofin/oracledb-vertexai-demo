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
       hours,
       metadata,
       created_at,
       updated_at
FROM store;
