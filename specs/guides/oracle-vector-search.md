# Oracle Database 23ai Vector Search

> **Context**: Native vector search capabilities in Oracle Database 23ai with VECTOR data type
> **Audience**: Backend developers, AI/ML engineers, database administrators, LLMs
> **Last Updated**: 2025-01-06

## Quick Reference

| Feature | Oracle 23ai Specification | Reference Section |
|---------|---------------------------|-------------------|
| **Vector Type** | `VECTOR(dimensions, format)` | [VECTOR Data Type](#vector-data-type) |
| **Dimensions** | Flexible (e.g., 768 for text-embedding-004) | [Dimensions](#dimensions) |
| **Formats** | FLOAT32, FLOAT64, INT8, BINARY | [Formats](#vector-formats) |
| **Dense Vectors** | Standard array of values | [Dense Vectors](#dense-vectors) |
| **Sparse Vectors** | Indices + values representation | [Sparse Vectors](#sparse-vectors) |
| **HNSW Index** | `CREATE INDEX ... USING hnsw` | [HNSW Indexes](#hnsw-indexes) |
| **IVFFlat Index** | `CREATE INDEX ... USING ivfflat` | [IVFFlat Indexes](#ivfflat-indexes) |
| **Similarity (Cosine)** | `VECTOR_DISTANCE(v1, v2, COSINE)` | [Similarity Functions](#similarity-functions) |
| **Similarity (L2)** | `VECTOR_DISTANCE(v1, v2, EUCLIDEAN)` | [Similarity Functions](#similarity-functions) |
| **Similarity (Dot)** | `VECTOR_DISTANCE(v1, v2, DOT)` | [Similarity Functions](#similarity-functions) |
| **Python Driver** | python-oracledb 2.x | [Python Integration](#python-integration) |
| **NumPy Support** | Type handlers for ndarray | [NumPy Integration](#numpy-integration) |
| **Performance** | `SPATIAL_VECTOR_ACCELERATION` | [Performance Tuning](#performance-tuning) |

## Table of Contents

1. [VECTOR Data Type](#vector-data-type)
2. [Dense vs Sparse Vectors](#dense-vs-sparse-vectors)
3. [Creating Tables with VECTOR Columns](#creating-tables-with-vector-columns)
4. [Index Types](#index-types)
5. [Similarity Functions](#similarity-functions)
6. [Python Integration (python-oracledb)](#python-integration)
7. [NumPy Integration](#numpy-integration)
8. [Query Patterns](#query-patterns)
9. [Connection Pooling](#connection-pooling)
10. [Performance Tuning](#performance-tuning)
11. [Monitoring and Statistics](#monitoring-and-statistics)
12. [Migration Patterns](#migration-patterns)
13. [Troubleshooting](#troubleshooting)
14. [Code Examples](#code-examples)
15. [References](#references)

---

## VECTOR Data Type

Oracle Database 23ai introduces a native `VECTOR` data type for storing and querying vector embeddings. This is a first-class data type optimized for AI/ML workloads, particularly semantic similarity search.

### Syntax

```sql
VECTOR(dimension, element_type)
```

**Parameters**:
- `dimension`: Integer specifying vector dimensionality (e.g., 768 for Vertex AI text-embedding-004)
- `element_type`: Optional format specification (FLOAT32, FLOAT64, INT8, BINARY)

### Dimensions

Oracle supports both **fixed** and **flexible** dimensions:

**Fixed Dimensions** (Recommended):
```sql
CREATE TABLE products (
    id NUMBER PRIMARY KEY,
    name VARCHAR2(255),
    embedding VECTOR(768, FLOAT32)  -- Fixed 768 dimensions
);
```

**Flexible Dimensions**:
```sql
CREATE TABLE mixed_vectors (
    id NUMBER PRIMARY KEY,
    embedding VECTOR(*, FLOAT32)  -- Variable dimensions
);
```

**Best Practice**: Use fixed dimensions when all vectors have the same size (which is typical for a single embedding model).

### Vector Formats

Oracle 23ai supports four vector element types:

| Format | Storage | Range | Use Case |
|--------|---------|-------|----------|
| **FLOAT32** | 32-bit float | ±3.4e38 | Default, best for most embeddings |
| **FLOAT64** | 64-bit float | ±1.7e308 | Higher precision (rarely needed) |
| **INT8** | 8-bit signed integer | -128 to 127 | Quantized embeddings, memory optimization |
| **BINARY** | 8-bit unsigned | 0-255 | Binary embeddings, maximum compression |

**Default**: If no format is specified, Oracle uses FLOAT64.

**Example Specifications**:
```sql
embedding VECTOR(768, FLOAT32)  -- 768 dimensions, 32-bit floats
embedding VECTOR(768, FLOAT64)  -- 768 dimensions, 64-bit floats
embedding VECTOR(768, INT8)     -- 768 dimensions, 8-bit integers
embedding VECTOR(768, BINARY)   -- 768 dimensions, binary (96 bytes)
```

**Storage Calculation**:
- FLOAT32: dimensions × 4 bytes (e.g., 768 × 4 = 3,072 bytes)
- FLOAT64: dimensions × 8 bytes (e.g., 768 × 8 = 6,144 bytes)
- INT8: dimensions × 1 byte (e.g., 768 × 1 = 768 bytes)
- BINARY: dimensions ÷ 8 bytes (e.g., 768 ÷ 8 = 96 bytes)

---

## Dense vs Sparse Vectors

Oracle 23ai supports both dense and sparse vector representations.

### Dense Vectors

**Definition**: Standard vectors where all elements are stored explicitly.

**Characteristics**:
- All dimensions have values
- Standard array representation
- Most common for embeddings

**Python Example**:
```python
import array
dense_vector = array.array('f', [1.5, 2.0, 3.5, 4.0])  # All values present
```

**Oracle Storage**:
```sql
CREATE TABLE products (
    embedding VECTOR(768, FLOAT32)  -- Dense vector
);
```

### Sparse Vectors

**Definition**: Vectors where most elements are zero, stored as (indices, values) pairs.

**Characteristics**:
- Only non-zero elements stored
- Represented as struct with `num_dimensions`, `indices`, `values`
- Significant memory savings for sparse data

**Python Example**:
```python
import oracledb
import array

# Sparse vector: 25 total dimensions, only 3 non-zero values at indices 6, 10, 18
sparse_vector = oracledb.SparseVector(
    num_dimensions=25,
    indices=[6, 10, 18],
    values=array.array('f', [26.25, 129.625, 579.875])
)
```

**Oracle Storage**:
```sql
CREATE TABLE sparse_data (
    embedding VECTOR(25, FLOAT32, SPARSE)  -- Sparse vector
);
```

**When to Use**:
- **Dense**: Standard embeddings from models (text-embedding-004, etc.)
- **Sparse**: TF-IDF vectors, BM25 scores, topic models, feature vectors

---

## Creating Tables with VECTOR Columns

### Basic Table with Dense Vectors

```sql
-- Products table with 768-dimensional embeddings (Vertex AI text-embedding-004)
CREATE TABLE products (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    description CLOB,
    price NUMBER(10, 2),
    category VARCHAR2(100),
    sku VARCHAR2(100) UNIQUE,
    in_stock NUMBER(1) DEFAULT 1,  -- Oracle uses NUMBER for boolean
    metadata JSON,  -- JSON data type (23ai)
    embedding VECTOR(768, FLOAT32),  -- Nullable for gradual generation
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Table with Multiple Vector Types

```sql
-- Demonstration table showing different vector formats
CREATE TABLE vector_examples (
    id NUMBER PRIMARY KEY,
    vec_float32 VECTOR(3, FLOAT32),
    vec_float64 VECTOR(3, FLOAT64),
    vec_int8 VECTOR(3, INT8),
    vec_binary VECTOR(24, BINARY)  -- Must be multiple of 8
);
```

### Table with Sparse Vectors

```sql
-- Intent exemplars with sparse representations
CREATE TABLE intent_exemplars (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    intent VARCHAR2(100) NOT NULL,
    phrase VARCHAR2(4000) NOT NULL,
    embedding VECTOR(768, FLOAT32, SPARSE),  -- Sparse format
    confidence_threshold NUMBER(3, 2) DEFAULT 0.7,
    usage_count NUMBER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (intent, phrase)
);
```

### Embedding Cache Table

```sql
-- Cache table for storing generated embeddings
CREATE TABLE embedding_cache (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    text_hash VARCHAR2(64) NOT NULL,  -- SHA256 hash of input text
    embedding VECTOR(768, FLOAT32) NOT NULL,
    model_name VARCHAR2(100) NOT NULL,
    hit_count NUMBER DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (text_hash, model_name)
);

-- Indexes for fast lookup
CREATE INDEX idx_embedding_cache_model ON embedding_cache(model_name);
CREATE INDEX idx_embedding_cache_hit_count ON embedding_cache(hit_count DESC);
```

---

## Index Types

Oracle 23ai supports two primary vector index types: **HNSW** and **IVFFlat**.

### HNSW Indexes

**HNSW** (Hierarchical Navigable Small World) is a graph-based approximate nearest neighbor index.

#### Creating HNSW Index

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

#### HNSW Parameters

| Parameter | Description | Default | Tuning Guidelines |
|-----------|-------------|---------|-------------------|
| **M** | Max connections per layer | 16 | Higher = better recall, more memory. Range: 2-100. Sweet spot: 12-48. |
| **EF_CONSTRUCTION** | Size of dynamic candidate list during build | 64 | Higher = better index quality, slower build. Range: 4-1000. Sweet spot: 64-200. |
| **DISTANCE** | Distance metric | COSINE | Options: COSINE, EUCLIDEAN, DOT |

#### HNSW Query Parameters

```sql
-- Set at session level for query-time tuning
ALTER SESSION SET hnsw_ef_search = 100;  -- Higher = better recall, slower query
```

#### HNSW Characteristics

**Pros**:
- Fast queries (constant-time complexity)
- High recall accuracy
- Good for real-time applications

**Cons**:
- High memory usage (~2-3x data size)
- Slower index build
- Complex parameter tuning

**Best For**:
- Large datasets (>100K vectors)
- Real-time search requirements
- High recall accuracy needed
- Sufficient memory available

### IVFFlat Indexes

**IVFFlat** (Inverted File with Flat compression) partitions vectors into clusters for fast search.

#### Creating IVFFlat Index

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

#### IVFFlat Parameters

| Parameter | Description | Tuning Guidelines |
|-----------|-------------|-------------------|
| **LISTS** | Number of clusters/partitions | Formula: `SQRT(num_rows)`. Min: 10, Max: 10000. For 1K rows: 100, For 10K rows: 100, For 100K rows: 316, For 1M rows: 1000. |
| **DISTANCE** | Distance metric | Options: COSINE, EUCLIDEAN, DOT |

#### IVFFlat Query Parameters

```sql
-- Set number of lists to search at query time
ALTER SESSION SET ivfflat_probes = 10;  -- Higher = better recall, slower query
-- Default: lists / 10
```

#### IVFFlat Characteristics

**Pros**:
- Lower memory usage (~1.5x data size)
- Faster index build
- Simple parameter tuning

**Cons**:
- Lower recall than HNSW
- Query time increases with dataset size
- Requires periodic rebuilding

**Best For**:
- Medium datasets (1K-1M vectors)
- Memory-constrained environments
- Development/testing
- Frequent updates

### Index Type Comparison

| Metric | HNSW | IVFFlat |
|--------|------|---------|
| **Build Time** | Slow | Fast |
| **Query Speed** | Fast (constant) | Medium (varies) |
| **Memory Usage** | High (2-3x) | Low (1.5x) |
| **Recall** | Excellent | Good |
| **Best Dataset Size** | >100K | 1K-1M |
| **Update Performance** | Slow | Medium |

### Choosing an Index Type

**Use HNSW when**:
- Dataset > 100K vectors
- Real-time queries required
- Memory is available
- Recall accuracy is critical

**Use IVFFlat when**:
- Dataset < 1M vectors
- Memory is limited
- Frequent updates occur
- Development/testing phase

**No Index (Exact Search)**:
- Dataset < 1K vectors
- Perfect recall required
- Query time not critical

---

## Similarity Functions

Oracle 23ai provides the `VECTOR_DISTANCE` function for computing similarity between vectors.

### VECTOR_DISTANCE Syntax

```sql
VECTOR_DISTANCE(vector1, vector2, distance_metric)
```

**Returns**: Numeric distance value (interpretation depends on metric)

### Distance Metrics

#### 1. Cosine Similarity (COSINE)

**Formula**: `1 - (A·B) / (||A|| × ||B||)`

**Returns**: 0 (identical) to 2 (opposite)

**Use When**:
- Embeddings are normalized (most ML models)
- Direction matters more than magnitude
- Semantic similarity (text embeddings)

**Oracle Query**:
```sql
SELECT
    id,
    name,
    1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) as similarity_score
FROM products
WHERE 1 - VECTOR_DISTANCE(embedding, :query_vector, COSINE) >= 0.7
ORDER BY VECTOR_DISTANCE(embedding, :query_vector, COSINE)
LIMIT 5;
```

**Interpretation**:
- Distance 0 = Vectors are identical
- Distance 1 = Vectors are orthogonal (90°)
- Distance 2 = Vectors are opposite (180°)
- Similarity = `1 - distance` (converts to 0-1 scale)

#### 2. Euclidean Distance (EUCLIDEAN / L2)

**Formula**: `SQRT(Σ(A[i] - B[i])²)`

**Returns**: 0 (identical) to ∞ (unbounded)

**Use When**:
- Absolute magnitude matters
- Non-normalized embeddings
- Spatial data

**Oracle Query**:
```sql
SELECT
    id,
    name,
    VECTOR_DISTANCE(embedding, :query_vector, EUCLIDEAN) as distance
FROM products
WHERE VECTOR_DISTANCE(embedding, :query_vector, EUCLIDEAN) <= 10.0
ORDER BY VECTOR_DISTANCE(embedding, :query_vector, EUCLIDEAN)
LIMIT 5;
```

**Interpretation**:
- Lower distance = more similar
- Scale depends on vector magnitude
- Sensitive to embedding normalization

#### 3. Dot Product (DOT)

**Formula**: `A·B = Σ(A[i] × B[i])`

**Returns**: -∞ to +∞ (unbounded)

**Use When**:
- Maximum Inner Product Search (MIPS)
- Specific ML models require it
- Asymmetric similarity

**Oracle Query**:
```sql
SELECT
    id,
    name,
    -1 * VECTOR_DISTANCE(embedding, :query_vector, DOT) as similarity
FROM products
ORDER BY VECTOR_DISTANCE(embedding, :query_vector, DOT) ASC  -- Ascending for max dot product
LIMIT 5;
```

**Interpretation**:
- Higher dot product = more similar
- Not symmetric (order matters)
- Negative dot products indicate dissimilarity

### Choosing a Distance Metric

| Use Case | Recommended Metric | Why |
|----------|-------------------|-----|
| **Text Embeddings (Vertex AI)** | COSINE | Pre-normalized, semantic similarity |
| **Image Embeddings** | COSINE or L2 | Depends on model normalization |
| **TF-IDF Vectors** | COSINE | Normalized term frequencies |
| **Spatial Coordinates** | EUCLIDEAN | Absolute distances matter |
| **Recommendation Systems** | DOT | Asymmetric preferences |

---

## Python Integration

Oracle's `python-oracledb` driver (version 2.0+) provides native support for the VECTOR data type.

### Installation

```bash
# Install python-oracledb
pip install oracledb

# Or with uv
uv add oracledb
```

### Basic Connection

```python
import oracledb

# Connection parameters
connection = oracledb.connect(
    user="your_user",
    password="your_password",
    dsn="localhost:1521/FREEPDB1"
)
```

### Inserting Dense Vectors

#### Using array.array (Recommended)

```python
import array
import oracledb

# Create connection and cursor
connection = oracledb.connect(user="user", password="pass", dsn="dsn")
cursor = connection.cursor()

# Prepare vector data
vector_float32 = array.array('f', [1.625, 1.5, 1.0])  # 32-bit float
vector_float64 = array.array('d', [11.25, 11.75, 11.5])  # 64-bit float
vector_int8 = array.array('b', [1, 2, 3])  # 8-bit signed integer

# Insert into table
cursor.execute(
    """
    INSERT INTO products (name, vec_float32, vec_float64, vec_int8)
    VALUES (:name, :v32, :v64, :v8)
    """,
    name="Example Product",
    v32=vector_float32,
    v64=vector_float64,
    v8=vector_int8
)

connection.commit()
```

**array.array Type Codes**:
- `'f'`: FLOAT32 (4 bytes per element)
- `'d'`: FLOAT64 (8 bytes per element)
- `'b'`: INT8 (1 byte per element, signed)
- `'B'`: BINARY (1 byte per element, unsigned)

#### Using Lists (Auto-conversion)

```python
# python-oracledb can convert lists to vectors automatically
vector_list = [1.5, 2.0, 3.5, 4.0]

cursor.execute(
    "INSERT INTO products (embedding) VALUES (:vec)",
    vec=vector_list  # Automatically converted to array.array
)
```

### Inserting Sparse Vectors

```python
import oracledb
import array

# Create sparse vector: 25 dimensions, 3 non-zero values
sparse_vector = oracledb.SparseVector(
    num_dimensions=25,
    indices=[6, 10, 18],  # Zero-based indices
    values=array.array('f', [26.25, 129.625, 579.875])
)

cursor.execute(
    "INSERT INTO sparse_table (embedding) VALUES (:vec)",
    vec=sparse_vector
)
```

### Fetching Vectors

#### Default Behavior (array.array)

```python
# Fetch vectors - returned as array.array by default
cursor.execute("SELECT id, embedding FROM products WHERE id = 1")
for row in cursor:
    product_id, vector = row
    print(f"ID: {product_id}")
    print(f"Vector type: {type(vector)}")  # <class 'array.array'>
    print(f"Vector: {vector}")
```

#### Convert to Lists

```python
# Use output type handler to convert to lists
def output_type_handler(cursor, metadata):
    if metadata.type_code is oracledb.DB_TYPE_VECTOR:
        return cursor.var(
            metadata.type_code,
            arraysize=cursor.arraysize,
            outconverter=list  # Convert to list
        )

connection.outputtypehandler = output_type_handler

cursor.execute("SELECT embedding FROM products")
for (vector,) in cursor:
    print(type(vector))  # <class 'list'>
```

### Parameter Binding for Queries

```python
# Proper parameter binding with VECTOR_DISTANCE
query_embedding = array.array('f', [0.1, 0.2, 0.3, ...])  # 768 dimensions

cursor.execute(
    """
    SELECT
        id,
        name,
        1 - VECTOR_DISTANCE(embedding, :query, COSINE) as similarity
    FROM products
    WHERE 1 - VECTOR_DISTANCE(embedding, :query, COSINE) >= :threshold
    ORDER BY VECTOR_DISTANCE(embedding, :query, COSINE)
    FETCH FIRST :limit ROWS ONLY
    """,
    query=query_embedding,
    threshold=0.7,
    limit=5
)

results = cursor.fetchall()
```

### Connection Pooling

```python
import oracledb

# Create connection pool
pool = oracledb.create_pool(
    user="user",
    password="password",
    dsn="localhost:1521/FREEPDB1",
    min=2,  # Minimum connections
    max=10,  # Maximum connections
    increment=1,  # Growth increment
    threaded=True  # Thread-safe pool
)

# Acquire connection from pool
connection = pool.acquire()
cursor = connection.cursor()

# Use connection...

# Release back to pool
pool.release(connection)

# Close pool when done
pool.close()
```

**Pooling Best Practices**:
- **min**: 2-5 (keeps connections warm)
- **max**: CPU cores × 2-4 for I/O-bound apps
- **increment**: 1-2 (grow gradually)
- Always use `try/finally` to ensure release

---

## NumPy Integration

python-oracledb supports NumPy arrays for vector operations, providing seamless integration with scientific Python stack.

### Prerequisites

```bash
pip install numpy
```

### Input Type Handler (NumPy → Oracle)

```python
import numpy as np
import array
import oracledb

def numpy_converter_in(value):
    """Convert NumPy array to array.array for Oracle."""
    if value.dtype == np.float64:
        dtype = 'd'
    elif value.dtype == np.float32:
        dtype = 'f'
    elif value.dtype == np.uint8:
        dtype = 'B'
    else:  # int8 and others
        dtype = 'b'
    return array.array(dtype, value.tolist())

def input_type_handler(cursor, value, arraysize):
    """Handle NumPy arrays as input."""
    if isinstance(value, np.ndarray):
        return cursor.var(
            oracledb.DB_TYPE_VECTOR,
            arraysize=arraysize,
            inconverter=numpy_converter_in
        )

# Register handler
connection.inputtypehandler = input_type_handler

# Now you can insert NumPy arrays directly
vector_np = np.array([1.625, 1.5, 1.0], dtype=np.float32)
cursor.execute(
    "INSERT INTO products (embedding) VALUES (:vec)",
    vec=vector_np  # Automatically converted
)
```

### Output Type Handler (Oracle → NumPy)

```python
import numpy as np
import oracledb

def numpy_converter_out(value):
    """Convert array.array to NumPy array."""
    return np.array(value, copy=False, dtype=value.typecode)

def output_type_handler(cursor, metadata):
    """Handle VECTOR as NumPy arrays."""
    if metadata.type_code is oracledb.DB_TYPE_VECTOR:
        return cursor.var(
            metadata.type_code,
            arraysize=cursor.arraysize,
            outconverter=numpy_converter_out
        )

# Register handler
connection.outputtypehandler = output_type_handler

# Fetch vectors as NumPy arrays
cursor.execute("SELECT embedding FROM products")
for (vector,) in cursor:
    print(type(vector))  # <class 'numpy.ndarray'>
    print(vector.dtype)  # dtype('float32')

    # Can now use NumPy operations
    magnitude = np.linalg.norm(vector)
    normalized = vector / magnitude
```

### Complete NumPy Integration Example

```python
import numpy as np
import array
import oracledb

# Type converters
def numpy_converter_in(value):
    if value.dtype == np.float64:
        dtype = 'd'
    elif value.dtype == np.float32:
        dtype = 'f'
    elif value.dtype == np.uint8:
        dtype = 'B'
    else:
        dtype = 'b'
    return array.array(dtype, value.tolist())

def numpy_converter_out(value):
    return np.array(value, copy=False, dtype=value.typecode)

def input_type_handler(cursor, value, arraysize):
    if isinstance(value, np.ndarray):
        return cursor.var(
            oracledb.DB_TYPE_VECTOR,
            arraysize=arraysize,
            inconverter=numpy_converter_in
        )

def output_type_handler(cursor, metadata):
    if metadata.type_code is oracledb.DB_TYPE_VECTOR:
        return cursor.var(
            metadata.type_code,
            arraysize=cursor.arraysize,
            outconverter=numpy_converter_out
        )

# Setup connection
connection = oracledb.connect(user="user", password="pass", dsn="dsn")
connection.inputtypehandler = input_type_handler
connection.outputtypehandler = output_type_handler

cursor = connection.cursor()

# Insert NumPy array
embedding = np.random.rand(768).astype(np.float32)
cursor.execute(
    "INSERT INTO products (id, embedding) VALUES (:id, :vec)",
    id=1,
    vec=embedding
)

# Fetch as NumPy array
cursor.execute("SELECT embedding FROM products WHERE id = 1")
(fetched_embedding,) = cursor.fetchone()

print(type(fetched_embedding))  # <class 'numpy.ndarray'>
print(np.array_equal(embedding, fetched_embedding))  # True
```

---

## Query Patterns

### Basic Similarity Search

```python
# Location: app/services/product.py
import array
from typing import Any

async def vector_similarity_search(
    query_embedding: list[float],
    similarity_threshold: float = 0.7,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search products using vector similarity."""

    # Convert list to array.array for Oracle
    query_vector = array.array('f', query_embedding)

    # Execute similarity search
    cursor.execute(
        """
        SELECT
            id,
            name,
            description,
            price,
            category,
            1 - VECTOR_DISTANCE(embedding, :query, COSINE) as similarity_score
        FROM products
        WHERE embedding IS NOT NULL
          AND in_stock = 1
          AND 1 - VECTOR_DISTANCE(embedding, :query, COSINE) >= :threshold
        ORDER BY VECTOR_DISTANCE(embedding, :query, COSINE)
        FETCH FIRST :limit ROWS ONLY
        """,
        query=query_vector,
        threshold=similarity_threshold,
        limit=limit
    )

    return cursor.fetchall()
```

### Query with Filtering

```python
# Combined vector search with metadata filtering
cursor.execute(
    """
    SELECT
        p.id,
        p.name,
        p.price,
        1 - VECTOR_DISTANCE(p.embedding, :query, COSINE) as similarity
    FROM products p
    WHERE p.embedding IS NOT NULL
      AND p.category = :category
      AND p.price BETWEEN :min_price AND :max_price
      AND p.in_stock = 1
      AND 1 - VECTOR_DISTANCE(p.embedding, :query, COSINE) >= :threshold
    ORDER BY VECTOR_DISTANCE(p.embedding, :query, COSINE)
    FETCH FIRST :limit ROWS ONLY
    """,
    query=query_vector,
    category="coffee",
    min_price=5.0,
    max_price=15.0,
    threshold=0.6,
    limit=10
)
```

### Batch Similarity Search

```python
# Find similar items for multiple query vectors
query_vectors = [
    array.array('f', vec1),
    array.array('f', vec2),
    array.array('f', vec3)
]

results = []
for query_vec in query_vectors:
    cursor.execute(
        """
        SELECT id, name,
               1 - VECTOR_DISTANCE(embedding, :query, COSINE) as similarity
        FROM products
        WHERE 1 - VECTOR_DISTANCE(embedding, :query, COSINE) >= 0.7
        ORDER BY VECTOR_DISTANCE(embedding, :query, COSINE)
        FETCH FIRST 5 ROWS ONLY
        """,
        query=query_vec
    )
    results.append(cursor.fetchall())
```

### Hybrid Search (Vector + Text)

```python
# Combine vector similarity with text search
cursor.execute(
    """
    SELECT
        p.id,
        p.name,
        p.description,
        1 - VECTOR_DISTANCE(p.embedding, :query_vec, COSINE) as vec_similarity,
        CONTAINS(p.description, :search_text, 1) as text_score
    FROM products p
    WHERE p.embedding IS NOT NULL
      AND (
          1 - VECTOR_DISTANCE(p.embedding, :query_vec, COSINE) >= 0.6
          OR CONTAINS(p.description, :search_text, 1) > 0
      )
    ORDER BY
        (1 - VECTOR_DISTANCE(p.embedding, :query_vec, COSINE)) * 0.7 +
        (CONTAINS(p.description, :search_text, 1) / 100.0) * 0.3 DESC
    FETCH FIRST 10 ROWS ONLY
    """,
    query_vec=query_vector,
    search_text="espresso coffee beans"
)
```

---

## Connection Pooling

### AsyncPG-style Pooling with python-oracledb

```python
# Location: app/config.py
import oracledb
from typing import Any

class DatabaseConfig:
    """Oracle database configuration."""

    def __init__(
        self,
        user: str,
        password: str,
        dsn: str,
        min_pool_size: int = 2,
        max_pool_size: int = 10,
        pool_timeout: float = 30.0,
    ):
        self.user = user
        self.password = password
        self.dsn = dsn
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.pool_timeout = pool_timeout
        self._pool: oracledb.ConnectionPool | None = None

    def create_pool(self) -> oracledb.ConnectionPool:
        """Create connection pool."""
        if self._pool is None:
            self._pool = oracledb.create_pool(
                user=self.user,
                password=self.password,
                dsn=self.dsn,
                min=self.min_pool_size,
                max=self.max_pool_size,
                increment=1,
                threaded=True,
                getmode=oracledb.POOL_GETMODE_WAIT,
                wait_timeout=int(self.pool_timeout * 1000),  # milliseconds
            )
        return self._pool

    def close_pool(self) -> None:
        """Close connection pool."""
        if self._pool:
            self._pool.close()
            self._pool = None

# Usage
db_config = DatabaseConfig(
    user="myuser",
    password="mypassword",
    dsn="localhost:1521/FREEPDB1",
    min_pool_size=2,
    max_pool_size=10,
)

pool = db_config.create_pool()

# Acquire and use connection
connection = pool.acquire()
try:
    cursor = connection.cursor()
    cursor.execute("SELECT ...")
    results = cursor.fetchall()
finally:
    pool.release(connection)
```

### Pool Sizing Guidelines

| Environment | Min Size | Max Size | Formula |
|-------------|----------|----------|---------|
| **Development** | 1-2 | 5-10 | Small, quick iteration |
| **Testing** | 2 | 5 | Consistent, predictable |
| **Production** | 2-5 | CPUs × 2-4 | Scale with load |
| **High Concurrency** | 5-10 | CPUs × 4-8 | Many simultaneous users |

**Oracle Connection Limits**:
- Default max connections: Depends on PROCESSES parameter
- Check: `SELECT value FROM v$parameter WHERE name = 'processes';`
- Reserve 20-30% for admin/maintenance
- Allocate per application based on load

---

## Performance Tuning

### SPATIAL_VECTOR_ACCELERATION Parameter

Enable Oracle's spatial vector acceleration for improved query performance:

```sql
-- At system level
ALTER SYSTEM SET SPATIAL_VECTOR_ACCELERATION = TRUE;

-- At session level
ALTER SESSION SET SPATIAL_VECTOR_ACCELERATION = TRUE;
```

**Impact**: Optimizes vector distance calculations using hardware acceleration when available.

### INMEMORY_DEEP_VECTORIZATION

Enable deep vectorization for in-memory columnar operations:

```sql
ALTER SYSTEM SET INMEMORY_DEEP_VECTORIZATION = TRUE;
```

**Impact**: Vectorizes complex SQL operations (joins, aggregations) using SIMD hardware.

### Index Hints

Force use of specific index:

```sql
SELECT /*+ INDEX(p idx_product_embedding_hnsw) */
    p.id,
    p.name,
    VECTOR_DISTANCE(p.embedding, :query, COSINE) as distance
FROM products p
WHERE VECTOR_DISTANCE(p.embedding, :query, COSINE) < 0.5;
```

### Query Plan Analysis

Use `EXPLAIN PLAN` to verify index usage:

```sql
EXPLAIN PLAN FOR
SELECT
    id, name,
    VECTOR_DISTANCE(embedding, :query, COSINE) as distance
FROM products
WHERE VECTOR_DISTANCE(embedding, :query, COSINE) < 0.5
ORDER BY distance
FETCH FIRST 10 ROWS ONLY;

-- View the plan
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);
```

**Look for**:
- "INDEX RANGE SCAN" on vector index (good)
- "TABLE ACCESS FULL" (bad - not using index)

### Statistics Gathering

Keep statistics current for optimal query plans:

```sql
-- Gather stats for products table
BEGIN
    DBMS_STATS.GATHER_TABLE_STATS(
        ownname => 'YOUR_SCHEMA',
        tabname => 'PRODUCTS',
        estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE,
        method_opt => 'FOR ALL COLUMNS SIZE AUTO',
        cascade => TRUE
    );
END;
/
```

---

## Monitoring and Statistics

### Index Statistics

```sql
-- View index information
SELECT
    index_name,
    table_name,
    index_type,
    status,
    num_rows,
    last_analyzed
FROM user_indexes
WHERE table_name = 'PRODUCTS'
  AND index_name LIKE '%EMBEDDING%';
```

### Query Performance

```sql
-- Top SQL by elapsed time
SELECT
    sql_id,
    sql_text,
    elapsed_time/1000000 as elapsed_seconds,
    executions,
    (elapsed_time/1000000) / NULLIF(executions, 0) as avg_seconds
FROM v$sql
WHERE sql_text LIKE '%VECTOR_DISTANCE%'
ORDER BY elapsed_time DESC
FETCH FIRST 10 ROWS ONLY;
```

### Vector Index Health

```sql
-- Check index size and usage
SELECT
    segment_name,
    segment_type,
    bytes/1024/1024 as size_mb,
    blocks
FROM user_segments
WHERE segment_name LIKE '%EMBEDDING%';
```

---

## Migration Patterns

### Adding VECTOR Column to Existing Table

```sql
-- Step 1: Add VECTOR column (nullable)
ALTER TABLE products ADD (embedding VECTOR(768, FLOAT32));

-- Step 2: Populate embeddings (in batches via application)
-- See Python code below

-- Step 3: Create index after population
CREATE INDEX idx_product_embedding_hnsw
ON products (embedding)
INDEXTYPE IS HNSW
PARAMETERS ('DISTANCE COSINE, M 16, EF_CONSTRUCTION 64');

-- Step 4: Make NOT NULL if desired (after all populated)
ALTER TABLE products MODIFY (embedding NOT NULL);
```

### Bulk Embedding Update (Python)

```python
import array
from typing import List

def bulk_update_embeddings(
    product_ids: List[int],
    embeddings: List[List[float]],
    batch_size: int = 100
):
    """Bulk update product embeddings."""
    connection = pool.acquire()
    cursor = connection.cursor()

    try:
        # Prepare batch data
        batch_data = [
            (product_id, array.array('f', embedding))
            for product_id, embedding in zip(product_ids, embeddings)
        ]

        # Execute batch update
        cursor.executemany(
            """
            UPDATE products
            SET embedding = :embedding,
                updated_at = SYSTIMESTAMP
            WHERE id = :product_id
            """,
            batch_data
        )

        connection.commit()
        print(f"Updated {len(batch_data)} embeddings")

    finally:
        pool.release(connection)
```

### Rebuilding Indexes

```sql
-- Drop existing index
DROP INDEX idx_product_embedding_hnsw;

-- Recreate with new parameters
CREATE INDEX idx_product_embedding_hnsw
ON products (embedding)
INDEXTYPE IS HNSW
PARAMETERS ('DISTANCE COSINE, M 32, EF_CONSTRUCTION 128');
```

---

## Troubleshooting

### Issue: Slow Vector Searches

**Symptoms**: Queries taking >1 second

**Diagnosis**:
```sql
-- Check if index exists
SELECT index_name, index_type, status
FROM user_indexes
WHERE table_name = 'PRODUCTS';

-- Check query plan
EXPLAIN PLAN FOR <your query>;
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);
```

**Solutions**:
1. **No index**: Create HNSW or IVFFlat index
2. **Index not used**: Check WHERE clause includes distance function
3. **Index needs tuning**: Adjust M, EF_CONSTRUCTION, or LISTS parameters
4. **Statistics stale**: Gather fresh statistics

### Issue: Index Not Being Used

**Symptoms**: EXPLAIN PLAN shows "TABLE ACCESS FULL"

**Solutions**:
```sql
-- 1. Ensure WHERE clause uses distance function
-- ❌ BAD
WHERE similarity_score >= 0.7

-- ✅ GOOD
WHERE VECTOR_DISTANCE(embedding, :query, COSINE) < 0.3

-- 2. Force index with hint
SELECT /*+ INDEX(p idx_product_embedding_hnsw) */ ...

-- 3. Check index status
SELECT index_name, status FROM user_indexes;
-- Status should be 'VALID', not 'UNUSABLE'

-- 4. Rebuild if needed
ALTER INDEX idx_product_embedding_hnsw REBUILD;
```

### Issue: Out of Memory During Index Build

**Symptoms**: `ORA-04030: out of process memory`

**Solutions**:
1. **Increase PGA**:
```sql
ALTER SYSTEM SET pga_aggregate_target = 2G;
```

2. **Use IVFFlat instead of HNSW** (less memory):
```sql
CREATE INDEX idx_product_embedding_ivfflat
ON products (embedding)
INDEXTYPE IS IVFFLAT
PARAMETERS ('DISTANCE COSINE, LISTS 100');
```

3. **Reduce HNSW parameters**:
```sql
-- Lower M and EF_CONSTRUCTION
PARAMETERS ('M 8, EF_CONSTRUCTION 32')
```

### Issue: TypeError with array.array

**Symptoms**: `TypeError: a bytes-like object is required`

**Solution**: Use correct type code for array.array

```python
# ❌ BAD
vector = array.array('i', [1.5, 2.0, 3.5])  # 'i' is integer

# ✅ GOOD
vector = array.array('f', [1.5, 2.0, 3.5])  # 'f' is float32
vector = array.array('d', [1.5, 2.0, 3.5])  # 'd' is float64
```

### Issue: Dimension Mismatch

**Symptoms**: `ORA-51805: Vector dimension mismatch`

**Solution**: Ensure all vectors have same dimensions

```python
# Check dimensions before insert
expected_dims = 768
if len(embedding) != expected_dims:
    raise ValueError(f"Expected {expected_dims} dims, got {len(embedding)}")

cursor.execute(
    "INSERT INTO products (embedding) VALUES (:vec)",
    vec=array.array('f', embedding)
)
```

---

## Code Examples

### Complete Product Search Service

```python
# Location: app/services/product.py
import array
import oracledb
from typing import List, Dict, Any

class ProductService:
    """Service for product operations with vector search."""

    def __init__(self, connection: oracledb.Connection):
        self.connection = connection

    async def vector_similarity_search(
        self,
        query_embedding: List[float],
        similarity_threshold: float = 0.7,
        limit: int = 5,
        category: str | None = None
    ) -> List[Dict[str, Any]]:
        """
        Search products using vector similarity.

        Args:
            query_embedding: 768-dimensional embedding vector
            similarity_threshold: Minimum similarity score (0.0-1.0)
            limit: Maximum number of results
            category: Optional category filter

        Returns:
            List of product dicts with similarity scores
        """
        cursor = self.connection.cursor()

        # Convert to array.array for Oracle
        query_vector = array.array('f', query_embedding)

        # Build query with optional category filter
        query = """
            SELECT
                id,
                name,
                description,
                price,
                category,
                sku,
                1 - VECTOR_DISTANCE(embedding, :query, COSINE) as similarity_score
            FROM products
            WHERE embedding IS NOT NULL
              AND in_stock = 1
              AND 1 - VECTOR_DISTANCE(embedding, :query, COSINE) >= :threshold
        """

        params = {
            'query': query_vector,
            'threshold': similarity_threshold,
            'limit': limit
        }

        if category:
            query += " AND category = :category"
            params['category'] = category

        query += """
            ORDER BY VECTOR_DISTANCE(embedding, :query, COSINE)
            FETCH FIRST :limit ROWS ONLY
        """

        cursor.execute(query, **params)

        # Convert to dictionaries
        columns = [col[0].lower() for col in cursor.description]
        results = []
        for row in cursor:
            results.append(dict(zip(columns, row)))

        return results

    async def update_product_embedding(
        self,
        product_id: int,
        embedding: List[float]
    ) -> None:
        """Update product embedding vector."""
        cursor = self.connection.cursor()

        vector = array.array('f', embedding)

        cursor.execute(
            """
            UPDATE products
            SET embedding = :embedding,
                updated_at = SYSTIMESTAMP
            WHERE id = :product_id
            """,
            embedding=vector,
            product_id=product_id
        )

        self.connection.commit()
```

---

## References

### Official Documentation

- **Oracle Database 23ai Documentation**: [docs.oracle.com/en/database/oracle/oracle-database/23/](https://docs.oracle.com/en/database/oracle/oracle-database/23/)
- **Oracle AI Vector Search User's Guide**: [docs.oracle.com/en/database/oracle/oracle-database/23/vecse/](https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/)
- **python-oracledb Documentation**: [python-oracledb.readthedocs.io](https://python-oracledb.readthedocs.io/)
- **python-oracledb Vector Data Type**: [python-oracledb.readthedocs.io/en/latest/user_guide/vector_data_type.html](https://python-oracledb.readthedocs.io/en/latest/user_guide/vector_data_type.html)

### Context7 Library References

Use Context7 MCP for up-to-date documentation:

```python
# Resolve python-oracledb library
resolve-library-id(libraryName="oracle python-oracledb")

# Get vector-specific documentation
get-library-docs(
    context7CompatibleLibraryID="/oracle/python-oracledb",
    topic="vector search AI vector data type"
)
```

### Related Project Guides

- **[Oracle JSON Features](./oracle-json.md)** - JSON Relational Duality
- **[Oracle Performance Tuning](./oracle-performance.md)** - Database optimization
- **[Vertex AI Integration](./vertex-ai-integration.md)** - Embedding generation
- **[SQLSpec Patterns](./sqlspec-patterns.md)** - Service layer integration
- **[Architecture](./architecture.md)** - Overall system design

---

**Last Updated**: 2025-01-06
**Version**: 1.0
**Oracle Database**: 23ai
**python-oracledb**: 2.x
