-- Configure Oracle 23ai vector memory pool for HNSW INMEMORY indexes.
--
-- vector_memory_size is a STATIC parameter (SCOPE=SPFILE only) so the pool
-- is not allocated until the next instance restart. This script runs as the
-- first init step on a fresh container (gvenzl/oracle-free executes
-- /container-entrypoint-initdb.d/*.sql in alphabetical order as SYSDBA on the
-- CDB), so we set the SPFILE value and then bounce the instance before any
-- subsequent init script runs. After restart the Vector Memory pool is live
-- and downstream init / migrations / HNSW INMEMORY index DDL succeed.
--
-- 4G is the project floor for the demo dataset (~50 products + ~1000 intent
-- exemplars at 3072 dims); bump if `bulk-embed` reports ORA-51963.

ALTER SYSTEM SET vector_memory_size = 4G SCOPE = SPFILE;

SHUTDOWN IMMEDIATE
STARTUP
