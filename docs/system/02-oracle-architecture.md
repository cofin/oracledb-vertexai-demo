# 🏛️ Oracle-First Architecture: One Database to Rule Them All

## Oracle 23AI: The Unified Solution

### Everything in One Place

```
┌─────────────────────────────────────────┐
│           Oracle Database 23AI          │
│                                         │
│  ┌─────────────┐  ┌─────────────┐       │
│  │   Vectors   │  │  Relations  │       │
│  │  with HNSW  │  │  with SQL   │       │
│  └─────────────┘  └─────────────┘       │
│                                         │
│  ┌─────────────┐  ┌─────────────┐       │
│  │    JSON     │  │   Cache     │       │
│  │  Documents  │  │  with TTL   │       │
│  └─────────────┘  └─────────────┘       │
│                                         │
│  ┌─────────────┐  ┌─────────────┐       │
│  │  Sessions   │  │  Full-Text  │       │
│  │   Storage   │  │   Search    │       │
│  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────┘
```

## Native AI Capabilities

### 1. Vector Storage and Search

**Oracle 23AI Approach:**

```sql
-- It's just SQL with vectors!
CREATE TABLE products (
    id NUMBER PRIMARY KEY,
    name VARCHAR2(200),
    description CLOB,
    embedding VECTOR(768, FLOAT32)
);

-- Lightning-fast similarity search
SELECT name, description,
       VECTOR_DISTANCE(embedding, :query_vector, COSINE) as similarity
FROM products
WHERE VECTOR_DISTANCE(embedding, :query_vector, COSINE) < 0.8
ORDER BY similarity
FETCH FIRST 5 ROWS ONLY;
```

### 2. Session Management Without Redis

```sql
-- Atomic operation with TTL
INSERT INTO user_sessions (
    session_id, user_id, data, expires_at
) VALUES (
    :session_id, :user_id, :json_data,
    SYSTIMESTAMP + INTERVAL '1' HOUR
);

-- Automatic cleanup job
BEGIN
    DBMS_SCHEDULER.create_job(
        job_name => 'CLEANUP_SESSIONS',
        job_action => 'DELETE FROM user_sessions WHERE expires_at < SYSTIMESTAMP',
        repeat_interval => 'FREQ=HOURLY'
    );
END;
```

### 3. Response and Embeddings Caching

```sql
-- In-memory caching built-in (as implemented in our migration)
CREATE TABLE response_cache (
    -- ... column definitions ...
) INMEMORY PRIORITY HIGH;

CREATE TABLE intent_exemplar (
    -- ... column definitions ...
) INMEMORY PRIORITY HIGH;

-- Smart caching with automatic TTL
MERGE INTO response_cache USING dual ON (cache_key = :key)
WHEN MATCHED THEN
    UPDATE SET response = :data, expires_at = SYSTIMESTAMP + INTERVAL '5' MINUTE
WHEN NOT MATCHED THEN
    INSERT (cache_key, response, expires_at)
    VALUES (:key, :data, SYSTIMESTAMP + INTERVAL '5' MINUTE);
```

### Advanced Caching Architecture

**Two-Tier Caching Strategy:**

```python
# 1. Embedding Cache (24-hour TTL)
# Stores vector embeddings to prevent redundant API calls
class EmbeddingCache:
    def __init__(self, connection):
        self.connection = connection
        self._memory_cache = {}  # In-process cache

    async def get_embedding(self, query):
        # Check memory first (microseconds)
        if query in self._memory_cache:
            return self._memory_cache[query]

        # Check Oracle cache (milliseconds)
        result = await self.fetch_from_oracle(query)
        if result:
            return result

        embedding = await generate_embedding(query)
        await self.store_in_oracle(query, embedding)
        return embedding

# 2. Response Cache (5-minute TTL)
# Stores complete AI responses for repeated queries
class ResponseCache:
    async def get_cached_response(self, prompt, user_id):
        # User-specific cache keys
        cache_key = hash(f"{prompt}:{user_id}")
        return await self.fetch_from_oracle(cache_key)
```

### Hybrid Queries - The Killer Feature

Join in vector distance with spatial in a single query

```sql
-- Find coffee that's similar AND in stock nearby
SELECT p.name, p.price, s.address, i.quantity,
       VECTOR_DISTANCE(p.embedding, :taste_vector, COSINE) as match_score
FROM products p
JOIN inventory i ON p.id = i.product_id
JOIN shops s ON i.shop_id = s.id
WHERE VECTOR_DISTANCE(p.embedding, :taste_vector, COSINE) < 0.7
  AND ST_Distance(s.location, :user_location) < 5000 -- Within 5km
  AND i.quantity > 0
ORDER BY match_score, distance
FETCH FIRST 10 ROWS ONLY;
```

## Implementation Patterns

### Service Architecture

```python
import oracledb

class UnifiedDataService:
    """One service, all capabilities - using raw Oracle SQL"""

    def __init__(self, connection: oracledb.AsyncConnection):
        self.connection = connection

    async def semantic_search(self, query: str, user_location: tuple):
        """Vector search + geospatial + inventory in ONE query"""
        query_embedding = await self.create_embedding(query)

        cursor = self.connection.cursor()
        try:
            await cursor.execute("""
                SELECT p.*, s.*,
                       VECTOR_DISTANCE(p.embedding, :embedding, COSINE) as score
                FROM product p
                JOIN inventory i ON p.id = i.product_id
                JOIN shop s ON i.shop_id = s.id
                WHERE VECTOR_DISTANCE(p.embedding, :embedding, COSINE) < 0.8
                  AND i.quantity > 0
                ORDER BY score
                FETCH FIRST 10 ROWS ONLY
            """, {
                "embedding": query_embedding
            })

            return await cursor.fetchall()
        finally:
            cursor.close()
```

### Advanced Areas to Explore

#### 1.Partitioning

```sql
-- Partition metrics by day automatically
CREATE TABLE search_metrics (
    id NUMBER,
    query_time TIMESTAMP,
    response_ms NUMBER
) PARTITION BY RANGE (query_time)
INTERVAL (INTERVAL '1' DAY);
```

#### 2. In-Database Machine Learning

```sql
-- Train models without data movement
BEGIN
    DBMS_DATA_MINING.CREATE_MODEL(
        model_name => 'coffee_preferences',
        mining_function => DBMS_DATA_MINING.CLASSIFICATION,
        data_table_name => 'user_interactions',
        target_column_name => 'purchased'
    );
END;
```
