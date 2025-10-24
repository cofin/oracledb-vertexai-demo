# Example Expert Research

> This is an example research output from the Expert agent.

## Research Topic: Oracle Caching Patterns

**Date**: 2025-10-09
**Requirement**: add-product-recommendation-caching
**Researcher**: Expert Agent
**MCP Tools Used**: Context7 (/oracle/python-oracledb), Zen thinkdeep, SQLcl MCP

## Summary

Researched Oracle-backed caching strategies for recommendation system. Recommendation: Use Oracle table with TTL-based expiration.

## Approach Analysis

### Option 1: Oracle Table Cache (RECOMMENDED)

**Pros**:

- No new infrastructure
- ACID guarantees
- Leverage existing connection pool
- Can query cache contents (debugging)

**Cons**:

- Slower than in-memory cache (1-2ms vs microseconds)
- Adds database load

**Implementation**:

```sql
CREATE TABLE recommendation_cache (
    cache_key VARCHAR2(64) PRIMARY KEY,
    user_id NUMBER REFERENCES users(id),
    recommendations JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX idx_recommendation_cache_expires
ON recommendation_cache(expires_at);
```

### Option 2: Redis Cache

**Pros**:

- Very fast (microseconds)
- Built-in TTL
- Widely used pattern

**Cons**:

- New infrastructure to manage
- Another failure point
- Connection pool overhead

### Option 3: Application-Level Cache (dict)

**Pros**:

- Fastest possible
- No external dependencies

**Cons**:

- Not shared across processes
- Lost on restart
- Memory management required

## Recommendation

**Use Option 1: Oracle Table Cache**

Rationale:

1. Simple infrastructure (already have Oracle)
2. Performance acceptable (1-2ms latency fine for recommendations)
3. ACID guarantees prevent cache inconsistency
4. Can debug by querying cache table
5. Can add Redis later if needed (easy migration)

## Cache TTL Strategy

**Recommended TTL**: 5 minutes

Reasoning:

- Recommendations don't need real-time freshness
- 5 min balances performance vs staleness
- Can adjust based on usage metrics

**Cleanup Strategy**:

```sql
-- Run periodically to remove expired entries
DELETE FROM recommendation_cache
WHERE expires_at < CURRENT_TIMESTAMP;
```

## Code Example

```python
from app.services.base import SQLSpecService
from datetime import datetime, timedelta
import hashlib
import json

class CacheService(SQLSpecService):
    async def get_cached_recommendations(
        self,
        user_id: int,
        query_params: dict,
    ) -> list[dict] | None:
        """Get cached recommendations if available."""
        # Generate cache key
        cache_key = self._generate_cache_key(user_id, query_params)

        # Query cache
        result = await self.driver.select_one_or_none(
            """
            SELECT recommendations
            FROM recommendation_cache
            WHERE cache_key = :key
              AND expires_at > CURRENT_TIMESTAMP
            """,
            key=cache_key,
        )

        if result:
            return json.loads(result["recommendations"])
        return None

    async def set_cached_recommendations(
        self,
        user_id: int,
        query_params: dict,
        recommendations: list[dict],
        ttl_minutes: int = 5,
    ) -> None:
        """Cache recommendations with TTL."""
        cache_key = self._generate_cache_key(user_id, query_params)
        expires_at = datetime.now() + timedelta(minutes=ttl_minutes)

        await self.driver.execute(
            """
            INSERT INTO recommendation_cache
                (cache_key, user_id, recommendations, expires_at)
            VALUES (:key, :user_id, :recs, :expires)
            ON CONFLICT (cache_key) DO UPDATE
            SET recommendations = :recs, expires_at = :expires
            """,
            key=cache_key,
            user_id=user_id,
            recs=json.dumps(recommendations),
            expires=expires_at,
        )

    def _generate_cache_key(self, user_id: int, query_params: dict) -> str:
        """Generate SHA256 cache key from user_id and params."""
        data = f"{user_id}:{json.dumps(query_params, sort_keys=True)}"
        return hashlib.sha256(data.encode()).hexdigest()
```

## Performance Expectations

- **Cache hit**: ~1-2ms (Oracle query)
- **Cache miss + generation**: ~50-100ms (Vertex AI embedding + similarity search)
- **Target hit rate**: >80%

## Sources

- Context7: /oracle/python-oracledb (2025-10-09) - UPSERT syntax, JSON handling
- Local guide: docs/guides/oracle-performance.md - Oracle caching patterns
- Zen thinkdeep: Architectural analysis of caching options
- Existing code: app/services/vertex_ai.py - Similar caching pattern for embeddings

## Next Steps

1. Create migration for recommendation_cache table
2. Implement CacheService methods
3. Integrate with RecommendationService
4. Add tests for cache hit/miss scenarios
5. Monitor cache hit rate in production
