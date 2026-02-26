# Oracle Database 23ai Data Types Research

> **Research Date**: 2025-10-17
> **Oracle Version**: Oracle Database 23ai Free
> **Sources**: Context7 Oracle Documentation, python-oracledb docs, Web Search (2025)
> **Purpose**: Comprehensive guide for data type best practices in Oracle 23ai

---

## Table of Contents

1. [Boolean Data Type](#1-boolean-data-type)
2. [JSON Storage Options](#2-json-storage-options)
3. [Vector Data Types](#3-vector-data-types)
4. [Identity Columns](#4-identity-columns)
5. [Timestamp Types](#5-timestamp-types)
6. [Summary & Recommendations](#summary--recommendations)

---

## 1. Boolean Data Type

### ✅ **Native BOOLEAN Support Available**

Oracle Database 23ai introduced **native BOOLEAN data type** support in SQL - a major enhancement that brings Oracle in line with other modern database platforms.

#### **Key Features**

- **ISO SQL Standard Compliant**: Fully compliant with ISO SQL standard BOOLEAN type
- **Native Support**: First-class data type in both SQL and PL/SQL
- **Client Driver Support**: python-oracledb 2.x+ supports binding and fetching BOOLEAN values
- **Available in**: Oracle 23ai (all editions including Free)

#### **Syntax**

```sql
-- Create table with BOOLEAN column
CREATE TABLE products (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    in_stock BOOLEAN DEFAULT TRUE,  -- Native BOOLEAN type
    is_featured BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert with BOOLEAN values
INSERT INTO products (name, in_stock, is_featured)
VALUES ('Espresso Beans', TRUE, FALSE);

-- Query with BOOLEAN conditions
SELECT * FROM products WHERE in_stock = TRUE;
```

#### **Python Integration (python-oracledb)**

```python
import oracledb

# Binding BOOLEAN values
cursor.execute(
    """
    INSERT INTO products (name, in_stock, is_featured)
    VALUES (:name, :in_stock, :featured)
    """,
    name="Coffee Beans",
    in_stock=True,  # Python bool → Oracle BOOLEAN
    featured=False
)

# Fetching BOOLEAN values
cursor.execute("SELECT id, name, in_stock FROM products WHERE id = 1")
product_id, name, in_stock = cursor.fetchone()
print(f"In stock: {in_stock}")  # Returns Python bool
```

#### **Type Conversions (PLSQL_IMPLICIT_CONVERSION_BOOL)**

Oracle 23ai includes the `PLSQL_IMPLICIT_CONVERSION_BOOL` parameter for controlling implicit type conversions:

```sql
-- Enable implicit conversions (not recommended for new code)
ALTER SESSION SET PLSQL_IMPLICIT_CONVERSION_BOOL = TRUE;

-- When TRUE:
-- Numeric → BOOLEAN: 0 = FALSE, non-zero = TRUE
-- BOOLEAN → Numeric: TRUE = 1, FALSE = 0
-- Character → BOOLEAN: 'true', 't', 'yes', 'y', '1', 'on' = TRUE (case-insensitive)
--                       'false', 'f', 'no', 'n', '0', 'off' = FALSE
-- BOOLEAN → Character: TRUE = 'TRUE', FALSE = 'FALSE'
```

#### **Best Practices**

✅ **DO**: Use native BOOLEAN for boolean semantics
```sql
CREATE TABLE settings (
    id NUMBER PRIMARY KEY,
    feature_enabled BOOLEAN DEFAULT FALSE  -- Clear, semantic
);
```

❌ **DON'T**: Use NUMBER(1) or CHAR(1) workarounds
```sql
-- OLD WAY (Oracle < 23ai) - avoid in new schemas
CREATE TABLE settings (
    id NUMBER PRIMARY KEY,
    feature_enabled NUMBER(1) DEFAULT 0  -- 0/1 pattern, less clear
);
```

#### **Migration from NUMBER(1) Pattern**

If migrating from older schemas using `NUMBER(1)` for booleans:

```sql
-- Step 1: Add new BOOLEAN column
ALTER TABLE products ADD (in_stock_new BOOLEAN);

-- Step 2: Migrate data
UPDATE products SET in_stock_new = CASE
    WHEN in_stock = 1 THEN TRUE
    WHEN in_stock = 0 THEN FALSE
    ELSE NULL
END;

-- Step 3: Drop old column and rename
ALTER TABLE products DROP COLUMN in_stock;
ALTER TABLE products RENAME COLUMN in_stock_new TO in_stock;
```

---

## 2. JSON Storage Options

### ✅ **Native JSON Type (Recommended)**

Oracle 23ai provides the **JSON data type** (introduced in 21c, enhanced in 23ai) with optimized binary storage.

#### **JSON vs JSONB Comparison**

| Feature | Oracle JSON | PostgreSQL JSONB | Notes |
|---------|-------------|------------------|-------|
| **Binary Storage** | ✅ Yes (OSON format) | ✅ Yes | Oracle uses "Optimized Storage for JSON" (OSON) |
| **Type Name** | `JSON` | `JSONB` | Different names, same concept |
| **Validation** | Automatic | Automatic | Both validate on insert |
| **Indexing** | JSON Search Index, functional indexes | GIN, GiST indexes | Oracle supports multiple index types |
| **Performance** | Optimized for queries | Optimized for queries | Both avoid re-parsing |
| **SQL Access** | `JSON_VALUE`, `JSON_QUERY`, `JSON_TABLE` | `->`, `->>`, `jsonb_path_query` | Different syntax, similar capabilities |

#### **Oracle JSON Storage Formats**

Oracle 23ai supports **three JSON storage formats**:

1. **OSON (Optimized Storage for JSON)** - Default, recommended
   - Binary format (like PostgreSQL JSONB)
   - Fast queries and updates
   - Efficient storage
   - Supports SecureFiles LOBs

2. **TBX (Transportable Binary XML)** - Default for XMLType in 23ai
   - Binary XML storage
   - Used when JSON data also needs XML access

3. **CSX (Not-Transportable Binary XML)** - Legacy
   - Backward compatibility only
   - Not recommended for new applications

#### **Syntax**

```sql
-- Create table with JSON column (uses OSON by default)
CREATE TABLE products (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    metadata JSON,  -- Native JSON type with binary OSON storage
    attributes JSON CHECK (attributes IS JSON),  -- With validation constraint
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert JSON data
INSERT INTO products (name, metadata)
VALUES (
    'Espresso Blend',
    JSON('{"origin": "Colombia", "roast": "dark", "weight_kg": 1.0}')
);

-- Query JSON data
SELECT
    id,
    name,
    JSON_VALUE(metadata, '$.origin') as origin,
    JSON_VALUE(metadata, '$.roast') as roast_level
FROM products
WHERE JSON_VALUE(metadata, '$.origin') = 'Colombia';
```

#### **JSON Modifiers (23ai Feature)**

Oracle 23ai introduces **JSON modifiers** for schema validation:

```sql
-- JSON with specific structure constraints
CREATE TABLE products (
    id NUMBER PRIMARY KEY,
    metadata JSON(OBJECT),     -- Must be JSON object
    tags JSON(ARRAY),          -- Must be JSON array
    price JSON(NUMBER),        -- Must be JSON number
    description JSON(SCALAR)   -- Must be JSON scalar (string, number, boolean, null)
);
```

#### **Python Integration**

```python
import oracledb
import json

# Insert JSON data
metadata = {
    "origin": "Ethiopia",
    "roast": "medium",
    "weight_kg": 1.0,
    "certifications": ["organic", "fair-trade"]
}

cursor.execute(
    """
    INSERT INTO products (name, metadata)
    VALUES (:name, :metadata)
    """,
    name="Ethiopian Blend",
    metadata=json.dumps(metadata)  # Convert dict to JSON string
)

# Fetch JSON data
cursor.execute("SELECT id, name, metadata FROM products WHERE id = 1")
product_id, name, metadata_json = cursor.fetchone()
metadata = json.loads(metadata_json)  # Convert JSON string to dict
print(f"Origin: {metadata['origin']}")
```

#### **JSON Indexing**

```sql
-- Functional index on JSON path (for frequent queries)
CREATE INDEX idx_product_origin
ON products (JSON_VALUE(metadata, '$.origin'));

-- Multivalue index for JSON arrays
CREATE MULTIVALUE INDEX idx_product_tags
ON products (JSON_VALUE(metadata, '$.tags[*]'));

-- JSON Search Index (for text search across all JSON content)
CREATE SEARCH INDEX idx_product_metadata_search
ON products (metadata)
FOR JSON;
```

#### **Best Practices**

✅ **DO**: Use native JSON type for semi-structured data
```sql
CREATE TABLE products (
    id NUMBER PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    metadata JSON  -- Clear, validated, optimized
);
```

✅ **DO**: Add IS JSON constraints for additional safety
```sql
CREATE TABLE products (
    id NUMBER PRIMARY KEY,
    metadata JSON CHECK (metadata IS JSON)  -- Explicit validation
);
```

❌ **DON'T**: Use VARCHAR2/CLOB for JSON without constraints
```sql
-- BAD - no validation, no optimization
CREATE TABLE products (
    id NUMBER PRIMARY KEY,
    metadata VARCHAR2(4000)  -- Can store invalid JSON
);
```

---

## 3. Vector Data Types

### ✅ **Native VECTOR Type (23ai AI Feature)**

Oracle 23ai introduced the **VECTOR data type** for AI/ML workloads, optimized for semantic similarity search.

#### **Comprehensive Vector Type Specifications**

```sql
VECTOR(dimensions, element_type, storage_mode)
```

**Parameters**:
- `dimensions`: 1-65535 (or `*` for flexible)
- `element_type`: FLOAT32, FLOAT64, INT8, BINARY
- `storage_mode`: DENSE (default), SPARSE

#### **Element Type Details**

| Format | Storage | Range | Use Case | Example |
|--------|---------|-------|----------|---------|
| **FLOAT32** | 32-bit float | ±3.4e38 | Default, most embeddings | `VECTOR(768, FLOAT32)` |
| **FLOAT64** | 64-bit float | ±1.7e308 | Higher precision (rare) | `VECTOR(768, FLOAT64)` |
| **INT8** | 8-bit signed int | -128 to 127 | Quantized embeddings | `VECTOR(768, INT8)` |
| **BINARY** | 1 bit per dimension | 0-1 | Maximum compression | `VECTOR(1024, BINARY)` |

#### **Storage Calculation**

```python
# FLOAT32 (recommended for Vertex AI embeddings)
storage_bytes = dimensions * 4
# Example: 768 dimensions * 4 = 3,072 bytes

# FLOAT64 (higher precision)
storage_bytes = dimensions * 8
# Example: 768 dimensions * 8 = 6,144 bytes

# INT8 (quantized)
storage_bytes = dimensions * 1
# Example: 768 dimensions * 1 = 768 bytes

# BINARY (maximum compression)
storage_bytes = dimensions / 8
# Example: 1024 dimensions / 8 = 128 bytes
# Note: BINARY dimensions MUST be multiple of 8
```

#### **Syntax Examples**

```sql
-- Products table with 768-dimensional embeddings (Vertex AI text-embedding-005)
CREATE TABLE products (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    description CLOB,
    price NUMBER(10, 2),
    embedding VECTOR(768, FLOAT32),  -- Fixed dimensions, FLOAT32 format
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table with flexible dimensions (not recommended for production)
CREATE TABLE mixed_vectors (
    id NUMBER PRIMARY KEY,
    embedding VECTOR(*, FLOAT32)  -- Variable dimensions
);

-- Table with multiple vector formats
CREATE TABLE vector_examples (
    id NUMBER PRIMARY KEY,
    vec_float32 VECTOR(3, FLOAT32),     -- 3 dims, 32-bit float
    vec_float64 VECTOR(3, FLOAT64),     -- 3 dims, 64-bit float
    vec_int8 VECTOR(3, INT8),           -- 3 dims, 8-bit int
    vec_binary VECTOR(24, BINARY)       -- 24 dims, binary (must be multiple of 8)
);

-- Sparse vector (for TF-IDF, topic models)
CREATE TABLE sparse_vectors (
    id NUMBER PRIMARY KEY,
    embedding VECTOR(768, FLOAT32, SPARSE)  -- Only non-zero values stored
);
```

#### **Python Integration (python-oracledb 2.x)**

```python
import array
import oracledb

# Insert dense vector (recommended method)
embedding = [0.1, 0.2, 0.3, ...]  # 768 dimensions from Vertex AI

# Convert to array.array for Oracle
vector_array = array.array('f', embedding)  # 'f' = FLOAT32

cursor.execute(
    """
    INSERT INTO products (name, embedding)
    VALUES (:name, :embedding)
    """,
    name="Coffee Beans",
    embedding=vector_array
)

# Fetch vector
cursor.execute("SELECT id, name, embedding FROM products WHERE id = 1")
product_id, name, embedding_array = cursor.fetchone()
print(f"Embedding type: {type(embedding_array)}")  # <class 'array.array'>
print(f"Dimensions: {len(embedding_array)}")       # 768

# Convert array.array to list if needed
embedding_list = list(embedding_array)
```

#### **array.array Type Codes**

```python
import array

# FLOAT32 (most common)
vec_float32 = array.array('f', [1.5, 2.0, 3.5])  # 'f' = 4 bytes

# FLOAT64
vec_float64 = array.array('d', [1.5, 2.0, 3.5])  # 'd' = 8 bytes

# INT8
vec_int8 = array.array('b', [1, 2, 3])  # 'b' = signed 1 byte

# BINARY (UINT8)
vec_binary = array.array('B', [201, 15])  # 'B' = unsigned 1 byte
```

#### **Sparse Vectors (Advanced)**

```python
import oracledb
import array

# Sparse vector: 25 total dimensions, only 3 non-zero values
sparse_vector = oracledb.SparseVector(
    num_dimensions=25,
    indices=[6, 10, 18],  # Zero-based indices of non-zero values
    values=array.array('f', [26.25, 129.625, 579.875])
)

cursor.execute(
    "INSERT INTO sparse_table (embedding) VALUES (:vec)",
    vec=sparse_vector
)
```

#### **Vector Indexes**

Oracle 23ai supports two vector index types:

##### **HNSW (Hierarchical Navigable Small World)**

```sql
-- Create HNSW index for cosine similarity
CREATE INDEX idx_product_embedding_hnsw
ON products (embedding)
INDEXTYPE IS HNSW
PARAMETERS ('
    DISTANCE COSINE,
    M 16,
    EF_CONSTRUCTION 64
');
```

**HNSW Parameters**:
- `M`: Max connections per layer (2-100, default 16). Higher = better recall, more memory.
- `EF_CONSTRUCTION`: Build quality (4-1000, default 64). Higher = better index, slower build.
- `DISTANCE`: COSINE, EUCLIDEAN, DOT

**Best for**: Large datasets (>100K vectors), real-time queries, high recall needed

##### **IVFFlat (Inverted File with Flat compression)**

```sql
-- Create IVFFlat index for cosine similarity
CREATE INDEX idx_product_embedding_ivfflat
ON products (embedding)
INDEXTYPE IS IVFFLAT
PARAMETERS ('
    DISTANCE COSINE,
    LISTS 100
');
```

**IVFFlat Parameters**:
- `LISTS`: Number of clusters. Formula: `SQRT(num_rows)`. For 10K rows → ~100 lists.
- `DISTANCE`: COSINE, EUCLIDEAN, DOT

**Best for**: Medium datasets (1K-1M vectors), memory-constrained, development/testing

#### **Best Practices**

✅ **DO**: Use fixed dimensions matching your embedding model
```sql
CREATE TABLE products (
    embedding VECTOR(768, FLOAT32)  -- text-embedding-005 = 768 dims
);
```

✅ **DO**: Use FLOAT32 for most ML embeddings
```sql
-- FLOAT32 is standard for Vertex AI, OpenAI, etc.
embedding VECTOR(768, FLOAT32)
```

✅ **DO**: Add vector column as nullable initially
```sql
-- Allow gradual embedding generation
CREATE TABLE products (
    id NUMBER PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    embedding VECTOR(768, FLOAT32)  -- Nullable, generate asynchronously
);
```

❌ **DON'T**: Use flexible dimensions (`*`) in production
```sql
-- BAD - can't create efficient indexes, dimension mismatches
embedding VECTOR(*, FLOAT32)
```

❌ **DON'T**: Use FLOAT64 unless you have specific precision requirements
```sql
-- BAD - 2x storage, rarely needed
embedding VECTOR(768, FLOAT64)  -- 6,144 bytes vs 3,072 for FLOAT32
```

---

## 4. Identity Columns

### ✅ **GENERATED ALWAYS AS IDENTITY (Recommended)**

Oracle 12c+ supports **identity columns** for auto-incrementing primary keys - the modern replacement for sequences + triggers.

#### **Syntax**

```sql
-- Basic identity column (recommended)
CREATE TABLE products (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Identity with custom options
CREATE TABLE products (
    id NUMBER GENERATED ALWAYS AS IDENTITY (
        START WITH 1000
        INCREMENT BY 1
        MINVALUE 1000
        MAXVALUE 9999999999
        NOCACHE
        NOORDER
    ) PRIMARY KEY,
    name VARCHAR2(255) NOT NULL
);

-- Identity with BY DEFAULT (allows manual inserts)
CREATE TABLE products (
    id NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name VARCHAR2(255) NOT NULL
);
```

#### **GENERATED ALWAYS vs GENERATED BY DEFAULT**

| Feature | GENERATED ALWAYS | GENERATED BY DEFAULT |
|---------|------------------|----------------------|
| **Auto-increment** | ✅ Always | ✅ Always (if not provided) |
| **Manual insert** | ❌ Not allowed | ✅ Allowed |
| **Use case** | Strict auto-increment | Flexible (migrations, imports) |

```sql
-- GENERATED ALWAYS - strict
CREATE TABLE strict_id (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR2(100)
);

INSERT INTO strict_id (name) VALUES ('Product 1');  -- ✅ OK, ID auto-assigned
INSERT INTO strict_id (id, name) VALUES (999, 'Product 2');  -- ❌ ERROR: cannot insert into identity column

-- GENERATED BY DEFAULT - flexible
CREATE TABLE flexible_id (
    id NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name VARCHAR2(100)
);

INSERT INTO flexible_id (name) VALUES ('Product 1');  -- ✅ OK, ID auto-assigned
INSERT INTO flexible_id (id, name) VALUES (999, 'Product 2');  -- ✅ OK, manual ID allowed
```

#### **Python Integration**

```python
import oracledb

# Insert with auto-generated ID
cursor.execute(
    """
    INSERT INTO products (name, price)
    VALUES (:name, :price)
    RETURNING id INTO :new_id
    """,
    name="Coffee Beans",
    price=12.99,
    new_id=cursor.var(int)
)

new_id = cursor.var('new_id').getvalue()[0]
print(f"New product ID: {new_id}")

connection.commit()
```

#### **Inspecting Identity Columns**

```sql
-- View all identity columns in your schema
SELECT
    table_name,
    column_name,
    generation_type,  -- ALWAYS or BY DEFAULT
    identity_options
FROM user_tab_identity_cols
ORDER BY table_name;
```

#### **Best Practices**

✅ **DO**: Use GENERATED ALWAYS AS IDENTITY for new tables
```sql
CREATE TABLE products (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,  -- Modern, clean
    name VARCHAR2(255) NOT NULL
);
```

✅ **DO**: Use NUMBER data type for identity columns
```sql
-- Standard Oracle numeric type
id NUMBER GENERATED ALWAYS AS IDENTITY
```

❌ **DON'T**: Use sequences + triggers for new tables
```sql
-- OLD WAY (Oracle < 12c) - avoid in new schemas
CREATE SEQUENCE products_seq;

CREATE OR REPLACE TRIGGER products_bi
BEFORE INSERT ON products
FOR EACH ROW
BEGIN
    IF :NEW.id IS NULL THEN
        :NEW.id := products_seq.NEXTVAL;
    END IF;
END;
```

#### **Migration from Sequence Pattern**

If migrating from older sequence-based schemas:

```sql
-- Step 1: Note current sequence value
SELECT products_seq.CURRVAL FROM DUAL;  -- e.g., 1500

-- Step 2: Add new identity column
ALTER TABLE products ADD (id_new NUMBER GENERATED ALWAYS AS IDENTITY
    START WITH 1501 INCREMENT BY 1);

-- Step 3: Backfill data
UPDATE products SET id_new = id;

-- Step 4: Drop old column and rename
ALTER TABLE products DROP COLUMN id;
ALTER TABLE products RENAME COLUMN id_new TO id;

-- Step 5: Drop old sequence and trigger
DROP SEQUENCE products_seq;
DROP TRIGGER products_bi;
```

---

## 5. Timestamp Types

### ✅ **TIMESTAMP WITH TIME ZONE (Recommended for UTC)**

Oracle provides robust timestamp types with time zone support. For modern applications, **TIMESTAMP WITH TIME ZONE** is recommended.

#### **Timestamp Type Comparison**

| Type | Size | Time Zone | Use Case |
|------|------|-----------|----------|
| **DATE** | 7 bytes | No | Legacy, date only (no fractional seconds) |
| **TIMESTAMP** | 11 bytes | No | High precision, no time zone |
| **TIMESTAMP WITH TIME ZONE** | 13 bytes | ✅ Yes | **Recommended for UTC timestamps** |
| **TIMESTAMP WITH LOCAL TIME ZONE** | 11 bytes | Converts to session TZ | User-local times |

#### **Syntax**

```sql
-- Recommended: TIMESTAMP WITH TIME ZONE
CREATE TABLE products (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,  -- Stores TZ
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,  -- Stores TZ
    published_at TIMESTAMP WITH TIME ZONE  -- Nullable
);

-- Alternative: TIMESTAMP (no time zone)
CREATE TABLE events (
    id NUMBER PRIMARY KEY,
    event_time TIMESTAMP(6),  -- 6 fractional seconds, no TZ
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- Alternative: TIMESTAMP WITH LOCAL TIME ZONE (converts to session TZ)
CREATE TABLE user_events (
    id NUMBER PRIMARY KEY,
    event_time TIMESTAMP WITH LOCAL TIME ZONE  -- Converts to user's TZ
);
```

#### **Fractional Seconds Precision**

```sql
-- Specify fractional seconds (0-9, default is 6)
CREATE TABLE events (
    event_time TIMESTAMP(3) WITH TIME ZONE,  -- Millisecond precision
    event_time_ns TIMESTAMP(9) WITH TIME ZONE  -- Nanosecond precision
);
```

#### **Python Integration**

```python
import oracledb
from datetime import datetime, timezone

# Insert with timezone-aware datetime
now_utc = datetime.now(timezone.utc)

cursor.execute(
    """
    INSERT INTO products (name, created_at, updated_at)
    VALUES (:name, :created, :updated)
    """,
    name="Coffee Beans",
    created=now_utc,  # Python datetime with tzinfo
    updated=now_utc
)

# Fetch timestamp
cursor.execute("SELECT id, name, created_at FROM products WHERE id = 1")
product_id, name, created_at = cursor.fetchone()
print(f"Created: {created_at}")  # Returns Python datetime with tzinfo
print(f"Timezone: {created_at.tzinfo}")  # Shows time zone
```

#### **Oracle Time Zone Configuration**

```sql
-- View database time zone
SELECT DBTIMEZONE FROM DUAL;  -- e.g., '+00:00' (UTC)

-- View session time zone
SELECT SESSIONTIMEZONE FROM DUAL;  -- e.g., 'America/Los_Angeles'

-- Set session time zone
ALTER SESSION SET TIME_ZONE = 'UTC';
ALTER SESSION SET TIME_ZONE = 'America/New_York';
ALTER SESSION SET TIME_ZONE = '+00:00';  -- Numeric offset

-- View available time zones
SELECT * FROM V$TIMEZONE_NAMES ORDER BY TZNAME;
```

#### **TIME_AT_DBTIMEZONE Parameter (23ai Feature)**

Oracle 23ai introduces the `TIME_AT_DBTIMEZONE` parameter for controlling time zone behavior:

```sql
-- Configure time-dependent operations
ALTER SYSTEM SET TIME_AT_DBTIMEZONE = OFF;      -- Use host system TZ (default)
ALTER SYSTEM SET TIME_AT_DBTIMEZONE = USER_SQL; -- SYSDATE/SYSTIMESTAMP use DBTIMEZONE
ALTER SYSTEM SET TIME_AT_DBTIMEZONE = DATABASE; -- All operations use DBTIMEZONE
```

**Affects**: `SYSDATE`, `SYSTIMESTAMP`, DATE/TIMESTAMP queries, job scheduling, materialized view refresh, Oracle Flashback.

#### **Best Practices**

✅ **DO**: Use TIMESTAMP WITH TIME ZONE for all timestamps
```sql
CREATE TABLE products (
    id NUMBER PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,  -- Explicit TZ
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

✅ **DO**: Store all timestamps in UTC at database level
```sql
-- Set database time zone to UTC (during database creation)
CREATE DATABASE ... SET TIME_ZONE = 'UTC';
```

✅ **DO**: Use DEFAULT CURRENT_TIMESTAMP for auto-timestamps
```sql
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP  -- Auto-populated
```

❌ **DON'T**: Use DATE for timestamps with time zones
```sql
-- BAD - DATE has no time zone, only second precision
created_at DATE DEFAULT SYSDATE  -- No TZ, loses fractional seconds
```

❌ **DON'T**: Use VARCHAR2 for timestamps
```sql
-- BAD - no validation, no date arithmetic
created_at VARCHAR2(30)  -- Error-prone, inefficient
```

#### **Common Timestamp Queries**

```sql
-- Current timestamp with time zone
SELECT CURRENT_TIMESTAMP FROM DUAL;
-- Returns: 2025-10-17 15:30:45.123456 -07:00

-- Convert to specific time zone
SELECT created_at AT TIME ZONE 'America/New_York'
FROM products
WHERE id = 1;

-- Extract components
SELECT
    EXTRACT(YEAR FROM created_at) as year,
    EXTRACT(MONTH FROM created_at) as month,
    EXTRACT(DAY FROM created_at) as day,
    EXTRACT(HOUR FROM created_at) as hour,
    EXTRACT(TIMEZONE_HOUR FROM created_at) as tz_hour
FROM products;

-- Date arithmetic
SELECT
    created_at,
    created_at + INTERVAL '7' DAY as one_week_later,
    created_at - INTERVAL '1' HOUR as one_hour_ago
FROM products;
```

---

## Summary & Recommendations

### **Recommended Data Type Patterns for Oracle 23ai**

#### **Complete Table Example**

```sql
-- Modern Oracle 23ai table with all recommended patterns
CREATE TABLE products (
    -- Primary key: Identity column
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Text columns
    name VARCHAR2(255) NOT NULL,
    description CLOB,
    sku VARCHAR2(100) UNIQUE,

    -- Numeric columns
    price NUMBER(10, 2) NOT NULL,
    stock_quantity NUMBER DEFAULT 0,

    -- Boolean columns (23ai native)
    in_stock BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,

    -- JSON column (binary OSON storage)
    metadata JSON,
    attributes JSON CHECK (attributes IS JSON),

    -- Vector column for AI/ML (768-dim embeddings)
    embedding VECTOR(768, FLOAT32),

    -- Timestamp columns with time zone
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP WITH TIME ZONE
);

-- Create vector index for similarity search
CREATE INDEX idx_product_embedding_hnsw
ON products (embedding)
INDEXTYPE IS HNSW
PARAMETERS ('DISTANCE COSINE, M 16, EF_CONSTRUCTION 64');

-- Create JSON indexes for frequent queries
CREATE INDEX idx_product_metadata_origin
ON products (JSON_VALUE(metadata, '$.origin'));
```

### **Quick Reference Guide**

| Use Case | Oracle 23ai Type | Example | Notes |
|----------|-----------------|---------|-------|
| **Primary Key** | `NUMBER GENERATED ALWAYS AS IDENTITY` | `id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY` | Modern auto-increment |
| **Boolean** | `BOOLEAN` | `in_stock BOOLEAN DEFAULT TRUE` | Native in 23ai |
| **Timestamps** | `TIMESTAMP WITH TIME ZONE` | `created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP` | Store UTC |
| **JSON** | `JSON` | `metadata JSON` | Binary OSON storage |
| **Embeddings** | `VECTOR(768, FLOAT32)` | `embedding VECTOR(768, FLOAT32)` | For Vertex AI text-embedding-005 |
| **Text (short)** | `VARCHAR2(n)` | `name VARCHAR2(255)` | Up to 4000 bytes |
| **Text (long)** | `CLOB` | `description CLOB` | For long text |
| **Decimal** | `NUMBER(p, s)` | `price NUMBER(10, 2)` | Exact numeric |
| **Integer** | `NUMBER` | `quantity NUMBER` | Integer values |

### **Migration Checklist from Older Oracle Versions**

- [ ] Replace `NUMBER(1)` boolean pattern with native `BOOLEAN`
- [ ] Replace `VARCHAR2/CLOB` JSON storage with native `JSON` type
- [ ] Replace `SEQUENCE + TRIGGER` with `GENERATED ALWAYS AS IDENTITY`
- [ ] Replace `DATE` with `TIMESTAMP WITH TIME ZONE` for timestamps
- [ ] Add `VECTOR` columns for AI/ML embeddings
- [ ] Set database time zone to UTC
- [ ] Update application code to use native boolean values
- [ ] Update JSON queries to use `JSON_VALUE`, `JSON_QUERY`, `JSON_TABLE`
- [ ] Test vector similarity search with appropriate index types

### **Python Driver Version Requirements**

- **python-oracledb 2.x+**: Required for BOOLEAN, VECTOR, and enhanced JSON support
- **Thin mode**: Recommended (no Oracle client required)
- **Thick mode**: Optional (requires Oracle Instant Client)

### **Oracle 23ai Free Edition Notes**

All features documented here are available in **Oracle Database 23ai Free Edition**:
- ✅ Native BOOLEAN data type
- ✅ Native JSON data type with OSON storage
- ✅ VECTOR data type with HNSW/IVFFlat indexes
- ✅ GENERATED ALWAYS AS IDENTITY
- ✅ TIMESTAMP WITH TIME ZONE
- ✅ All modern SQL:2023 features

---

## Sources

1. **Oracle Database 23ai Documentation**
   - Context7: `/websites/oracle-en-database-oracle-oracle-database-23`
   - Official docs: https://docs.oracle.com/en/database/oracle/oracle-database/23/

2. **Oracle AI Vector Search User's Guide**
   - Context7: `/websites/oracle-en-database-oracle-oracle-database-23-vecse`
   - Official docs: https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/

3. **python-oracledb Documentation**
   - Context7: `/oracle/python-oracledb`
   - Official docs: https://python-oracledb.readthedocs.io/

4. **Web Search (2025)**
   - Oracle 23ai BOOLEAN type announcements
   - Community guides and best practices
   - SQLAlchemy Oracle 23ai support discussions

---

**Last Updated**: 2025-10-17
**Researched by**: Expert Agent (Claude)
**Oracle Version**: Oracle Database 23ai Free
**Python Driver**: python-oracledb 2.x
