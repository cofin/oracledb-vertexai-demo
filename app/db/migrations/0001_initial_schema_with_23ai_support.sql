-- Vector Demo Migration
-- Version: 0001
-- Description: Initial schema with pgvector support
-- Created: 2025-09-06T21:07:17.624967+00:00
-- Author: cody
-- name: migrate-0001-up
-- Enable pgvector extension for vector operations
CREATE EXTENSION if NOT EXISTS vector;


-- Products table with vector embeddings for semantic search
CREATE TABLE product (
    id serial PRIMARY KEY,
    name varchar(255) NOT NULL,
    description text,
    price decimal(10, 2),
    category varchar(100),
    sku varchar(100) UNIQUE,
    in_stock boolean DEFAULT true,
    metadata jsonb,
    embedding vector (768), -- 768 dimensions for Vertex AI textembedding-gecko
    created_at timestamp with time zone DEFAULT current_timestamp,
    updated_at timestamp with time zone DEFAULT current_timestamp
);


-- Store locations for coffee shop finder
CREATE TABLE store (
    id serial PRIMARY KEY,
    name varchar(255) NOT NULL,
    address text NOT NULL,
    city varchar(100),
    state varchar(50),
    zip varchar(20),
    phone varchar(50),
    hours jsonb, -- Store hours by day: {"monday": "7am-9pm", "tuesday": "7am-9pm", ...}
    metadata jsonb,
    created_at timestamp with time zone DEFAULT current_timestamp,
    updated_at timestamp with time zone DEFAULT current_timestamp
);


-- Chat sessions for user conversations
CREATE TABLE chat_session (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id varchar(255), -- Session identifier
    session_data jsonb, -- Session metadata
    last_activity timestamp with time zone DEFAULT current_timestamp,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT current_timestamp,
    updated_at timestamp with time zone DEFAULT current_timestamp
);


-- Chat conversations for message history
CREATE TABLE chat_conversation (
    id serial PRIMARY KEY,
    session_id uuid REFERENCES chat_session (id) ON DELETE CASCADE,
    role varchar(100) NOT NULL,
    content text NOT NULL,
    metadata jsonb, -- Intent classification, confidence scores, etc.
    intent_classification jsonb, -- Stores intent, confidence, exemplar_match
    created_at timestamp with time zone DEFAULT current_timestamp
);


-- Response cache for LLM responses
CREATE TABLE response_cache (
    id serial PRIMARY KEY,
    cache_key varchar(255) UNIQUE NOT NULL, -- Hash of query + context
    response_data jsonb NOT NULL, -- Cached response
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT current_timestamp
);


-- Embedding cache for vector embeddings
CREATE TABLE embedding_cache (
    id serial PRIMARY KEY,
    text_hash varchar(255) NOT NULL, -- Hash of input text
    embedding vector (768) NOT NULL, -- Cached embedding
    model varchar(100) NOT NULL, -- Model used for embedding
    hit_count integer DEFAULT 0, -- Track cache usage
    last_accessed timestamp with time zone DEFAULT current_timestamp, -- Last access time
    created_at timestamp with time zone DEFAULT current_timestamp,
    UNIQUE (text_hash, model) -- Allow same text for different models
);


-- Intent exemplars for vector-based intent classification
CREATE TABLE intent_exemplar (
    id serial PRIMARY KEY,
    intent varchar(100) NOT NULL,
    phrase text NOT NULL,
    embedding vector (768) NOT NULL, -- 768 dimensions for Vertex AI textembedding-gecko
    confidence_threshold real DEFAULT 0.7,
    usage_count integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT current_timestamp,
    updated_at timestamp with time zone DEFAULT current_timestamp,
    UNIQUE (intent, phrase)
);


-- Search metrics for performance tracking
CREATE TABLE search_metric (
    id serial PRIMARY KEY,
    session_id uuid REFERENCES chat_session (id),
    query_text text,
    intent varchar(100),
    confidence_score real,
    vector_search_results integer,
    vector_search_time_ms integer,
    llm_response_time_ms integer,
    total_response_time_ms integer,
    embedding_generation_time_ms integer,
    embedding_cache_hit boolean DEFAULT false,
    vector_search_cache_hit boolean DEFAULT false,
    intent_exemplar_used varchar(255),
    avg_similarity_score real,
    created_at timestamp with time zone DEFAULT current_timestamp
);


