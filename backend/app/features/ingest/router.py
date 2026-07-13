from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from app.core.database import get_session_factory
from app.features.ingest.service import ingest_service

router = APIRouter()

class IngestTriggerRequest(BaseModel):
    urls: List[str] = Field(..., min_items=1, description="List of seed URLs to collect data from")
    collector: str = Field("http_collector", description="Name of the collection plugin to use")
    retries: int = Field(3, ge=0, le=5, description="Number of retries for transient connection errors")

class IngestTriggerResponse(BaseModel):
    job_id: str = Field(..., description="Unique UUID identifier for the triggered job")
    status: str = Field(..., description="Initial status of the triggered job")

class IngestJobStatusResponse(BaseModel):
    id: str
    collector: str
    status: str
    urls: List[str]
    collected_count: int
    error: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]

@router.post("/trigger", response_model=IngestTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_ingest(
    payload: IngestTriggerRequest,
    session_factory = Depends(get_session_factory)
) -> Any:
    """
    Trigger a collection job asynchronously in the background.
    """
    try:
        # Verify that the collector is registered before starting the background task
        ingest_service.get_collector(payload.collector)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    job_id = ingest_service.trigger_job(
        collector_name=payload.collector,
        session_factory=session_factory,
        urls=payload.urls,
        retries=payload.retries
    )
    
    return {"job_id": job_id, "status": "pending"}

@router.get("/status/{job_id}", response_model=IngestJobStatusResponse)
async def get_job_status(job_id: str) -> Any:
    """
    Retrieve the status and results of a specific collection job.
    """
    status_info = ingest_service.get_job_status(job_id)
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingest job '{job_id}' not found."
        )
    return status_info

@router.get("/status", response_model=List[IngestJobStatusResponse])
async def list_jobs() -> Any:
    """
    Retrieve statuses of all collection jobs.
    """
    return list(ingest_service.jobs.values())
