import hashlib
import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.features.documents.models import Document
from app.features.documents.schemas import DocumentCreate, DocumentUpdate

def compute_hash(text: str) -> str:
    """Compute the SHA-256 hash of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

async def create_document(db: AsyncSession, obj_in: DocumentCreate) -> Document:
    """
    Create a new Document. 
    If hash is not provided, compute it from raw_text.
    Automatically flag as a duplicate if the hash already exists in the DB.
    """
    doc_data = obj_in.model_dump()
    
    # Compute hash if missing
    if not doc_data.get("hash") and doc_data.get("raw_text"):
        doc_data["hash"] = compute_hash(doc_data["raw_text"])
        
    # Check for duplicate hash
    doc_hash = doc_data.get("hash")
    duplicate_flag = False
    if doc_hash:
        stmt = select(Document).where(Document.hash == doc_hash).limit(1)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            duplicate_flag = True
            
    # Map Python's 'metadata' field to the SQLAlchemy model's 'metadata_' attribute
    metadata_val = doc_data.pop("metadata", None)
    
    db_obj = Document(
        **doc_data,
        metadata_=metadata_val,
        duplicate_flag=duplicate_flag
    )
    
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_document(db: AsyncSession, document_id: uuid.UUID) -> Optional[Document]:
    """Retrieve a single document by its UUID."""
    stmt = select(Document).where(Document.id == document_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_documents(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Document]:
    """Retrieve a paginated list of documents."""
    stmt = select(Document).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def update_document(
    db: AsyncSession, db_obj: Document, obj_in: DocumentUpdate
) -> Document:
    """Update an existing Document."""
    update_data = obj_in.model_dump(exclude_unset=True)
    
    # If raw_text is updated and hash is not explicitly set, recompute hash and check duplicates
    if "raw_text" in update_data and "hash" not in update_data:
        update_data["hash"] = compute_hash(update_data["raw_text"])
        
    if "hash" in update_data:
        stmt = select(Document).where(
            Document.hash == update_data["hash"], 
            Document.id != db_obj.id
        ).limit(1)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            update_data["duplicate_flag"] = True
        else:
            update_data["duplicate_flag"] = False

    # Extract metadata if it was modified
    if "metadata" in update_data:
        db_obj.metadata_ = update_data.pop("metadata")

    for field, value in update_data.items():
        setattr(db_obj, field, value)
        
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def delete_document(db: AsyncSession, document_id: uuid.UUID) -> bool:
    """Delete a document by its UUID."""
    db_obj = await get_document(db, document_id)
    if not db_obj:
        return False
    await db.delete(db_obj)
    await db.commit()
    return True
