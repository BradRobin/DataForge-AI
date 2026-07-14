import csv
import io
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.documents.models import Document

logger = logging.getLogger("dataforge.export.service")

class ExportService:
    """
    Dataset Export Engine for filtering and downloading data in JSON, CSV, or Parquet formats.
    """
    async def export_dataset(
        self,
        db: AsyncSession,
        format_type: str,
        source: Optional[str] = None,
        language: Optional[str] = None,
        min_quality: Optional[float] = None,
        exclude_duplicates: bool = False
    ) -> Tuple[bytes, str, str]:
        """
        Query database with filters and export records in JSON, CSV, or Parquet formats.
        Returns a tuple of (file_bytes, media_type, filename).
        """
        stmt = select(Document)
        
        # Apply filters dynamically
        if source:
            stmt = stmt.where(Document.source == source)
        if language:
            stmt = stmt.where(Document.language == language)
        if min_quality is not None:
            stmt = stmt.where(Document.quality_score >= min_quality)
        if exclude_duplicates:
            stmt = stmt.where((Document.duplicate_flag == False) | (Document.duplicate_flag == None))
            
        result = await db.execute(stmt)
        documents = result.scalars().all()
        
        if not documents:
            raise ValueError("No documents found matching the specified filters.")
            
        # Serialize database records into list of dictionaries
        data_list: List[Dict[str, Any]] = []
        for doc in documents:
            data_list.append({
                "id": str(doc.id),
                "source": doc.source,
                "url": doc.url,
                "title": doc.title,
                "author": doc.author,
                "language": doc.language,
                "publication_date": doc.publication_date.isoformat() if doc.publication_date else None,
                "collection_timestamp": doc.collection_timestamp.isoformat() if doc.collection_timestamp else None,
                "raw_text": doc.raw_text,
                "cleaned_text": doc.cleaned_text,
                "quality_score": doc.quality_score,
                "duplicate_flag": doc.duplicate_flag,
                "hash": doc.hash,
                "metadata": doc.metadata_ if doc.metadata_ else {}
            })
            
        # Format dataset to requested file representation
        format_type = format_type.lower()
        if format_type == "json":
            file_bytes = json.dumps(data_list, indent=2).encode("utf-8")
            media_type = "application/json"
            filename = "dataset_export.json"
            
        elif format_type == "csv":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=data_list[0].keys())
            writer.writeheader()
            
            for row in data_list:
                # Convert metadata dict to string to fit in single CSV cell
                row_copy = row.copy()
                row_copy["metadata"] = json.dumps(row_copy["metadata"])
                writer.writerow(row_copy)
                
            file_bytes = output.getvalue().encode("utf-8")
            media_type = "text/csv"
            filename = "dataset_export.csv"
            
        elif format_type == "parquet":
            # Flatten metadata dict into string to prevent PyArrow nested schema conversion errors
            data_for_pandas = []
            for row in data_list:
                row_copy = row.copy()
                row_copy["metadata"] = json.dumps(row_copy["metadata"])
                data_for_pandas.append(row_copy)
                
            df = pd.DataFrame(data_for_pandas)
            
            # Export dataframe to parquet bytes using pyarrow engine
            buffer = io.BytesIO()
            df.to_parquet(buffer, index=False, engine="pyarrow")
            file_bytes = buffer.getvalue()
            
            media_type = "application/octet-stream"
            filename = "dataset_export.parquet"
            
        else:
            raise ValueError(f"Unsupported export format '{format_type}'.")
            
        return file_bytes, media_type, filename

# Singleton instance of ExportService
export_service = ExportService()
