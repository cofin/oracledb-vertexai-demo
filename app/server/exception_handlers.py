"""Custom exception handlers for HTMX integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from google.api_core import exceptions as google_exceptions
from litestar.exceptions import HTTPException, ValidationException
from litestar.plugins.htmx import HTMXTemplate
from litestar.status_codes import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

if TYPE_CHECKING:
    from litestar import Request
    from litestar.response import Response


class HTMXValidationException(ValidationException):
    """Validation exception that triggers HTMX events."""

    def __init__(self, detail: str, field: str | None = None) -> None:
        super().__init__(detail=detail)
        self.field = field


class HTMXAPIException(HTTPException):
    """API exception that triggers HTMX events."""

    def __init__(
        self,
        detail: str = "Service error occurred",
        status_code: int = HTTP_500_INTERNAL_SERVER_ERROR,
        retry: bool = True,
    ) -> None:
        super().__init__(detail=detail, status_code=status_code)
        self.retry = retry


class VectorDemoException(HTTPException):
    """Exception specific to vector demo operations."""

    def __init__(
        self,
        detail: str = "Vector operation failed",
        status_code: int = HTTP_500_INTERNAL_SERVER_ERROR,
        operation: str = "vector_search",
        error_type: str = "unknown",
    ) -> None:
        super().__init__(detail=detail, status_code=status_code)
        self.operation = operation
        self.error_type = error_type


def handle_validation_exception(request: Request, exc: ValidationException) -> Response:
    """Handle validation exceptions with HTMX events."""
    # Generate CSP nonce if needed
    csp_nonce = getattr(request.app.state, "csp_nonce_generator", lambda: "")()

    # Determine if this is a custom HTMX validation exception
    field = getattr(exc, "field", "message") if isinstance(exc, HTMXValidationException) else "message"

    # Return HTMX template with validation error event
    return HTMXTemplate(
        template_name="partials/chat_response.html",
        context={
            "user_message": "Invalid input",
            "ai_response": str(exc.detail) if hasattr(exc, "detail") else str(exc),
            "query_id": "",
            "csp_nonce": csp_nonce,
        },
        status_code=HTTP_400_BAD_REQUEST,
        trigger_event="validation:error",
        params={"error": str(exc), "field": field},
        after="settle",
    )


def handle_google_api_exception(request: Request, exc: google_exceptions.GoogleAPIError) -> Response:
    """Handle Google API exceptions with HTMX events."""
    # Generate CSP nonce
    csp_nonce = getattr(request.app.state, "csp_nonce_generator", lambda: "")()

    # Get the message from the request body if available
    user_message = "Your request"

    return HTMXTemplate(
        template_name="partials/chat_response.html",
        context={
            "user_message": user_message,
            "ai_response": "Sorry, I encountered an error processing your request. Please try again.",
            "query_id": "",
            "csp_nonce": csp_nonce,
        },
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        # Trigger an API error event for client-side handling
        trigger_event="api:error",
        params={"type": "google_api_error", "retry": True},
        after="receive",
    )


def handle_htmx_api_exception(request: Request, exc: HTMXAPIException) -> Response:
    """Handle custom HTMX API exceptions."""
    # Generate CSP nonce
    csp_nonce = getattr(request.app.state, "csp_nonce_generator", lambda: "")()

    # Get the message from the request body if available
    user_message = "Your request"

    return HTMXTemplate(
        template_name="partials/chat_response.html",
        context={
            "user_message": user_message,
            "ai_response": exc.detail,
            "query_id": "",
            "csp_nonce": csp_nonce,
        },
        status_code=exc.status_code,
        # Trigger an API error event for client-side handling
        trigger_event="api:error",
        params={"type": "service_error", "retry": exc.retry},
        after="receive",
    )


def handle_generic_exception(request: Request, exc: Exception) -> Response:
    """Handle any unexpected exceptions."""
    # Log the exception for debugging
    request.logger.error("Unexpected error", exc_info=exc)

    # Generate CSP nonce
    csp_nonce = getattr(request.app.state, "csp_nonce_generator", lambda: "")()

    return HTMXTemplate(
        template_name="partials/chat_response.html",
        context={
            "user_message": "Your request",
            "ai_response": "An unexpected error occurred. Please try again later.",
            "query_id": "",
            "csp_nonce": csp_nonce,
        },
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        # Trigger a generic error event
        trigger_event="api:error",
        params={"type": "unexpected_error", "retry": False},
        after="receive",
    )


def handle_value_error(request: Request, exc: ValueError) -> Response:
    """Handle ValueError exceptions (often from Vertex AI)."""

    csp_nonce = getattr(request.app.state, "csp_nonce_generator", lambda: "")()

    user_message = "Your request"

    return HTMXTemplate(
        template_name="partials/chat_response.html",
        context={
            "user_message": user_message,
            "ai_response": "Sorry, I encountered an error processing your request. Please try again.",
            "query_id": "",
            "csp_nonce": csp_nonce,
        },
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        # Trigger an API error event for client-side handling
        trigger_event="api:error",
        params={"type": "value_error", "retry": True},
        after="receive",
    )


def handle_vector_demo_exception(request: Request, exc: VectorDemoException) -> Response:
    """Handle vector demo specific exceptions with tailored responses."""

    csp_nonce = getattr(request.app.state, "csp_nonce_generator", lambda: "")()

    # Get the query from the request
    query = "Your query"

    # Determine error message based on operation
    error_messages = {
        "embedding": "Failed to generate embedding for your query. Please try a different search term.",
        "vector_search": "Vector search failed. The database might be temporarily unavailable.",
        "metrics": "Failed to record search metrics, but your search was processed.",
    }

    error_message = error_messages.get(exc.operation, exc.detail)

    return HTMXTemplate(
        template_name="partials/_vector_results.html",
        context={
            "results": [],
            "search_time": "N/A",
            "embedding_time": "N/A",
            "oracle_time": "N/A",
            "error": error_message,
            "query": query,
            "csp_nonce": csp_nonce,
        },
        status_code=exc.status_code,
        # Trigger vector-specific error event
        trigger_event="vector:error",
        params={
            "operation": exc.operation,
            "error_type": exc.error_type,
            "retry": exc.error_type != "validation",
        },
        after="settle",
    )


# Exception handler mapping for registration
exception_handlers = {
    ValidationException: handle_validation_exception,
    HTMXValidationException: handle_validation_exception,
    google_exceptions.GoogleAPIError: handle_google_api_exception,
    HTMXAPIException: handle_htmx_api_exception,
    VectorDemoException: handle_vector_demo_exception,
    ValueError: handle_value_error,
}
