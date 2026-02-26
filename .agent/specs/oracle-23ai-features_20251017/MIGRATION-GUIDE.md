# Oracle 23ai Data Types Migration Guide

**Purpose**: Guide for migrating existing Oracle schemas to use modern Oracle 23ai data types
**Target Audience**: Database administrators, backend developers
**Prerequisites**: Oracle Database 23ai, python-oracledb 2.x

---

## Migration Checklist

- [ ] **Step 1**: Identify columns using legacy patterns (NUMBER(1) for bool, VARCHAR2 for JSON, etc.)
- [ ] **Step 2**: Plan migration order (start with non-critical tables)
- [ ] **Step 3**: Backup database before migration
- [ ] **Step 4**: Migrate tables to new data types
- [ ] **Step 5**: Update application code to use native types
- [ ] **Step 6**: Test thoroughly
- [ ] **Step 7**: Deploy to production with rollback plan

---

## Migration 1: NUMBER(1) → BOOLEAN

### Identify Affected Columns

```sql
-- Find NUMBER(1) columns that might be booleans
SELECT
    table_name,
    column_name,
    data_type,
    data_precision,
    data_scale,
    nullable
FROM user_tab_columns
WHERE data_type = 'NUMBER'
  AND data_precision = 1
  AND data_scale = 0
ORDER BY table_name, column_name;
```

### Migration Strategy: Add New Column + Backfill

```sql
-- Step 1: Add new BOOLEAN column
ALTER TABLE products ADD (in_stock_new BOOLEAN);

-- Step 2: Backfill data with conversion
UPDATE products SET in_stock_new = CASE
    WHEN in_stock = 1 THEN TRUE
    WHEN in_stock = 0 THEN FALSE
    ELSE NULL
END;
COMMIT;

-- Step 3: Verify data integrity
SELECT COUNT(*) FROM products WHERE in_stock IS NULL AND in_stock_new IS NULL;
SELECT COUNT(*) FROM products WHERE in_stock = 1 AND in_stock_new = TRUE;
SELECT COUNT(*) FROM products WHERE in_stock = 0 AND in_stock_new = FALSE;

-- Step 4: Drop old column
ALTER TABLE products DROP COLUMN in_stock;

-- Step 5: Rename new column
ALTER TABLE products RENAME COLUMN in_stock_new TO in_stock;

-- Step 6: Add default if needed
ALTER TABLE products MODIFY (in_stock DEFAULT TRUE);
```

### Application Code Changes

**Before (OLD)**:
```python
# Python code using NUMBER(1)
cursor.execute(
    "INSERT INTO products (in_stock) VALUES (:val)",
    val=1  # Integer
)

in_stock_int = cursor.fetchone()[0]  # Returns 1 or 0
is_in_stock = bool(in_stock_int)  # Convert to bool
```

**After (NEW)**:
```python
# Python code using BOOLEAN
cursor.execute(
    "INSERT INTO products (in_stock) VALUES (:val)",
    val=True  # Native Python bool
)

in_stock = cursor.fetchone()[0]  # Returns Python bool directly
```

---

## Migration 2: VARCHAR2/CLOB → JSON

### Identify Affected Columns

```sql
-- Find VARCHAR2/CLOB columns that store JSON
-- (Requires manual inspection or application knowledge)
SELECT
    table_name,
    column_name,
    data_type,
    data_length
FROM user_tab_columns
WHERE (data_type = 'VARCHAR2' OR data_type = 'CLOB')
  AND column_name LIKE '%JSON%'
   OR column_name LIKE '%METADATA%'
   OR column_name LIKE '%ATTRIBUTES%'
ORDER BY table_name, column_name;
```

### Migration Strategy: Add New Column + Validate

