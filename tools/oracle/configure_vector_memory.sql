-- Copyright 2026 Google LLC
-- SPDX-License-Identifier: Apache-2.0

-- Standalone DBA script for sizing the Oracle 23ai vector memory pool.
--
-- Use this when you cannot rely on container init (autonomous database,
-- shared dev DB, prod) or you need to bump the pool size without recreating
-- the container. Run as SYSDBA against the CDB.
--
--   sqlplus / as sysdba @tools/oracle/configure_vector_memory.sql
--
-- The example below targets a 4 GB vector pool with a 6 GB SGA — appropriate
-- for Oracle Standard / Enterprise / Autonomous, where SGA is unconstrained.
-- DO NOT run these values against Oracle Database Free Edition: Free caps
-- total SGA at 2 GB and emits ORA-56752 if exceeded. For Free, mirror
-- tools/oracle/on_init/00_configure_vector_memory.sql (sga_max_size = 2G,
-- vector_memory_size = 512M).
--
-- vector_memory_size and sga_max_size are STATIC parameters — the SPFILE
-- writes only take effect after a database restart. The SHUTDOWN/STARTUP
-- block at the bottom of this script handles that; comment those lines out
-- if you cannot bounce the instance from this session.

ALTER SYSTEM SET sga_max_size = 6G SCOPE = SPFILE;
ALTER SYSTEM SET sga_target = 6G SCOPE = SPFILE;
ALTER SYSTEM SET vector_memory_size = 4G SCOPE = SPFILE;

PROMPT Vector memory pool size set in SPFILE. Restarting instance...

SHUTDOWN IMMEDIATE
STARTUP

PROMPT Verifying allocated pool...

SELECT NAME, ROUND(BYTES / 1024 / 1024, 2) AS MB
  FROM V$SGAINFO
 WHERE NAME IN ('Vector Memory', 'Vector Memory Area', 'Maximum SGA Size');
