from datetime import date, datetime
import uuid
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, model_validator

class DocumentBase(BaseModel):
    source: str = Field(..., max_length=255, description="Source of the document (e.g., scrape, upload)")
    url: Optional[str] = Field(None, max_length=2048, description="Origin URL of the document")
    title: Optional[str] = Field(None, max_length=512, description="Title of the document")
    author: Optional[str] = Field(None, max_length=255, description="Author of the document")
    language: Optional[str] = Field(None, max_length=50, description="Language of the document")
    publication_date: Optional[date] = Field(None, description="Date of publication")
    raw_text: str = Field(..., description="Unprocessed raw text content")
    cleaned_text: Optional[str] = Field(None, description="Processed cleaned text content")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata dictionary")
    hash: Optional[str] = Field(None, max_length=64, description="Unique hash for deduplication")
    quality_score: Optional[float] = Field(0.0, description="Document quality score")

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    source: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=2048)
    title: Optional[str] = Field(None, max_length=512)
    author: Optional[str] = Field(None, max_length=255)
    language: Optional[str] = Field(None, max_length=50)
    publication_date: Optional[date] = None
    raw_text: Optional[str] = None
    cleaned_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    hash: Optional[str] = Field(None, max_length=64)
    duplicate_flag: Optional[bool] = None
    quality_score: Optional[float] = None

class DocumentResponse(DocumentBase):
    id: uuid.UUID
    collection_timestamp: datetime
    duplicate_flag: bool

    model_config = {
        "from_attributes": True
    }

    @model_validator(mode="before")
    @classmethod
    def resolve_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        
        # Convert SQLAlchemy object to dict, resolving metadata_ attribute to metadata field
        return {
            "id": getattr(data, "id", None),
            "source": getattr(data, "source", None),
            "url": getattr(data, "url", None),
            "title": getattr(data, "title", None),
            "author": getattr(data, "author", None),
            "language": getattr(data, "language", None),
            "publication_date": getattr(data, "publication_date", None),
            "collection_timestamp": getattr(data, "collection_timestamp", None),
            "raw_text": getattr(data, "raw_text", None),
            "cleaned_text": getattr(data, "cleaned_text", None),
            "metadata": getattr(data, "metadata_", {}),
            "hash": getattr(data, "hash", None),
            "duplicate_flag": getattr(data, "duplicate_flag", False),
            "quality_score": getattr(data, "quality_score", 0.0),
        }
