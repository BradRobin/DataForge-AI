from typing import Any, Dict
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.documents.schemas import DocumentResponse
from app.features.quality.service import quality_service

router = APIRouter()

class QualityTextRequest(BaseModel):
    text: str = Field(..., description="Raw or cleaned text string to grade")

class QualityTextResponse(BaseModel):
    quality_score: float = Field(..., description="Overall document quality score between 0 and 100")
    sub_scores: Dict[str, float] = Field(..., description="Breakdown of sub-scores contributing to the quality score")
    metrics: Dict[str, Any] = Field(..., description="Raw text metrics evaluated by the engine")

class QualityBatchRequest(BaseModel):
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of documents to evaluate in this batch")

class QualityBatchResponse(BaseModel):
    processed_count: int = Field(..., description="Number of documents successfully evaluated and scored")

@router.post("/text", response_model=QualityTextResponse, status_code=status.HTTP_200_OK)
async def evaluate_raw_text(
    payload: QualityTextRequest
) -> Any:
    """
    Evaluate raw or cleaned text and calculate sub-scores and overall quality score.
    Useful for sandbox testing of text datasets.
    """
    return quality_service.evaluate_text(payload.text)

@router.post("/{document_id}", response_model=DocumentResponse, status_code=status.HTTP_200_OK)
async def evaluate_document_by_id(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Evaluate a specific stored document by its UUID, calculating and saving its quality score in the database.
    """
    try:
        updated_doc = await quality_service.evaluate_document_by_id(db=db, document_id=document_id)
        return updated_doc
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.post("/batch/run", response_model=QualityBatchResponse, status_code=status.HTTP_200_OK)
async def evaluate_documents_batch(
    payload: QualityBatchRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Run evaluation on a batch of stored documents that have not been scored yet.
    """
    count = await quality_service.evaluate_batch(db=db, limit=payload.limit)
    return {"processed_count": count}
