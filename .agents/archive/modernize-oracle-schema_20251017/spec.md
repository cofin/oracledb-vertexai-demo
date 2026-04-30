# Spec: Modernize Oracle Schema & Fix Data Model Parity

## Overview
Add the missing `store` table to match the PostgreSQL reference, and modernize all data types to use Oracle 23ai native features (BOOLEAN, JSON, VECTOR). Update domain services to handle the new types correctly.

## Goals
1. **Achieve Schema Parity**: Oracle schema matches PostgreSQL feature set.
2. **Use Modern Types**: Leverage Oracle 23ai native BOOLEAN and VECTOR types.
3. **Fix Fixture Loading**: All fixtures load successfully.
4. **Update DDD Services**: Ensure `app/domain/products/` handles the modernized types.

## Implementation Plan

### Phase 1: Database Schema Updates
- [x] Task bd-3o1.1: Update `app/db/migrations/0001_cymball_coffee_products.sql` to add `store` table.
- [x] Task bd-3o1.2: Modernize boolean and timestamp columns in migrations.

### Phase 2: Fixtures & Application Code
- [x] Task bd-3o1.3: Update `app/db/utils.py` fixture table order.
- [x] Task bd-3o1.4: Update `app/domain/products/services/_product.py` for correct boolean handling.
- [x] Task bd-3o1.5: Test fixture loading (`uv run app db load-fixtures`).

### Phase 3: Documentation & Verification
- [x] Task bd-3o1.6: Update schema documentation and README.
- [x] Task bd-3o1.7: Run integration tests to verify metrics and product searches.
