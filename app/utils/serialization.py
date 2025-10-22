"""High-performance serialization utilities using msgspec.

This module provides JSON encoding/decoding with support for common data types
including numpy arrays, which are used for vector embeddings.

TODO: Upstream to SQLSpec
========================
This serialization logic should be upstreamed to SQLSpec's litestar integration.
The following components need to be added:

1. **SQLSpec Core** (`sqlspec/utils/serialization.py`):
   - Add `numpy_array_enc_hook`, `numpy_array_dec_hook`, `numpy_array_predicate`
   - Export from `sqlspec.utils.serializers`

2. **SQLSpec Litestar Plugin** (`sqlspec/extensions/litestar/__init__.py`):
   - Auto-configure type encoders/decoders in `SQLSpecPlugin.on_app_init()`
   - Add: `app_config.type_encoders = {np.ndarray: numpy_array_enc_hook}`
   - Add: `app_config.type_decoders = [(numpy_array_predicate, general_dec_hook)]`

3. **Benefits**:
   - Users get numpy serialization automatically when using SQLSpecPlugin
   - No need to manually configure type encoders in every app
   - Consistent serialization across all SQLSpec + Litestar apps

4. **Implementation Pattern**:
   ```python
   # In SQLSpecPlugin.on_app_init():
   try:
       import numpy as np
       from sqlspec.utils.serializers import (
           numpy_array_enc_hook,
           numpy_array_predicate,
           general_dec_hook,
       )
       app_config.type_encoders = {np.ndarray: numpy_array_enc_hook}
       app_config.type_decoders = [(numpy_array_predicate, general_dec_hook)]
   except ImportError:
       # NumPy not installed, skip numpy serialization
       pass
   ```

For now, this is implemented locally until it can be upstreamed.
"""

from __future__ import annotations

import datetime
from typing import Any, Literal, overload
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


@overload
def to_json(data: Any, *, as_bytes: Literal[False] = ...) -> str: ...


@overload
def to_json(data: Any, *, as_bytes: Literal[True]) -> bytes: ...


def to_json(data: Any, *, as_bytes: bool = False) -> str | bytes:
    """Encode data to JSON string or bytes.

    Args:
        data: Data to encode.
        as_bytes: Whether to return bytes instead of string for optimal performance.

    Returns:
        JSON string or bytes representation based on as_bytes parameter.
    """
    if isinstance(data, bytes):
        return data
    return _msgspec_json_encoder.encode(data)


@overload
def from_json(data: str) -> Any: ...


@overload
def from_json(data: bytes, *, decode_bytes: bool = ...) -> Any: ...


def from_json(data: str | bytes, *, decode_bytes: bool = True) -> Any:
    """Decode JSON string or bytes to Python object.

    Args:
        data: JSON string or bytes to decode.
        decode_bytes: Whether to decode bytes input (vs passing through).

    Returns:
        Decoded Python object.
    """
    if isinstance(data, bytes):
        return data
    return _msgspec_json_encoder.encode(data)


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


# NumPy Array Serialization Support for Vector Embeddings
def numpy_array_predicate(type_: type[Any]) -> bool:
    """Check if type is a numpy array.

    Used by Litestar's type decoder system to identify numpy arrays.

    Args:
        type_: Type to check

    Returns:
        True if type is a numpy array type
    """
    import numpy as np

    return type_ is np.ndarray or (hasattr(type_, "__origin__") and str(type_).startswith("numpy.ndarray"))


def numpy_array_enc_hook(arr: Any) -> Any:
    """Convert numpy array to list for JSON serialization.

    Used by Litestar's type encoder system to serialize numpy arrays
    to JSON-compatible lists. This is essential for returning vector
    embeddings in API responses.

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

    Used to reconstruct numpy arrays when receiving JSON data.

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

    Dispatcher for type-specific decoders. Currently handles numpy arrays.

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


__all__ = (
    "from_json",
    "general_dec_hook",
    "numpy_array_dec_hook",
    "numpy_array_enc_hook",
    "numpy_array_predicate",
    "to_json",
)
