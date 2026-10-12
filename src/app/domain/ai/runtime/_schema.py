# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""JSON Schema to Gemini FunctionDeclaration schema translation."""

from typing import Any

__all__ = ("GEMINI_ALLOWED_KEYS", "translate_to_gemini_schema")

GEMINI_ALLOWED_KEYS = frozenset({
    "description",
    "enum",
    "format",
    "items",
    "nullable",
    "properties",
    "required",
    "type",
})


def translate_to_gemini_schema(raw_schema: dict[str, Any]) -> dict[str, Any]:
    """Translate msgspec JSON Schema output into Gemini FunctionDeclaration schema subset.

    Args:
        raw_schema: Raw JSON Schema dictionary from msgspec.json.schema.

    Returns:
        Gemini-compliant JSON schema dictionary with lowercase JSON Schema types and filtered keys.
    """
    defs = raw_schema.get("$defs", {})
    return _visit_schema_node(raw_schema, defs)


def _visit_schema_node(node: Any, defs: dict[str, Any]) -> dict[str, Any]:
    """Recursively process a schema node.

    Args:
        node: The schema node to inspect.
        defs: Definitions dictionary from the root schema.

    Returns:
        Cleaned Gemini schema dictionary.
    """
    if not isinstance(node, dict):
        return {"type": "string"}
    if "$ref" in node:
        ref_name = str(node["$ref"]).rsplit("/", maxsplit=1)[-1]
        resolved = defs.get(ref_name)
        return _visit_schema_node(resolved, defs) if isinstance(resolved, dict) else {"type": "object"}
    if "anyOf" in node:
        branches = [b for b in node["anyOf"] if isinstance(b, dict)]
        non_null = [b for b in branches if b.get("type") != "null"]
        has_null = len(non_null) != len(branches)
        merged: dict[str, Any] = _visit_schema_node(non_null[0], defs) if non_null else {"type": "string"}
        if has_null:
            merged["nullable"] = True
        return merged

    out: dict[str, Any] = {}
    for key, val in node.items():
        if key not in GEMINI_ALLOWED_KEYS:
            continue
        if key == "type" and isinstance(val, str):
            out["type"] = val.lower()
        elif key == "properties" and isinstance(val, dict):
            out["properties"] = {prop: _visit_schema_node(spec, defs) for prop, spec in val.items()}
        elif key == "items" and isinstance(val, dict):
            out["items"] = _visit_schema_node(val, defs)
        elif key == "enum" and isinstance(val, list):
            out["enum"] = [str(item) for item in val]
        else:
            out[key] = val
    out.setdefault("type", "object" if "properties" in out else "string")
    return out
