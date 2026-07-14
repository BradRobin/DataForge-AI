import logging
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.documents.models import Document
from app.features.dedup.simhash import compute_simhash, hamming_distance

logger = logging.getLogger("dataforge.dedup.service")

class DedupService:
    """
    Service for intelligent document deduplication using exact hash and SimHash near-duplicate detection.
    """
    async def run_deduplication(self, db: AsyncSession, threshold: int = 3) -> Dict[str, Any]:
        """
        Run deduplication on all documents.
        Flags exact and near-duplicates based on a Hamming distance threshold.
        """
        # Fetch all documents ordered by oldest first (first collected is considered the original)
        stmt = select(Document).order_by(Document.collection_timestamp.asc())
        result = await db.execute(stmt)
        documents = result.scalars().all()
        
        unique_docs: List[Document] = []
        unique_simhashes: List[int] = []
        
        exact_duplicates = 0
        near_duplicates = 0
        
        for doc in documents:
            # Initialize or clean metadata keys for duplicate tracking
            if doc.metadata_ is None:
                doc.metadata_ = {}
                
            # 1. Exact Duplicate check using hash
            is_exact = False
            if doc.hash:
                for original_doc in unique_docs:
                    if original_doc.hash == doc.hash:
                        is_exact = True
                        doc.duplicate_flag = True
                        # Update metadata to record duplicate lineage
                        doc.metadata_["duplicate_type"] = "exact"
                        doc.metadata_["duplicate_of"] = str(original_doc.id)
                        exact_duplicates += 1
                        logger.info(f"Flagged EXACT duplicate: {doc.id} of {original_doc.id}")
                        break
                        
            if is_exact:
                db.add(doc)
                continue

            # 2. Near Duplicate check using SimHash
            # Retrieve cached SimHash or compute it
            simhash_hex = doc.metadata_.get("simhash")
            if simhash_hex:
                try:
                    fingerprint = int(simhash_hex, 16)
                except ValueError:
                    fingerprint = compute_simhash(doc.cleaned_text or doc.raw_text)
                    doc.metadata_["simhash"] = hex(fingerprint)
            else:
                fingerprint = compute_simhash(doc.cleaned_text or doc.raw_text)
                doc.metadata_["simhash"] = hex(fingerprint)
                
            is_near = False
            for original_doc, original_hash in zip(unique_docs, unique_simhashes):
                distance = hamming_distance(fingerprint, original_hash)
                if distance <= threshold:
                    is_near = True
                    doc.duplicate_flag = True
                    doc.metadata_["duplicate_type"] = "near"
                    doc.metadata_["duplicate_of"] = str(original_doc.id)
                    doc.metadata_["similarity_distance"] = distance
                    near_duplicates += 1
                    logger.info(f"Flagged NEAR duplicate (distance {distance}): {doc.id} of {original_doc.id}")
                    break
                    
            if is_near:
                db.add(doc)
                continue

            # If not a duplicate, mark as unique and add to comparisons pool
            doc.duplicate_flag = False
            # Remove any residual duplicate info in case of reprocessing
            doc.metadata_.pop("duplicate_type", None)
            doc.metadata_.pop("duplicate_of", None)
            doc.metadata_.pop("similarity_distance", None)
            
            unique_docs.append(doc)
            unique_simhashes.append(fingerprint)
            db.add(doc)
            
        await db.commit()
        
        return {
            "processed_count": len(documents),
            "exact_duplicates_found": exact_duplicates,
            "near_duplicates_found": near_duplicates,
            "total_duplicates": exact_duplicates + near_duplicates
        }

    async def get_duplicate_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Query and compute statistics about duplicates in the database."""
        # Count total documents
        stmt_total = select(Document)
        res_total = await db.execute(stmt_total)
        documents = res_total.scalars().all()
        total_count = len(documents)
        
        if total_count == 0:
            return {
                "total_documents": 0,
                "unique_documents": 0,
                "exact_duplicates": 0,
                "near_duplicates": 0,
                "total_duplicates": 0,
                "duplicate_ratio": 0.0
            }
            
        duplicates = [d for d in documents if d.duplicate_flag]
        duplicate_count = len(duplicates)
        
        exact_count = sum(1 for d in duplicates if d.metadata_.get("duplicate_type") == "exact")
        near_count = sum(1 for d in duplicates if d.metadata_.get("duplicate_type") == "near")
        
        return {
            "total_documents": total_count,
            "unique_documents": total_count - duplicate_count,
            "exact_duplicates": exact_count,
            "near_duplicates": near_count,
            "total_duplicates": duplicate_count,
            "duplicate_ratio": round(duplicate_count / total_count, 4)
        }

# Singleton instance of DedupService
dedup_service = DedupService()
