-- SPDX-FileCopyrightText: 2026 Google LLC
-- SPDX-License-Identifier: Apache-2.0

-- name: get-cached-response
SELECT id, cache_key, response_data, created_at, expires_at
FROM response_cache
WHERE cache_key = :key
  AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP);

-- name: upsert-response-cache
MERGE INTO response_cache rc
USING (
    SELECT :cache_key AS cache_key,
           :response_data AS response_data,
           :expires_at AS expires_at
    FROM dual
) src
ON (rc.cache_key = src.cache_key)
WHEN MATCHED THEN
    UPDATE SET rc.response_data = src.response_data,
               rc.expires_at = src.expires_at,
               rc.updated_at = CURRENT_TIMESTAMP
WHEN NOT MATCHED THEN
    INSERT (cache_key, response_data, expires_at)
    VALUES (src.cache_key, src.response_data, src.expires_at);

-- name: get-cached-embedding
SELECT id, text_hash, embedding, model, created_at, last_accessed, hit_count
FROM embedding_cache
WHERE text_hash = :hash
  AND model = :model;

-- name: upsert-embedding-cache
MERGE INTO embedding_cache ec
USING (
    SELECT :text_hash AS text_hash,
           :model AS model
    FROM dual
) src
ON (ec.text_hash = src.text_hash AND ec.model = src.model)
WHEN MATCHED THEN
    UPDATE SET ec.embedding = :embedding,
               ec.last_accessed = CURRENT_TIMESTAMP
WHEN NOT MATCHED THEN
    INSERT (text_hash, embedding, model)
    VALUES (src.text_hash, :embedding, src.model);

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
WHERE created_at > CURRENT_TIMESTAMP - NUMTODSINTERVAL(:window_start_hours, 'HOUR')
  AND created_at <= CURRENT_TIMESTAMP - NUMTODSINTERVAL(:window_end_hours, 'HOUR');

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

-- name: delete-stale-agent-sessions
DELETE FROM agent_session
WHERE updated_at < CURRENT_TIMESTAMP - NUMTODSINTERVAL(:retention_days, 'DAY');
