"""Simulation endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends

from f1_pipeline.api.dependencies import ConfigDep, JobManagerDep, PathsDep
from f1_pipeline.api.schemas.simulations import (
    JobQueuedResponse,
    JobStatusResponse,
    SimulationCreateRequest,
    SimulationResultResponse
)
from f1_pipeline.api.services.simulation_service import SimulationService
from f1_pipeline.db.repositories.jobs import JobRepository

router = APIRouter()


def get_simulation_service(
    config: ConfigDep,
    paths: PathsDep,
    job_manager: JobManagerDep
) -> SimulationService:
    return SimulationService(config, paths, job_manager)


SimulationServiceDep = Annotated[SimulationService, Depends(get_simulation_service)]


@router.post("", response_model=JobQueuedResponse)
async def create_simulation(request: SimulationCreateRequest, service: SimulationServiceDep):
    """Submit a Layer 4 simulation request as a background job."""
    return service.create_simulation(request)


@router.get("/{simulation_id}", response_model=JobStatusResponse)
async def get_simulation_status(simulation_id: str):
    """Check the status of a simulation background job."""
    repo = JobRepository()
    job = repo.get_job(simulation_id)
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Simulation job not found")
        
    return JobStatusResponse(
        job_id=job["id"],
        status=job["status"],
        progress=job["progress"],
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
        error_message=job.get("error_message")
    )


@router.get("/{simulation_id}/results", response_model=SimulationResultResponse)
async def get_simulation_results(simulation_id: str, service: SimulationServiceDep):
    """Fetch the summarized results of a completed simulation."""
    return service.get_simulation_result(simulation_id)
