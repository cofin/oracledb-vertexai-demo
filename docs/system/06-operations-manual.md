# 📋 Operations Manual: Running Your AI System in Production

## Quick Reference Card

### Critical Commands
```bash
# System Health
uv run app health-check              # Full system diagnostic
uv run app database check-connection # Database connectivity
uv run app vertex-ai test           # AI service status

# Emergency Procedures
uv run app emergency offline-mode    # Enable fallback mode
uv run app cache clear              # Clear all caches
uv run app database repair-indexes  # Fix vector indexes

# Performance
uv run app metrics realtime         # Live metrics dashboard
uv run app performance analyze      # Performance report
```

## System Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Load Balancer │────▶│  App Instances  │────▶│  Oracle 23AI    │
│   (nginx/ALB)   │     │  (3+ replicas)  │     │  (Primary)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │                         │
                                ▼                         ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │   Vertex AI     │     │  Oracle 23AI    │
                        │   (External)    │     │  (Standby)      │
                        └─────────────────┘     └─────────────────┘
```

## Daily Operations Checklist

### Morning Checks (5 minutes)
```bash
# 1. System health
uv run app health-check --comprehensive

# 2. Check overnight metrics
uv run app metrics summary --period=24h

# 3. Review error logs
uv run app logs errors --since=yesterday

# 4. Cache efficiency
uv run app cache stats
```

### Expected Values
- Response time: <500ms (p95)
- Error rate: <0.1%
- Cache hit rate: >80%
- Vector search: <50ms

## Monitoring & Alerting

### Key Metrics to Watch

#### 1. Application Metrics
```python
# Real-time monitoring query
SELECT
    DATE_TRUNC('minute', created_at) as minute,
    COUNT(*) as requests,
    AVG(search_time_ms) as avg_search_time,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY search_time_ms) as p95_time,
    COUNT(CASE WHEN error_code IS NOT NULL THEN 1 END) as errors
FROM search_metrics
WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '1 hour'
GROUP BY DATE_TRUNC('minute', created_at)
ORDER BY minute DESC;
```

#### 2. Database Metrics
```sql
-- Vector index health
SELECT
    index_name,
    num_rows,
    distinct_keys,
    leaf_blocks,
    clustering_factor
FROM user_indexes
WHERE index_type = 'VECTOR';

-- Session usage
SELECT
    COUNT(*) as active_sessions,
    COUNT(CASE WHEN expires_at < SYSTIMESTAMP THEN 1 END) as expired,
    AVG(EXTRACT(EPOCH FROM (expires_at - created_at))/3600) as avg_duration_hours
FROM user_sessions
WHERE created_at > SYSTIMESTAMP - INTERVAL '1' DAY;
```

#### 3. AI Service Metrics
```python
# Monitor Vertex AI usage
async def check_ai_metrics():
    return {
        "model_latency": await vertex_ai.get_avg_latency(),
        "token_usage": await vertex_ai.get_token_count(),
        "error_rate": await vertex_ai.get_error_rate(),
        "fallback_count": await vertex_ai.get_fallback_usage()
    }
```

### Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|---------|
| Response Time (p95) | >750ms | >1500ms | Scale up instances |
| Error Rate | >1% | >5% | Check logs, enable fallback |
| Cache Hit Rate | <70% | <50% | Analyze query patterns |
| DB Connections | >80% | >95% | Increase pool size |
| AI Errors | >2% | >10% | Switch to fallback model |

## Deployment Procedures

### Rolling Deployment (Zero Downtime)

```bash
# 1. Build new image
docker build -t coffee-ai:v2.1.0 .

# 2. Test new image
docker run --rm coffee-ai:v2.1.0 uv run app test

# 3. Deploy to staging
kubectl set image deployment/coffee-ai coffee-ai=coffee-ai:v2.1.0 -n staging

# 4. Run smoke tests
uv run app test smoke --env=staging

