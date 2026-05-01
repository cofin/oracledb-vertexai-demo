# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Compatibility exports for ``coffee`` data operation helpers."""

from __future__ import annotations

from app.cli._helpers.cache import clear_application_cache
from app.cli._helpers.database import downgrade_database, upgrade_database
from app.cli._helpers.embeddings import generate_product_embeddings
from app.cli._helpers.fixtures import (
    display_available_tables,
    display_export_results,
    display_fixture_list,
    display_fixture_results,
    export_fixture_data,
    get_fixture_status,
    load_fixture_data,
    process_fixture_result,
)
from app.cli._helpers.models import show_model_info

__all__ = (
    "clear_application_cache",
    "display_available_tables",
    "display_export_results",
    "display_fixture_list",
    "display_fixture_results",
    "downgrade_database",
    "export_fixture_data",
    "generate_product_embeddings",
    "get_fixture_status",
    "load_fixture_data",
    "process_fixture_result",
    "show_model_info",
    "upgrade_database",
)
