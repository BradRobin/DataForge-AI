import uuid
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.documents import crud, schemas

router = APIRouter()

@router.post("/", response_model=schemas.DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document_in: schemas.DocumentCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new document.
    """
    return await crud.create_document(db=db, obj_in=document_in)

@router.get("/", response_model=List[schemas.DocumentResponse])
async def read_documents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Retrieve a list of documents.
    """
    return await crud.get_documents(db=db, skip=skip, limit=limit)

@router.get("/{document_id}", response_model=schemas.DocumentResponse)
async def read_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Retrieve a specific document by its UUID.
    """
    document = await crud.get_document(db=db, document_id=document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return document

@router.put("/{document_id}", response_model=schemas.DocumentResponse)
async def update_document(
    document_id: uuid.UUID,
    document_in: schemas.DocumentUpdate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update a document.
    """
    document = await crud.get_document(db=db, document_id=document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return await crud.update_document(db=db, db_obj=document, obj_in=document_in)

@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Delete a document.
    """
    success = await crud.delete_document(db=db, document_id=document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return {"status": "success", "message": "Document deleted successfully"}
