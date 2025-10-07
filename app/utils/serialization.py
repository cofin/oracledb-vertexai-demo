"""High-performance serialization utilities using msgspec.

Based on upstream utils/serialization.py but optimized for our SQLSpec-based architecture.
Provides fast JSON encoding/decoding with support for common data types including numpy arrays.
"""

from __future__ import annotations

import datetime
from typing import Any
from uuid import UUID

import msgspec


def _default_encoder(value: Any) -> str:
    """Default encoder for non-standard types.

    Handles serialization of:
    - UUID objects to string
    - datetime objects to ISO format with Z suffix
    - date objects to ISO format
    - Other objects via string conversion

    Args:
        value: Object to encode

    Returns:
        String representation of the object

    Raises:
        TypeError: If object cannot be serialized
    """
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime.datetime):
        return convert_datetime_to_gmt_iso(value)
    if isinstance(value, datetime.date):
        return convert_date_to_iso(value)

    try:
        return str(value)
    except Exception as exc:
        msg = f"Cannot serialize {type(value).__name__}"
        raise TypeError(msg) from exc


# Global msgspec encoders for performance
_msgspec_json_encoder = msgspec.json.Encoder(enc_hook=_default_encoder)
_msgspec_json_decoder = msgspec.json.Decoder()


def to_json(value: Any) -> bytes:
    """Encode object to JSON bytes using optimized msgspec package.

    Args:
        value: Object to encode

    Returns:
        JSON encoded bytes
    """
    if isinstance(value, bytes):
        return value
    return _msgspec_json_encoder.encode(value)


def from_json(value: bytes | str) -> Any:
    """Decode JSON bytes/string to object using optimized msgspec package.

    Args:
        value: JSON bytes or string to decode

    Returns:
        Decoded Python object
    """
    return _msgspec_json_decoder.decode(value)


def convert_datetime_to_gmt_iso(dt: datetime.datetime) -> str:
    """Convert datetime to GMT ISO format with Z suffix.

    Args:
        dt: Datetime object to convert

    Returns:
        ISO formatted datetime string with Z suffix
    """
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=datetime.UTC)
    return dt.isoformat().replace("+00:00", "Z")


def convert_date_to_iso(dt: datetime.date) -> str:
    """Convert date to ISO format string.

    Args:
        dt: Date object to convert

    Returns:
        ISO formatted date string
    """
    return dt.isoformat()


# NumPy Array Serialization Support
def numpy_array_predicate(type_: type[Any]) -> bool:
    """Check if type is a numpy array.

    Args:
        type_: Type to check

    Returns:
        True if type is a numpy array type
    """
    import numpy as np
    return type_ is np.ndarray or (hasattr(type_, "__origin__") and str(type_).startswith("numpy.ndarray"))


def numpy_array_enc_hook(arr: Any) -> Any:
    """Convert numpy array to list for serialization.

    Args:
        arr: Numpy array to convert

    Returns:
        List representation of the numpy array
    """

    import numpy as np
    if isinstance(arr, np.ndarray):
        return arr.tolist()
    return arr


def numpy_array_dec_hook(obj: Any) -> Any:
    """Convert list back to numpy array for deserialization.

    Args:
        obj: Object to convert (expected to be a list)

    Returns:
        Numpy array if obj is a list, otherwise obj unchanged
    """

    if isinstance(obj, list):
        import numpy as np
        return np.array(obj, dtype=np.float32)
    return obj


def general_dec_hook(type_: type[Any], obj: Any) -> Any:
    """General decoder hook for custom types.

    Args:
        type_: Target type for conversion
        obj: Object to convert

    Returns:
        Converted object

    Raises:
        NotImplementedError: For unsupported types
    """
    if numpy_array_predicate(type_):
        return numpy_array_dec_hook(obj)
    msg = f"Encountered unknown type: {type_!s}"
    raise NotImplementedError(msg)
