from typing import Any
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.dedup.service import dedup_service

router = APIRouter()

class DedupRunRequest(BaseModel):
    threshold: int = Field(3, ge=0, le=64, description="Hamming distance similarity threshold (0-64). Lower values require higher similarity.")

class DedupRunResponse(BaseModel):
    processed_count: int = Field(..., description="Total number of documents evaluated")
    exact_duplicates_found: int = Field(..., description="Number of exact duplicates flagged")
    near_duplicates_found: int = Field(..., description="Number of near-duplicates flagged")
    total_duplicates: int = Field(..., description="Sum of all duplicates flagged")

class DedupStatsResponse(BaseModel):
    total_documents: int = Field(..., description="Total documents stored in the database")
    unique_documents: int = Field(..., description="Number of unique non-duplicate documents")
    exact_duplicates: int = Field(..., description="Number of exact duplicates")
    near_duplicates: int = Field(..., description="Number of near-duplicates")
    total_duplicates: int = Field(..., description="Total duplicate count")
    duplicate_ratio: float = Field(..., description="Ratio of duplicates over total documents")

@router.post("/run", response_model=DedupRunResponse, status_code=status.HTTP_200_OK)
async def run_deduplication(
    payload: DedupRunRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Run duplicate detection on all documents in the database.
    Flags duplicates by setting their duplicate_flag to True.
    """
    return await dedup_service.run_deduplication(db=db, threshold=payload.threshold)

@router.get("/stats", response_model=DedupStatsResponse, status_code=status.HTTP_200_OK)
async def get_dedup_stats(
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Retrieve statistics on duplicates, exact duplicates, and near-duplicates.
    """
    return await dedup_service.get_duplicate_stats(db=db)
