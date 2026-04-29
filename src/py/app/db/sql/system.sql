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
SELECT SUM(hit_count) AS total_hits,
       COUNT(*)       AS total_entries
FROM embedding_cache;

-- name: get-performance-stats
SELECT COUNT(*)              AS total_searches,
       AVG(search_time_ms)   AS avg_search_time_ms,
       AVG(oracle_time_ms)   AS avg_oracle_time_ms,
       AVG(similarity_score) AS avg_similarity_score
FROM search_metric
WHERE created_at > :since;

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
SELECT id, intent, phrase
FROM intent_exemplar
ORDER BY id;
