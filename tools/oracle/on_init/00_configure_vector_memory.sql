-- Copyright 2026 Google LLC
-- SPDX-License-Identifier: Apache-2.0

-- Configure Oracle 23ai vector memory pool for HNSW INMEMORY indexes.
--
-- vector_memory_size is a STATIC parameter (SCOPE=SPFILE only), so the pool
-- is not allocated until the next instance restart. This script runs as the
-- first init step on a fresh container (gvenzl/oracle-free executes
-- /container-entrypoint-initdb.d/*.sql in alphabetical order as SYSDBA on the
-- CDB), so we set the SPFILE value and bounce the instance before any
-- subsequent init script runs. After restart the Vector Memory pool is live
-- and downstream init / migrations / HNSW INMEMORY index DDL succeed.
--
-- Oracle 23ai Free Edition rejects sga_max_size / sga_target overrides
-- (ORA-56752 — Free is locked to ~1.5 G SGA + 512 M PGA = 2 G total). The
-- vector pool must therefore fit inside the existing SGA. 512 M is plenty
-- for the demo dataset (~50 products + ~1000 intent exemplars at 3072 dims
-- ≈ 13 MB raw, ~18 MB with HNSW overhead). On Standard / Enterprise /
-- Autonomous you can scale the pool (and SGA) up — see
-- tools/oracle/configure_vector_memory.sql for an example. Bump the pool
-- further if `bulk-embed` reports ORA-51963 (pool exhausted).

ALTER SYSTEM SET vector_memory_size = 512M SCOPE = SPFILE;

SHUTDOWN IMMEDIATE
STARTUP
