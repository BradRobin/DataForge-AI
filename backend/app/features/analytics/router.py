from typing import Any, Dict, List
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.analytics.service import analytics_service

router = APIRouter()

class LengthStats(BaseModel):
    avg_word_count: float = Field(..., description="Average word count across documents")
    median_word_count: float = Field(..., description="Median word count across documents")
    avg_char_count: float = Field(..., description="Average character count across documents")
    median_char_count: float = Field(..., description="Median character count across documents")

class QualityStats(BaseModel):
    avg_score: float = Field(..., description="Average quality score")
    median_score: float = Field(..., description="Median quality score")
    min_score: float = Field(..., description="Minimum quality score")
    max_score: float = Field(..., description="Maximum quality score")
    buckets: Dict[str, int] = Field(..., description="Distribution of quality scores across standard grade buckets")

class KeywordFreq(BaseModel):
    word: str = Field(..., description="Keyword string")
    frequency: int = Field(..., description="Occurrence count of keyword")

class AnalyticsOverviewResponse(BaseModel):
    total_documents: int = Field(..., description="Total documents in dataset")
    unique_documents: int = Field(..., description="Total unique documents")
    duplicate_documents: int = Field(..., description="Total duplicates flagged")
    duplicate_rate: float = Field(..., description="Ratio of duplicates over total documents")
    length_stats: LengthStats = Field(..., description="Heuristic length metrics")
    language_distribution: Dict[str, int] = Field(..., description="Breakdown of document counts by language")
    source_distribution: Dict[str, int] = Field(..., description="Breakdown of document counts by ingestion source")
    quality_stats: QualityStats = Field(..., description="Quality score summaries and buckets")
    top_keywords: List[KeywordFreq] = Field(..., description="Top 10 highest frequency keywords across unique documents")
    collection_timeline: Dict[str, int] = Field(..., description="Timeline of document collection counts grouped by day")

@router.get("/overview", response_model=AnalyticsOverviewResponse, status_code=status.HTTP_200_OK)
async def get_dataset_analytics_overview(
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Generate dataset-wide analytics, timelines, keywords, and quality distributions.
    Provides a dashboard-ready JSON payload.
    """
    return await analytics_service.get_dataset_analytics(db=db)
