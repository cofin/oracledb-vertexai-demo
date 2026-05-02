-- SPDX-FileCopyrightText: 2026 Google LLC
-- SPDX-License-Identifier: Apache-2.0

-- name: get-cached-response
SELECT id, cache_key, response_data, created_at, expires_at
FROM response_cache
WHERE cache_key = :key
  AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP);

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

-- name: metrics-scatter-points
SELECT similarity_score                    AS similarity_score,
       COALESCE(search_time_ms, 0)         AS total_ms,
       COALESCE(oracle_time_ms, 0)         AS oracle_ms,
       COALESCE(embedding_time_ms, 0)      AS embedding_ms
FROM search_metric
WHERE created_at > :since
  AND similarity_score IS NOT NULL
ORDER BY created_at
FETCH FIRST 80 ROWS ONLY;

-- name: metrics-breakdown
SELECT COALESCE(AVG(embedding_time_ms), 0) AS embedding_ms,
       COALESCE(AVG(oracle_time_ms), 0)    AS oracle_ms,
       COALESCE(AVG(ai_time_ms), 0)        AS ai_ms,
       COALESCE(AVG(intent_time_ms), 0)    AS intent_ms,
       COALESCE(
           AVG(
               GREATEST(
                   COALESCE(search_time_ms, 0)
                   - COALESCE(embedding_time_ms, 0)
                   - COALESCE(oracle_time_ms, 0)
                   - COALESCE(ai_time_ms, 0)
                   - COALESCE(intent_time_ms, 0),
                   0
               )
           ),
           0
       ) AS other_ms
FROM search_metric
WHERE created_at > :since;

-- name: explain-plan-display
SELECT plan_table_output
FROM TABLE(DBMS_XPLAN.DISPLAY(NULL, NULL, 'TYPICAL +PREDICATE +NOTE'));
