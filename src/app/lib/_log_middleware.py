# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""ASGI logging middleware and before-send extraction helpers."""

from __future__ import annotations

import logging
import re
import sys
from inspect import isawaitable
from typing import TYPE_CHECKING, Any, Literal

import structlog
from litestar.data_extractors import ConnectionDataExtractor, ResponseDataExtractor
from litestar.enums import ScopeType
from litestar.exceptions import HTTPException, WebSocketException
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from litestar.utils.empty import value_or_default
from litestar.utils.scope.state import ScopeState
from structlog.contextvars import bind_contextvars

from app.lib._log_security import apply_security_headers
from app.lib.settings import get_settings

if TYPE_CHECKING:
    from litestar.connection import Request
    from litestar.types.asgi_types import ASGIApp, Message, Receive, Scope, Send

LOGGER = structlog.getLogger()

HTTP_RESPONSE_START: Literal["http.response.start"] = "http.response.start"
HTTP_RESPONSE_BODY: Literal["http.response.body"] = "http.response.body"
REQUEST_BODY_FIELD: Literal["body"] = "body"

settings = get_settings()


# This is so that it shows up properly in the Litestar UI. Instead of reading
# `middleware_factory`, we use a name that makes sense.
def StructlogMiddleware(app: ASGIApp) -> ASGIApp:  # noqa: N802
    """Middleware to ensure that every request has a clean structlog context."""

    async def middleware(scope: Scope, receive: Receive, send: Send) -> None:
        """Clean up structlog contextvars."""
        structlog.contextvars.clear_contextvars()
        await app(scope, receive, send)

    return middleware


def after_exception_hook_handler(exc: Exception, _scope: Scope) -> None:
    """Bind exception info into structlog context vars for server errors."""
    if isinstance(exc, HTTPException) and exc.status_code < HTTP_500_INTERNAL_SERVER_ERROR:
        return
    if isinstance(exc, WebSocketException):
        return
    bind_contextvars(exc_info=sys.exc_info())


class BeforeSendHandler:
    """Extraction of request and response data from connection scope."""

    __slots__ = (
        "do_log_request",
        "do_log_response",
        "exclude_paths",
        "include_compressed_body",
        "logger",
        "request_extractor",
        "response_extractor",
    )

    def __init__(self) -> None:
        """Configure the handler."""
        self.exclude_paths = re.compile(settings.log.EXCLUDE_PATHS)
        self.do_log_request = bool(settings.log.REQUEST_FIELDS)
        self.do_log_response = bool(settings.log.RESPONSE_FIELDS)
        self.include_compressed_body = settings.log.INCLUDE_COMPRESSED_BODY
        self.request_extractor = ConnectionDataExtractor(
            extract_body="body" in settings.log.REQUEST_FIELDS,
            extract_client="client" in settings.log.REQUEST_FIELDS,
            extract_content_type="content_type" in settings.log.REQUEST_FIELDS,
            extract_cookies="cookies" in settings.log.REQUEST_FIELDS,
            extract_headers="headers" in settings.log.REQUEST_FIELDS,
            extract_method="method" in settings.log.REQUEST_FIELDS,
            extract_path="path" in settings.log.REQUEST_FIELDS,
            extract_path_params="path_params" in settings.log.REQUEST_FIELDS,
            extract_query="query" in settings.log.REQUEST_FIELDS,
            extract_scheme="scheme" in settings.log.REQUEST_FIELDS,
            obfuscate_cookies=settings.log.OBFUSCATE_COOKIES,
            obfuscate_headers=settings.log.OBFUSCATE_HEADERS,
            parse_body=False,
            parse_query=False,
        )
        self.response_extractor = ResponseDataExtractor(
            extract_body="body" in settings.log.RESPONSE_FIELDS,
            extract_headers="headers" in settings.log.RESPONSE_FIELDS,
            extract_status_code="status_code" in settings.log.RESPONSE_FIELDS,
            obfuscate_cookies=settings.log.OBFUSCATE_COOKIES,
            obfuscate_headers=settings.log.OBFUSCATE_HEADERS,
        )

    async def __call__(self, message: Message, scope: Scope) -> None:
        """Receive ASGI response messages and log per configuration."""
        if message["type"] == HTTP_RESPONSE_START:
            apply_security_headers(message)

        if scope["type"] == ScopeType.HTTP and self.exclude_paths.findall(scope["path"]):
            return

        if message["type"] == HTTP_RESPONSE_START:
            scope["state"]["log_level"] = (
                logging.ERROR if message["status"] >= HTTP_500_INTERNAL_SERVER_ERROR else logging.INFO
            )
            scope["state"][HTTP_RESPONSE_START] = message
        elif message["type"] == HTTP_RESPONSE_BODY and message["more_body"] is False:
            scope["state"][HTTP_RESPONSE_BODY] = message
            try:
                if self.do_log_request:
                    await self.log_request(scope)
                if self.do_log_response:
                    await self.log_response(scope)
                await LOGGER.alog(
                    scope["state"]["log_level"],
                    f"{scope['method'] if scope['type'] == ScopeType.HTTP else scope['type']} {scope['path']}",
                )
            except Exception as e:  # noqa: BLE001
                structlog.contextvars.clear_contextvars()
                await LOGGER.aerror("Error in logging before-send handler!", reason=f"{type(e).__name__}{e.args}")

    async def log_request(self, scope: Scope) -> None:
        """Handle extracting the request data and logging the message."""
        extracted_data = await self.extract_request_data(request=scope["app"].request_class(scope))  # pyright: ignore
        structlog.contextvars.bind_contextvars(**extracted_data)

    async def log_response(self, scope: Scope) -> None:
        """Handle extracting the response data and logging the message."""
        extracted_data = self.extract_response_data(scope=scope)
        structlog.contextvars.bind_contextvars(**extracted_data)

    async def extract_request_data(self, request: Request[Any, Any, Any]) -> dict[str, Any]:
        """Create a dictionary of values for the log."""
        data: dict[str, Any] = {}
        extracted_data = self.request_extractor(connection=request)
        missing = object()
        for key in settings.log.REQUEST_FIELDS:
            value = extracted_data.get(key, missing)
            if value is missing:  # pragma: no cover
                continue
            if isawaitable(value):
                try:
                    value = await value
                except RuntimeError:
                    if key != REQUEST_BODY_FIELD:
                        raise  # pragma: no cover
                    value = None
            data[key] = value
        return data

    def extract_response_data(self, scope: Scope) -> dict[str, Any]:
        """Extract data from the response."""
        data: dict[str, Any] = {}
        extracted_data = self.response_extractor(
            messages=(scope["state"][HTTP_RESPONSE_START], scope["state"][HTTP_RESPONSE_BODY]),
        )
        missing = object()
        connection_state = ScopeState.from_scope(scope)
        response_body_compressed = value_or_default(connection_state.response_compressed, False)
        for key in settings.log.RESPONSE_FIELDS:
            value = extracted_data.get(key, missing)
            if key == "body" and response_body_compressed and not self.include_compressed_body:
                continue
            if value is missing:  # pragma: no cover
                continue
            data[key] = value
        return data