```sql
-- Step 1: Add new JSON column
ALTER TABLE products ADD (metadata_new JSON);

-- Step 2: Backfill with validation
UPDATE products
SET metadata_new = metadata
WHERE metadata IS NOT NULL
  AND metadata IS JSON;  -- Validate JSON before copying

COMMIT;

-- Step 3: Check for invalid JSON (if any)
SELECT id, metadata
FROM products
WHERE metadata IS NOT NULL
  AND metadata IS NOT JSON;

-- Fix invalid JSON manually or skip those rows

-- Step 4: Verify data integrity
SELECT COUNT(*) FROM products WHERE metadata IS NULL AND metadata_new IS NULL;
SELECT COUNT(*) FROM products WHERE metadata IS NOT NULL AND metadata_new IS NOT NULL;

-- Step 5: Drop old column
ALTER TABLE products DROP COLUMN metadata;

-- Step 6: Rename new column
ALTER TABLE products RENAME COLUMN metadata_new TO metadata;

-- Step 7: Add IS JSON constraint
ALTER TABLE products MODIFY (metadata JSON CHECK (metadata IS JSON));
```

### Application Code Changes

**Before (OLD)**:
```python
import json

# Store JSON as string
metadata_dict = {"origin": "Colombia", "roast": "dark"}
metadata_str = json.dumps(metadata_dict)
cursor.execute("INSERT INTO products (metadata) VALUES (:val)", val=metadata_str)

# Fetch and parse JSON
metadata_str = cursor.fetchone()[0]
metadata_dict = json.loads(metadata_str)
```

**After (NEW)**:
```python
import json

# Still store as JSON string (Oracle handles validation)
metadata_dict = {"origin": "Colombia", "roast": "dark"}
metadata_str = json.dumps(metadata_dict)
cursor.execute("INSERT INTO products (metadata) VALUES (:val)", val=metadata_str)

# Fetch and parse JSON (same as before)
metadata_str = cursor.fetchone()[0]
metadata_dict = json.loads(metadata_str)

# OR use JSON_VALUE in SQL for direct access
cursor.execute(
    """
    SELECT id, name, JSON_VALUE(metadata, '$.origin') as origin
    FROM products
    WHERE id = :id
    """,
    id=1
)
```

**Update JSON Queries**:
```sql
-- Before: String parsing (inefficient)
SELECT * FROM products WHERE metadata LIKE '%Colombia%';

-- After: JSON path queries (efficient, indexed)
SELECT * FROM products WHERE JSON_VALUE(metadata, '$.origin') = 'Colombia';
```

---

## Migration 3: SEQUENCE + TRIGGER → IDENTITY

### Identify Affected Tables

```sql
-- Find sequences and their associated triggers
SELECT
    sequence_name,
    last_number,
    increment_by,
    cache_size
FROM user_sequences
WHERE sequence_name LIKE '%_SEQ'
ORDER BY sequence_name;

-- Find auto-increment triggers
SELECT trigger_name, table_name, trigger_type, triggering_event
FROM user_triggers
WHERE triggering_event = 'INSERT'
  AND trigger_type LIKE 'BEFORE%'
ORDER BY table_name;
```

### Migration Strategy: Recreate Table

**Option A: Recreate Table (Recommended for small tables)**

```sql
-- Step 1: Get current sequence value
SELECT products_seq.CURRVAL FROM DUAL;  -- e.g., 1500

-- Step 2: Create new table with identity column
CREATE TABLE products_new (
    id NUMBER GENERATED ALWAYS AS IDENTITY (START WITH 1501) PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    price NUMBER(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Step 3: Copy data (excluding ID, will be auto-generated)
INSERT INTO products_new (name, price, created_at)
SELECT name, price, created_at FROM products;

COMMIT;

-- Step 4: Verify row counts match
SELECT COUNT(*) FROM products;      -- e.g., 1500
SELECT COUNT(*) FROM products_new;  -- Should be 1500

-- Step 5: Drop old table and rename
DROP TABLE products CASCADE CONSTRAINTS;
ALTER TABLE products_new RENAME TO products;

-- Step 6: Recreate indexes and constraints
CREATE INDEX idx_product_name ON products(name);
-- ... other indexes and constraints

-- Step 7: Drop old sequence and trigger
DROP SEQUENCE products_seq;
DROP TRIGGER products_bi;
```

