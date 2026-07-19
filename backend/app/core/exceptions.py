"""
Global exception handlers.

WHY THIS EXISTS:
Without centralized exception handling, every endpoint would need its own
try/except blocks, leading to:
  - Inconsistent error response formats
  - Duplicated error handling logic
  - Leaked stack traces in production responses

These handlers intercept exceptions at the framework level and return a
consistent JSON structure for every error type.

WHY THIS RESPONSE FORMAT:
Every error response follows the same shape:
  {
    "error": "<error_category>",
    "detail": "<human_readable_or_structured_detail>"
  }

This lets frontend code check a single "error" field to determine the error
category, and use "detail" for display or debugging. Simpler than RFC 7807
Problem Details, which adds unnecessary complexity at this scale.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.exceptions")


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handle Pydantic validation errors from request parsing.

    Returns 422 with structured validation error details. These errors occur
    when request body, query params, or path params fail Pydantic validation.
    The detail field contains a cleaned error list so the client knows
    exactly which fields are invalid and why.

    WHY WE CLEAN THE ERRORS:
    Pydantic v2's exc.errors() can include non-JSON-serializable objects in
    the 'ctx' field (e.g., raw ValueError instances from model_validators).
    We extract only the fields that are always serializable: type, loc, msg.
    """
    errors = [
        {
            "type": err.get("type", "value_error"),
            "loc": err.get("loc", []),
            "msg": err.get("msg", "Validation error"),
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "detail": errors,
        },
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """
    Handle intentional HTTP exceptions raised by endpoint code.

    These are expected errors — a resource not found, unauthorized access,
    etc. We wrap them in our standard format but preserve the status code
    and detail message set by the raising code.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "detail": exc.detail,
        },
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Catch-all for unexpected exceptions.

    Logs the full traceback for debugging but returns a generic message
    to the client. Never expose internal error details in responses —
    they can leak implementation details useful to attackers.
    """
    logger.error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "detail": "An unexpected error occurred.",
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers on the FastAPI application.

    Called once during app initialization. Separating registration into a
    function keeps main.py clean and makes handlers easy to test.
    """
    app.add_exception_handler(
        RequestValidationError, validation_exception_handler
    )
    app.add_exception_handler(
        StarletteHTTPException, http_exception_handler
    )
    app.add_exception_handler(Exception, unhandled_exception_handler)
