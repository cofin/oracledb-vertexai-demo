# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""JSON and msgspec serialization helpers for Oracle Decimal, Struct, and NumPy types."""

from decimal import Decimal
from typing import Any

import msgspec
import numpy as np
from msgspec import structs
from sqlspec.typing import NUMPY_INSTALLED, UNSET
from sqlspec.utils.serializers import from_json, numpy_array_dec_hook, numpy_array_enc_hook, schema_dump, to_json
from sqlspec.utils.serializers._numpy import numpy_array_predicate

__all__ = (
    "from_json",
    "numpy_array_dec_hook",
    "numpy_array_enc_hook",
    "numpy_array_predicate",
    "sanitize_for_json",
    "schema_dump",
    "to_json",
)


def sanitize_for_json(obj: Any) -> Any:
    """Recursively convert Oracle Decimal, Struct, and NumPy values to JSON-safe Python types.

    Oracle's oracledb driver returns ``decimal.Decimal`` for NUMBER columns.
    This function ensures these are converted to int or float for standard JSON
    serialization (e.g. for Vertex AI tool outputs).

    It handles:
    - ``decimal.Decimal`` -> ``int`` or ``float``
    - ``msgspec.Struct`` -> ``dict`` (respecting ``rename`` config)
    - ``numpy.ndarray`` -> ``list``
    - ``numpy.generic`` -> Python scalar
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