# 5. Deploy to production (25% at a time)
kubectl rollout restart deployment/coffee-ai -n production
kubectl rollout status deployment/coffee-ai -n production

# 6. Monitor metrics
uv run app monitor deployment --version=v2.1.0
```

### Database Migrations

```bash
# 1. Backup current state
uv run app database backup --name=pre-migration-$(date +%Y%m%d)

# 2. Test migration on staging
uv run app database upgrade --env=staging --dry-run

# 3. Apply migration
uv run app database upgrade --env=production

# 4. Verify migration
uv run app database verify-schema
```

## Backup & Recovery

### Automated Backup Schedule

```yaml
# backup-config.yml
schedules:
  - name: hourly-cache
    tables: [response_cache, search_metrics]
    frequency: "0 * * * *"
    retention: 24 hours

  - name: daily-full
    tables: all
    frequency: "0 2 * * *"
    retention: 7 days

  - name: weekly-archive
    tables: all
    frequency: "0 3 * * 0"
    retention: 90 days
    compression: true
```

### Manual Data Export/Import

For demo environments or migration scenarios, use the built-in export utility:

```bash
# Export all tables with embeddings (compressed)
uv run app dump-data

# Export specific tables
uv run app dump-data --table intent_exemplar
uv run app dump-data --table product

# Export to custom location
uv run app dump-data --path /backup/$(date +%Y%m%d)

# Export without compression
uv run app dump-data --no-compress

# The exported files are automatically loaded by load-fixtures
# Priority: UPPERCASE.json.gz > lowercase.json.gz > lowercase.json
```

### Recovery Procedures

#### Scenario 1: Cache Corruption
```bash
# 1. Clear corrupted cache
uv run app cache clear --table=response_cache

# 2. Warm cache with common queries
uv run app cache warm --queries=top-1000

# 3. Monitor cache rebuild
uv run app cache monitor --realtime
```

### Intent Exemplar Cache Management

The intent exemplar cache stores embeddings for intent detection patterns. These are stored in Oracle In-Memory tables for ultra-fast access.

#### Clearing Intent Cache (After Adding New Patterns)
```bash
# Run the provided script to clear all cached exemplars
uv run python clear_intent_cache.py

# Or manually via SQL
sqlplus coffee_app/password@COFFEDB <<EOF
DELETE FROM intent_exemplar;
COMMIT;
EOF
```

#### Monitoring Intent Cache
```sql
-- Check cache status
SELECT intent, COUNT(*) as pattern_count
FROM intent_exemplar
GROUP BY intent;

-- Verify In-Memory status
SELECT segment_name, inmemory_size, bytes_not_populated
FROM v$im_segments
WHERE segment_name IN ('INTENT_EXEMPLAR', 'RESPONSE_CACHE');
```

**Note**: After clearing the cache, the next user request will automatically repopulate it with all current exemplar patterns (including any new ones added to the code).

#### Scenario 2: Vector Index Issues
```sql
-- Rebuild vector index
DROP INDEX idx_product_embedding;
CREATE INDEX idx_product_embedding ON products (embedding)
INDEXTYPE IS VECTOR
PARAMETERS ('TYPE=HNSW, NEIGHBORS=64');

-- Verify index health
SELECT * FROM v$vector_index_stats WHERE index_name = 'IDX_PRODUCT_EMBEDDING';
```

#### Scenario 3: Complete System Recovery
```bash
# 1. Restore database
uv run app database restore --backup=weekly-archive-20240615

# 2. Regenerate embeddings
uv run app embeddings regenerate --parallel=8

# 3. Clear and warm caches
uv run app cache rebuild

# 4. Verify system health
uv run app health-check --comprehensive
```

## Performance Tuning

### Database Optimization

```sql
-- 1. Update statistics
EXEC DBMS_STATS.GATHER_SCHEMA_STATS('COFFEE_APP');

