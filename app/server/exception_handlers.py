"""Custom exception handlers for JSON APIs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from google.api_core import exceptions as google_exceptions
from litestar.exceptions import HTTPException, ValidationException
from litestar.response import Response
from litestar.status_codes import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

if TYPE_CHECKING:
    from litestar import Request


def handle_validation_exception(request: Request, exc: ValidationException) -> Response:
    """Handle validation exceptions with JSON responses."""
    return Response(
        content={
            "error": "Validation Error",
            "detail": getattr(exc, "detail", str(exc)),
        },
        status_code=HTTP_400_BAD_REQUEST,
    )


def handle_google_api_exception(request: Request, exc: google_exceptions.GoogleAPIError) -> Response:
    """Handle Google API exceptions."""
    request.logger.error("Google API Error", exc_info=exc)
    return Response(
        content={
            "error": "Google API Error",
            "detail": "An error occurred while communicating with Google services.",
        },
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    )


def handle_generic_exception(request: Request, exc: Exception) -> Response:
    """Handle any unexpected exceptions."""
    request.logger.error("Unexpected error", exc_info=exc)
    return Response(
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred. Please try again later.",
        },
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    )


def handle_value_error(request: Request, exc: ValueError) -> Response:
    """Handle ValueError exceptions (often from Vertex AI)."""
    request.logger.error("ValueError occurred", exc_info=exc, error_message=str(exc))
    return Response(
        content={
            "error": "Value Error",
            "detail": str(exc),
        },
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    )

def handle_http_exception(request: Request, exc: HTTPException) -> Response:
    return Response(
        content={
            "error": "HTTP Exception",
            "detail": exc.detail,
        },
        status_code=exc.status_code
    )

# Exception handler mapping for registration
exception_handlers = {
    ValidationException: handle_validation_exception,
    google_exceptions.GoogleAPIError: handle_google_api_exception,
    ValueError: handle_value_error,
}