**Option B: Add Identity Column (For large tables, preserves existing IDs)**

```sql
-- Step 1: Note current max ID
SELECT MAX(id) FROM products;  -- e.g., 1500

-- Step 2: Create new table with identity column starting after max
CREATE TABLE products_new (
    id NUMBER GENERATED BY DEFAULT AS IDENTITY (START WITH 1501) PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    price NUMBER(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Step 3: Copy data INCLUDING existing IDs (BY DEFAULT allows manual IDs)
INSERT INTO products_new (id, name, price, created_at)
SELECT id, name, price, created_at FROM products;

COMMIT;

-- Step 4: Continue with steps 4-7 from Option A
```

### Application Code Changes

**Before (OLD)**:
```python
# Manual sequence handling
cursor.execute("SELECT products_seq.NEXTVAL FROM DUAL")
new_id = cursor.fetchone()[0]

cursor.execute(
    "INSERT INTO products (id, name) VALUES (:id, :name)",
    id=new_id,
    name="Coffee"
)
```

**After (NEW)**:
```python
# ID auto-generated, use RETURNING to get new ID
cursor.execute(
    """
    INSERT INTO products (name, price)
    VALUES (:name, :price)
    RETURNING id INTO :new_id
    """,
    name="Coffee",
    price=12.99,
    new_id=cursor.var(int)
)

new_id = cursor.var('new_id').getvalue()[0]
print(f"New product ID: {new_id}")
```

---

## Migration 4: DATE → TIMESTAMP WITH TIME ZONE

### Identify Affected Columns

```sql
-- Find DATE columns used for timestamps
SELECT
    table_name,
    column_name,
    data_type,
    nullable,
    data_default
FROM user_tab_columns
WHERE data_type = 'DATE'
  AND (column_name LIKE '%_AT' OR column_name LIKE '%_DATE')
ORDER BY table_name, column_name;
```

### Migration Strategy: Add New Column + Backfill

```sql
-- Step 1: Add new TIMESTAMP WITH TIME ZONE column
ALTER TABLE products ADD (created_at_new TIMESTAMP WITH TIME ZONE);

-- Step 2: Backfill data (DATE → TIMESTAMP WITH TIME ZONE)
-- Assumes existing DATE values are in UTC
UPDATE products
SET created_at_new = FROM_TZ(CAST(created_at AS TIMESTAMP), 'UTC');

COMMIT;

-- Step 3: Verify data integrity
SELECT
    created_at,
    created_at_new,
    CASE
        WHEN CAST(created_at AS TIMESTAMP) = CAST(created_at_new AS TIMESTAMP)
        THEN 'MATCH'
        ELSE 'MISMATCH'
    END as status
FROM products
WHERE ROWNUM <= 10;

-- Step 4: Drop old column
ALTER TABLE products DROP COLUMN created_at;

-- Step 5: Rename new column
ALTER TABLE products RENAME COLUMN created_at_new TO created_at;

-- Step 6: Add default for new rows
ALTER TABLE products MODIFY (created_at DEFAULT CURRENT_TIMESTAMP);
```

### Application Code Changes

**Before (OLD)**:
```python
from datetime import datetime

# DATE type (no time zone info)
now = datetime.now()  # Naive datetime
cursor.execute("INSERT INTO products (created_at) VALUES (:val)", val=now)

created_at = cursor.fetchone()[0]  # Returns naive datetime
```

**After (NEW)**:
```python
from datetime import datetime, timezone

# TIMESTAMP WITH TIME ZONE (includes TZ)
now_utc = datetime.now(timezone.utc)  # Timezone-aware datetime
cursor.execute("INSERT INTO products (created_at) VALUES (:val)", val=now_utc)

created_at = cursor.fetchone()[0]  # Returns timezone-aware datetime
print(f"Timezone: {created_at.tzinfo}")  # Shows UTC
```

---

## Migration 5: Add VECTOR Columns (New Feature)

### Adding Vector Column to Existing Table

