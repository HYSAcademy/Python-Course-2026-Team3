from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logger import logger
from app.services.validation_service import ValidationError 

class NonRetryableError(Exception):
    """
    Custom exception for Celery tasks. 
    Raised when a task fails due to an unrecoverable error 
    """
    pass

async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Global handler for our custom file validation errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc)},
    )


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches all unexpected errors (500) to prevent exposing stack traces to the client."""
    logger.exception(f"Unhandled exception on {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(Exception, internal_error_handler)