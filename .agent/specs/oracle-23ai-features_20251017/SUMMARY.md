# Oracle 23ai Data Types - Quick Summary

**Research Date**: 2025-10-17
**Full Report**: [oracle-23ai-data-types-research.md](./oracle-23ai-data-types-research.md)

---

## TL;DR - What You Need to Know

### ✅ 1. **BOOLEAN Data Type - YES, Native Support!**

Oracle 23ai has **native BOOLEAN** data type in SQL (finally!).

```sql
-- ✅ NEW WAY (Oracle 23ai)
CREATE TABLE products (
    in_stock BOOLEAN DEFAULT TRUE
);

-- ❌ OLD WAY (avoid in new schemas)
CREATE TABLE products (
    in_stock NUMBER(1) DEFAULT 1  -- 0/1 pattern
);
```

**Python Integration**:
```python
# Bind and fetch Python bool directly
cursor.execute("INSERT INTO products (in_stock) VALUES (:val)", val=True)
in_stock = cursor.fetchone()[0]  # Returns Python bool
```

---

### ✅ 2. **JSON vs JSONB - Oracle Has Binary JSON!**

Oracle's `JSON` type uses **OSON (Optimized Storage for JSON)** - binary format like PostgreSQL's JSONB.

| Feature | Oracle JSON (OSON) | PostgreSQL JSONB |
|---------|-------------------|------------------|
| Binary Storage | ✅ Yes | ✅ Yes |
| Auto Validation | ✅ Yes | ✅ Yes |
| Fast Queries | ✅ Yes | ✅ Yes |

```sql
-- ✅ RECOMMENDED
CREATE TABLE products (
    metadata JSON  -- Binary OSON storage by default
);

-- ❌ OLD WAY (avoid)
CREATE TABLE products (
    metadata VARCHAR2(4000)  -- No validation, no optimization
);
```

**No "JSONB" keyword** - Oracle just calls it `JSON`, but it's binary underneath.

---

### ✅ 3. **Vector Data Types - Comprehensive Support**

Oracle 23ai has **VECTOR** type with multiple formats:

```sql
-- For Vertex AI text-embedding-005 (768 dimensions)
CREATE TABLE products (
    embedding VECTOR(768, FLOAT32)  -- ← RECOMMENDED
);
```

**Format Options**:
- `FLOAT32` - Standard (3,072 bytes for 768 dims) ← **Use this**
- `FLOAT64` - Higher precision (6,144 bytes) - rarely needed
- `INT8` - Quantized (768 bytes) - advanced use
- `BINARY` - Maximum compression (96 bytes) - special use

**Python Integration**:
```python
import array

# Convert list to array.array for Oracle
embedding = [0.1, 0.2, ...]  # 768 floats
vector_array = array.array('f', embedding)  # 'f' = FLOAT32

cursor.execute("INSERT INTO products (embedding) VALUES (:vec)", vec=vector_array)
```

---

### ✅ 4. **Identity Columns - Modern Auto-Increment**

Use **GENERATED ALWAYS AS IDENTITY** instead of sequences + triggers:

```sql
-- ✅ NEW WAY (Oracle 12c+)
CREATE TABLE products (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY
);

-- ❌ OLD WAY (avoid in new schemas)
CREATE SEQUENCE products_seq;
CREATE TRIGGER products_bi ... -- Complicated!
```

**Python Integration**:
```python
cursor.execute(
    """
    INSERT INTO products (name) VALUES (:name)
    RETURNING id INTO :new_id
    """,
    name="Coffee",
    new_id=cursor.var(int)
)
new_id = cursor.var('new_id').getvalue()[0]
```

---

### ✅ 5. **Timestamp Types - Use WITH TIME ZONE**

**TIMESTAMP WITH TIME ZONE** is recommended for modern apps:

```sql
-- ✅ RECOMMENDED
CREATE TABLE products (
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ❌ AVOID
CREATE TABLE products (
    created_at DATE DEFAULT SYSDATE  -- No TZ, no fractional seconds
);
```

**Store everything in UTC** at database level, convert to user's TZ in application.

---

## Complete Modern Table Example

```sql
CREATE TABLE products (
    -- Auto-increment primary key
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Basic columns
    name VARCHAR2(255) NOT NULL,
    description CLOB,
    price NUMBER(10, 2),

    -- Boolean columns (23ai native)
    in_stock BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,

    -- JSON metadata (binary OSON)
    metadata JSON,

    -- Vector embeddings (768-dim from Vertex AI)
    embedding VECTOR(768, FLOAT32),

    -- Timestamps with time zone
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Vector similarity index
CREATE INDEX idx_product_embedding_hnsw
ON products (embedding)
INDEXTYPE IS HNSW
PARAMETERS ('DISTANCE COSINE, M 16, EF_CONSTRUCTION 64');
```

---

## Python Driver Requirements

- **python-oracledb 2.x+** required for BOOLEAN, VECTOR, enhanced JSON
- **Thin mode** recommended (no Oracle client needed)
- All features work in **Oracle 23ai Free Edition**

---

## Key Takeaways

1. ✅ **BOOLEAN**: Native support in 23ai - use it!
2. ✅ **JSON**: Binary storage (OSON) like PostgreSQL JSONB - just called `JSON`
3. ✅ **VECTOR**: Use `VECTOR(768, FLOAT32)` for Vertex AI embeddings
4. ✅ **Identity**: Use `GENERATED ALWAYS AS IDENTITY` for auto-increment
5. ✅ **Timestamps**: Use `TIMESTAMP WITH TIME ZONE` for UTC timestamps

---

**Next Steps**:
- Review full research document for detailed syntax and migration patterns
- Update existing schemas to use modern Oracle 23ai types
- Test with python-oracledb 2.x for full feature support
