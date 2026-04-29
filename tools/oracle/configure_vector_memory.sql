-- Standalone DBA script for sizing the Oracle 23ai vector memory pool.
--
-- Use this when you cannot rely on container init (autonomous database,
-- shared dev DB, prod) or you need to bump the pool size without recreating
-- the container. Run as SYSDBA against the CDB.
--
--   sqlplus / as sysdba @tools/oracle/configure_vector_memory.sql
--
-- vector_memory_size is a STATIC parameter — the SPFILE write only takes
-- effect after a database restart. The SHUTDOWN/STARTUP at the bottom of
-- this script handles that; comment those lines out if you cannot bounce
-- the instance from this session.

ALTER SYSTEM SET vector_memory_size = 4G SCOPE = SPFILE;

PROMPT Vector memory pool size set in SPFILE. Restarting instance...

SHUTDOWN IMMEDIATE
STARTUP

PROMPT Verifying allocated pool...

SELECT NAME, ROUND(BYTES / 1024 / 1024 / 1024, 2) AS GB
  FROM V$SGAINFO
 WHERE NAME = 'Vector Memory';
