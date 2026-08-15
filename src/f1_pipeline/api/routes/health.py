"""Health endpoints."""
from datetime import datetime, timezone

from fastapi import APIRouter

from f1_pipeline.api.schemas.common import HealthDependenciesResponse, HealthResponse

router = APIRouter()


@router.get("", response_model=HealthResponse)
async def health_check():
    """Basic health check to verify the API is running."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        environment="production", # Read from config in real app
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.get("/dependencies", response_model=HealthDependenciesResponse)
async def health_dependencies():
    """Detailed health check for backend dependencies."""
    # Note: These would actively ping the database and storage
    return HealthDependenciesResponse(
        database="healthy",
        storage="healthy",
        pipeline="healthy"
    )