-- Vector search result cache for reducing latency
CREATE TABLE vector_search_cache (
    id serial PRIMARY KEY,
    embedding_hash varchar(32) NOT NULL,
    similarity_threshold real NOT NULL,
    result_limit integer NOT NULL,
    product_ids integer[] NOT NULL,
    results_count integer NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT current_timestamp,
    last_accessed timestamp with time zone DEFAULT current_timestamp,
    hit_count integer DEFAULT 1,
    UNIQUE (embedding_hash, similarity_threshold, result_limit)
);


-- Indexes for performance optimization
-- Vector similarity search indexes (IVFFlat for approximate nearest neighbor)
CREATE INDEX product_embedding_ivfflat_idx ON product USING ivfflat (embedding vector_cosine_ops)
WITH
    (lists = 100);


-- Vector similarity index for intent exemplars
CREATE INDEX intent_exemplar_embedding_ivfflat_idx ON intent_exemplar USING ivfflat (embedding vector_cosine_ops)
WITH
    (lists = 100);


-- Full-text search indexes
CREATE INDEX product_name_gin_idx ON product USING gin (to_tsvector('english', name));


CREATE INDEX product_description_gin_idx ON product USING gin (to_tsvector('english', description));


-- Standard B-tree indexes
CREATE INDEX product_category_idx ON product (category);


CREATE INDEX product_in_stock_idx ON product (in_stock);


CREATE INDEX product_created_at_idx ON product (created_at);


-- Store indexes for location queries
CREATE INDEX store_city_idx ON store (city);


CREATE INDEX store_state_idx ON store (state);


CREATE INDEX store_zip_idx ON store (zip);


CREATE INDEX chat_session_user_id_idx ON chat_session (user_id);


CREATE INDEX chat_session_expires_at_idx ON chat_session (expires_at);


CREATE INDEX chat_session_last_activity_idx ON chat_session (last_activity);


CREATE INDEX chat_conversation_session_id_idx ON chat_conversation (session_id);


CREATE INDEX chat_conversation_created_at_idx ON chat_conversation (created_at);


CREATE INDEX response_cache_expires_at_idx ON response_cache (expires_at);


CREATE INDEX response_cache_created_at_idx ON response_cache (created_at);


CREATE INDEX embedding_cache_model_idx ON embedding_cache (model);


CREATE INDEX embedding_cache_created_at_idx ON embedding_cache (created_at);


CREATE INDEX embedding_cache_hit_count_idx ON embedding_cache (hit_count DESC);


CREATE INDEX embedding_cache_last_accessed_idx ON embedding_cache (last_accessed DESC);


-- Intent exemplar indexes
CREATE INDEX intent_exemplar_intent_idx ON intent_exemplar (intent);


CREATE INDEX intent_exemplar_usage_count_idx ON intent_exemplar (usage_count DESC);


CREATE INDEX search_metric_session_id_idx ON search_metric (session_id);


CREATE INDEX search_metric_intent_idx ON search_metric (intent);


CREATE INDEX search_metric_created_at_idx ON search_metric (created_at);


CREATE INDEX search_metric_similarity_score_idx ON search_metric (avg_similarity_score) WHERE avg_similarity_score IS NOT NULL;


-- Vector search cache indexes
CREATE INDEX idx_vector_search_cache_expires ON vector_search_cache (expires_at)
WHERE
    expires_at IS NOT NULL;


CREATE INDEX idx_vector_search_cache_lookup ON vector_search_cache (embedding_hash, similarity_threshold, result_limit);


-- Functions for automatic updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column () returns trigger AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language plpgsql;


-- Trigger for product updated_at
CREATE TRIGGER product_updated_at_trigger before
UPDATE ON product FOR each ROW
EXECUTE function update_updated_at_column ();


-- Trigger for intent_exemplar updated_at
CREATE TRIGGER intent_exemplar_updated_at_trigger before
UPDATE ON intent_exemplar FOR each ROW
EXECUTE function update_updated_at_column ();