-- 2. Pin hot tables in memory
ALTER TABLE products STORAGE (BUFFER_POOL KEEP);
ALTER TABLE response_cache INMEMORY PRIORITY CRITICAL;

-- 3. Optimize vector searches
ALTER SESSION SET "_vector_search_optimization_level" = 3;
```

### Application Tuning

```python
# config/performance.py
PERFORMANCE_SETTINGS = {
    # Connection pooling
    "db_pool_size": 20,
    "db_pool_timeout": 30,
    "db_pool_recycle": 3600,

    # Caching
    "cache_ttl_seconds": 300,
    "cache_max_size": 10000,

    # AI Service
    "embedding_batch_size": 100,
    "ai_timeout_seconds": 10,
    "ai_max_retries": 3,

    # Rate limiting
    "rate_limit_per_minute": 100,
    "burst_size": 20
}
```

### Query Optimization

```python
# Optimized vector search with hints
async def search_products_optimized(embedding: list[float], limit: int = 10):
    return await db.fetch_all("""
        SELECT /*+ LEADING(p) USE_NL(i s) INDEX(p idx_product_embedding) */
            p.id, p.name, p.description,
            VECTOR_DISTANCE(p.embedding, :embedding, COSINE) as similarity
        FROM products p
        WHERE p.status = 'ACTIVE'
          AND VECTOR_DISTANCE(p.embedding, :embedding, COSINE) < 0.8
        ORDER BY similarity
        FETCH FIRST :limit ROWS ONLY
    """, {"embedding": embedding, "limit": limit})
```

## Scaling Strategies

### Horizontal Scaling

```yaml
# kubernetes/autoscaling.yml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: coffee-ai-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: coffee-ai
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Database Scaling

```sql
-- Enable Oracle Real Application Clusters (RAC)
ALTER SYSTEM SET cluster_database=TRUE SCOPE=SPFILE;

-- Add read replicas for vector searches
CREATE DATABASE LINK vector_replica
CONNECT TO coffee_app IDENTIFIED BY password
USING 'oracle-replica:1521/VECTORDB';
```

## Security Operations

### Access Control

```python
# Implement API key rotation
async def rotate_api_keys():
    # Generate new keys
    new_keys = await generate_secure_keys()

    # Update configuration
    await update_config(new_keys)

    # Grace period for old keys
    await schedule_key_deprecation(hours=24)

    # Audit log
    await log_security_event("API_KEY_ROTATION", new_keys)
```

### Data Privacy

```sql
-- Implement data retention policies
CREATE OR REPLACE PROCEDURE purge_old_data AS
BEGIN
    -- Remove old search metrics
    DELETE FROM search_metrics
    WHERE created_at < SYSTIMESTAMP - INTERVAL '90' DAY;

    -- Anonymize old sessions
    UPDATE user_sessions
    SET user_id = 'ANONYMOUS-' || id,
        data = JSON_OBJECT('anonymized' VALUE 'true')
    WHERE created_at < SYSTIMESTAMP - INTERVAL '30' DAY;

    COMMIT;
END;
/

-- Schedule daily execution
BEGIN
    DBMS_SCHEDULER.CREATE_JOB(
        job_name => 'PURGE_OLD_DATA_JOB',
        job_type => 'STORED_PROCEDURE',
        job_action => 'purge_old_data',
        repeat_interval => 'FREQ=DAILY; BYHOUR=2'
    );
END;
/
```

## Incident Response

### Severity Levels

| Level | Description | Response Time | Example |
|-------|-------------|---------------|----------|
| P1 | System Down | 15 minutes | Database offline |
| P2 | Major Degradation | 1 hour | AI service errors >10% |
| P3 | Minor Issue | 4 hours | Slow queries |
| P4 | Cosmetic | Next business day | UI glitch |

### Response Playbooks

