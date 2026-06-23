# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the APEX REST Source Catalog OpenAPI exporter."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner


def _openapi_document() -> dict[str, object]:
    """Return a small app OpenAPI document with mixed APEX and non-APEX paths."""
    return {
        "openapi": "3.1.0",
        "info": {"title": "Full Cymbal Coffee API", "version": "1.2.3"},
        "servers": [{"url": "/"}],
        "paths": {
            "/api/apex/products": {
                "get": {
                    "tags": ["APEX REST Catalog"],
                    "operationId": "ApexListProducts",
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ApexProductList"}}
                            }
                        }
                    },
                }
            },
            "/api/chat/stream": {
                "post": {
                    "tags": ["Chat"],
                    "operationId": "StreamChat",
                    "responses": {"200": {"description": "chat stream"}},
                }
            },
            "/api/apex/recommendations": {
                "post": {
                    "tags": ["APEX REST Catalog"],
                    "operationId": "ApexCreateRecommendations",
                    "requestBody": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/ApexRecommendationRequest"}}
                        }
                    },
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ApexRecommendationResponse"}
                                }
                            }
                        }
                    },
                }
            },
            "/api/products": {
                "get": {
                    "tags": ["Products"],
                    "operationId": "ListProducts",
                    "responses": {"200": {"description": "full product list"}},
                }
            },
        },
        "components": {
            "schemas": {
                "ApexProductList": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/ApexProduct"},
                        }
                    },
                },
                "ApexProduct": {"type": "object", "properties": {"name": {"type": "string"}}},
                "ApexRecommendationRequest": {"type": "object", "properties": {"query": {"type": "string"}}},
                "ApexRecommendationResponse": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/ApexRecommendation"},
                        }
                    },
                },
                "ApexRecommendation": {"type": "object", "properties": {"name": {"type": "string"}}},
                "ChatMessage": {"type": "object", "properties": {"body": {"type": "string"}}},
            }
        },
    }


def test_build_apex_catalog_filters_paths_and_referenced_components() -> None:
    """The catalog contains only /api/apex paths and their reachable schemas."""
    from tools.oracle.apex_catalog import build_apex_catalog

    catalog = build_apex_catalog(_openapi_document(), server_url="http://localhost:8000")

    assert set(catalog["paths"]) == {"/api/apex/products", "/api/apex/recommendations"}
    assert "/api/chat/stream" not in catalog["paths"]
    assert "/api/products" not in catalog["paths"]
    assert catalog["servers"] == [
        {
            "url": "http://localhost:8000",
            "description": "Local Litestar app for APEX REST Source Catalog import",
        }
    ]
    assert catalog["info"] == {"title": "Cymbal Coffee APEX REST Source Catalog", "version": "1.2.3"}
    assert catalog["tags"] == [{"name": "APEX REST Catalog"}]
    assert set(catalog["components"]["schemas"]) == {
        "ApexProductList",
        "ApexProduct",
        "ApexRecommendationRequest",
        "ApexRecommendationResponse",
        "ApexRecommendation",
    }


def test_export_apex_openapi_catalog_writes_deterministic_json(tmp_path: Path) -> None:
    """The exporter creates parent directories and writes newline-terminated JSON."""
    from tools.oracle.apex_catalog import DEFAULT_APEX_OPENAPI_PATH, export_apex_openapi_catalog

    output_path = tmp_path / "generated" / "apex-catalog.openapi.json"

    result = export_apex_openapi_catalog(
        _openapi_document(),
        output_path=output_path,
        server_url="http://127.0.0.1:5006",
    )

    assert Path(".agents/generated/apex-catalog.openapi.json") == DEFAULT_APEX_OPENAPI_PATH
    assert result == output_path
    payload = output_path.read_text(encoding="utf-8")
    assert payload.endswith("\n")
    data = json.loads(payload)
    assert data["servers"][0]["url"] == "http://127.0.0.1:5006"
    assert list(data["paths"]) == sorted(data["paths"])


def test_apex_export_openapi_cli_invokes_catalog_exporter(tmp_path: Path) -> None:
    """`infra apex export-openapi` writes the catalog path selected by CLI options."""
    from tools.oracle.cli import apex as apex_cli

    output_path = tmp_path / "catalog.json"
    runner = CliRunner()
    with patch.object(apex_cli, "export_current_app_apex_catalog") as export:
        export.return_value = output_path
        result = runner.invoke(
            apex_cli.apex_group,
            ["export-openapi", "--output", str(output_path), "--server-url", "http://localhost:9000"],
        )

    assert result.exit_code == 0
    export.assert_called_once_with(output_path=output_path, server_url="http://localhost:9000")
    assert str(output_path) in result.output.replace("\n", "")
