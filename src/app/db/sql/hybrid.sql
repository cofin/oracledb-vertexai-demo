-- SPDX-FileCopyrightText: 2026 Google LLC
-- SPDX-License-Identifier: Apache-2.0

-- docs:start-hybrid-rrf-sql
-- name: hybrid-search-turn
WITH
route_lex AS (
    SELECT r.id,
           r.route_label,
           r.title,
           SCORE(1) AS lexical_score,
           ROW_NUMBER() OVER (ORDER BY SCORE(1) DESC, r.id) AS lexical_rank
    FROM chat_route r
    WHERE :has_text_query = 1
      AND CONTAINS(r.exemplar_text, :text_query, 1) > 0
    FETCH FIRST :limit ROWS ONLY
),
route_vec_top AS (
    SELECT r.id,
           r.route_label,
           r.title,
           1 - VECTOR_DISTANCE(r.embedding, :query_vector, COSINE) AS vector_similarity
    FROM chat_route r
    WHERE r.embedding IS NOT NULL
    ORDER BY VECTOR_DISTANCE(r.embedding, :query_vector, COSINE)
    FETCH APPROX FIRST :limit ROWS ONLY
),
route_vec AS (
    SELECT rv.id,
           rv.route_label,
           rv.title,
           rv.vector_similarity,
           ROWNUM AS vector_rank
    FROM route_vec_top rv
),
route_fused AS (
    SELECT COALESCE(l.id, v.id) AS entity_id,
           COALESCE(l.route_label, v.route_label) AS route_label,
           COALESCE(l.title, v.title) AS name,
           COALESCE(l.lexical_score, 0) AS lexical_score,
           COALESCE(v.vector_similarity, 0) AS vector_similarity,
           l.lexical_rank,
           v.vector_rank,
           (CASE WHEN l.lexical_rank IS NOT NULL THEN 1.0 / (:rrf_k + l.lexical_rank) ELSE 0 END) +
           (CASE WHEN v.vector_rank IS NOT NULL THEN 1.0 / (:rrf_k + v.vector_rank) ELSE 0 END) AS rrf_score
    FROM route_lex l
    FULL OUTER JOIN route_vec v ON l.id = v.id
),
route_rrf AS (
    SELECT 'route' AS entity_type,
           MAX(entity_id) AS entity_id,
           route_label,
           route_label AS name,
           MAX(name) AS description,
           CAST(NULL AS VARCHAR2(100)) AS category,
           CAST(NULL AS NUMBER(10, 2)) AS price,
           CAST(NULL AS NUMBER(1)) AS in_stock,
           CAST(NULL AS VARCHAR2(100)) AS city,
           CAST(NULL AS VARCHAR2(50)) AS state,
           CAST(NULL AS VARCHAR2(500)) AS address,
           MAX(lexical_score) AS lexical_score,
           MAX(vector_similarity) AS vector_similarity,
           MIN(lexical_rank) AS lexical_rank,
           MIN(vector_rank) AS vector_rank,
           MAX(rrf_score) AS rrf_score
    FROM route_fused
    GROUP BY route_label
),
prod_lex AS (
    SELECT p.id,
           p.name,
           p.description,
           p.category,
           p.price,
           CASE WHEN p.in_stock THEN 1 ELSE 0 END AS in_stock,
           SCORE(2) AS lexical_score,
           ROW_NUMBER() OVER (ORDER BY SCORE(2) DESC, p.id) AS lexical_rank
    FROM product p
    WHERE :has_text_query = 1
      AND CONTAINS(p.description, :text_query, 2) > 0
    FETCH FIRST :limit ROWS ONLY
),
prod_vec_top AS (
    SELECT p.id,
           p.name,
           p.description,
           p.category,
           p.price,
           CASE WHEN p.in_stock THEN 1 ELSE 0 END AS in_stock,
           1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) AS vector_similarity
    FROM product p
    WHERE p.embedding IS NOT NULL
    ORDER BY VECTOR_DISTANCE(p.embedding, :query_vector, COSINE)
    FETCH APPROX FIRST :limit ROWS ONLY
),
prod_vec AS (
    SELECT pv.id,
           pv.name,
           pv.description,
           pv.category,
           pv.price,
           pv.in_stock,
           pv.vector_similarity,
           ROWNUM AS vector_rank
    FROM prod_vec_top pv
),
prod_rrf AS (
    SELECT 'product' AS entity_type,
           COALESCE(l.id, v.id) AS entity_id,
           CAST(NULL AS VARCHAR2(64)) AS route_label,
           COALESCE(l.name, v.name) AS name,
           COALESCE(l.description, v.description) AS description,
           COALESCE(l.category, v.category) AS category,
           COALESCE(l.price, v.price) AS price,
           COALESCE(l.in_stock, v.in_stock) AS in_stock,
           CAST(NULL AS VARCHAR2(100)) AS city,
           CAST(NULL AS VARCHAR2(50)) AS state,
           CAST(NULL AS VARCHAR2(500)) AS address,
           COALESCE(l.lexical_score, 0) AS lexical_score,
           COALESCE(v.vector_similarity, 0) AS vector_similarity,
           l.lexical_rank,
           v.vector_rank,
           (CASE WHEN l.lexical_rank IS NOT NULL THEN 1.0 / (:rrf_k + l.lexical_rank) ELSE 0 END) +
           (CASE WHEN v.vector_rank IS NOT NULL THEN 1.0 / (:rrf_k + v.vector_rank) ELSE 0 END) AS rrf_score
    FROM prod_lex l
    FULL OUTER JOIN prod_vec v ON l.id = v.id
    ORDER BY rrf_score DESC
    FETCH FIRST :limit ROWS ONLY
),
store_lex AS (
    SELECT s.id,
           s.name,
           s.address,
           s.city,
           s.state,
           SCORE(3) AS lexical_score,
           ROW_NUMBER() OVER (ORDER BY SCORE(3) DESC, s.id) AS lexical_rank
    FROM store s
    WHERE :has_text_query = 1
      AND CONTAINS(s.address, :text_query, 3) > 0
    FETCH FIRST :limit ROWS ONLY
),
store_rrf AS (
    SELECT 'store' AS entity_type,
           s.id AS entity_id,
           CAST(NULL AS VARCHAR2(64)) AS route_label,
           s.name,
           s.address AS description,
           CAST(NULL AS VARCHAR2(100)) AS category,
           CAST(NULL AS NUMBER(10, 2)) AS price,
           CAST(NULL AS NUMBER(1)) AS in_stock,
           s.city,
           s.state,
           s.address,
           s.lexical_score,
           CAST(NULL AS NUMBER) AS vector_similarity,
           s.lexical_rank,
           CAST(NULL AS NUMBER) AS vector_rank,
           1.0 / (:rrf_k + s.lexical_rank) AS rrf_score
    FROM store_lex s
)
SELECT * FROM route_rrf
UNION ALL
SELECT * FROM prod_rrf
UNION ALL
SELECT * FROM store_rrf
ORDER BY entity_type, rrf_score DESC;
-- docs:end-hybrid-rrf-sql

