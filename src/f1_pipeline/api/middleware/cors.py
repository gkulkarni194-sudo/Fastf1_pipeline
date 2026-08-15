"""CORS configuration."""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app: FastAPI) -> None:
    # Use environment variable to set CORS origins
    # Default to localhost for development
    origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")
    
    origins = [orig.strip() for orig in origins_str.split(",") if orig.strip()]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
