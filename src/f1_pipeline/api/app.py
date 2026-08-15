"""Main FastAPI application."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from f1_pipeline.api.middleware.cors import setup_cors
from f1_pipeline.api.middleware.errors import add_exception_handlers
# Ensure routes are imported and included after they are created
# from f1_pipeline.api.routes import router as api_router
from f1_pipeline.core.config import load_config
from f1_pipeline.core.logging import configure_logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    config = load_config()
    configure_logging(level=config.log_level, console=True)
    logger.info("F1 Strategy API Starting up...")
    
    # Initialize global job manager here if we need an active worker loop,
    # but since we'll use concurrent.futures via the manager, we're okay.
    
    yield
    # Shutdown
    logger.info("F1 Strategy API Shutting down...")


def create_app() -> FastAPI:
    """Factory to create the FastAPI application."""
    app = FastAPI(
        title="F1 Strategy Simulation API",
        description="Layer 6 API exposing the F1 Strategy Pipeline (Layers 0-5).",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # Setup Middleware
    setup_cors(app)
    add_exception_handlers(app)

    # Include Routes
    from f1_pipeline.api.routes import router as api_router
    app.include_router(api_router, prefix="/api/v1")

    @app.middleware("http")
    async def add_request_id_header(request: Request, call_next):
        import uuid
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        # Add to request state for access in routes
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    return app

app = create_app()