-- name: hybrid-term-hits
SELECT jt.term AS term,
       (SELECT COUNT(*)
        FROM product p
        WHERE CONTAINS(p.description, '{' || jt.term || '}') > 0) AS hit_count
FROM JSON_TABLE(
    :terms_json,
    '$[*]' COLUMNS (term VARCHAR2(128) PATH '$')
) jt;

-- name: hybrid-search-products
WITH
prod_lex AS (
    SELECT p.id,
           p.name,
           p.description,
           p.price,
           1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) AS similarity_score,
           SCORE(1) AS lexical_score,
           ROW_NUMBER() OVER (ORDER BY SCORE(1) DESC, p.id) AS lexical_rank
    FROM product p
    WHERE :has_text_query = 1
      AND CONTAINS(p.description, :text_query, 1) > 0
    FETCH FIRST :limit ROWS ONLY
),
prod_vec_top AS (
    SELECT p.id,
           p.name,
           p.description,
           p.price,
           1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) AS similarity_score
    FROM product p
    WHERE 1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) > :threshold
    ORDER BY VECTOR_DISTANCE(p.embedding, :query_vector, COSINE)
    FETCH APPROX FIRST :limit ROWS ONLY
),
prod_vec AS (
    SELECT v.id,
           v.name,
           v.description,
           v.price,
           v.similarity_score,
           ROWNUM AS vector_rank
    FROM prod_vec_top v
)
SELECT COALESCE(l.id, v.id) AS id,
       COALESCE(l.name, v.name) AS name,
       COALESCE(l.description, v.description) AS description,
       COALESCE(l.price, v.price) AS price,
       COALESCE(v.similarity_score, l.similarity_score, 0) AS similarity_score,
       COALESCE(l.lexical_score, 0) AS lexical_score,
       l.lexical_rank,
       v.vector_rank,
       (CASE WHEN l.lexical_rank IS NOT NULL THEN 1.0 / (:rrf_k + l.lexical_rank) ELSE 0 END) +
       (CASE WHEN v.vector_rank IS NOT NULL THEN 1.0 / (:rrf_k + v.vector_rank) ELSE 0 END) AS rrf_score
