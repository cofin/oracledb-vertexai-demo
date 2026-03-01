from decimal import Decimal
from typing import Any

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
    """Recursively convert Oracle Decimal values to JSON-safe Python types.

    Oracle's oracledb driver returns ``decimal.Decimal`` for NUMBER columns
    and JSON numeric values.  This function walks arbitrarily nested dicts
    and lists, converting Decimal → int (when lossless) or float.
    """
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    return obj
