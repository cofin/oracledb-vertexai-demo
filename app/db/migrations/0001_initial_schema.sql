-- Oracle 23AI Vector Demo Migration
-- Version: 0001
-- Description: Initial schema with Oracle AI Vector Search support
-- Created: 2025-10-07
-- Author: cody
-- name: migrate-0001-up

-- Products table with vector embeddings for semantic search
CREATE TABLE product (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    description CLOB,
    price NUMBER(10, 2),
    category VARCHAR2(100),
    sku VARCHAR2(100) UNIQUE,
    in_stock NUMBER(1) DEFAULT 1 CHECK (in_stock IN (0, 1)),
    metadata JSON,
    embedding VECTOR(768, FLOAT32),
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
    updated_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

COMMENT ON TABLE product IS 'Products with vector embeddings for semantic search';
COMMENT ON COLUMN product.embedding IS '768-dimensional vector for Vertex AI text-embedding-004';
COMMENT ON COLUMN product.in_stock IS 'Boolean: 1=in stock, 0=out of stock';


-- Response cache for LLM responses
CREATE TABLE response_cache (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cache_key VARCHAR2(255) UNIQUE NOT NULL,
    response_data JSON NOT NULL,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

COMMENT ON TABLE response_cache IS 'Cached LLM responses to reduce API calls';
COMMENT ON COLUMN response_cache.cache_key IS 'Hash of query + context for cache lookup';


-- Embedding cache for vector embeddings
CREATE TABLE embedding_cache (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    text_hash VARCHAR2(255) NOT NULL,
    embedding VECTOR(768, FLOAT32) NOT NULL,
    model VARCHAR2(100) NOT NULL,
    hit_count NUMBER DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT SYSTIMESTAMP,
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
    CONSTRAINT embedding_cache_uk UNIQUE (text_hash, model)
);

COMMENT ON TABLE embedding_cache IS 'Cached embeddings to reduce Vertex AI API calls';
COMMENT ON COLUMN embedding_cache.text_hash IS 'MD5 hash of input text';
COMMENT ON COLUMN embedding_cache.embedding IS '768-dimensional embedding vector';


-- Intent exemplars for vector-based intent classification
CREATE TABLE intent_exemplar (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    intent VARCHAR2(100) NOT NULL,
    phrase VARCHAR2(1000) NOT NULL,
    embedding VECTOR(768, FLOAT32) NOT NULL,
    confidence_threshold NUMBER(3, 2) DEFAULT 0.7,
    usage_count NUMBER DEFAULT 0,
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP,
    updated_at TIMESTAMP DEFAULT SYSTIMESTAMP,
    CONSTRAINT intent_exemplar_uk UNIQUE (intent, phrase)
);

COMMENT ON TABLE intent_exemplar IS 'Intent classification training examples with embeddings';
COMMENT ON COLUMN intent_exemplar.confidence_threshold IS 'Minimum similarity score for this exemplar to match';


-- Search metrics for performance tracking
CREATE TABLE search_metric (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id VARCHAR2(128),
    query_text VARCHAR2(4000),
    intent VARCHAR2(100),
    confidence_score NUMBER(3, 2),
    vector_search_results NUMBER,
    vector_search_time_ms NUMBER,
    llm_response_time_ms NUMBER,
    total_response_time_ms NUMBER,
    embedding_generation_time_ms NUMBER,
    embedding_cache_hit NUMBER(1) DEFAULT 0 CHECK (embedding_cache_hit IN (0, 1)),
    vector_search_cache_hit NUMBER(1) DEFAULT 0 CHECK (vector_search_cache_hit IN (0, 1)),
    intent_exemplar_used VARCHAR2(255),
    avg_similarity_score NUMBER(3, 2),
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

COMMENT ON TABLE search_metric IS 'Search performance metrics and analytics';
COMMENT ON COLUMN search_metric.session_id IS 'References adk_sessions.session_id (created by ADK extension)';


-- Indexes for performance optimization

-- Vector similarity search indexes for product embeddings
CREATE VECTOR INDEX product_embedding_idx ON product (embedding)
ORGANIZATION NEIGHBOR PARTITIONS
WITH TARGET ACCURACY 95;

-- Vector similarity index for intent exemplar embeddings
CREATE VECTOR INDEX intent_exemplar_embedding_idx ON intent_exemplar (embedding)
ORGANIZATION NEIGHBOR PARTITIONS
WITH TARGET ACCURACY 95;


-- Standard B-tree indexes for product table
CREATE INDEX product_category_idx ON product (category);
CREATE INDEX product_in_stock_idx ON product (in_stock);
CREATE INDEX product_created_at_idx ON product (created_at);


-- Cache indexes for expiration and lookup
CREATE INDEX response_cache_expires_at_idx ON response_cache (expires_at);
CREATE INDEX response_cache_created_at_idx ON response_cache (created_at);


-- Embedding cache indexes
CREATE INDEX embedding_cache_model_idx ON embedding_cache (model);
CREATE INDEX embedding_cache_created_at_idx ON embedding_cache (created_at);
CREATE INDEX embedding_cache_hit_count_idx ON embedding_cache (hit_count DESC);
CREATE INDEX embedding_cache_last_accessed_idx ON embedding_cache (last_accessed DESC);


-- Intent exemplar indexes
CREATE INDEX intent_exemplar_intent_idx ON intent_exemplar (intent);
CREATE INDEX intent_exemplar_usage_count_idx ON intent_exemplar (usage_count DESC);


-- Search metrics indexes
CREATE INDEX search_metric_session_id_idx ON search_metric (session_id);
CREATE INDEX search_metric_intent_idx ON search_metric (intent);
CREATE INDEX search_metric_created_at_idx ON search_metric (created_at);
CREATE INDEX search_metric_similarity_idx ON search_metric (avg_similarity_score);


-- Oracle Text indexes for full-text search on product
BEGIN
    CTX_DDL.CREATE_PREFERENCE('product_lexer', 'BASIC_LEXER');
    CTX_DDL.SET_ATTRIBUTE('product_lexer', 'index_text', 'YES');
END;

CREATE INDEX product_name_text_idx ON product (name)
INDEXTYPE IS CTXSYS.CONTEXT
PARAMETERS ('LEXER product_lexer SYNC (ON COMMIT)');

CREATE INDEX product_description_text_idx ON product (description)
INDEXTYPE IS CTXSYS.CONTEXT
PARAMETERS ('LEXER product_lexer SYNC (ON COMMIT)');


-- Triggers for automatic updated_at timestamps

CREATE OR REPLACE TRIGGER product_updated_at_trg
BEFORE UPDATE ON product
FOR EACH ROW
BEGIN
    :NEW.updated_at := SYSTIMESTAMP;
END;

CREATE OR REPLACE TRIGGER intent_exemplar_updated_at_trg
BEFORE UPDATE ON intent_exemplar
FOR EACH ROW
BEGIN
    :NEW.updated_at := SYSTIMESTAMP;
END;


-- name: migrate-0001-down

-- Drop triggers
DROP TRIGGER IF EXISTS product_updated_at_trg;
DROP TRIGGER IF EXISTS intent_exemplar_updated_at_trg;


-- Drop Oracle Text indexes
DROP INDEX IF EXISTS product_description_text_idx;
DROP INDEX IF EXISTS product_name_text_idx;

BEGIN
    CTX_DDL.DROP_PREFERENCE('product_lexer');
EXCEPTION
    WHEN OTHERS THEN NULL;
END;


-- Drop search metric indexes
DROP INDEX IF EXISTS search_metric_similarity_idx;
DROP INDEX IF EXISTS search_metric_created_at_idx;
DROP INDEX IF EXISTS search_metric_intent_idx;
DROP INDEX IF EXISTS search_metric_session_id_idx;


-- Drop intent exemplar indexes
DROP INDEX IF EXISTS intent_exemplar_usage_count_idx;
DROP INDEX IF EXISTS intent_exemplar_intent_idx;


-- Drop embedding cache indexes
DROP INDEX IF EXISTS embedding_cache_last_accessed_idx;
DROP INDEX IF EXISTS embedding_cache_hit_count_idx;
DROP INDEX IF EXISTS embedding_cache_created_at_idx;
DROP INDEX IF EXISTS embedding_cache_model_idx;


-- Drop response cache indexes
DROP INDEX IF EXISTS response_cache_created_at_idx;
DROP INDEX IF EXISTS response_cache_expires_at_idx;


-- Drop product indexes
DROP INDEX IF EXISTS product_created_at_idx;
DROP INDEX IF EXISTS product_in_stock_idx;
DROP INDEX IF EXISTS product_category_idx;


-- Drop vector indexes
DROP INDEX IF EXISTS intent_exemplar_embedding_idx;
DROP INDEX IF EXISTS product_embedding_idx;


-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS search_metric PURGE;
DROP TABLE IF EXISTS intent_exemplar PURGE;
DROP TABLE IF EXISTS embedding_cache PURGE;
DROP TABLE IF EXISTS response_cache PURGE;
DROP TABLE IF EXISTS product PURGE;
