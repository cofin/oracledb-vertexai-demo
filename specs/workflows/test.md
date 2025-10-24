# Test Workflow

Invoke the Testing agent to create comprehensive test suites for Oracle, Vertex AI, and ADK features.

## Invocation by AI Platform

- **Gemini**: `/prompt test {requirement-slug}`
- **Claude Code**: Use Task tool with subagent_type="testing"
- **Codex**: `/invoke testing {requirement-slug}`

## What This Does

- Reads implementation from `specs/active/{slug}/recovery.md`
- Creates unit and integration tests
- Tests Oracle vector search, caching, ADK agents
- Tests edge cases and performance
- Validates coverage targets

## Usage Examples

### Gemini

```
/prompt test vector-search-caching
```

### Claude Code

```python
Task(
    subagent_type="testing",
    description="Create test suite",
    prompt="Create comprehensive tests for specs/active/vector-search-caching/"
)
```

### Codex

```
/invoke testing vector-search-caching
```

## What the Testing Agent Will Do

1. **Read implementation details** from recovery.md and progress.md
2. **Consult testing guide** (specs/guides/)
3. **Create unit tests** in tests/unit/:
   - Service layer business logic
   - Utility functions
   - Fast, no external dependencies
4. **Create integration tests** in tests/integration/:
   - Oracle vector search operations
   - Vertex AI embedding generation
   - Cache hit/miss scenarios
   - ADK agent tool execution
5. **Test edge cases**:
   - Empty results
   - Large datasets
   - Concurrent operations
   - Error conditions
6. **Validate performance**:
   - No N+1 queries
   - Acceptable response times
   - Cache efficiency
7. **Verify coverage targets** (> 80%)
8. **Update workspace** - tasks.md, progress.md

## Test Categories

### Unit Tests (`tests/unit/`)

- Service layer logic
- Data validation
- Utility functions
- Fast execution

### Integration Tests (`tests/integration/`)

- Oracle vector operations
- Vertex AI embeddings
- Cache behavior
- ADK agents
- Database transactions

### API Tests (`tests/api/`)

- Litestar routes
- HTMX partials
- Request/response validation
- Error handling

## Test Patterns Used

### Service Layer Tests

```python
@pytest.mark.asyncio
async def test_vector_similarity_search(product_service):
    query_embedding = [0.1] * 768
    results = await product_service.vector_similarity_search(
        query_embedding=query_embedding,
        similarity_threshold=0.3,
        limit=10
    )
    assert len(results) > 0
    assert all(r['similarity'] < 0.3 for r in results)
```

### Cache Tests

```python
@pytest.mark.asyncio
async def test_embedding_cache_hit(cache_service):
    result1 = await cache_service.get_or_generate_embedding("coffee")
    result2 = await cache_service.get_or_generate_embedding("coffee")
    assert result1 == result2
    assert cache_service.cache_hits == 1
```

### ADK Agent Tests

```python
@pytest.mark.asyncio
async def test_adk_product_search():
    agent = create_product_agent()
    response = await agent.send("Find espresso products")
    assert "espresso" in response.lower()
```

## Running Tests

```bash
# All tests
pytest tests/

# With coverage
pytest tests/ --cov=app --cov-report=html

# Parallel execution
pytest tests/ -n auto

# Specific category
pytest tests/unit/
pytest tests/integration/
pytest tests/api/
```

## After Testing

Next steps:

- **Review**: `/prompt review {slug}` (Gemini) or invoke Docs & Vision agent
- All tests must pass before review
- Testing agent hands off to Docs & Vision for quality gate
