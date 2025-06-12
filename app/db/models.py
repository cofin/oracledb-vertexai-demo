# ruff: noqa: TC003
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from advanced_alchemy.base import BigIntAuditBase, UUIDAuditBase
from advanced_alchemy.types import ORA_JSONB, DateTimeUTC
from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.oracle import VECTOR, VectorStorageFormat
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Company(BigIntAuditBase):
    """Company Table"""

    name: Mapped[str] = mapped_column(String(255))
    # -----------
    # ORM Relationships
    # ------------

    products: Mapped[list[Product]] = relationship(
        back_populates="company",
        lazy="selectin",
        uselist=True,
        cascade="all, delete",
    )


class Shop(BigIntAuditBase):
    """Shop Table"""

    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(1000))
    # -----------
    # ORM Relationships
    # ------------
    inventory: Mapped[list[Inventory]] = relationship(
        back_populates="shop",
        lazy="selectin",
        uselist=True,
        cascade="all, delete",
    )


class Product(BigIntAuditBase):
    """Product Table"""

    company_id: Mapped[int] = mapped_column(ForeignKey("company.id", ondelete="cascade"), nullable=False)
    name: Mapped[str] = mapped_column(String(255))
    current_price: Mapped[float]
    size: Mapped[str] = mapped_column("SIZE", String(50))
    description: Mapped[str] = mapped_column(String(2000))
    # Oracle 23AI vector field for embeddings
    embedding: Mapped[list[float] | None] = mapped_column(
        VECTOR(dim=768, storage_format=VectorStorageFormat.FLOAT32),  # type: ignore[no-untyped-call]
        nullable=True,
    )
    embedding_generated_on: Mapped[datetime | None] = mapped_column(DateTimeUTC, nullable=True)
    # -----------
    # ORM Relationships
    # ------------
    company: Mapped[Company] = relationship(
        viewonly=True,
        back_populates="products",
        innerjoin=True,
        uselist=False,
        lazy="joined",
    )

    inventory: Mapped[list[Inventory]] = relationship(
        back_populates="product",
        cascade="all, delete",
        lazy="noload",
        viewonly=True,
    )


class Inventory(UUIDAuditBase):
    """Inventory Table"""

    shop_id: Mapped[int] = mapped_column(
        ForeignKey("shop.id", ondelete="cascade"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id", ondelete="cascade"),
        nullable=False,
    )
    # -----------
    # ORM Relationships
    # ------------
    shop: Mapped[Shop] = relationship(back_populates="inventory", innerjoin=True, uselist=False, lazy="joined")
    shop_name: AssociationProxy[str] = association_proxy("shop", "name")
    shop_address: AssociationProxy[str] = association_proxy("shop", "address")
    product: Mapped[Product] = relationship(back_populates="inventory", innerjoin=True, uselist=False, lazy="joined")
    product_name: AssociationProxy[str] = association_proxy("product", "name")
    current_price: AssociationProxy[str] = association_proxy("product", "current_price")


# Oracle-specific models for AI features


class UserSession(UUIDAuditBase):
    """Oracle-native session storage with JSON data."""

    __tablename__ = "user_session"

    session_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    data: Mapped[dict] = mapped_column(ORA_JSONB, nullable=False, default=dict)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)

    # Relationships
    conversations: Mapped[list[ChatConversation]] = relationship(
        back_populates="session",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_session_expires", "expires_at"),
        Index("ix_session_user_expires", "user_id", "expires_at"),
    )


class ChatConversation(UUIDAuditBase):
    """Conversation history with Oracle JSON storage."""

    __tablename__ = "chat_conversation"

    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_session.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'user' | 'assistant' | 'system'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_metadata: Mapped[dict] = mapped_column(ORA_JSONB, nullable=False, default=dict)

    # Relationships
    session: Mapped[UserSession] = relationship(
        back_populates="conversations",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_chat_user_time", "user_id", "created_at"),
        Index("ix_chat_session_time", "session_id", "created_at"),
    )


class ResponseCache(UUIDAuditBase):
    """Oracle-native response caching with TTL."""

    __tablename__ = "response_cache"

    cache_key: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    query_text: Mapped[str] = mapped_column(String(4000), nullable=True)
    response: Mapped[dict] = mapped_column(ORA_JSONB, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    hit_count: Mapped[int] = mapped_column(default=0)

    __table_args__ = (
        Index("ix_cache_expires", "expires_at"),
        Index("ix_cache_key_expires", "cache_key", "expires_at"),
    )


class SearchMetrics(UUIDAuditBase):
    """Real-time search performance metrics."""

    __tablename__ = "search_metrics"

    query_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
    search_time_ms: Mapped[float] = mapped_column(nullable=False)
    embedding_time_ms: Mapped[float] = mapped_column(nullable=False)
    oracle_time_ms: Mapped[float] = mapped_column(nullable=False)
    similarity_score: Mapped[float] = mapped_column(nullable=True)
    result_count: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        Index("ix_metrics_time", "created_at", "search_time_ms"),
        Index("ix_metrics_user_time", "user_id", "created_at"),
    )


class AppConfig(UUIDAuditBase):
    """Application configuration in Oracle."""

    __tablename__ = "app_config"

    key: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    value: Mapped[dict] = mapped_column(ORA_JSONB, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)

    __table_args__ = (Index("ix_config_key", "key"),)


class IntentExemplar(BigIntAuditBase):
    """Cache for intent router exemplar embeddings."""

    __tablename__ = "intent_exemplar"

    intent: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    phrase: Mapped[str] = mapped_column(String(500), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        VECTOR(dim=768, storage_format=VectorStorageFormat.FLOAT32),  # type: ignore[no-untyped-call]
        nullable=True,
    )

    __table_args__ = (Index("ix_intent_phrase", "intent", "phrase", unique=True),)
