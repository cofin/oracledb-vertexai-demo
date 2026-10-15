-- SPDX-FileCopyrightText: 2026 Google LLC
-- SPDX-License-Identifier: Apache-2.0

-- name: get-ai-session
SELECT
    id,
    user_id,
    app_name,
    state,
    created_at,
    updated_at
FROM agent_session
WHERE id = :session_id AND user_id = :user_id;

-- name: upsert-ai-session
MERGE INTO agent_session dest
USING (
    SELECT
        :session_id AS id,
        :user_id AS user_id,
        :app_name AS app_name,
        :state AS state,
        SYSTIMESTAMP AS updated_at
    FROM dual
) src
ON (dest.id = src.id AND dest.user_id = src.user_id)
WHEN MATCHED THEN
    UPDATE SET
        dest.state = src.state,
        dest.updated_at = src.updated_at
WHEN NOT MATCHED THEN
    INSERT (id, user_id, app_name, state, created_at, updated_at)
    VALUES (src.id, src.user_id, src.app_name, src.state, SYSTIMESTAMP, SYSTIMESTAMP);

-- name: clear-ai-session
DELETE FROM agent_session
WHERE id = :session_id AND user_id = :user_id;

-- name: append-ai-event
INSERT INTO agent_event (
    session_id,
    invocation_id,
    seq,
    turn,
    agent,
    content,
    actions,
    created_at
) VALUES (
    :session_id,
    :invocation_id,
    :seq,
    :turn,
    :agent,
    :content,
    :actions,
    SYSTIMESTAMP
);

-- name: list-ai-events
SELECT
    id,
    session_id,
    invocation_id,
    seq,
    turn,
    agent,
    content,
    actions,
    created_at
FROM agent_event
WHERE session_id = :session_id
ORDER BY seq ASC, id ASC;

-- name: next-ai-event-seq
SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq
FROM agent_event
WHERE session_id = :session_id;
