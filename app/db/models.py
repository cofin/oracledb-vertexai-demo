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

from advanced_alchemy.base import BigIntAuditBase, UUIDAuditBase
from sqlalchemy import ForeignKey, String
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
    latitude: Mapped[float]
    longitude: Mapped[float]
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
    size: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(2000))
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
    shop_latitude: AssociationProxy[str] = association_proxy("shop", "latitude")
    shop_longitude: AssociationProxy[str] = association_proxy("shop", "longitude")
    product: Mapped[Product] = relationship(back_populates="inventory", innerjoin=True, uselist=False, lazy="joined")
    product_name: AssociationProxy[str] = association_proxy("product", "name")
    current_price: AssociationProxy[str] = association_proxy("product", "current_price")
