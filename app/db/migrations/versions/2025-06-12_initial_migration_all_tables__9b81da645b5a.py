# type: ignore
"""Initial migration - all tables consolidated

Revision ID: 9b81da645b5a
Revises: 
Create Date: 2025-06-12 15:16:50.887230+00:00

"""
from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from advanced_alchemy.types import EncryptedString, EncryptedText, GUID, ORA_JSONB, DateTimeUTC
from sqlalchemy import Text, text  # noqa: F401
from sqlalchemy.dialects import oracle
from sqlalchemy.dialects.oracle import VectorStorageFormat
if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["downgrade", "upgrade", "schema_upgrades", "schema_downgrades", "data_upgrades", "data_downgrades"]

sa.GUID = GUID
sa.DateTimeUTC = DateTimeUTC
sa.ORA_JSONB = ORA_JSONB
sa.EncryptedString = EncryptedString
sa.EncryptedText = EncryptedText

# revision identifiers, used by Alembic.
revision = '9b81da645b5a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            schema_upgrades()
            data_upgrades()

def downgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            data_downgrades()
            schema_downgrades()

def schema_upgrades() -> None:
    """Schema upgrade migrations using raw Oracle DDL for clarity."""
    
    # Create sequences for auto-incrementing BigInt primary keys
    op.execute("""
        CREATE SEQUENCE company_id_seq 
        START WITH 1 
        INCREMENT BY 1 
        NOMAXVALUE 
        CACHE 20
    """)
    
    op.execute("""
        CREATE SEQUENCE shop_id_seq 
        START WITH 1 
        INCREMENT BY 1 
        NOMAXVALUE 
        CACHE 20
    """)
    
    op.execute("""
        CREATE SEQUENCE product_id_seq 
        START WITH 1 
        INCREMENT BY 1 
        NOMAXVALUE 
        CACHE 20
    """)
    
    op.execute("""
        CREATE SEQUENCE intent_exemplar_id_seq 
        START WITH 1 
        INCREMENT BY 1 
        NOMAXVALUE 
        CACHE 20
    """)
    
    # Create app_config table
    op.execute("""
        CREATE TABLE app_config (
            id RAW(16) DEFAULT SYS_GUID() NOT NULL,
            key VARCHAR2(256 CHAR) NOT NULL,
            value JSON NOT NULL,
            description VARCHAR2(500 CHAR),
            sa_orm_sentinel NUMBER(10),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CONSTRAINT pk_app_config PRIMARY KEY (id),
            CONSTRAINT uq_app_config_key UNIQUE (key),
            CONSTRAINT chk_app_config_json CHECK (value IS JSON)
        )
    """)
    
    # Create company table
    op.execute("""
        CREATE TABLE company (
            id NUMBER(19) DEFAULT company_id_seq.NEXTVAL NOT NULL,
            name VARCHAR2(255 CHAR) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CONSTRAINT pk_company PRIMARY KEY (id)
        )
    """)
    
    # Create shop table
    op.execute("""
        CREATE TABLE shop (
            id NUMBER(19) DEFAULT shop_id_seq.NEXTVAL NOT NULL,
            name VARCHAR2(255 CHAR) NOT NULL,
            address VARCHAR2(1000 CHAR) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CONSTRAINT pk_shop PRIMARY KEY (id)
        )
    """)
    
    # Create intent_exemplar table with Oracle 23AI vector support and In-Memory option
    op.execute("""
        CREATE TABLE intent_exemplar (
            id NUMBER(19) DEFAULT intent_exemplar_id_seq.NEXTVAL NOT NULL,
            intent VARCHAR2(50 CHAR) NOT NULL,
            phrase VARCHAR2(500 CHAR) NOT NULL,
            embedding VECTOR(768, FLOAT32),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CONSTRAINT pk_intent_exemplar PRIMARY KEY (id)
        ) INMEMORY PRIORITY HIGH
    """)
    
    # Create indexes for intent_exemplar
    op.execute("CREATE INDEX ix_intent_exemplar_intent ON intent_exemplar (intent)")
    op.execute("CREATE UNIQUE INDEX ix_intent_phrase ON intent_exemplar (intent, phrase)")
    
    # Create response_cache table with Oracle JSON support and In-Memory option
    op.execute("""
        CREATE TABLE response_cache (
            id RAW(16) DEFAULT SYS_GUID() NOT NULL,
            cache_key VARCHAR2(256 CHAR) NOT NULL,
            query_text VARCHAR2(4000 CHAR),
            response JSON NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            hit_count NUMBER(10) DEFAULT 0 NOT NULL,
            sa_orm_sentinel NUMBER(10),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CONSTRAINT pk_response_cache PRIMARY KEY (id),
            CONSTRAINT uq_response_cache_key UNIQUE (cache_key),
            CONSTRAINT chk_response_json CHECK (response IS JSON)
        ) INMEMORY PRIORITY HIGH
    """)
    
    # Create indexes for response_cache
    op.execute("CREATE INDEX ix_cache_expires ON response_cache (expires_at)")
    op.execute("CREATE INDEX ix_cache_key_expires ON response_cache (cache_key, expires_at)")
    
    # Create search_metrics table for performance monitoring
    op.execute("""
        CREATE TABLE search_metrics (
            id RAW(16) DEFAULT SYS_GUID() NOT NULL,
            query_id VARCHAR2(128 CHAR) NOT NULL,
            user_id VARCHAR2(128 CHAR),
            search_time_ms BINARY_DOUBLE NOT NULL,
            embedding_time_ms BINARY_DOUBLE NOT NULL,
            oracle_time_ms BINARY_DOUBLE NOT NULL,
            similarity_score BINARY_DOUBLE,
            result_count NUMBER(10) NOT NULL,
            sa_orm_sentinel NUMBER(10),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CONSTRAINT pk_search_metrics PRIMARY KEY (id)
        )
    """)
    
    # Create indexes for search_metrics
    op.execute("CREATE INDEX ix_search_metrics_query_id ON search_metrics (query_id)")
    op.execute("CREATE INDEX ix_search_metrics_user_id ON search_metrics (user_id)")
    op.execute("CREATE INDEX ix_metrics_time ON search_metrics (created_at, search_time_ms)")
    op.execute("CREATE INDEX ix_metrics_user_time ON search_metrics (user_id, created_at)")
    
    # Create user_session table with Oracle JSON support
    op.execute("""
        CREATE TABLE user_session (
            id RAW(16) DEFAULT SYS_GUID() NOT NULL,
            session_id VARCHAR2(128 CHAR) NOT NULL,
            user_id VARCHAR2(128 CHAR) NOT NULL,
            data JSON DEFAULT '{}' NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            sa_orm_sentinel NUMBER(10),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CONSTRAINT pk_user_session PRIMARY KEY (id),
            CONSTRAINT uq_user_session_id UNIQUE (session_id),
            CONSTRAINT chk_session_data CHECK (data IS JSON)
        )
    """)
    
    # Create indexes for user_session
    op.execute("CREATE INDEX ix_user_session_user_id ON user_session (user_id)")
    op.execute("CREATE INDEX ix_session_expires ON user_session (expires_at)")
    op.execute("CREATE INDEX ix_session_user_expires ON user_session (user_id, expires_at)")
    
    # Create chat_conversation table
    op.execute("""
        CREATE TABLE chat_conversation (
            id RAW(16) DEFAULT SYS_GUID() NOT NULL,
            session_id RAW(16) NOT NULL,
            user_id VARCHAR2(128 CHAR) NOT NULL,
            role VARCHAR2(20 CHAR) NOT NULL,
            content CLOB NOT NULL,
            message_metadata JSON DEFAULT '{}' NOT NULL,
            sa_orm_sentinel NUMBER(10),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CONSTRAINT pk_chat_conversation PRIMARY KEY (id),
            CONSTRAINT fk_chat_session FOREIGN KEY (session_id) 
                REFERENCES user_session(id) ON DELETE CASCADE,
            CONSTRAINT chk_msg_metadata CHECK (message_metadata IS JSON),
            CONSTRAINT chk_role CHECK (role IN ('user', 'assistant', 'system'))
        )
    """)
    
    # Create indexes for chat_conversation
    op.execute("CREATE INDEX ix_chat_conversation_user_id ON chat_conversation (user_id)")
    op.execute("CREATE INDEX ix_chat_session_time ON chat_conversation (session_id, created_at)")
    op.execute("CREATE INDEX ix_chat_user_time ON chat_conversation (user_id, created_at)")
    
    # Create product table with Oracle 23AI vector support
    op.execute("""
        CREATE TABLE product (
            id NUMBER(19) DEFAULT product_id_seq.NEXTVAL NOT NULL,
            company_id NUMBER(19) NOT NULL,
            name VARCHAR2(255 CHAR) NOT NULL,
            current_price BINARY_DOUBLE NOT NULL,
            "SIZE" VARCHAR2(50 CHAR) NOT NULL,
            description VARCHAR2(2000 CHAR) NOT NULL,
            embedding VECTOR(768, FLOAT32),
            embedding_generated_on TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CONSTRAINT pk_product PRIMARY KEY (id),
            CONSTRAINT fk_product_company FOREIGN KEY (company_id) 
                REFERENCES company(id) ON DELETE CASCADE
        )
    """)
    
    # Create vector index for similarity search on products
    op.execute("""
        CREATE VECTOR INDEX idx_product_embedding ON product(embedding) 
        ORGANIZATION NEIGHBOR PARTITIONS 
        DISTANCE COSINE 
        WITH TARGET ACCURACY 95
    """)
    
    # Create inventory table (junction table between shop and product)
    op.execute("""
        CREATE TABLE inventory (
            id RAW(16) DEFAULT SYS_GUID() NOT NULL,
            shop_id NUMBER(19) NOT NULL,
            product_id NUMBER(19) NOT NULL,
            sa_orm_sentinel NUMBER(10),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CONSTRAINT pk_inventory PRIMARY KEY (id),
            CONSTRAINT fk_inventory_shop FOREIGN KEY (shop_id) 
                REFERENCES shop(id) ON DELETE CASCADE,
            CONSTRAINT fk_inventory_product FOREIGN KEY (product_id) 
                REFERENCES product(id) ON DELETE CASCADE,
            CONSTRAINT uq_shop_product UNIQUE (shop_id, product_id)
        )
    """)
    
    # Note: For updated_at columns, we rely on the application layer (SQLAlchemy) 
    # to handle updates via the AuditBase mixin which automatically updates 
    # these fields on save. This is more portable than database triggers.

def schema_downgrades() -> None:
    """Schema downgrade migrations."""
    # Drop tables in reverse order of creation
    op.execute("DROP TABLE inventory")
    op.execute("DROP TABLE product")
    op.execute("DROP TABLE chat_conversation")
    op.execute("DROP TABLE user_session")
    op.execute("DROP TABLE shop")
    op.execute("DROP TABLE search_metrics")
    op.execute("DROP TABLE response_cache")
    op.execute("DROP TABLE intent_exemplar")
    op.execute("DROP TABLE company")
    op.execute("DROP TABLE app_config")
    
    # Drop sequences
    op.execute("DROP SEQUENCE intent_exemplar_id_seq")
    op.execute("DROP SEQUENCE product_id_seq")
    op.execute("DROP SEQUENCE shop_id_seq")
    op.execute("DROP SEQUENCE company_id_seq")

def data_upgrades() -> None:
    """Add any optional data upgrade migrations here!"""

def data_downgrades() -> None:
    """Add any optional data downgrade migrations here!"""