```sql
-- Step 1: Add VECTOR column (nullable for gradual generation)
ALTER TABLE products ADD (embedding VECTOR(768, FLOAT32));

-- Step 2: Generate embeddings asynchronously in application
-- (Don't populate here, embeddings generated via Vertex AI API)

-- Step 3: Create index AFTER most embeddings are populated
-- (Index creation on empty/sparse table is inefficient)
CREATE INDEX idx_product_embedding_hnsw
ON products (embedding)
INDEXTYPE IS HNSW
PARAMETERS ('DISTANCE COSINE, M 16, EF_CONSTRUCTION 64');

-- Step 4: (Optional) Make NOT NULL after all populated
-- ALTER TABLE products MODIFY (embedding NOT NULL);
```

### Application Code for Embedding Generation

```python
import array
from vertexai.language_models import TextEmbeddingModel

# Initialize Vertex AI embedding model
model = TextEmbeddingModel.from_pretrained("text-embedding-005")

# Fetch products without embeddings
cursor.execute(
    "SELECT id, name, description FROM products WHERE embedding IS NULL"
)

for product_id, name, description in cursor:
    # Generate embedding
    text = f"{name}. {description}"
    embedding_response = model.get_embeddings([text])
    embedding = embedding_response[0].values  # List of 768 floats

    # Convert to array.array for Oracle
    vector_array = array.array('f', embedding)

    # Update product with embedding
    cursor.execute(
        """
        UPDATE products
        SET embedding = :embedding,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = :id
        """,
        embedding=vector_array,
        id=product_id
    )

connection.commit()
```

---

## Post-Migration Validation

### 1. Data Integrity Checks

```sql
-- Check for NULL values in NOT NULL columns
SELECT table_name, column_name
FROM user_tab_columns
WHERE nullable = 'N'
  AND table_name IN ('PRODUCTS', 'ORDERS', ...)
ORDER BY table_name;

-- Check row counts match expectations
SELECT table_name, num_rows
FROM user_tables
WHERE table_name IN ('PRODUCTS', 'ORDERS', ...)
ORDER BY table_name;

-- Check data type consistency
SELECT
    table_name,
    column_name,
    data_type,
    data_length,
    data_precision,
    data_scale
FROM user_tab_columns
WHERE table_name IN ('PRODUCTS', 'ORDERS', ...)
ORDER BY table_name, column_id;
```

### 2. Index Validation

```sql
-- Verify all indexes are VALID
SELECT
    index_name,
    table_name,
    index_type,
    status,
    uniqueness
FROM user_indexes
WHERE table_name IN ('PRODUCTS', 'ORDERS', ...)
ORDER BY table_name, index_name;

-- Rebuild invalid indexes
-- ALTER INDEX idx_name REBUILD;
```

### 3. Constraint Validation

```sql
-- Verify all constraints are ENABLED
SELECT
    constraint_name,
    table_name,
    constraint_type,
    status,
    validated
FROM user_constraints
WHERE table_name IN ('PRODUCTS', 'ORDERS', ...)
ORDER BY table_name, constraint_name;
```

### 4. Application Testing

- [ ] Test CRUD operations on migrated tables
- [ ] Test boolean queries with TRUE/FALSE literals
- [ ] Test JSON queries with JSON_VALUE/JSON_QUERY
- [ ] Test identity column auto-increment
- [ ] Test timestamp insertion with time zones
- [ ] Test vector similarity search (if applicable)
- [ ] Performance test on production-scale data
- [ ] Load test with concurrent users

---

## Rollback Plan

### Before Migration: Create Backup

```sql
-- Export schema and data
expdp username/password DIRECTORY=backup_dir DUMPFILE=pre_migration.dmp SCHEMAS=myschema

-- Or create backup tables
CREATE TABLE products_backup AS SELECT * FROM products;
CREATE TABLE orders_backup AS SELECT * FROM orders;
```

### If Migration Fails: Restore

