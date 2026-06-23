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

-- docs:start-vector-search-sql
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
-- docs:end-vector-search-sql

-- name: vector-search-products-by-store
SELECT p.id,
       p.name,
       p.description,
       p.price,
       s.id AS store_id,
       s.name AS store_name,
       spi.quantity_available,
       spi.stock_status,
       spi.pickup_available,
       1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) AS similarity_score
FROM product p
JOIN store_product_inventory spi ON spi.product_id = p.id
JOIN store s ON s.id = spi.store_id
WHERE spi.store_id = :store_id
  AND 1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) > :threshold
ORDER BY
       CASE spi.stock_status
           WHEN 'IN_STOCK' THEN 1
           WHEN 'LOW_STOCK' THEN 2
           ELSE 3
       END,
       similarity_score DESC
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
