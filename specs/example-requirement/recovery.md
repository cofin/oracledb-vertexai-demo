# Recovery Guide: Example Requirement

> This shows how to resume work after a conversation break.

## Current Status

**Status**: Example (Not Started)
**Last Updated**: 2025-10-09
**Last Completed Task**: None
**Next Task**: This is an example - start with `/plan {your-feature}`

## To Resume Work

1. **Read PRD**: `specs/example-requirement/prd.md`
2. **Check Tasks**: `specs/example-requirement/tasks.md`
3. **Review Progress**: `specs/example-requirement/progress.md`
4. **Read Research**: `specs/example-requirement/research/` (all files)
5. **Understand Context**: [Key decisions, assumptions, blockers below]

## Key Decisions Made

- **Decision 1**: Use Oracle table for cache (TTL-based expiration)
  - **Rationale**: Leverages existing database, no new infrastructure
  - **Alternative Considered**: Redis (rejected: adds complexity)

- **Decision 2**: 5-minute cache TTL
  - **Rationale**: Balance freshness vs performance
  - **Can Adjust**: Based on usage patterns

## Blockers

- **Blocker 1**: None currently
  - **How to Unblock**: N/A

## Files Modified

In a real requirement, this would list:

- `app/services/cache.py` - Implemented CacheService
- `app/services/recommendation.py` - Integrated cache
- `app/db/migrations/versions/004_add_cache_table.sql` - Migration
- `tests/test_cache_service.py` - Tests
- `docs/guides/oracle-performance.md` - Documentation

## Research Outputs

In a real requirement, this would reference:

- `research/oracle-caching-patterns.md` - Expert research on Oracle caching
- `research/cache-ttl-analysis.md` - Expert analysis of TTL strategies
- `research/performance-benchmarks.md` - Performance measurements

## Agent Coordination History

In a real requirement, this would show:

- **2025-10-09 14:30**: Planner created PRD and tasks
- **2025-10-09 15:00**: Expert researched caching patterns (wrote to research/)
- **2025-10-09 16:30**: Expert implemented CacheService
- **2025-10-09 17:45**: Testing created 12 tests, all passing
- **2025-10-09 19:00**: Docs & Vision completed quality review and cleanup

## How to Continue

1. If implementing: Run `/implement` to continue where Expert left off
2. If testing: Run `/test` to create/run tests
3. If reviewing: Run `/review` for quality gate + documentation + cleanup
4. If planning new work: Run `/plan {new-feature}`

## Context for Next Agent

**For Expert**: Implementation patterns established, follow cache TTL approach
**For Testing**: Focus on cache hit/miss scenarios, TTL expiration
**For Docs & Vision**: Update oracle-performance.md and architecture.md
