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

from litestar import Controller, get
from litestar.params import Dependency

from app.domain.system.schemas import IntentExemplar
from app.domain.system.services import ExemplarService
from app.lib.di import Inject
from app.lib.service import FilterTypes, OffsetPagination, create_filter_dependencies


class ExemplarController(Controller):
    """Intent-classification exemplar endpoints (powers the explore page).

    Ch 4 wires the live-vs-ground-truth panel onto this listing — Ch 2 ships the
    plumbing only.
    """

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