```sql
-- Option 1: Import from export
impdp username/password DIRECTORY=backup_dir DUMPFILE=pre_migration.dmp SCHEMAS=myschema TABLE_EXISTS_ACTION=REPLACE

-- Option 2: Restore from backup tables
DROP TABLE products;
CREATE TABLE products AS SELECT * FROM products_backup;
-- Recreate indexes and constraints
```

---

## Migration Order Recommendations

1. **Start with non-critical tables** (test/staging environments)
2. **Migrate read-heavy tables first** (less write contention)
3. **Schedule migrations during low-traffic windows**
4. **Migrate incrementally** (one table or column type at a time)
5. **Monitor performance** after each migration
6. **Keep rollback plan ready**

---

## Tools and Scripts

### Python Migration Script Template

```python
import oracledb
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_boolean_column(connection, table_name, column_name):
    """Migrate NUMBER(1) column to BOOLEAN."""
    cursor = connection.cursor()

    try:
        # Step 1: Add new BOOLEAN column
        logger.info(f"Adding {column_name}_new column to {table_name}")
        cursor.execute(f"ALTER TABLE {table_name} ADD ({column_name}_new BOOLEAN)")

        # Step 2: Backfill data
        logger.info(f"Backfilling {column_name}_new from {column_name}")
        cursor.execute(f"""
            UPDATE {table_name}
            SET {column_name}_new = CASE
                WHEN {column_name} = 1 THEN TRUE
                WHEN {column_name} = 0 THEN FALSE
                ELSE NULL
            END
        """)
        connection.commit()

        # Step 3: Verify
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} IS NULL AND {column_name}_new IS NULL")
        null_count = cursor.fetchone()[0]
        logger.info(f"NULL count: {null_count}")

        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} = 1 AND {column_name}_new = TRUE")
        true_count = cursor.fetchone()[0]
        logger.info(f"TRUE count: {true_count}")

        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} = 0 AND {column_name}_new = FALSE")
        false_count = cursor.fetchone()[0]
        logger.info(f"FALSE count: {false_count}")

        # Step 4: Drop old column
        logger.info(f"Dropping old {column_name} column")
        cursor.execute(f"ALTER TABLE {table_name} DROP COLUMN {column_name}")

        # Step 5: Rename new column
        logger.info(f"Renaming {column_name}_new to {column_name}")
        cursor.execute(f"ALTER TABLE {table_name} RENAME COLUMN {column_name}_new TO {column_name}")

        connection.commit()
        logger.info(f"Migration complete for {table_name}.{column_name}")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        connection.rollback()
        raise

# Usage
connection = oracledb.connect(user="user", password="pass", dsn="dsn")
migrate_boolean_column(connection, "products", "in_stock")
connection.close()
```

---

## Common Issues and Solutions

### Issue 1: ORA-51805 - Vector dimension mismatch

**Cause**: Trying to insert vector with wrong dimensions

**Solution**:
```python
# Always validate dimensions before insert
expected_dims = 768
if len(embedding) != expected_dims:
    raise ValueError(f"Expected {expected_dims} dims, got {len(embedding)}")
```

### Issue 2: JSON validation fails on migration

**Cause**: Existing VARCHAR2/CLOB data contains invalid JSON

**Solution**:
```sql
-- Identify invalid JSON rows
SELECT id, metadata FROM products WHERE metadata IS NOT JSON;

-- Fix or skip invalid rows before migration
UPDATE products SET metadata = NULL WHERE metadata IS NOT JSON;
-- Or manually fix JSON syntax errors
```

### Issue 3: Identity column starts at 1 instead of max+1

**Cause**: Forgot to set START WITH on identity column

**Solution**:
```sql
-- Get max ID first
SELECT MAX(id) FROM products;  -- e.g., 1500

-- Create identity with START WITH max+1
CREATE TABLE products_new (
    id NUMBER GENERATED ALWAYS AS IDENTITY (START WITH 1501) PRIMARY KEY,
    ...
);
```

---

**Next Steps**:
- Review full research document for detailed data type specifications
- Test migrations on development database first
- Plan production migration with rollback strategy
- Update application code to use native types
