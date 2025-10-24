# Oracle Database JSON Guide

Comprehensive guide to JSON features in Oracle Database 23ai, including JSON Relational Duality, native JSON data type, query functions, and integration patterns with this application's architecture.

## Table of Contents

- [Overview](#overview)
- [Quick Reference](#quick-reference)
- [JSON Data Type](#json-data-type)
- [JSON Validation](#json-validation)
- [JSON Query Functions](#json-query-functions)
- [JSON Relational Duality](#json-relational-duality)
- [JSON Indexes](#json-indexes)
- [Python Integration](#python-integration)
- [Performance Optimization](#performance-optimization)
- [Integration with Vector Search](#integration-with-vector-search)
- [Migration Patterns](#migration-patterns)
- [Troubleshooting](#troubleshooting)

## Overview

Oracle Database 23ai provides native JSON support with:

- **JSON data type**: Native binary format (OSON) for optimal performance
- **JSON Relational Duality**: Unified relational and document model
- **Rich query functions**: JSON_VALUE, JSON_QUERY, JSON_TABLE, JSON_EXISTS
- **Flexible indexing**: Functional indexes, multivalue indexes, search indexes
- **ACID transactions**: Full transactional consistency for JSON documents
- **Type safety**: Schema validation with IS JSON constraints

**Key Capabilities**:

- Store JSON as VARCHAR2, CLOB, or BLOB with validation
- Query JSON with SQL and dot notation
- Create updateable views that present tables as JSON collections
- Index nested JSON properties for performance
- Integrate JSON metadata with VECTOR embeddings

**Performance**: Oracle's OSON (Optimized Storage for JSON) format provides faster parsing and querying than text-based JSON storage.

## Quick Reference

| Operation            | SQL Syntax                                                             | Python Example                                                                      |
| -------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Store JSON           | `INSERT INTO products (metadata) VALUES ('{"color": "blue"}')`         | `cursor.execute("INSERT INTO products (metadata) VALUES (:1)", [json.dumps(data)])` |
| Extract scalar       | `SELECT JSON_VALUE(metadata, '$.color') FROM products`                 | `cursor.execute("SELECT JSON_VALUE(metadata, '$.color') FROM products")`            |
| Extract object/array | `SELECT JSON_QUERY(metadata, '$.tags') FROM products`                  | `cursor.execute("SELECT JSON_QUERY(metadata, '$.tags') FROM products")`             |
| Check existence      | `WHERE JSON_EXISTS(metadata, '$.tags[*]?(@.type == "featured")')`      | Filter with JSON path expression                                                    |
| Convert to rows      | `SELECT jt.* FROM products, JSON_TABLE(metadata, '$' COLUMNS ...)`     | Parse JSON in Python or use JSON_TABLE                                              |
| Duality view         | `CREATE JSON RELATIONAL DUALITY VIEW product_dv AS SELECT ...`         | Access via REST or SQL                                                              |
| Validate             | `metadata JSON` or `CHECK (metadata IS JSON)`                          | Python validates before insert                                                      |
| Index property       | `CREATE INDEX idx_color ON products (JSON_VALUE(metadata, '$.color'))` | Transparent acceleration                                                            |

## JSON Data Type

### Native JSON Column

Oracle 23ai supports JSON as a first-class data type:

```sql
CREATE TABLE products (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    description CLOB,
    price NUMBER(10, 2) NOT NULL,
    category VARCHAR2(100),

    -- JSON column with native validation
    metadata JSON,

    -- Vector embedding
    embedding VECTOR(768, FLOAT32),

    created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
    updated_at TIMESTAMP DEFAULT SYSTIMESTAMP
);
```

**JSON Column Types**:

- `JSON` (23ai+): Native binary format (OSON), best performance
- `VARCHAR2(4000)` with `IS JSON` constraint: Small documents
- `CLOB` with `IS JSON` constraint: Large documents (>4KB)
- `BLOB` with `IS JSON` constraint: Binary storage

**Native JSON Benefits**:

- Automatic validation at insert/update
- Optimized storage format (OSON)
- Faster query performance
- Native indexing support

### Example: Product Metadata

```sql
INSERT INTO products (name, description, price, category, metadata)
VALUES (
    'Ethiopian Yirgacheffe',
    'Bright and floral with notes of bergamot',
    24.99,
    'coffee',
    JSON('{"origin": "Ethiopia", "process": "washed", "altitude": "1900-2200m", "notes": ["floral", "citrus", "tea-like"], "roast_level": "light"}')
);
```

**Metadata Schema Example**:

```json
{
  "origin": "Ethiopia",
  "region": "Yirgacheffe",
  "process": "washed",
  "altitude": "1900-2200m",
  "notes": ["floral", "citrus", "tea-like"],
  "roast_level": "light",
  "certifications": ["organic", "fair-trade"],
  "cupping_score": 92,
  "harvest_date": "2024-11",
  "available_sizes": [
    { "size": "12oz", "price": 24.99 },
    { "size": "5lb", "price": 89.99 }
  ]
}
```

## JSON Validation

### IS JSON Constraint

Validate JSON format at database level:

```sql
-- Method 1: Native JSON type (automatic validation)
CREATE TABLE products (
    metadata JSON
);

-- Method 2: IS JSON constraint on text columns
CREATE TABLE products (
    metadata CLOB CHECK (metadata IS JSON)
);

-- Method 3: Strict validation with schema
CREATE TABLE products (
    metadata CLOB CHECK (metadata IS JSON STRICT)
);
```

**Validation Modes**:

- `IS JSON`: Lenient (allows duplicate keys)
- `IS JSON STRICT`: Strict (rejects duplicate keys)
- `IS JSON (WITH UNIQUE KEYS)`: Explicit uniqueness check

### Schema Validation

Oracle 23ai supports JSON Schema validation:

```sql
-- Create JSON schema
CREATE TABLE product_schema (
    schema_name VARCHAR2(100) PRIMARY KEY,
    schema_doc JSON
);

INSERT INTO product_schema (schema_name, schema_doc)
VALUES ('product_metadata_v1', JSON('{
    "type": "object",
    "properties": {
        "origin": {"type": "string"},
        "process": {"type": "string", "enum": ["washed", "natural", "honey"]},
        "altitude": {"type": "string"},
        "notes": {"type": "array", "items": {"type": "string"}},
        "roast_level": {"type": "string", "enum": ["light", "medium", "dark"]},
        "cupping_score": {"type": "number", "minimum": 0, "maximum": 100}
    },
    "required": ["origin", "roast_level"]
}'));

-- Apply schema validation (23ai feature)
ALTER TABLE products
ADD CONSTRAINT chk_metadata_schema
CHECK (JSON_SCHEMA_VALID('product_metadata_v1', metadata) = 1);
```

### Python Validation

Validate JSON before insert:

```python
import json
from typing import Any

def validate_product_metadata(metadata: dict[str, Any]) -> bool:
    """Validate product metadata structure."""
    required_fields = ["origin", "roast_level"]
    valid_roast_levels = ["light", "medium", "dark"]

    # Check required fields
    for field in required_fields:
        if field not in metadata:
            raise ValueError(f"Missing required field: {field}")

    # Validate roast level
    if metadata["roast_level"] not in valid_roast_levels:
        raise ValueError(f"Invalid roast_level: {metadata['roast_level']}")

    # Validate cupping score
    if "cupping_score" in metadata:
        score = metadata["cupping_score"]
        if not isinstance(score, (int, float)) or score < 0 or score > 100:
            raise ValueError(f"Invalid cupping_score: {score}")

    return True

# Usage
metadata = {
    "origin": "Ethiopia",
    "roast_level": "light",
    "cupping_score": 92
}

validate_product_metadata(metadata)

# Insert with validation
cursor.execute(
    """
    INSERT INTO products (name, price, category, metadata)
    VALUES (:name, :price, :category, :metadata)
    """,
    name="Ethiopian Yirgacheffe",
    price=24.99,
    category="coffee",
    metadata=json.dumps(metadata)
)
```

## JSON Query Functions

### JSON_VALUE - Extract Scalar Values

Extract single scalar values from JSON:

```sql
-- Extract string value
SELECT
    id,
    name,
    JSON_VALUE(metadata, '$.origin') as origin,
    JSON_VALUE(metadata, '$.roast_level') as roast_level
FROM products
WHERE category = 'coffee';

-- Extract numeric value
SELECT
    id,
    name,
    JSON_VALUE(metadata, '$.cupping_score' RETURNING NUMBER) as cupping_score
FROM products
WHERE JSON_VALUE(metadata, '$.cupping_score' RETURNING NUMBER) >= 90;

-- With error handling
SELECT
    id,
    name,
    JSON_VALUE(metadata, '$.origin' ERROR ON ERROR) as origin,
    JSON_VALUE(metadata, '$.cupping_score' DEFAULT -1 ON ERROR) as score
FROM products;
```

**JSON_VALUE Syntax**:

```sql
JSON_VALUE(
    json_column,
    'json_path'
    [RETURNING datatype]
    [ERROR | NULL | DEFAULT value ON ERROR]
    [ERROR | NULL | DEFAULT value ON EMPTY]
)
```

### JSON_QUERY - Extract Objects and Arrays

Extract complex JSON structures:

```sql
-- Extract array
SELECT
    id,
    name,
    JSON_QUERY(metadata, '$.notes') as tasting_notes
FROM products;

-- Extract nested object
SELECT
    id,
    name,
    JSON_QUERY(metadata, '$.available_sizes[*]') as sizes
FROM products;

-- Extract with formatting
SELECT
    id,
    JSON_QUERY(metadata, '$' PRETTY) as formatted_metadata
FROM products;
```

**JSON_QUERY Returns**:

- Objects: `{"key": "value"}`
- Arrays: `["item1", "item2"]`
- Always returns JSON string, never scalar

### JSON_TABLE - Convert JSON to Relational

Transform JSON documents into relational rows:

```sql
-- Extract nested data into columns
SELECT
    p.id,
    p.name,
    jt.size,
    jt.price as size_price
FROM products p,
     JSON_TABLE(
         p.metadata,
         '$.available_sizes[*]'
         COLUMNS (
             size VARCHAR2(20) PATH '$.size',
             price NUMBER PATH '$.price'
         )
     ) jt
WHERE p.category = 'coffee';

-- Complex nested extraction
SELECT
    p.id,
    p.name,
    jt.origin,
    jt.process,
    jt.altitude,
    jt.note
FROM products p,
     JSON_TABLE(
         p.metadata,
         '$'
         COLUMNS (
             origin VARCHAR2(100) PATH '$.origin',
             process VARCHAR2(50) PATH '$.process',
             altitude VARCHAR2(50) PATH '$.altitude',
             NESTED PATH '$.notes[*]'
                 COLUMNS (note VARCHAR2(100) PATH '$')
         )
     ) jt;
```

**Result**:

```
ID | NAME                    | ORIGIN   | PROCESS | ALTITUDE    | NOTE
---|-------------------------|----------|---------|-------------|----------
1  | Ethiopian Yirgacheffe   | Ethiopia | washed  | 1900-2200m  | floral
1  | Ethiopian Yirgacheffe   | Ethiopia | washed  | 1900-2200m  | citrus
1  | Ethiopian Yirgacheffe   | Ethiopia | washed  | 1900-2200m  | tea-like
```

### JSON_EXISTS - Filter by JSON Content

Check for JSON path existence:

```sql
-- Products with organic certification
SELECT id, name
FROM products
WHERE JSON_EXISTS(
    metadata,
    '$.certifications[*]?(@.string() == "organic")'
);

-- Products with high cupping scores
SELECT id, name
FROM products
WHERE JSON_EXISTS(
    metadata,
    '$?(@.cupping_score >= 90)'
);

-- Products from specific region
SELECT id, name
FROM products
WHERE JSON_EXISTS(
    metadata,
    '$.region?(@.string() == "Yirgacheffe")'
);
```

## JSON Relational Duality

JSON Relational Duality Views provide a unified interface for relational and document data models.

### What is Relational Duality?

**Key Concept**: Store data in relational tables, query as JSON documents.

**Benefits**:

- Single source of truth (relational tables)
- ACID transactions for JSON operations
- REST API auto-generated from views
- Bi-directional updates (SQL ↔ JSON)
- No data duplication or ETL

### Creating Duality Views

```sql
-- Create duality view for products with related data
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW product_dv AS
SELECT JSON {
    '_id': p.id,
    'name': p.name,
    'description': p.description,
    'price': p.price,
    'category': p.category,
    'metadata': p.metadata,
    'in_stock': p.in_stock,
    'reviews': [
        SELECT JSON {
            'review_id': r.id,
            'rating': r.rating,
            'comment': r.comment,
            'reviewer': r.reviewer_name,
            'created_at': r.created_at
        }
        FROM reviews r
        WHERE r.product_id = p.id
    ]
}
FROM products p
WITH INSERT UPDATE DELETE;
```

**View Options**:

- `WITH INSERT`: Allow document inserts
- `WITH UPDATE`: Allow document updates
- `WITH DELETE`: Allow document deletes
- `WITH INSERT UPDATE DELETE`: All operations enabled

### Querying Duality Views

```sql
-- Query as JSON documents
SELECT * FROM product_dv
WHERE JSON_VALUE(data, '$.category') = 'coffee';

-- Query with JSON_TABLE
SELECT
    jt._id,
    jt.name,
    jt.price
FROM product_dv,
     JSON_TABLE(
         data, '$'
         COLUMNS (
             _id NUMBER PATH '$._id',
             name VARCHAR2(255) PATH '$.name',
             price NUMBER PATH '$.price'
         )
     ) jt;
```

### Inserting via Duality Views

```sql
-- Insert new product as JSON document
INSERT INTO product_dv VALUES ('{
    "name": "Colombian Supremo",
    "description": "Balanced and smooth",
    "price": 19.99,
    "category": "coffee",
    "in_stock": true,
    "metadata": {
        "origin": "Colombia",
        "process": "washed",
        "roast_level": "medium"
    }
}');

-- Underlying products table automatically updated
```

### Updating via Duality Views

```sql
-- Update entire document
UPDATE product_dv
SET data = JSON_MERGEPATCH(data, '{
    "price": 22.99,
    "in_stock": false
}')
WHERE JSON_VALUE(data, '$._id') = 123;

-- Update specific field
UPDATE product_dv
SET data = JSON_TRANSFORM(
    data,
    SET '$.metadata.roast_level' = 'dark'
)
WHERE JSON_VALUE(data, '$.name') = 'Colombian Supremo';
```

### REST API Auto-Generation

Oracle REST Data Services (ORDS) auto-generates REST APIs from duality views:

```bash
# GET all products
curl -X GET https://your-ords-url/product_dv/

# GET specific product
curl -X GET https://your-ords-url/product_dv/123

# POST new product
curl -X POST https://your-ords-url/product_dv/ \
  -H "Content-Type: application/json" \
  -d '{"name": "New Coffee", "price": 24.99}'

# PATCH update product
curl -X PATCH https://your-ords-url/product_dv/123 \
  -H "Content-Type: application/json" \
  -d '{"price": 22.99}'

# DELETE product
curl -X DELETE https://your-ords-url/product_dv/123
```

## JSON Indexes

### Functional Indexes

Index specific JSON properties for query performance:

```sql
-- Index origin field
CREATE INDEX idx_product_origin
ON products (JSON_VALUE(metadata, '$.origin'));

-- Index cupping score (numeric)
CREATE INDEX idx_product_cupping_score
ON products (JSON_VALUE(metadata, '$.cupping_score' RETURNING NUMBER));

-- Index roast level
CREATE INDEX idx_product_roast_level
ON products (JSON_VALUE(metadata, '$.roast_level'));

-- Composite index
CREATE INDEX idx_product_origin_roast
ON products (
    JSON_VALUE(metadata, '$.origin'),
    JSON_VALUE(metadata, '$.roast_level')
);
```

**Query Using Index**:

```sql
-- Uses idx_product_origin
SELECT id, name, price
FROM products
WHERE JSON_VALUE(metadata, '$.origin') = 'Ethiopia';

-- Uses idx_product_cupping_score
SELECT id, name
FROM products
WHERE JSON_VALUE(metadata, '$.cupping_score' RETURNING NUMBER) >= 90
ORDER BY JSON_VALUE(metadata, '$.cupping_score' RETURNING NUMBER) DESC;
```

### Multivalue Indexes

Index array elements for efficient filtering:

```sql
-- Index array values (certifications)
CREATE MULTIVALUE INDEX idx_product_certifications
ON products (
    JSON_VALUE(metadata, '$.certifications[*]' RETURNING VARCHAR2(100))
);

-- Index array values (tasting notes)
CREATE MULTIVALUE INDEX idx_product_notes
ON products (
    JSON_VALUE(metadata, '$.notes[*]' RETURNING VARCHAR2(100))
);
```

**Query Using Multivalue Index**:

```sql
-- Efficiently find products with specific certification
SELECT id, name
FROM products
WHERE JSON_EXISTS(
    metadata,
    '$.certifications[*]?(@.string() == "organic")'
);

-- Find products with specific tasting note
SELECT id, name
FROM products
WHERE JSON_EXISTS(
    metadata,
    '$.notes[*]?(@.string() == "floral")'
);
```

### JSON Search Indexes

Full-text search on JSON content:

```sql
-- Create search index on JSON column
CREATE SEARCH INDEX idx_product_metadata_search
ON products (metadata)
FOR JSON;

-- Query with text search
SELECT id, name, SCORE(1)
FROM products
WHERE JSON_TEXTCONTAINS(metadata, '$', 'floral citrus', 1)
ORDER BY SCORE(1) DESC;
```

## Python Integration

### Inserting JSON Data

```python
import json
import oracledb

# Connect
connection = oracledb.connect(
    user="user",
    password="password",
    dsn="localhost:1521/FREEPDB1"
)
cursor = connection.cursor()

# Product metadata
metadata = {
    "origin": "Ethiopia",
    "region": "Yirgacheffe",
    "process": "washed",
    "altitude": "1900-2200m",
    "notes": ["floral", "citrus", "tea-like"],
    "roast_level": "light",
    "certifications": ["organic", "fair-trade"],
    "cupping_score": 92
}

# Insert with JSON
cursor.execute(
    """
    INSERT INTO products (name, description, price, category, metadata)
    VALUES (:name, :description, :price, :category, :metadata)
    """,
    name="Ethiopian Yirgacheffe",
    description="Bright and floral with notes of bergamot",
    price=24.99,
    category="coffee",
    metadata=json.dumps(metadata)  # Convert dict to JSON string
)

connection.commit()
```

### Querying JSON Data

```python
# Query with JSON extraction
cursor.execute(
    """
    SELECT
        id,
        name,
        price,
        JSON_VALUE(metadata, '$.origin') as origin,
        JSON_VALUE(metadata, '$.roast_level') as roast_level,
        JSON_VALUE(metadata, '$.cupping_score' RETURNING NUMBER) as score
    FROM products
    WHERE category = :category
        AND JSON_VALUE(metadata, '$.cupping_score' RETURNING NUMBER) >= :min_score
    ORDER BY JSON_VALUE(metadata, '$.cupping_score' RETURNING NUMBER) DESC
    """,
    category="coffee",
    min_score=90
)

for row in cursor:
    print(f"{row[1]} ({row[3]}) - Score: {row[5]}, ${row[2]}")
```

### Updating JSON Data

```python
# Update entire metadata
new_metadata = {
    "origin": "Ethiopia",
    "process": "natural",  # Changed
    "roast_level": "medium",  # Changed
    "cupping_score": 94  # Updated
}

cursor.execute(
    """
    UPDATE products
    SET metadata = :metadata,
        updated_at = SYSTIMESTAMP
    WHERE id = :product_id
    """,
    metadata=json.dumps(new_metadata),
    product_id=123
)

# Partial update with JSON_MERGEPATCH
cursor.execute(
    """
    UPDATE products
    SET metadata = JSON_MERGEPATCH(metadata, :patch),
        updated_at = SYSTIMESTAMP
    WHERE id = :product_id
    """,
    patch=json.dumps({"price": 22.99, "in_stock": False}),
    product_id=123
)

connection.commit()
```

### Working with JSON Arrays

```python
# Fetch array elements
cursor.execute(
    """
    SELECT
        id,
        name,
        JSON_QUERY(metadata, '$.notes') as notes_json
    FROM products
    WHERE id = :product_id
    """,
    product_id=123
)

row = cursor.fetchone()
notes = json.loads(row[2])  # Parse JSON array
print(f"Tasting notes: {', '.join(notes)}")

# Use JSON_TABLE to flatten arrays
cursor.execute(
    """
    SELECT
        p.id,
        p.name,
        jt.note
    FROM products p,
         JSON_TABLE(
             p.metadata,
             '$.notes[*]'
             COLUMNS (note VARCHAR2(100) PATH '$')
         ) jt
    WHERE p.id = :product_id
    """,
    product_id=123
)

for row in cursor:
    print(f"Note: {row[2]}")
```

## Performance Optimization

### Query Optimization

```sql
-- Use JSON_EXISTS for filtering (can use indexes)
-- GOOD
SELECT id, name
FROM products
WHERE JSON_EXISTS(metadata, '$.origin?(@.string() == "Ethiopia")');

-- AVOID (function in WHERE clause harder to optimize)
SELECT id, name
FROM products
WHERE JSON_VALUE(metadata, '$.origin') = 'Ethiopia';
```

### Materialized Views

Pre-compute frequently accessed JSON data:

```sql
-- Materialized view with JSON extraction
CREATE MATERIALIZED VIEW mv_product_summary
BUILD IMMEDIATE
REFRESH FAST ON COMMIT
AS
SELECT
    id,
    name,
    price,
    JSON_VALUE(metadata, '$.origin') as origin,
    JSON_VALUE(metadata, '$.roast_level') as roast_level,
    JSON_VALUE(metadata, '$.cupping_score' RETURNING NUMBER) as cupping_score
FROM products;

-- Query materialized view (fast)
SELECT * FROM mv_product_summary
WHERE origin = 'Ethiopia'
  AND cupping_score >= 90;
```

### JSON Expression Caching

Oracle automatically caches JSON path expressions:

```sql
-- Set JSON_EXPRESSION_CHECK for validation
ALTER SESSION SET JSON_EXPRESSION_CHECK = 'ERROR';  -- Strict validation
-- or
ALTER SESSION SET JSON_EXPRESSION_CHECK = 'WARNING';  -- Log warnings
-- or
ALTER SESSION SET JSON_EXPRESSION_CHECK = 'IGNORE';  -- No validation (faster)
```

### Storage Optimization

```sql
-- Use native JSON type for optimal storage
CREATE TABLE products (
    metadata JSON  -- OSON format, compressed, optimized
);

-- For very large JSON documents, use BLOB with compression
CREATE TABLE products (
    metadata BLOB CHECK (metadata IS JSON)
)
LOB (metadata) STORE AS SECUREFILE (
    COMPRESS HIGH
    CACHE
);
```

## Integration with Vector Search

Combine JSON metadata filtering with vector similarity search:

```sql
-- Vector search with JSON metadata filtering
SELECT
    id,
    name,
    1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) as similarity,
    JSON_VALUE(metadata, '$.origin') as origin,
    JSON_VALUE(metadata, '$.roast_level') as roast_level
FROM products
WHERE
    -- JSON filters
    JSON_VALUE(metadata, '$.roast_level') = 'light'
    AND JSON_EXISTS(metadata, '$.certifications[*]?(@.string() == "organic")')
    -- Vector similarity filter
    AND 1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) >= :threshold
ORDER BY VECTOR_DISTANCE(embedding, :query_vector, COSINE)
FETCH FIRST :limit ROWS ONLY;
```

**Python Implementation**:

```python
import array
import json

async def search_with_metadata_filter(
    query_embedding: list[float],
    roast_level: str | None = None,
    min_cupping_score: float | None = None,
    certifications: list[str] | None = None,
    similarity_threshold: float = 0.7,
    limit: int = 5
) -> list[dict]:
    """Vector search with JSON metadata filtering."""

    # Build dynamic SQL
    sql_conditions = [
        "1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) >= :threshold"
    ]
    params = {
        "query_vector": array.array('f', query_embedding),
        "threshold": similarity_threshold,
        "limit": limit
    }

    if roast_level:
        sql_conditions.append("JSON_VALUE(metadata, '$.roast_level') = :roast_level")
        params["roast_level"] = roast_level

    if min_cupping_score:
        sql_conditions.append(
            "JSON_VALUE(metadata, '$.cupping_score' RETURNING NUMBER) >= :min_score"
        )
        params["min_score"] = min_cupping_score

    if certifications:
        # Add condition for each certification
        for i, cert in enumerate(certifications):
            sql_conditions.append(
                f"JSON_EXISTS(metadata, '$.certifications[*]?(@.string() == :cert{i})')"
            )
            params[f"cert{i}"] = cert

    sql = f"""
        SELECT
            id,
            name,
            description,
            price,
            1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) as similarity,
            JSON_QUERY(metadata, '$') as metadata_json
        FROM products
        WHERE {' AND '.join(sql_conditions)}
        ORDER BY VECTOR_DISTANCE(embedding, :query_vector, COSINE)
        FETCH FIRST :limit ROWS ONLY
    """

    cursor.execute(sql, **params)
    results = []
    for row in cursor:
        results.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "price": row[3],
            "similarity": row[4],
            "metadata": json.loads(row[5])
        })

    return results
```

## Migration Patterns

### From PostgreSQL JSONB

```sql
-- PostgreSQL JSONB
CREATE TABLE products (
    metadata JSONB
);

-- Oracle equivalent
CREATE TABLE products (
    metadata JSON  -- or BLOB with IS JSON constraint
);

-- PostgreSQL operators
SELECT * FROM products WHERE metadata @> '{"origin": "Ethiopia"}';
SELECT * FROM products WHERE metadata ? 'origin';
SELECT metadata ->> 'origin' FROM products;

-- Oracle equivalents
SELECT * FROM products
WHERE JSON_EXISTS(metadata, '$.origin?(@.string() == "Ethiopia")');

SELECT * FROM products
WHERE JSON_EXISTS(metadata, '$.origin');

SELECT JSON_VALUE(metadata, '$.origin') FROM products;
```

### Migrating Data

```python
# PostgreSQL → Oracle migration
import psycopg2
import oracledb
import json

# Source (PostgreSQL)
pg_conn = psycopg2.connect("postgresql://...")
pg_cursor = pg_conn.cursor()

# Target (Oracle)
oracle_conn = oracledb.connect(user="...", password="...", dsn="...")
oracle_cursor = oracle_conn.cursor()

# Fetch from PostgreSQL
pg_cursor.execute("SELECT id, name, metadata FROM products")

# Insert into Oracle
for row in pg_cursor:
    product_id, name, metadata = row

    # metadata is already dict from psycopg2
    metadata_json = json.dumps(metadata)

    oracle_cursor.execute(
        """
        INSERT INTO products (id, name, metadata)
        VALUES (:id, :name, :metadata)
        """,
        id=product_id,
        name=name,
        metadata=metadata_json
    )

oracle_conn.commit()
```

## Troubleshooting

### Issue: JSON validation fails

**Symptom**:

```
ORA-40441: JSON syntax error
```

**Solution**:

```python
# Validate JSON before insert
import json

def validate_json(data):
    try:
        json.dumps(data)  # Will raise ValueError if invalid
        return True
    except (ValueError, TypeError) as e:
        print(f"Invalid JSON: {e}")
        return False

# Use before insert
if validate_json(metadata):
    cursor.execute("INSERT INTO products (metadata) VALUES (:1)", [json.dumps(metadata)])
```

### Issue: JSON_VALUE returns NULL

**Symptom**:

```sql
SELECT JSON_VALUE(metadata, '$.origin') FROM products;
-- Returns NULL for all rows
```

**Solution**:

```sql
-- Check JSON path syntax
SELECT JSON_QUERY(metadata, '$' PRETTY) FROM products;

-- Use ERROR ON ERROR to see issues
SELECT JSON_VALUE(metadata, '$.origin' ERROR ON ERROR) FROM products;

-- Verify JSON is valid
SELECT metadata FROM products WHERE metadata IS JSON;
```

### Issue: Slow JSON queries

**Symptom**: Queries with JSON_VALUE in WHERE clause are slow.

**Solution**:

```sql
-- Create functional index
CREATE INDEX idx_product_origin
ON products (JSON_VALUE(metadata, '$.origin'));

-- Verify index usage
EXPLAIN PLAN FOR
SELECT * FROM products
WHERE JSON_VALUE(metadata, '$.origin') = 'Ethiopia';

SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);
```

### Issue: Cannot update nested JSON property

**Symptom**: Need to update deep nested value without replacing entire document.

**Solution**:

```sql
-- Use JSON_TRANSFORM
UPDATE products
SET metadata = JSON_TRANSFORM(
    metadata,
    SET '$.available_sizes[0].price' = 29.99
)
WHERE id = 123;

-- Or JSON_MERGEPATCH for partial updates
UPDATE products
SET metadata = JSON_MERGEPATCH(metadata, '{
    "available_sizes": [
        {"size": "12oz", "price": 29.99}
    ]
}')
WHERE id = 123;
```

## See Also

- [Oracle Vector Search Guide](oracle-vector-search.md) - Vector similarity search integration
- [Oracle Performance Guide](oracle-performance.md) - Query optimization
- [SQLSpec Patterns](sqlspec-patterns.md) - Service layer integration
- [Architecture Overview](architecture.md) - System design

## Resources

- Oracle JSON Developer's Guide: <https://docs.oracle.com/en/database/oracle/oracle-database/23/adjsn/>
- JSON Relational Duality: <https://docs.oracle.com/en/database/oracle/oracle-database/23/jsnvu/>
- python-oracledb JSON support: <https://python-oracledb.readthedocs.io/en/latest/user_guide/json_data_type.html>
