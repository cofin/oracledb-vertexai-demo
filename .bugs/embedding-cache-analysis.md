# Embedding Cache Flow Analysis

## Summary

After tracing the data flow, I found that **embeddings are NOT being cached in the response cache**. The system correctly separates embedding storage from response caching.

## Data Flow Analysis

### 1. Product Service (product.py)

- Returns full products WITH embeddings (lines 27, 52, 91)
- Products contain embedding data as Oracle VECTOR type

### 2. Recommendation Service (recommendation.py)

- Fetches products with embeddings from ProductService
- **However**, when building context for the AI, it only extracts name and description:

  ```python
  # Line 260-261
  chat_metadata["product_matches"] = [
      f"- {product['name']}: {product['description']}" for product in similar_products
  ]
  ```

- The context passed to vertex_ai only contains formatted strings, not raw product objects

### 3. Vertex AI Service (vertex_ai.py)

- The cache_key (line 258) is built from: `f"{query}|{context}|{intent}|{persona}"`
- The context only contains product names and descriptions as formatted text
- When caching responses (line 114), only stores:

  ```python
  {"content": content, "model": self.model_name}
  ```

  Where `content` is the AI-generated text response

### 4. Response Cache Service (response_cache.py)

- Stores responses as JSON using `json.dumps(response, ensure_ascii=False)` (line 108)
- The response only contains the AI-generated text and model name
- NO embeddings are included

### 5. Embedding Cache Service (embedding_cache.py)

- Completely separate cache for embeddings
- Stores only the embedding vectors (768-dimensional float arrays)
- Uses Oracle's native VECTOR type for efficient storage
- Has its own table: `embedding_cache`

## Two Separate Caching Systems

1. **Response Cache** (`response_cache` table)
   - Stores: Complete LLM responses as JSON
   - Key: Query + context + intent + persona
   - TTL: 5 minutes (short for freshness)
   - Content: AI-generated text responses only

2. **Embedding Cache** (`embedding_cache` table)
   - Stores: Vector embeddings (768-dimensional arrays)
   - Key: Normalized query text
   - TTL: 24 hours (long since embeddings are expensive)
   - Content: Raw vector data only

## Conclusion

The embeddings are NOT being cached in the response cache. The system has proper separation of concerns:

- Embeddings are cached separately in their own table with appropriate data types
- Response cache only contains AI-generated text responses
- Product embeddings never make it into the response cache because they're filtered out when building the context string
