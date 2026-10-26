# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""JSON and msgspec serialization helpers for Oracle Decimal, Struct, and NumPy types."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, overload

import msgspec
import numpy as np
from msgspec import structs
from sqlspec.typing import NUMPY_INSTALLED, UNSET
from sqlspec.utils.serializers import from_json, numpy_array_dec_hook, numpy_array_enc_hook, schema_dump, to_json
from sqlspec.utils.serializers._numpy import numpy_array_predicate

__all__ = (
    "decode_json",
    "encode_json",
    "encode_json_bytes",
    "format_json",
    "from_json",
    "numpy_array_dec_hook",
    "numpy_array_enc_hook",
    "numpy_array_predicate",
    "sanitize_for_json",
    "schema_dump",
    "to_json",
    "to_schema",
)


def encode_json_bytes(value: Any) -> bytes:
    """Serialize a Python or msgspec value into UTF-8 JSON bytes."""
    return _JSON_ENCODER.encode(value)


def encode_json(value: Any) -> str:
    """Serialize a Python or msgspec value into a UTF-8 JSON string."""
    return _JSON_ENCODER.encode(value).decode("utf-8")


def format_json(value: Any, *, indent: int = 2) -> str:
    """Serialize and pretty-format a Python or msgspec value into indented UTF-8 JSON."""
    raw = _JSON_ENCODER.encode(value)
    return msgspec.json.format(raw, indent=indent).decode("utf-8")


@overload
def decode_json[SchemaT](value: str | bytes | bytearray | memoryview, *, target_type: type[SchemaT]) -> SchemaT: ...


@overload
def decode_json(value: str | bytes | bytearray | memoryview, *, target_type: None = None) -> Any: ...


def decode_json[SchemaT](
    value: str | bytes | bytearray | memoryview, *, target_type: type[SchemaT] | None = None
) -> Any:
    """Decode JSON text or bytes into an optional msgspec target type."""
    if target_type is not None:
        return msgspec.json.decode(value, type=target_type, dec_hook=numpy_array_dec_hook)
    return msgspec.json.decode(value, dec_hook=numpy_array_dec_hook)


def to_schema[SchemaT](data: Any, schema_type: type[SchemaT]) -> SchemaT:
    """Coerce an arbitrary mapping or built-in value into a typed schema class."""
    return msgspec.convert(data, type=schema_type, strict=False, dec_hook=numpy_array_dec_hook)


def sanitize_for_json(obj: Any) -> Any:
    """Recursively convert Oracle Decimal, Struct, and NumPy values to JSON-safe Python types.

    Oracle's oracledb driver returns ``decimal.Decimal`` for NUMBER columns.
    This function ensures these are converted to int or float for standard JSON
    serialization (e.g. for Vertex AI tool outputs).
    """
    if NUMPY_INSTALLED and isinstance(obj, np.ndarray | np.generic):
        return [sanitize_for_json(v) for v in obj.tolist()] if isinstance(obj, np.ndarray) else obj.item()

    if isinstance(obj, msgspec.Struct):
        fields = structs.fields(obj)
        res = {}
        for field in fields:
            val = getattr(obj, field.name, UNSET)
            if val is not UNSET:
                res[field.encode_name] = sanitize_for_json(val)
        return res

    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)

    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]

    return obj


def _json_enc_hook(value: Any) -> Any:
    """Encode Oracle Decimal, Path, and NumPy types for msgspec JSON serialization."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if NUMPY_INSTALLED and isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    return numpy_array_enc_hook(value)


_JSON_ENCODER: msgspec.json.Encoder = msgspec.json.Encoder(enc_hook=_json_enc_hook)
