-- SPDX-FileCopyrightText: 2026 Google LLC
-- SPDX-License-Identifier: Apache-2.0

-- name: list-inventory-summary
SELECT s.id AS store_id,
       s.name AS store_name,
       COUNT(spi.id) AS product_count,
       COALESCE(SUM(CASE WHEN spi.stock_status = 'IN_STOCK' THEN 1 ELSE 0 END), 0) AS in_stock_count,
       COALESCE(SUM(CASE WHEN spi.stock_status = 'LOW_STOCK' THEN 1 ELSE 0 END), 0) AS low_stock_count,
       COALESCE(SUM(CASE WHEN spi.stock_status = 'OUT_OF_STOCK' THEN 1 ELSE 0 END), 0) AS out_of_stock_count,
       COALESCE(SUM(spi.quantity_available), 0) AS total_quantity
FROM store s
LEFT JOIN store_product_inventory spi ON spi.store_id = s.id
GROUP BY s.id, s.name
ORDER BY s.name;

-- name: list-store-inventory
SELECT spi.id,
       spi.store_id,
       spi.product_id,
       spi.quantity_available,
       spi.stock_status,
       spi.pickup_available,
       spi.updated_at,
       s.name AS store_name,
       s.address AS store_address,
       s.city AS store_city,
       s.state AS store_state,
       s.zip AS store_zip,
       s.latitude,
       s.longitude,
       s.timezone,
       s.google_place_id,
       p.name AS product_name,
       p.description AS product_description,
       p.category AS product_category,
       p.sku AS product_sku,
       p.price AS product_price
FROM store_product_inventory spi
JOIN store s ON s.id = spi.store_id
JOIN product p ON p.id = spi.product_id
WHERE spi.store_id = :store_id
ORDER BY
       CASE spi.stock_status
           WHEN 'IN_STOCK' THEN 1
           WHEN 'LOW_STOCK' THEN 2
           ELSE 3
       END,
       p.name;

-- name: search-store-inventory
SELECT spi.id,
       spi.store_id,
       spi.product_id,
       spi.quantity_available,
       spi.stock_status,
       spi.pickup_available,
       spi.updated_at,
       s.name AS store_name,
       s.address AS store_address,
       s.city AS store_city,
       s.state AS store_state,
       s.zip AS store_zip,
       s.latitude,
       s.longitude,
       s.timezone,
       s.google_place_id,
       p.name AS product_name,
       p.description AS product_description,
       p.category AS product_category,
       p.sku AS product_sku,
       p.price AS product_price
FROM store_product_inventory spi
JOIN store s ON s.id = spi.store_id
JOIN product p ON p.id = spi.product_id
WHERE spi.store_id = :store_id
  AND (LOWER(p.name) LIKE '%' || LOWER(:q) || '%'
       OR LOWER(p.category) = LOWER(:q)
       OR LOWER(p.sku) = LOWER(:q)
       OR TO_CHAR(p.id) = :q)
ORDER BY
       CASE spi.stock_status
           WHEN 'IN_STOCK' THEN 1
           WHEN 'LOW_STOCK' THEN 2
           ELSE 3
       END,
       p.name
FETCH FIRST :limit ROWS ONLY;

-- name: find-stores-with-product-inventory
SELECT spi.id,
       spi.store_id,
       spi.product_id,
       spi.quantity_available,
       spi.stock_status,
       spi.pickup_available,
       spi.updated_at,
       s.name AS store_name,
       s.address AS store_address,
       s.city AS store_city,
       s.state AS store_state,
       s.zip AS store_zip,
       s.latitude,
       s.longitude,
       s.timezone,
       s.google_place_id,
       p.name AS product_name,
       p.category AS product_category,
       p.sku AS product_sku,
       p.price AS product_price
FROM store_product_inventory spi
JOIN store s ON s.id = spi.store_id
JOIN product p ON p.id = spi.product_id
WHERE spi.product_id = :product_id
ORDER BY
       CASE spi.stock_status
           WHEN 'IN_STOCK' THEN 1
           WHEN 'LOW_STOCK' THEN 2
           ELSE 3
       END,
       s.city,
       s.name;

-- name: find-product-availability-by-query
SELECT spi.id,
       spi.store_id,
       spi.product_id,
       spi.quantity_available,
       spi.stock_status,
       spi.pickup_available,
       spi.updated_at,
       s.name AS store_name,
       s.address AS store_address,
       s.city AS store_city,
       s.state AS store_state,
       s.zip AS store_zip,
       s.latitude,
       s.longitude,
       s.timezone,
       s.google_place_id,
       p.name AS product_name,
       p.category AS product_category,
       p.sku AS product_sku,
       p.price AS product_price
FROM store_product_inventory spi
JOIN store s ON s.id = spi.store_id
JOIN product p ON p.id = spi.product_id
WHERE LOWER(p.name) = LOWER(:product_query)
   OR LOWER(p.sku) = LOWER(:product_query)
   OR TO_CHAR(p.id) = :product_query
ORDER BY
       CASE spi.stock_status
           WHEN 'IN_STOCK' THEN 1
           WHEN 'LOW_STOCK' THEN 2
           ELSE 3
       END,
       s.city,
       s.name;
