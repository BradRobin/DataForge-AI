from typing import Any, List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.features.documents.crud import get_document, update_document
from app.features.documents.models import Document
from app.features.documents.schemas import DocumentResponse, DocumentUpdate
from app.features.clean.service import TextCleaner

router = APIRouter()
cleaner = TextCleaner()

class CleanTextRequest(BaseModel):
    text: str = Field(..., description="Raw text string to clean and normalize")

class CleanTextResponse(BaseModel):
    cleaned_text: str = Field(..., description="Processed and cleaned text output")

class CleanBatchRequest(BaseModel):
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of documents to clean in this batch")

class CleanBatchResponse(BaseModel):
    processed_count: int = Field(..., description="Number of documents successfully cleaned in this batch")

@router.post("/text", response_model=CleanTextResponse)
async def clean_raw_text(payload: CleanTextRequest) -> Any:
    """
    Clean and normalize raw text without database side effects.
    Useful for testing cleaning rules.
    """
    cleaned = cleaner.clean_document(payload.text)
    return {"cleaned_text": cleaned}

@router.post("/{document_id}", response_model=DocumentResponse)
async def clean_document_by_id(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Clean a specific document by its UUID, saving the result to the database.
    """
    doc = await get_document(db=db, document_id=document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
        
    cleaned_content = cleaner.clean_document(doc.raw_text)
    
    # Update document in database
    doc_update = DocumentUpdate(cleaned_text=cleaned_content)
    updated_doc = await update_document(db=db, db_obj=doc, obj_in=doc_update)
    return updated_doc

@router.post("/batch/run", response_model=CleanBatchResponse)
async def clean_documents_batch(
    payload: CleanBatchRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Find and clean a batch of documents in the database that have not been cleaned yet (cleaned_text is null).
    """
    # Query documents where cleaned_text is null or empty
    stmt = select(Document).where(
        (Document.cleaned_text == None) | (Document.cleaned_text == "")
    ).limit(payload.limit)
    
    result = await db.execute(stmt)
    docs = result.scalars().all()
    
    processed = 0
    for doc in docs:
        cleaned_content = cleaner.clean_document(doc.raw_text)
        doc_update = DocumentUpdate(cleaned_text=cleaned_content)
        await update_document(db=db, db_obj=doc, obj_in=doc_update)
        processed += 1
        
    return {"processed_count": processed}
