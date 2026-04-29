-- name: get-cached-response
SELECT id, cache_key, response_data, created_at, expires_at
FROM response_cache
WHERE cache_key = :key;

-- name: get-cached-embedding
SELECT embedding
FROM embedding_cache
WHERE text_hash = :hash
  AND model = :model;

-- name: get-cache-stats
SELECT COALESCE(SUM(hit_count), 0) AS total_hits,
       COALESCE(COUNT(*), 0)       AS total_entries
FROM embedding_cache;

-- name: get-performance-stats
SELECT COALESCE(COUNT(*), 0)              AS total_searches,
       COALESCE(AVG(search_time_ms), 0)   AS avg_search_time_ms,
       COALESCE(AVG(oracle_time_ms), 0)   AS avg_oracle_time_ms,
       COALESCE(AVG(similarity_score), 0) AS avg_similarity_score
FROM search_metric
WHERE created_at > :since;

-- name: metrics-time-series
SELECT TO_CHAR(TRUNC(created_at, 'MI'), 'HH24:MI') AS bucket,
       COALESCE(AVG(search_time_ms), 0)            AS total_ms,
       COALESCE(AVG(oracle_time_ms), 0)            AS oracle_ms,
       COALESCE(AVG(embedding_time_ms), 0)         AS embedding_ms
FROM search_metric
WHERE created_at > :since
GROUP BY TRUNC(created_at, 'MI')
ORDER BY TRUNC(created_at, 'MI');

-- name: explain-plan-display
SELECT plan_table_output FROM TABLE(DBMS_XPLAN.DISPLAY());

-- name: vector-search-exemplars
SELECT intent,
       phrase,
       1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) AS similarity,
       confidence_threshold
FROM intent_exemplar
WHERE embedding IS NOT NULL
ORDER BY similarity DESC
FETCH FIRST :limit ROWS ONLY;

-- name: list-exemplars
SELECT id,
       intent,
       phrase,
       confidence_threshold,
       usage_count,
       created_at,
       updated_at
FROM intent_exemplar;
