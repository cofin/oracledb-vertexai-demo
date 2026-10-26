# SPDX-FileCopyrightText: 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for FrozenBaseStruct, serialization helpers, exceptions, security principals, and OracleLoaderService."""

from __future__ import annotations

import gc
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import numpy as np
import pytest
from google.auth.exceptions import DefaultCredentialsError
from google.genai import errors as genai_errors
from litestar.exceptions import ServiceUnavailableException

from app.domain.chat.exceptions import AIServiceUnconfigured as ChatAIServiceUnconfigured
from app.lib.exceptions import (
    AIServiceUnconfigured,
    ApplicationError,
    ai_service_unconfigured_handler,
    is_credential_error,
    is_expected_service_unavailable,
)
from app.lib.schema import CamelizedFrozenStruct, FrozenBaseStruct, Message
from app.lib.security import _ApiKeyResolver, _ApiKeySlot, _ApiKeyVerifier
from app.lib.service import OracleAsyncService, OracleLoaderService, default_sql_loader
from app.utils.serialization import (
    decode_json,
    encode_json,
    encode_json_bytes,
    format_json,
    sanitize_for_json,
    to_schema,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlspec.adapters.oracledb import OracleAsyncConfig


class _SampleItem(FrozenBaseStruct, frozen=True, gc=False):
    """Sample frozen struct for serialization tests."""

    item_id: UUID
    created_at: datetime
    price: float
    label: str = "espresso"


class _SampleCamelItem(CamelizedFrozenStruct, frozen=True, gc=False):
    """Sample camelCase frozen struct for wire serialization tests."""

    store_name: str
    item_count: int = 1


class _StubAsyncConfig:
    """Stub async database config yielding a pooled mock driver."""

    __slots__ = ("_driver", "is_async")

    def __init__(self, driver: Any) -> None:
        self._driver = driver
        self.is_async = True

    @asynccontextmanager
    async def provide_session(self) -> AsyncGenerator[Any, None]:
        """Yield the configured mock driver."""
        yield self._driver


def test_frozen_structs_enforce_immutability_and_omit_gc_tracking() -> None:
    """Verify FrozenBaseStruct, CamelizedFrozenStruct, and Message omit GC tracking and forbid mutation."""
    now = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
    item = _SampleItem(item_id=uuid4(), created_at=now, price=4.75)
    camel = _SampleCamelItem(store_name="Bishop Arts", item_count=3)
    msg = Message(message="ready")

    assert gc.is_tracked(item) is False
    assert gc.is_tracked(camel) is False
    assert gc.is_tracked(msg) is False

    with pytest.raises(AttributeError):
        setattr(item, "price", 9.99)
    with pytest.raises(AttributeError):
        setattr(camel, "store_name", "Uptown")

    item_dict = item.to_dict()
    assert item_dict["price"] == 4.75
    camel_dict = camel.to_dict()
    assert camel_dict == {"storeName": "Bishop Arts", "itemCount": 3}


def test_serialization_helpers_round_trip_structs_decimals_and_numpy() -> None:
    """Verify encode_json_bytes, encode_json, format_json, decode_json, and to_schema round-trip typed payloads."""
    uid = uuid4()
    now = datetime(2026, 10, 24, 15, 30, tzinfo=UTC)
    payload = _SampleItem(item_id=uid, created_at=now, price=5.25, label="cortado")

    raw_bytes = encode_json_bytes(payload)
    assert isinstance(raw_bytes, bytes)

    raw_str = encode_json(payload)
    assert '"cortado"' in raw_str

    pretty = format_json({"cost": Decimal("4.50"), "vec": np.array([1.0, 2.0])}, indent=2)
    assert "\n  " in pretty

    decoded = decode_json(raw_bytes, target_type=_SampleItem)
    assert decoded == payload

    converted = to_schema(
        {"item_id": str(uid), "created_at": now.isoformat(), "price": 5.25, "label": "cortado"}, _SampleItem
    )
    assert converted == payload

    sanitized = sanitize_for_json({"qty": Decimal(3), "ratio": Decimal("1.25"), "arr": np.array([0.5, 1.5])})
    assert sanitized == {"qty": 3, "ratio": 1.25, "arr": [0.5, 1.5]}


def test_exceptions_classify_credentials_and_render_503_handler() -> None:
    """Verify ApplicationError, AIServiceUnconfigured, credential classifiers, and 503 handler."""
    assert ChatAIServiceUnconfigured is AIServiceUnconfigured
    assert issubclass(AIServiceUnconfigured, ServiceUnavailableException)
    assert issubclass(AIServiceUnconfigured, ApplicationError)

    exc = AIServiceUnconfigured("Configure VERTEX_AI_PROJECT_ID")
    assert exc.status_code == 503
    assert is_credential_error(exc) is True
    assert is_expected_service_unavailable(exc) is True

    adc_exc = DefaultCredentialsError.__new__(DefaultCredentialsError)
    Exception.__init__(adc_exc, "Your default credentials were not found.")
    assert is_credential_error(adc_exc) is True
    assert is_expected_service_unavailable(adc_exc) is True

    assert is_credential_error(KeyError("missing_column")) is False
    assert is_credential_error(KeyError("credentials")) is False
    assert is_credential_error(ValueError("invalid api key")) is False
    assert is_expected_service_unavailable(ValueError("bad_argument")) is False
    assert is_expected_service_unavailable(ValueError("invalid api key")) is False

    forbidden_client_err = genai_errors.ClientError(403, {"error": {"message": "403 Forbidden"}})
    assert is_credential_error(forbidden_client_err) is False
    assert is_expected_service_unavailable(forbidden_client_err) is True
    assert is_expected_service_unavailable(RuntimeError("403 Forbidden")) is False
    assert is_expected_service_unavailable(RuntimeError("SERVICE_DISABLED for Vertex AI")) is True

    response = ai_service_unconfigured_handler(MagicMock(), exc)
    assert response.status_code == 503
    assert response.content == {"detail": "Configure VERTEX_AI_PROJECT_ID", "status_code": 503}


def test_security_principal_dataclasses_are_slotted_and_resolver_frozen() -> None:
    """Verify API-key security helpers omit __dict__ and _ApiKeyResolver is frozen and GC-exempt."""
    slot = _ApiKeySlot()
    verifier = _ApiKeyVerifier(expected_key="token")
    resolver = _ApiKeyResolver()

    for obj in (slot, verifier, resolver):
        assert not hasattr(obj, "__dict__")

    assert gc.is_tracked(resolver) is False
    with pytest.raises(AttributeError):
        setattr(resolver, "extra", "mutated")


@pytest.mark.anyio
async def test_oracle_loader_service_supports_driver_and_config_modes() -> None:
    """Verify default_sql_loader and OracleLoaderService work with request drivers and app-scoped configs."""
    loader = default_sql_loader()
    assert default_sql_loader() is loader
    sql_stmt = loader.get_sql("vector-search-products")
    assert "VECTOR_DISTANCE" in str(sql_stmt)

    mock_driver = MagicMock()
    mock_driver.execute_many = AsyncMock(return_value="batch-ok")
    mock_driver.commit = AsyncMock()

    req_service = OracleLoaderService(mock_driver)
    assert isinstance(req_service, OracleAsyncService)
    assert not hasattr(req_service, "__dict__")
    assert "VECTOR_DISTANCE" in str(req_service.get_sql("vector-search-products"))

    result = await req_service.execute_many("INSERT INTO t VALUES (:a)", [{"a": 1}], auto_commit=True)
    assert result == "batch-ok"
    mock_driver.execute_many.assert_awaited_once()
    mock_driver.commit.assert_awaited_once()

    pooled_driver = MagicMock()
    pooled_driver.execute_many = AsyncMock(return_value="pooled-ok")
    pooled_driver.commit = AsyncMock()

    stub_config = cast("OracleAsyncConfig", _StubAsyncConfig(pooled_driver))
    app_service = OracleLoaderService.from_config(stub_config)

    async with app_service.provide_app_session() as session:
        assert session is pooled_driver

    pooled_result = await app_service.execute_many("INSERT INTO t VALUES (:a)", [{"a": 2}], auto_commit=True)
    assert pooled_result == "pooled-ok"
    pooled_driver.execute_many.assert_awaited_once()
    pooled_driver.commit.assert_awaited_once()
