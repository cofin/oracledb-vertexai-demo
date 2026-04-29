-- Copyright 2026 Google LLC
-- SPDX-License-Identifier: Apache-2.0

-- Verify Oracle 23ai vector memory pool is allocated on every container start.
-- A non-zero "Vector Memory" row in V$SGAINFO confirms HNSW INMEMORY indexes
-- can be built. Zero indicates the SPFILE setting was not applied (e.g. the
-- container was started without on_init running or vector_memory_size was
-- cleared); migrations using ORGANIZATION INMEMORY NEIGHBOR GRAPH will fail
-- with ORA-51962 until this is corrected.

SET SERVEROUTPUT ON

DECLARE
    l_pool_bytes NUMBER := 0;
BEGIN
    SELECT NVL(MAX(BYTES), 0)
      INTO l_pool_bytes
      FROM V$SGAINFO
     WHERE NAME IN ('Vector Memory', 'Vector Memory Area');

    IF l_pool_bytes = 0 THEN
        DBMS_OUTPUT.PUT_LINE('WARNING: vector_memory_size is 0 — HNSW INMEMORY indexes will fail.');
        DBMS_OUTPUT.PUT_LINE('  Run tools/oracle/configure_vector_memory.sql or restart the container.');
    ELSE
        DBMS_OUTPUT.PUT_LINE(
            'Vector Memory pool: ' || ROUND(l_pool_bytes / 1024 / 1024, 2) || ' MB allocated.'
        );
    END IF;
END;
/
