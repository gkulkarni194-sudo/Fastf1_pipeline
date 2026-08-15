"""Experiment tracing endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends

from f1_pipeline.api.services.experiment_service import ExperimentService

router = APIRouter()


def get_experiment_service() -> ExperimentService:
    return ExperimentService()


ExperimentServiceDep = Annotated[ExperimentService, Depends(get_experiment_service)]


@router.get("/{experiment_id}", response_model=dict)
async def get_experiment_lineage(experiment_id: str, service: ExperimentServiceDep):
    """Retrieve full pipeline lineage for an optimization run."""
    return service.get_experiment_lineage(experiment_id)
