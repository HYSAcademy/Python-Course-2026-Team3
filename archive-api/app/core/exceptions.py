from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logger import logger


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


async def unsupported_media_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=415,
        content={"detail": "Unsupported file type. Only .zip and .tar.gz are allowed."},
    )


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled exception on {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(Exception, internal_error_handler)
    app.add_exception_handler(UnicodeDecodeError, unsupported_media_handler)
