from litestar.exceptions import HTTPException


class AppServiceException(HTTPException):
    """Base exception for the application."""