FROM prod_lex l
FULL OUTER JOIN prod_vec v ON l.id = v.id
ORDER BY rrf_score DESC, similarity_score DESC
FETCH FIRST :limit ROWS ONLY;

-- name: explain-plan-hybrid-search
EXPLAIN PLAN FOR
WITH
prod_lex AS (
    SELECT p.id,
           p.name,
           p.description,
           p.price,
           1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) AS similarity_score,
           SCORE(1) AS lexical_score,
           ROW_NUMBER() OVER (ORDER BY SCORE(1) DESC, p.id) AS lexical_rank
    FROM product p
    WHERE :has_text_query = 1
      AND CONTAINS(p.description, :text_query, 1) > 0
    FETCH FIRST :limit ROWS ONLY
),
prod_vec_top AS (
    SELECT p.id,
           p.name,
           p.description,
           p.price,
           1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) AS similarity_score
    FROM product p
    WHERE 1 - VECTOR_DISTANCE(p.embedding, :query_vector, COSINE) > :threshold
    ORDER BY VECTOR_DISTANCE(p.embedding, :query_vector, COSINE)
    FETCH APPROX FIRST :limit ROWS ONLY
),
prod_vec AS (
    SELECT v.id,
           v.name,
           v.description,
           v.price,
           v.similarity_score,
           ROWNUM AS vector_rank
    FROM prod_vec_top v
)
SELECT COALESCE(l.id, v.id) AS id,
       COALESCE(l.name, v.name) AS name,
       COALESCE(l.description, v.description) AS description,
       COALESCE(l.price, v.price) AS price,
       COALESCE(v.similarity_score, l.similarity_score, 0) AS similarity_score,
       COALESCE(l.lexical_score, 0) AS lexical_score,
       l.lexical_rank,
       v.vector_rank,
       (CASE WHEN l.lexical_rank IS NOT NULL THEN 1.0 / (:rrf_k + l.lexical_rank) ELSE 0 END) +
       (CASE WHEN v.vector_rank IS NOT NULL THEN 1.0 / (:rrf_k + v.vector_rank) ELSE 0 END) AS rrf_score
FROM prod_lex l
FULL OUTER JOIN prod_vec v ON l.id = v.id
ORDER BY rrf_score DESC, similarity_score DESC
FETCH FIRST :limit ROWS ONLY;
