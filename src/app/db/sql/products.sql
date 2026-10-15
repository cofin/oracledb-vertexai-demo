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

-- name: list-apex-products
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
FROM product
WHERE (:q IS NULL
       OR LOWER(name) LIKE '%' || LOWER(:q) || '%'
       OR LOWER(description) LIKE '%' || LOWER(:q) || '%'
       OR LOWER(sku) = LOWER(:q))
  AND (:category IS NULL OR LOWER(category) = LOWER(:category))
ORDER BY name
OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY;

-- name: count-apex-products
SELECT COUNT(*) AS total
FROM product
WHERE (:q IS NULL
       OR LOWER(name) LIKE '%' || LOWER(:q) || '%'
       OR LOWER(description) LIKE '%' || LOWER(:q) || '%'
       OR LOWER(sku) = LOWER(:q))
  AND (:category IS NULL OR LOWER(category) = LOWER(:category));

-- name: get-vector-readiness
SELECT COUNT(*) AS product_count,
       COALESCE(SUM(CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END), 0) AS embedded_product_count
FROM product;

-- docs:start-vector-search-sql
-- name: vector-search-products
SELECT id,
       name,
       description,
       price,
       1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) AS similarity_score
FROM product
WHERE 1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) > :threshold
ORDER BY VECTOR_DISTANCE(embedding, :query_vector, COSINE)
FETCH APPROX FIRST :limit ROWS ONLY;
-- docs:end-vector-search-sql

-- name: vector-search-products-by-store
WITH candidate_products AS (
    SELECT p.id,
           p.name,
           p.description,
           p.price,
           1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) AS similarity_score
    FROM product p
    WHERE 1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) > :threshold
    ORDER BY VECTOR_DISTANCE(p.embedding, :query_vector, COSINE)
    FETCH APPROX FIRST 50 ROWS ONLY
)
SELECT cp.id,
       cp.name,
       cp.description,
       cp.price,
       s.id AS store_id,
       s.name AS store_name,
       spi.quantity_available,
       spi.stock_status,
       spi.pickup_available,
       cp.similarity_score
FROM candidate_products cp
JOIN store_product_inventory spi ON spi.product_id = cp.id
JOIN store s ON s.id = spi.store_id
WHERE spi.store_id = :store_id
ORDER BY
       CASE spi.stock_status
           WHEN 'IN_STOCK' THEN 1
           WHEN 'LOW_STOCK' THEN 2
           ELSE 3
       END,
       cp.similarity_score DESC
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
ORDER BY VECTOR_DISTANCE(embedding, :query_vector, COSINE)
FETCH APPROX FIRST :limit ROWS ONLY;
