"""Job repository for asynchronous API tasks."""
from __future__ import annotations

import logging
from typing import Any

from f1_pipeline.db.supabase_client import get_supabase_client
from supabase import Client

logger = logging.getLogger(__name__)


class JobRepository:
    """Repository for managing pipeline background jobs in Supabase."""

    def __init__(self, client: Client | None = None):
        self.client = client or get_supabase_client()

    def create_job(self, job_type: str, payload: dict | None = None) -> str:
        """Create a new job and return its UUID."""
        data = {
            "job_type": job_type,
            "status": "queued",
            "progress": 0.0,
            "payload": payload or {}
        }
        response = self.client.table("pipeline_jobs").insert(data).execute()
        return response.data[0]["id"]

    def update_job_status(self, job_id: str, status: str, progress: float | None = None) -> None:
        """Update job status and optionally progress."""
        data = {"status": status}
        if progress is not None:
            data["progress"] = progress
            
        if status == "running":
            data["started_at"] = "now()"
        elif status in ("completed", "failed", "cancelled"):
            data["completed_at"] = "now()"
            
        self.client.table("pipeline_jobs").update(data).eq("id", job_id).execute()

    def update_job_result(self, job_id: str, result_reference: str) -> None:
        """Store the successful output reference for a job."""
        data = {
            "status": "completed",
            "result_reference": result_reference,
            "progress": 1.0,
            "completed_at": "now()"
        }
        self.client.table("pipeline_jobs").update(data).eq("id", job_id).execute()

    def update_job_error(self, job_id: str, error_message: str) -> None:
        """Mark a job as failed with an error message."""
        data = {
            "status": "failed",
            "error_message": error_message,
            "completed_at": "now()"
        }
        self.client.table("pipeline_jobs").update(data).eq("id", job_id).execute()

    def get_job(self, job_id: str) -> dict | None:
        """Retrieve job status and metadata."""
        response = self.client.table("pipeline_jobs").select("*").eq("id", job_id).execute()
        if response.data:
            return response.data[0]
        return None
