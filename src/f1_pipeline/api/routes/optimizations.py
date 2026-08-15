"""Optimization endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends

from f1_pipeline.api.dependencies import ConfigDep, JobManagerDep, PathsDep
from f1_pipeline.api.schemas.optimizations import OptimizationCreateRequest, OptimizationResultResponse
from f1_pipeline.api.schemas.simulations import JobQueuedResponse, JobStatusResponse
from f1_pipeline.api.services.strategy_service import StrategyService
from f1_pipeline.db.repositories.jobs import JobRepository

router = APIRouter()


def get_strategy_service(
    config: ConfigDep,
    paths: PathsDep,
    job_manager: JobManagerDep
) -> StrategyService:
    return StrategyService(config, paths, job_manager)


StrategyServiceDep = Annotated[StrategyService, Depends(get_strategy_service)]


@router.post("", response_model=JobQueuedResponse)
async def create_optimization(request: OptimizationCreateRequest, service: StrategyServiceDep):
    """Submit a Layer 5 strategy optimization request as a background job."""
    return service.create_optimization(request)


@router.get("/{optimization_id}", response_model=JobStatusResponse)
async def get_optimization_status(optimization_id: str):
    """Check the status of an optimization background job."""
    repo = JobRepository()
    job = repo.get_job(optimization_id)
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Optimization job not found")
        
    return JobStatusResponse(
        job_id=job["id"],
        status=job["status"],
        progress=job["progress"],
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
        error_message=job.get("error_message")
    )


@router.get("/{optimization_id}/results", response_model=OptimizationResultResponse)
async def get_optimization_results(optimization_id: str):
    """Fetch the summarized results of a completed optimization."""
    # Stub implementation - would normally use StrategyAssetsRepository to fetch best
    return OptimizationResultResponse(
        optimization_id=optimization_id,
        best_strategy=None,
        best_score=0.0,
        best_race_time=5400.0,
        strategies_evaluated=1000,
        strategies_valid=800,
        algorithm="exhaustive",
        objective="race_time"
    )
