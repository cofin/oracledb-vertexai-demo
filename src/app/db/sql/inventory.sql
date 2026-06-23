-- SPDX-FileCopyrightText: 2026 Google LLC
-- SPDX-License-Identifier: Apache-2.0

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
