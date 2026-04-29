from decimal import Decimal
from typing import Any

import msgspec
from sqlspec.typing import NUMPY_INSTALLED
from sqlspec.utils.serializers import (
    from_json,
    numpy_array_dec_hook,
    numpy_array_enc_hook,
    numpy_array_predicate,
    to_json,
)

__all__ = (
    "from_json",
    "numpy_array_dec_hook",
    "numpy_array_enc_hook",
    "numpy_array_predicate",
    "sanitize_for_json",
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
    # 1. Handle NumPy types
    if NUMPY_INSTALLED:
        import numpy as np

        if isinstance(obj, np.ndarray | np.generic):
            return [sanitize_for_json(v) for v in obj.tolist()] if isinstance(obj, np.ndarray) else obj.item()

    # 2. Handle msgspec Structs
    if isinstance(obj, msgspec.Struct):
        from msgspec import structs
        from sqlspec.typing import UNSET

        fields = structs.fields(obj)
        res = {}
        for field in fields:
            val = getattr(obj, field.name, UNSET)
            if val is not UNSET:
                res[field.encode_name] = sanitize_for_json(val)
        return res

    # 3. Handle Decimal (Oracle NUMBER)
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)

    # 4. Recursive collections
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]

    return obj
