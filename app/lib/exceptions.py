from litestar.exceptions import HTTPException


class AppServiceException(HTTPException):
    """Base exception for the application."""


class RepositoryError(AppServiceException):
    """Exception raised for repository operations."""

    def __init__(self, detail: str = "Repository operation failed", status_code: int = 500) -> None:
        super().__init__(detail=detail, status_code=status_code)


class DatabaseConnectionError(RepositoryError):
    """Exception raised when database connection fails."""

    def __init__(self, detail: str = "Database connection failed") -> None:
        super().__init__(detail=detail, status_code=503)


# Backward compatibility alias
ApplicationError = AppServiceException
