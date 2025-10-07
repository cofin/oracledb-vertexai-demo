# Oracle Database Performance Optimization Guide

Comprehensive guide to optimizing Oracle Database 23ai performance for vector search, JSON operations, and high-throughput applications.

## Table of Contents

- [Overview](#overview)
- [Quick Reference](#quick-reference)
- [Vector Search Performance](#vector-search-performance)
- [Connection Pooling](#connection-pooling)
- [Query Optimization](#query-optimization)
- [Memory Management](#memory-management)
- [Index Tuning](#index-tuning)
- [Statistics and Monitoring](#statistics-and-monitoring)
- [Python Driver Optimization](#python-driver-optimization)
- [Troubleshooting Performance](#troubleshooting-performance)

## Overview

Oracle Database 23ai provides specialized features for optimizing vector search and JSON operations:

**Key Performance Features**:
- **SPATIAL_VECTOR_ACCELERATION**: GPU/SIMD acceleration for vector operations
- **INMEMORY_DEEP_VECTORIZATION**: In-Memory column store with SIMD
- **INMEMORY_OPTIMIZED_ARITHMETIC**: Hardware acceleration for vector calculations
- **OPTIMIZER_INMEMORY_AWARE**: Cost-based optimizer for In-Memory queries
- **Vector Indexes**: HNSW and IVFFlat for approximate nearest neighbor search
- **Connection Pooling**: Efficient connection reuse with python-oracledb

**Performance Goals for This Application**:
- Vector similarity search: <50ms (1000 products)
- JSON query with filtering: <20ms
- Embedding cache hit rate: >80%
- Connection pool utilization: 60-80%
- Query throughput: >100 queries/second

## Quick Reference

| Parameter/Feature | Setting | Purpose |
|-------------------|---------|---------|
| SPATIAL_VECTOR_ACCELERATION | TRUE | Enable vector acceleration |
| INMEMORY_DEEP_VECTORIZATION | TRUE | SIMD for vector operations |
| INMEMORY_OPTIMIZED_ARITHMETIC | ENABLE | Hardware acceleration |
| OPTIMIZER_INMEMORY_AWARE | TRUE | In-Memory query optimization |
| Connection pool min | 2 | Minimum idle connections |
| Connection pool max | 10 | Maximum total connections |
| HNSW index (m) | 16 | Connections per layer |
| HNSW index (ef_construction) | 64 | Build-time candidate list |
| IVFFlat index (lists) | sqrt(rows) | Number of partitions |
| PGA_AGGREGATE_TARGET | 1-2GB | Per-session memory |
| SGA_TARGET | 4-8GB | Shared memory |

## Vector Search Performance

### SPATIAL_VECTOR_ACCELERATION

Enable GPU or SIMD acceleration for vector distance calculations:

```sql
-- System-level setting (requires SYSDBA)
ALTER SYSTEM SET SPATIAL_VECTOR_ACCELERATION = TRUE SCOPE=BOTH;

-- Session-level setting
ALTER SESSION SET SPATIAL_VECTOR_ACCELERATION = TRUE;

-- Check current setting
SELECT name, value
FROM v$parameter
WHERE name = 'spatial_vector_acceleration';
```

**Performance Impact**:
- **2-4x faster** vector distance calculations
- GPU acceleration on compatible hardware
- SIMD (AVX2/AVX-512) on CPU fallback
- Automatic for VECTOR_DISTANCE function

**Requirements**:
- Oracle 23ai (23.4+)
- Compatible GPU (optional, for GPU acceleration)
- Modern CPU with AVX2+ (for SIMD acceleration)

### INMEMORY_DEEP_VECTORIZATION

Optimize In-Memory column store for vector operations:

```sql
-- Enable In-Memory Deep Vectorization
ALTER SYSTEM SET INMEMORY_DEEP_VECTORIZATION = TRUE SCOPE=BOTH;

-- Enable In-Memory for products table
ALTER TABLE products INMEMORY;

-- Verify In-Memory status
SELECT
    table_name,
    inmemory,
    inmemory_priority,
    inmemory_compression
FROM user_tables
WHERE table_name = 'PRODUCTS';

-- Check In-Memory population
SELECT
    segment_name,
    populate_status,
    bytes_not_populated
FROM v$im_segments
WHERE segment_name = 'PRODUCTS';
```

**Performance Impact**:
- **3-5x faster** queries on In-Memory data
- SIMD vectorization for batch operations
- Reduced I/O for frequently accessed data
- Automatic compression

**Best Practices**:
- Use for hot data (frequently queried)
- Monitor memory usage (`v$inmemory_area`)
- Consider priority (CRITICAL, HIGH, MEDIUM, LOW)
- Combine with INMEMORY_OPTIMIZED_ARITHMETIC

### INMEMORY_OPTIMIZED_ARITHMETIC

Hardware-accelerated arithmetic for vector calculations:

```sql
-- Enable optimized arithmetic
ALTER SYSTEM SET INMEMORY_OPTIMIZED_ARITHMETIC = ENABLE SCOPE=BOTH;

-- Check setting
SHOW PARAMETER inmemory_optimized_arithmetic;
```

**Performance Impact**:
- Hardware acceleration for vector math
- Faster aggregations and calculations
- Works with INMEMORY_DEEP_VECTORIZATION
- Automatic for NUMBER and VECTOR types

### Vector Index Selection

Choose the right index type for your workload:

**HNSW Index** (Hierarchical Navigable Small World):
```sql
CREATE INDEX idx_product_embedding_hnsw
ON products (embedding)
INDEXTYPE IS HNSW
PARAMETERS ('
    DISTANCE COSINE,
    M 16,
    EF_CONSTRUCTION 64
');
```

**Characteristics**:
- Best for: Read-heavy workloads, high recall requirements
- Build time: Slower (minutes for 100K vectors)
- Query time: Very fast (<10ms for 1M vectors)
- Memory: Higher (M * dimensions * 4 bytes per vector)
- Updates: Slower (rebuilds graph structure)

**Configuration Guidelines**:
- **M**: 8-64, higher = better recall, more memory
  - Small datasets (<10K): M=8-16
  - Medium datasets (10K-100K): M=16-32
  - Large datasets (>100K): M=32-64
- **EF_CONSTRUCTION**: 32-200, higher = better index quality
  - Quick builds: 32-64
  - Balanced: 64-128
  - High quality: 128-200

**IVFFlat Index** (Inverted File with Flat compression):
```sql
CREATE INDEX idx_product_embedding_ivfflat
ON products (embedding)
INDEXTYPE IS IVFFLAT
PARAMETERS ('
    DISTANCE COSINE,
    LISTS 100
');
```

**Characteristics**:
- Best for: Balanced read/write, frequent updates
- Build time: Faster (seconds for 100K vectors)
- Query time: Fast (<20ms for 1M vectors)
- Memory: Lower (centroid storage)
- Updates: Faster (partition-based)

**Configuration Guidelines**:
- **LISTS**: sqrt(num_rows) for balanced performance
  - 1K rows: LISTS=32
  - 10K rows: LISTS=100
  - 100K rows: LISTS=316
  - 1M rows: LISTS=1000

**Query-time Parameters**:
```sql
-- IVFFlat: Number of partitions to search
ALTER SESSION SET IVFFLAT_PROBES = 10;  -- Default: 1, Higher = better recall

-- HNSW: Search candidate list size
ALTER SESSION SET HNSW_EF_SEARCH = 100;  -- Default: 40, Higher = better recall
```

### Monitoring Vector Performance

```sql
-- Query execution plan
EXPLAIN PLAN FOR
SELECT
    id,
    name,
    1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) as similarity
FROM products
WHERE 1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) >= 0.7
ORDER BY VECTOR_DISTANCE(embedding, :query_vector, COSINE)
FETCH FIRST 5 ROWS ONLY;

SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);

-- Check for index usage (should see "INDEX RANGE SCAN")

-- Index statistics
SELECT
    index_name,
    num_rows,
    distinct_keys,
    leaf_blocks,
    status
FROM user_indexes
WHERE table_name = 'PRODUCTS';

-- Index usage tracking
SELECT
    index_name,
    table_name,
    used,
    start_tracking
FROM v$index_usage_info
WHERE table_name = 'PRODUCTS';
```

## Connection Pooling

### python-oracledb Pool Configuration

Optimal connection pooling is critical for performance:

```python
import oracledb

# Create connection pool
pool = oracledb.create_pool(
    user="product_user",
    password="password",
    dsn="localhost:1521/FREEPDB1",

    # Pool sizing
    min=2,              # Minimum connections (keep warm)
    max=10,             # Maximum connections
    increment=1,        # Connections to add when exhausted

    # Timeouts
    getmode=oracledb.POOL_GETMODE_WAIT,
    wait_timeout=30000,  # Wait 30s for connection (milliseconds)
    timeout=3600,        # Idle connection timeout (seconds)
    max_lifetime_session=3600,  # Recycle after 1 hour

    # Session configuration
    stmtcachesize=20,    # Statement cache per connection
    threaded=True        # Thread-safe pool
)

# Get connection from pool
connection = pool.acquire()

# Always release back to pool
try:
    cursor = connection.cursor()
    cursor.execute("SELECT ...")
finally:
    connection.close()  # Returns to pool, doesn't close
```

**Pool Sizing Guidelines**:

For **web applications** (this application):
- `min = 2`: Keep 2 connections warm for instant availability
- `max = CPUs * 2-4`: For 2 CPUs, max=10 is reasonable
- `increment = 1`: Add connections gradually
- `wait_timeout = 30000`: Fail requests if pool exhausted for 30s

For **batch processing**:
- `min = 1`: Minimize idle connections
- `max = CPUs * 1-2`: Fewer concurrent connections
- `increment = 2`: Add multiple connections when needed

For **high-concurrency APIs**:
- `min = 5-10`: More warm connections
- `max = CPUs * 4-8`: Higher concurrency
- `wait_timeout = 10000`: Fail fast (10s)

### Monitoring Connection Pools

```python
# Pool statistics
print(f"Pool opened: {pool.opened}")
print(f"Pool busy: {pool.busy}")
print(f"Pool max: {pool.max}")
print(f"Pool min: {pool.min}")
print(f"Pool increment: {pool.increment}")
print(f"Pool timeout: {pool.timeout}")

# Monitor utilization
utilization = (pool.busy / pool.opened) * 100 if pool.opened > 0 else 0
print(f"Pool utilization: {utilization:.1f}%")

# Ideal: 60-80% utilization
# <50%: Pool may be oversized
# >90%: Pool may be undersized (increase max)
```

### Database Session Configuration

```sql
-- Check active sessions
SELECT
    username,
    machine,
    program,
    status,
    COUNT(*) as session_count
FROM v$session
WHERE username IS NOT NULL
GROUP BY username, machine, program, status;

-- Connection limits
SELECT
    resource_name,
    current_utilization,
    max_utilization,
    limit_value
FROM v$resource_limit
WHERE resource_name IN ('sessions', 'processes');

-- Session memory usage
SELECT
    s.username,
    s.sid,
    s.serial#,
    ROUND(p.pga_used_mem / 1024 / 1024, 2) as pga_mb,
    ROUND(p.pga_alloc_mem / 1024 / 1024, 2) as pga_alloc_mb
FROM v$session s
JOIN v$process p ON s.paddr = p.addr
WHERE s.username = 'PRODUCT_USER'
ORDER BY p.pga_used_mem DESC;
```

## Query Optimization

### Bind Variables

Always use bind variables for parameter safety and performance:

```python
# GOOD - Uses bind variables (shared cursor)
cursor.execute(
    """
    SELECT id, name, price
    FROM products
    WHERE category = :category
        AND JSON_VALUE(metadata, '$.origin') = :origin
    """,
    category="coffee",
    origin="Ethiopia"
)

# BAD - Literal values (hard parse every time, SQL injection risk)
cursor.execute(
    f"""
    SELECT id, name, price
    FROM products
    WHERE category = 'coffee'
        AND JSON_VALUE(metadata, '$.origin') = 'Ethiopia'
    """
)
```

**Performance Impact**:
- **Shared cursors**: Reuse execution plans
- **Soft parse**: 10-100x faster than hard parse
- **Reduced CPU**: No SQL parsing overhead
- **Security**: Prevents SQL injection

### Fetching Strategies

Choose the right fetch strategy:

```python
# Fetch all rows (small result sets <1000 rows)
cursor.execute("SELECT * FROM products WHERE category = :cat", cat="coffee")
rows = cursor.fetchall()

# Fetch in batches (large result sets)
cursor.execute("SELECT * FROM products")
cursor.arraysize = 100  # Fetch 100 rows per round trip
while True:
    rows = cursor.fetchmany()
    if not rows:
        break
    process_rows(rows)

# Fetch one row at a time (streaming, low memory)
cursor.execute("SELECT * FROM products")
for row in cursor:
    process_row(row)
```

**Array Size Guidelines**:
- Default: 100 rows
- Small rows (<50 columns): 500-1000
- Large rows (CLOB, VECTOR): 50-100
- Network latency: Increase for remote databases

### Statement Caching

Reuse prepared statements:

```python
# Configure statement cache size (per connection)
connection = pool.acquire()
connection.stmtcachesize = 20  # Cache 20 prepared statements

# Statements with same SQL text reuse cached plan
for product_id in product_ids:
    cursor.execute(
        "SELECT * FROM products WHERE id = :id",
        id=product_id
    )
    # Second+ iterations reuse cached statement

# Check statement cache statistics
cursor.execute("""
    SELECT
        name,
        value
    FROM v$mystat m
    JOIN v$statname n ON m.statistic# = n.statistic#
    WHERE n.name LIKE 'parse count%'
""")
```

### Explain Plan Analysis

Analyze query execution plans:

```sql
-- Generate explain plan
EXPLAIN PLAN FOR
SELECT
    id,
    name,
    JSON_VALUE(metadata, '$.origin') as origin
FROM products
WHERE JSON_VALUE(metadata, '$.origin') = 'Ethiopia'
  AND in_stock = true;

-- Display plan
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY(format => 'BASIC'));

-- Detailed plan with costs
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY(format => 'ALL'));

-- Look for:
-- ✅ "INDEX RANGE SCAN" or "INDEX FAST FULL SCAN"
-- ❌ "TABLE ACCESS FULL" (unless expected for small tables)
-- ✅ Low cost values (<100 for simple queries)
-- ❌ High cost values (>1000 suggests missing indexes)
```

## Memory Management

### PGA (Program Global Area)

Configure per-session memory:

```sql
-- Set PGA aggregate target (all sessions combined)
ALTER SYSTEM SET PGA_AGGREGATE_TARGET = 2G SCOPE=BOTH;

-- Automatic PGA memory management
ALTER SYSTEM SET WORKAREA_SIZE_POLICY = AUTO SCOPE=BOTH;

-- Check PGA usage
SELECT
    name,
    value / 1024 / 1024 as value_mb
FROM v$pgastat
WHERE name IN (
    'aggregate PGA target parameter',
    'aggregate PGA auto target',
    'total PGA inuse',
    'total PGA allocated'
);

-- Per-session PGA
SELECT
    s.username,
    s.sid,
    p.pga_used_mem / 1024 / 1024 as pga_used_mb,
    p.pga_alloc_mem / 1024 / 1024 as pga_alloc_mb,
    p.pga_max_mem / 1024 / 1024 as pga_max_mb
FROM v$session s
JOIN v$process p ON s.paddr = p.addr
WHERE s.username IS NOT NULL
ORDER BY p.pga_used_mem DESC;
```

**Guidelines**:
- **Small databases** (<10GB): 1-2GB PGA
- **Medium databases** (10-100GB): 2-4GB PGA
- **Large databases** (>100GB): 4-8GB+ PGA
- Formula: `PGA = Total RAM * 0.2` (20% of RAM)

### SGA (System Global Area)

Configure shared memory:

```sql
-- Set SGA target (automatic memory management)
ALTER SYSTEM SET SGA_TARGET = 4G SCOPE=BOTH;
ALTER SYSTEM SET SGA_MAX_SIZE = 8G SCOPE=SPFILE;  -- Requires restart

-- Check SGA components
SELECT
    pool,
    name,
    bytes / 1024 / 1024 as size_mb
FROM v$sgastat
WHERE pool IS NOT NULL
ORDER BY pool, bytes DESC;

-- Buffer cache hit ratio (should be >90%)
SELECT
    name,
    value
FROM v$sysstat
WHERE name IN (
    'db block gets from cache',
    'consistent gets from cache',
    'physical reads cache'
);

-- Shared pool statistics
SELECT
    pool,
    name,
    bytes / 1024 / 1024 as size_mb
FROM v$sgastat
WHERE pool = 'shared pool'
  AND name IN ('free memory', 'sql area');
```

**Guidelines**:
- **Small databases**: 2-4GB SGA
- **Medium databases**: 4-8GB SGA
- **Large databases**: 8-16GB+ SGA
- Formula: `SGA = Total RAM * 0.6` (60% of RAM)

## Index Tuning

### Index Maintenance

```sql
-- Rebuild index (online, no downtime)
ALTER INDEX idx_product_embedding_hnsw REBUILD ONLINE;

-- Coalesce index (reorganize without rebuild)
ALTER INDEX idx_product_embedding_hnsw COALESCE;

-- Gather index statistics
EXEC DBMS_STATS.GATHER_INDEX_STATS(
    ownname => USER,
    indname => 'IDX_PRODUCT_EMBEDDING_HNSW'
);

-- Check index fragmentation
SELECT
    index_name,
    leaf_blocks,
    distinct_keys,
    ROUND(leaf_blocks / distinct_keys, 2) as blocks_per_key
FROM user_indexes
WHERE table_name = 'PRODUCTS';

-- If blocks_per_key > 2, consider rebuild
```

### Invisible Indexes (Testing)

Test index impact without dropping:

```sql
-- Make index invisible (not used by optimizer)
ALTER INDEX idx_product_origin INVISIBLE;

-- Test query performance without index
-- (Optimizer won't use invisible index)

-- Make visible again
ALTER INDEX idx_product_origin VISIBLE;
```

## Statistics and Monitoring

### Table and Index Statistics

Accurate statistics are critical for query optimization:

```sql
-- Gather table statistics
EXEC DBMS_STATS.GATHER_TABLE_STATS(
    ownname => USER,
    tabname => 'PRODUCTS',
    estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE,
    method_opt => 'FOR ALL COLUMNS SIZE AUTO',
    cascade => TRUE  -- Include indexes
);

-- Check statistics staleness
SELECT
    table_name,
    num_rows,
    last_analyzed,
    stale_stats
FROM user_tab_statistics
WHERE table_name = 'PRODUCTS';

-- Auto statistics gathering (recommended)
BEGIN
    DBMS_STATS.SET_TABLE_PREFS(
        ownname => USER,
        tabname => 'PRODUCTS',
        pname => 'STALE_PERCENT',
        pvalue => '10'  -- Regather if 10% of rows change
    );
END;
/
```

### Real-Time Performance Monitoring

```sql
-- Active sessions
SELECT
    s.sid,
    s.serial#,
    s.username,
    s.status,
    s.sql_id,
    s.event,
    s.wait_time,
    s.seconds_in_wait
FROM v$session s
WHERE s.username IS NOT NULL
  AND s.status = 'ACTIVE';

-- Long-running queries
SELECT
    s.sid,
    s.serial#,
    s.username,
    q.sql_text,
    s.last_call_et as seconds_running
FROM v$session s
JOIN v$sql q ON s.sql_id = q.sql_id
WHERE s.status = 'ACTIVE'
  AND s.last_call_et > 60  -- Running >60 seconds
ORDER BY s.last_call_et DESC;

-- Top SQL by elapsed time
SELECT
    sql_id,
    executions,
    ROUND(elapsed_time / 1000000, 2) as elapsed_sec,
    ROUND(cpu_time / 1000000, 2) as cpu_sec,
    ROUND(elapsed_time / executions / 1000, 2) as avg_ms,
    SUBSTR(sql_text, 1, 100) as sql_text
FROM v$sql
WHERE executions > 0
ORDER BY elapsed_time DESC
FETCH FIRST 10 ROWS ONLY;
```

## Python Driver Optimization

### Thick Mode vs Thin Mode

python-oracledb supports two modes:

**Thin Mode** (Default, Pure Python):
```python
import oracledb

# Thin mode (no Oracle Client required)
connection = oracledb.connect(
    user="user",
    password="password",
    dsn="localhost:1521/FREEPDB1"
)

# Good for: Cloud, containers, simple queries
# Limitations: Some advanced features unavailable
```

**Thick Mode** (Oracle Client Libraries):
```python
import oracledb

# Initialize thick mode (requires Oracle Instant Client)
oracledb.init_oracle_client(lib_dir="/path/to/instantclient")

# Connect (same API)
connection = oracledb.connect(
    user="user",
    password="password",
    dsn="localhost:1521/FREEPDB1"
)

# Good for: Maximum performance, advanced features
# Requirements: Oracle Instant Client installed
```

**When to use Thick Mode**:
- Advanced features (connection pooling, DRCP)
- High performance requirements
- Continuous Query Notification (CQN)
- Advanced Queuing (AQ)

### Batch Operations

Reduce round trips with batch operations:

```python
# Insert multiple rows (single round trip)
data = [
    ("Product A", 19.99, "coffee"),
    ("Product B", 24.99, "coffee"),
    ("Product C", 29.99, "tea")
]

cursor.executemany(
    "INSERT INTO products (name, price, category) VALUES (:1, :2, :3)",
    data
)

# Batch size tuning
cursor.executemany(
    "INSERT INTO products (name, price, category) VALUES (:1, :2, :3)",
    data,
    batcherrors=True,  # Continue on errors
    arraydmlrowcounts=True  # Get per-row counts
)

# Check batch results
for i, error in enumerate(cursor.getbatcherrors()):
    print(f"Row {i}: Error {error.message}")
```

## Troubleshooting Performance

### Issue: Slow Vector Queries

**Symptoms**: Vector similarity search takes >100ms for small datasets.

**Diagnosis**:
```sql
EXPLAIN PLAN FOR
SELECT * FROM products
WHERE 1 - VECTOR_DISTANCE(embedding, :query, COSINE) >= 0.7
ORDER BY VECTOR_DISTANCE(embedding, :query, COSINE)
FETCH FIRST 5 ROWS ONLY;

SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);
```

**Solutions**:
1. **Check SPATIAL_VECTOR_ACCELERATION**: `ALTER SESSION SET SPATIAL_VECTOR_ACCELERATION = TRUE;`
2. **Verify index exists**: `SELECT index_name FROM user_indexes WHERE table_name = 'PRODUCTS';`
3. **Rebuild index**: `ALTER INDEX idx_product_embedding_hnsw REBUILD ONLINE;`
4. **Gather statistics**: `EXEC DBMS_STATS.GATHER_TABLE_STATS(USER, 'PRODUCTS', cascade => TRUE);`
5. **Increase HNSW_EF_SEARCH**: `ALTER SESSION SET HNSW_EF_SEARCH = 200;`

### Issue: Connection Pool Exhaustion

**Symptoms**: `ORA-24457: OCISessionGet() timed out waiting for pool to create new connection`

**Diagnosis**:
```python
print(f"Pool busy: {pool.busy}")
print(f"Pool max: {pool.max}")
print(f"Utilization: {(pool.busy / pool.max) * 100:.1f}%")
```

**Solutions**:
1. **Increase max connections**: `pool.reconfigure(max=20)`
2. **Reduce wait_timeout**: `pool.reconfigure(wait_timeout=10000)` (fail fast)
3. **Check for connection leaks**: Ensure all connections are released
4. **Monitor utilization**: Keep <80% to handle spikes

### Issue: High CPU Usage

**Symptoms**: Database CPU at 90%+, queries slow.

**Diagnosis**:
```sql
-- Top CPU consumers
SELECT
    s.sid,
    s.serial#,
    s.username,
    s.cpu_time / 1000000 as cpu_sec,
    q.sql_text
FROM v$session s
JOIN v$sql q ON s.sql_id = q.sql_id
ORDER BY s.cpu_time DESC
FETCH FIRST 5 ROWS ONLY;
```

**Solutions**:
1. **Check for missing indexes**: Look for full table scans
2. **Analyze query plans**: Use EXPLAIN PLAN
3. **Enable INMEMORY**: `ALTER TABLE products INMEMORY;`
4. **Tune vector indexes**: Adjust HNSW parameters
5. **Limit concurrent queries**: Use connection pool limits

### Issue: Memory Errors

**Symptoms**: `ORA-04030: out of process memory`

**Diagnosis**:
```sql
SELECT
    name,
    value / 1024 / 1024 as value_mb
FROM v$pgastat
WHERE name LIKE '%PGA%target%' OR name LIKE '%PGA%allocated%';
```

**Solutions**:
1. **Increase PGA**: `ALTER SYSTEM SET PGA_AGGREGATE_TARGET = 4G;`
2. **Reduce batch size**: Use smaller `cursor.arraysize`
3. **Optimize queries**: Reduce memory-intensive operations
4. **Monitor per-session PGA**: Identify memory-hungry sessions

## See Also

- [Oracle Vector Search Guide](oracle-vector-search.md) - Vector index optimization
- [Oracle JSON Guide](oracle-json.md) - JSON query performance
- [Architecture Overview](architecture.md) - System design and data flow

## Resources

- Oracle Performance Tuning Guide: https://docs.oracle.com/en/database/oracle/oracle-database/23/tgdba/
- python-oracledb Performance: https://python-oracledb.readthedocs.io/en/latest/user_guide/tuning.html
- Vector Search Performance: https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/performance-tuning.html
