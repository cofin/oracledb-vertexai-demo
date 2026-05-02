-- SPDX-FileCopyrightText: 2026 Google LLC
-- SPDX-License-Identifier: Apache-2.0

-- name: get-product
SELECT id,
       name,
       description,
       price,
       category,
       sku,
       in_stock,
       metadata,
       embedding,
       created_at,
       updated_at
FROM product;

-- name: list-products
SELECT id,
       name,
       description,
       price,
       category,
       sku,
       in_stock,
       metadata,
       created_at,
       updated_at
FROM product;

-- name: list-products-for-embedding
SELECT id, name, description
FROM product
ORDER BY id;

-- name: vector-search-products
SELECT id,
       name,
       description,
       price,
       1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) AS similarity_score
FROM product
WHERE 1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) > :threshold
ORDER BY similarity_score DESC
FETCH FIRST :limit ROWS ONLY;

-- name: explain-plan-vector-search
EXPLAIN PLAN FOR
SELECT id,
       name,
       description,
       price,
       1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) AS similarity_score
FROM product
WHERE 1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) > :threshold
ORDER BY similarity_score DESC
FETCH FIRST :limit ROWS ONLY;
