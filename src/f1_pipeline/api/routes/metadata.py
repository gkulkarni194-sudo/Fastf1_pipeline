"""Metadata endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends

from f1_pipeline.api.services.metadata_service import MetadataService

router = APIRouter()


def get_metadata_service() -> MetadataService:
    return MetadataService()


MetadataServiceDep = Annotated[MetadataService, Depends(get_metadata_service)]


@router.get("/seasons", response_model=list[int])
async def get_seasons(service: MetadataServiceDep):
    """Retrieve a list of available F1 seasons in the pipeline."""
    return service.get_seasons()


@router.get("/events", response_model=list[str])
async def get_events(season: int, service: MetadataServiceDep):
    """Retrieve available events for a given season."""
    return service.get_events(season)


@router.get("/sessions", response_model=list[str])
async def get_sessions(season: int, event: str, service: MetadataServiceDep):
    """Retrieve available sessions for a given event."""
    return service.get_sessions(season, event)


@router.get("/drivers", response_model=list[str])
async def get_drivers(season: int, event: str, service: MetadataServiceDep):
    """Retrieve available drivers for a given event."""
    return service.get_drivers(season, event)
