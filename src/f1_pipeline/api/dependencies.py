"""FastAPI Dependencies."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from f1_pipeline.api.jobs.manager import JobManager
from f1_pipeline.core.config import RuntimeConfig, load_config
from f1_pipeline.core.paths import ProjectPaths


def get_config() -> RuntimeConfig:
    return load_config()


def get_paths() -> ProjectPaths:
    return ProjectPaths.from_root()


def get_job_manager() -> JobManager:
    """Return a singleton instance of the Job Manager.
    
    In a full production setup with Celery, this might return a Celery task submitter.
    Here, it returns our threadpool-backed background job manager.
    """
    return JobManager.get_instance()


ConfigDep = Annotated[RuntimeConfig, Depends(get_config)]
PathsDep = Annotated[ProjectPaths, Depends(get_paths)]
JobManagerDep = Annotated[JobManager, Depends(get_job_manager)]