#### P1: System Down
```bash
# 1. Enable emergency mode
uv run app emergency activate

# 2. Check critical services
uv run app diagnose --comprehensive

# 3. Failover if needed
uv run app failover --to=standby

# 4. Notify stakeholders
uv run app notify --severity=P1 --message="System failover initiated"

# 5. Begin root cause analysis
uv run app logs collect --period=1h --output=incident-$(date +%Y%m%d-%H%M%S).tar.gz
```

#### P2: AI Service Degradation
```bash
# 1. Switch to fallback model
uv run app ai fallback-mode enable

# 2. Reduce AI load
uv run app ai rate-limit --requests-per-minute=50

# 3. Monitor recovery
uv run app ai monitor --interval=1m

# 4. Gradual recovery
uv run app ai recovery --gradual --duration=30m
```

## Maintenance Windows

### Monthly Maintenance Tasks

```bash
#!/bin/bash
# maintenance-script.sh

echo "Starting monthly maintenance - $(date)"

# 1. Database maintenance
uv run app database analyze-tables
uv run app database rebuild-indexes --type=vector
uv run app database update-statistics

# 2. Clean up old data
uv run app cleanup sessions --older-than=30d
uv run app cleanup metrics --older-than=90d
uv run app cleanup logs --older-than=7d

# 3. Performance analysis
uv run app performance report --month=$(date +%Y-%m)

# 4. Security audit
uv run app security audit --comprehensive
uv run app security rotate-keys

echo "Maintenance completed - $(date)"
```

## Cost Optimization

### Monitor AI Usage

```python
# Track and optimize AI costs
async def analyze_ai_costs():
    costs = await db.fetch_one("""
        SELECT
            COUNT(*) as total_requests,
            SUM(CASE WHEN cache_hit THEN 0 ELSE 1 END) as api_calls,
            AVG(token_count) as avg_tokens,
            SUM(token_count) * 0.00001 as estimated_cost_usd
        FROM ai_usage_metrics
        WHERE created_at > CURRENT_DATE - INTERVAL '30 days'
    """)

    return {
        "monthly_cost": costs["estimated_cost_usd"],
        "cache_savings": costs["total_requests"] - costs["api_calls"],
        "optimization_potential": identify_duplicate_queries()
    }
```

### Database Cost Management

```sql
-- Implement compression for historical data
ALTER TABLE search_metrics
COMPRESS FOR OLTP
PARTITION BY RANGE (created_at) (
    PARTITION p_current VALUES LESS THAN (SYSTIMESTAMP),
    PARTITION p_history VALUES LESS THAN (MAXVALUE) COMPRESS FOR ARCHIVE HIGH
);
```

## Compliance & Auditing

### Audit Trail

```python
# Comprehensive audit logging
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    audit_entry = {
        "timestamp": datetime.utcnow(),
        "user_id": request.headers.get("X-User-ID"),
        "method": request.method,
        "path": request.url.path,
        "ip_address": request.client.host
    }

    response = await call_next(request)

    audit_entry["status_code"] = response.status_code
    audit_entry["duration_ms"] = response.headers.get("X-Process-Time")

    await audit_logger.log(audit_entry)
    return response
```

## Support Escalation

### Tier 1: Application Support
- Monitor dashboards
- Run diagnostic commands
- Clear caches
- Restart services

### Tier 2: Database/AI Support
- Query optimization
- Index management
- Model tuning
- Performance analysis

### Tier 3: Architecture/Vendor
- Oracle support tickets
- Google Cloud support
- Architecture changes
- Capacity planning

## Quick Reference: Common Issues

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| Slow searches | Index fragmentation | Rebuild vector indexes |
| High latency | Cold cache | Run cache warming |
| AI errors | Rate limiting | Enable fallback mode |
| Memory issues | Large result sets | Implement pagination |
| Connection errors | Pool exhaustion | Increase pool size |

---

*"Great operations is invisible. When everything works smoothly, nobody notices - and that's exactly what we want."* - SRE Team Lead
