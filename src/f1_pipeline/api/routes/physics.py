"""Physics endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends

from f1_pipeline.api.dependencies import PathsDep
from f1_pipeline.api.schemas.physics import PhysicsParametersResponse
from f1_pipeline.api.services.physics_service import PhysicsService

router = APIRouter()


def get_physics_service(paths: PathsDep) -> PhysicsService:
    return PhysicsService(paths)


PhysicsServiceDep = Annotated[PhysicsService, Depends(get_physics_service)]


@router.get("/runs/{physics_run_id}", response_model=dict)
async def get_physics_run(physics_run_id: str, service: PhysicsServiceDep):
    """Retrieve metadata about a specific Layer 3 physics run."""
    return service.get_run_metadata(physics_run_id)


@router.get("/parameters", response_model=PhysicsParametersResponse)
async def get_physics_parameters(
    season: int,
    event: str,
    session: str,
    driver: str,
    service: PhysicsServiceDep
):
    """Retrieve derived physical parameters for a specific driver-session."""
    return service.get_parameters(season, event, session, driver)
