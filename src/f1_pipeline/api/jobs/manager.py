"""Background Job Manager."""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from f1_pipeline.db.repositories.jobs import JobRepository

logger = logging.getLogger(__name__)


class JobManager:
    """Manages background execution of long-running pipeline tasks.
    
    In a real production environment, this would be an adapter for Celery or RQ.
    Here, it uses asyncio and a ThreadPoolExecutor, paired with the JobRepository
    so status is persisted to Supabase.
    """
    _instance = None
    
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.repo = JobRepository()
        
    @classmethod
    def get_instance(cls) -> JobManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
        
    def submit(self, job_type: str, payload: dict, func: Callable, *args: Any, **kwargs: Any) -> str:
        """Submit a job to be run in the background.
        
        Args:
            job_type: String identifier (e.g., 'simulation', 'optimization').
            payload: JSON metadata to save with the job.
            func: The blocking pipeline function to execute.
            args, kwargs: Arguments for the function.
            
        Returns:
            job_id (str)
        """
        # Create record in DB
        job_id = self.repo.create_job(job_type, payload)
        
        # We need a reference to the active event loop to spawn the task
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._run_job(job_id, func, *args, **kwargs))
        except RuntimeError:
            logger.error("No running event loop to schedule background job.")
            self.repo.update_job_error(job_id, "No running event loop to schedule job.")
            
        return job_id
        
    async def _run_job(self, job_id: str, func: Callable, *args: Any, **kwargs: Any) -> None:
        """Run the job in the threadpool and update status."""
        logger.info(f"Starting job {job_id} in background thread...")
        
        # Mark running
        try:
            self.repo.update_job_status(job_id, "running", progress=0.0)
        except Exception as e:
            logger.error(f"Failed to mark job {job_id} running: {e}")
            return
            
        loop = asyncio.get_running_loop()
        try:
            # Execute blocking function
            result_reference = await loop.run_in_executor(
                self.executor,
                lambda: func(*args, **kwargs)
            )
            # Mark completed with the result ID (e.g., simulation_id or optimization_id)
            self.repo.update_job_result(job_id, result_reference)
            logger.info(f"Job {job_id} completed successfully.")
            
        except Exception as exc:
            logger.error(f"Job {job_id} failed: {exc}", exc_info=True)
            try:
                self.repo.update_job_error(job_id, str(exc))
            except Exception as inner_exc:
                logger.error(f"Failed to update job {job_id} error status: {inner_exc}")
