# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Product domain schemas package."""

from ._apex import (
    ApexInventoryList,
    ApexInventorySummaryList,
    ApexInventorySummaryRow,
    ApexOpenAPIStatus,
    ApexProduct,
    ApexProductList,
    ApexRecommendation,
    ApexRecommendationRequest,
    ApexRecommendationResponse,
    ApexStoreList,
    ApexVectorReadiness,
    ApexVectorStatus,
)
from ._products import (
    ExplainPlan,
    ExplainPlanRow,
    Product,
    ProductAvailability,
    ProductMatch,
    Store,
    StoreDistance,
    StoreHours,
    StoreProductInventory,
    VectorDemo,
    VectorDemoMatch,
    VectorQuery,
)

__all__ = (
    "ApexInventoryList",
    "ApexInventorySummaryList",
    "ApexInventorySummaryRow",
    "ApexOpenAPIStatus",
    "ApexProduct",
    "ApexProductList",
    "ApexRecommendation",
    "ApexRecommendationRequest",
    "ApexRecommendationResponse",
    "ApexStoreList",
    "ApexVectorReadiness",
    "ApexVectorStatus",
    "ExplainPlan",
    "ExplainPlanRow",
    "Product",
    "ProductAvailability",
    "ProductMatch",
    "Store",
    "StoreDistance",
    "StoreHours",
    "StoreProductInventory",
    "VectorDemo",
    "VectorDemoMatch",
    "VectorQuery",
)
