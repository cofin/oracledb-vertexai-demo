# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

from litestar import Controller, get
from litestar.params import Dependency

from app.domain.system.schemas import IntentExemplar
from app.domain.system.services import ExemplarService
from app.lib.di import Inject
from app.lib.service import FilterTypes, OffsetPagination, create_filter_dependencies


class ExemplarController(Controller):
    """Read-only listing of intent-classification exemplars."""

    path = "/api/exemplars"
    tags = ["Exemplars"]
    dependencies = create_filter_dependencies({
        "pagination_type": "limit_offset",
        "sort_field": "id",
        "sort_order": "asc",
        "id_filter": int,
        "id_field": "id",
        "search": ["intent", "phrase"],
        "search_ignore_case": True,
        "created_at": True,
    })

    @get("/", operation_id="ListExemplars", name="exemplars:list", summary="List Intent Exemplars")
    async def list_exemplars(
        self,
        exemplars_service: Inject[ExemplarService],
        filters: list[FilterTypes] = Dependency(skip_validation=True),
    ) -> OffsetPagination[IntentExemplar]:
        """List intent exemplars with pagination, search, and filtering."""
        return await exemplars_service.list_with_count(*filters)
