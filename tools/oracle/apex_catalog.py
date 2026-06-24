# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Filtered OpenAPI export for APEX REST Source Catalog imports."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from ipaddress import ip_address
from pathlib import Path
from typing import Any

APEX_PATH_PREFIX = "/api/apex/"
DEFAULT_APEX_OPENAPI_PATH = Path(".agents/generated/apex-catalog.openapi.json")
DEFAULT_APEX_CATALOG_TITLE = "Cymbal Coffee APEX REST Source Catalog"
DEFAULT_APEX_TAG = "APEX REST Catalog"
_SCHEMA_REF_PREFIX = "#/components/schemas/"


def build_apex_catalog(openapi_document: dict[str, Any], *, server_url: str | None = None) -> dict[str, Any]:
    """Build an OpenAPI document containing only APEX REST Source Catalog paths."""
    paths = openapi_document.get("paths", {})
    filtered_paths = {
        path: deepcopy(path_item)
        for path, path_item in sorted(paths.items())
        if isinstance(path, str) and path.startswith(APEX_PATH_PREFIX)
    }

    catalog: dict[str, Any] = {
        "openapi": openapi_document.get("openapi", "3.1.0"),
        "info": {"title": DEFAULT_APEX_CATALOG_TITLE, "version": _document_version(openapi_document)},
        "servers": [
            {
                "url": _normalize_server_url(server_url or _default_server_url()),
                "description": "Local Litestar app for APEX REST Source Catalog import",
            }
        ],
        "tags": [{"name": name} for name in _catalog_tag_names(filtered_paths)],
        "paths": filtered_paths,
    }

    components = _filtered_components(openapi_document, filtered_paths)
    if components:
        catalog["components"] = components
    return catalog


def export_apex_openapi_catalog(
    openapi_document: dict[str, Any], *, output_path: Path = DEFAULT_APEX_OPENAPI_PATH, server_url: str | None = None
) -> Path:
    """Write a filtered APEX catalog OpenAPI artifact and return its path."""
    catalog = build_apex_catalog(openapi_document, server_url=server_url)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def export_current_app_apex_catalog(
    *, output_path: Path = DEFAULT_APEX_OPENAPI_PATH, server_url: str | None = None
) -> Path:
    """Create the app OpenAPI schema and export its APEX REST Source Catalog subset."""
    return export_apex_openapi_catalog(_current_app_openapi_document(), output_path=output_path, server_url=server_url)


def _current_app_openapi_document() -> dict[str, Any]:
    from app.server.asgi import create_app

    return create_app().openapi_schema.to_schema()


def _document_version(openapi_document: dict[str, Any]) -> str:
    info = openapi_document.get("info", {})
    if isinstance(info, dict):
        return str(info.get("version") or "0.0.0")
    return "0.0.0"


def _default_server_url() -> str:
    if app_url := os.getenv("APP_URL"):
        return app_url
    host = _apex_import_host(os.getenv("LITESTAR_HOST", "localhost"))
    return f"http://{host}:{os.getenv('LITESTAR_PORT', '8000')}"


def _apex_import_host(host: str) -> str:
    try:
        if ip_address(host).is_unspecified:
            return "localhost"
    except ValueError:
        pass
    return host


def _normalize_server_url(server_url: str) -> str:
    normalized = server_url.strip()
    if not normalized:
        return _default_server_url()
    return normalized if normalized == "/" else normalized.rstrip("/")


def _catalog_tag_names(paths: dict[str, Any]) -> list[str]:
    names: set[str] = set()
    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            tags = operation.get("tags", [])
            if isinstance(tags, list):
                names.update(tag for tag in tags if isinstance(tag, str))
    return sorted(names or {DEFAULT_APEX_TAG})


def _filtered_components(openapi_document: dict[str, Any], filtered_paths: dict[str, Any]) -> dict[str, Any]:
    components = openapi_document.get("components", {})
    if not isinstance(components, dict):
        return {}
    schemas = components.get("schemas", {})
    if not isinstance(schemas, dict):
        return {}

    referenced = _schema_refs(filtered_paths)
    selected: set[str] = set()
    pending = list(referenced)
    while pending:
        schema_name = pending.pop()
        if schema_name in selected or schema_name not in schemas:
            continue
        selected.add(schema_name)
        pending.extend(_schema_refs(schemas[schema_name]) - selected)

    if not selected:
        return {}
    return {"schemas": {name: deepcopy(schemas[name]) for name in sorted(selected)}}


def _schema_refs(node: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith(_SCHEMA_REF_PREFIX):
            refs.add(ref.removeprefix(_SCHEMA_REF_PREFIX))
        for value in node.values():
            refs.update(_schema_refs(value))
    elif isinstance(node, list):
        for value in node:
            refs.update(_schema_refs(value))
    return refs