-- Trigger for chat_session updated_at
CREATE TRIGGER chat_session_updated_at_trigger before
UPDATE ON chat_session FOR each ROW
EXECUTE function update_updated_at_column ();


-- Trigger for search_metric updated_at
CREATE TRIGGER search_metric_updated_at_trigger before
UPDATE ON search_metric FOR each ROW
EXECUTE function update_updated_at_column ();


-- Trigger for store updated_at
CREATE TRIGGER store_updated_at_trigger before
UPDATE ON store FOR each ROW
EXECUTE function update_updated_at_column ();


-- name: migrate-0001-down
-- Drop triggers and functions
DROP TRIGGER if EXISTS chat_session_updated_at_trigger ON chat_session cascade;
DROP TRIGGER if EXISTS update_chat_session_updated_at ON chat_session cascade;


DROP TRIGGER if EXISTS intent_exemplar_updated_at_trigger ON intent_exemplar cascade;
DROP TRIGGER if EXISTS update_intent_exemplar_updated_at ON intent_exemplar cascade;


DROP TRIGGER if EXISTS product_updated_at_trigger ON product cascade;
DROP TRIGGER if EXISTS update_product_updated_at ON product cascade;


DROP TRIGGER if EXISTS search_metric_updated_at_trigger ON search_metric cascade;


DROP TRIGGER if EXISTS store_updated_at_trigger ON store cascade;


-- Drop indexes
DROP INDEX if EXISTS intent_exemplar_usage_count_idx;


DROP INDEX if EXISTS intent_exemplar_intent_idx;


DROP INDEX if EXISTS intent_exemplar_embedding_ivfflat_idx;


DROP INDEX if EXISTS embedding_cache_last_accessed_idx;


DROP INDEX if EXISTS embedding_cache_hit_count_idx;


DROP INDEX if EXISTS product_embedding_ivfflat_idx;


DROP INDEX if EXISTS product_name_gin_idx;


DROP INDEX if EXISTS product_description_gin_idx;


DROP INDEX if EXISTS product_category_idx;


DROP INDEX if EXISTS product_in_stock_idx;


DROP INDEX if EXISTS product_created_at_idx;


-- Drop store indexes
DROP INDEX if EXISTS store_city_idx;


DROP INDEX if EXISTS store_state_idx;


DROP INDEX if EXISTS store_zip_idx;


DROP INDEX if EXISTS chat_session_user_id_idx;


DROP INDEX if EXISTS chat_session_expires_at_idx;


DROP INDEX if EXISTS chat_session_last_activity_idx;


DROP INDEX if EXISTS chat_conversation_session_id_idx;


DROP INDEX if EXISTS chat_conversation_created_at_idx;


DROP INDEX if EXISTS response_cache_expires_at_idx;


DROP INDEX if EXISTS response_cache_created_at_idx;


DROP INDEX if EXISTS embedding_cache_model_idx;


DROP INDEX if EXISTS embedding_cache_created_at_idx;


DROP INDEX if EXISTS search_metric_session_id_idx;
DROP INDEX if EXISTS search_metrics_session_id_idx;


DROP INDEX if EXISTS search_metric_intent_idx;
DROP INDEX if EXISTS search_metrics_intent_idx;


DROP INDEX if EXISTS search_metric_created_at_idx;
DROP INDEX if EXISTS search_metrics_created_at_idx;


DROP INDEX if EXISTS search_metric_similarity_score_idx;


DROP INDEX if EXISTS idx_vector_search_cache_expires;


DROP INDEX if EXISTS idx_vector_search_cache_lookup;


-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS vector_search_cache cascade;
DROP TABLE IF EXISTS search_metric cascade;
DROP TABLE IF EXISTS search_metrics cascade;


DROP TABLE IF EXISTS intent_exemplar cascade;


DROP TABLE IF EXISTS embedding_cache cascade;


DROP TABLE IF EXISTS response_cache cascade;


DROP TABLE IF EXISTS chat_conversation cascade;


DROP TABLE IF EXISTS chat_session cascade;


DROP TABLE IF EXISTS store cascade;


DROP TABLE IF EXISTS product cascade;


DROP FUNCTION if EXISTS update_updated_at_column () cascade;


-- Drop extension
DROP EXTENSION if EXISTS vector cascade;
