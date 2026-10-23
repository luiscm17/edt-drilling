"""Stable, sanitized public error translation; infrastructure errors propagate."""

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from openoil.application.hydraulics import (
    InvalidCaseId,
    MissingCase,
    UnsupportedInput,
)


def register_error_handlers(app):
    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # Do not echo untrusted input, nonfinite floats, or framework-specific errors.
        detail = (
            "invalid case id"
            if request.url.path.startswith("/api/v1/cases/")
            else "invalid request body"
        )
        return JSONResponse(status_code=422, content={"detail": detail})

    @app.exception_handler(UnsupportedInput)
    @app.exception_handler(InvalidCaseId)
    async def invalid_case(request, error):
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.exception_handler(MissingCase)
    async def missing_case(request, error):
        return JSONResponse(status_code=404, content={"detail": str(error)})
