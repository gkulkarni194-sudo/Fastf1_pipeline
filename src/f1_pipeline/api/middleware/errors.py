"""Error handlers."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def add_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        req_id = getattr(request.state, "request_id", "unknown")
        
        # Format standardized error
        error_payload = {
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail),
                "request_id": req_id
            }
        }
        return JSONResponse(status_code=exc.status_code, content=error_payload)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        req_id = getattr(request.state, "request_id", "unknown")
        logger.warning(f"Validation error [Req: {req_id}]: {exc.errors()}")
        
        error_payload = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request payload or parameters are invalid.",
                "details": exc.errors(),
                "request_id": req_id
            }
        }
        return JSONResponse(status_code=422, content=error_payload)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        req_id = getattr(request.state, "request_id", "unknown")
        logger.error(f"Unhandled exception [Req: {req_id}]: {exc}", exc_info=True)
        
        error_payload = {
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred in the pipeline.",
                "request_id": req_id
            }
        }
        return JSONResponse(status_code=500, content=error_payload)
