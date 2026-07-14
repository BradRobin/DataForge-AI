from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.export.service import export_service

router = APIRouter()

@router.get("", status_code=status.HTTP_200_OK)
async def download_dataset_export(
    format: str = Query(..., description="Export file format: 'json', 'csv', or 'parquet'"),
    source: Optional[str] = Query(None, description="Filter documents by ingestion source"),
    language: Optional[str] = Query(None, description="Filter documents by language"),
    min_quality: Optional[float] = Query(None, description="Filter documents by minimum quality score"),
    exclude_duplicates: bool = Query(False, description="If true, excludes duplicate documents from the export"),
    db: AsyncSession = Depends(get_db)
) -> Response:
    """
    Download the filtered documents dataset in JSON, CSV, or Parquet format.
    """
    try:
        file_bytes, media_type, filename = await export_service.export_dataset(
            db=db,
            format_type=format,
            source=source,
            language=language,
            min_quality=min_quality,
            exclude_duplicates=exclude_duplicates
        )
        
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
        
        return Response(
            content=file_bytes,
            media_type=media_type,
            headers=headers
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
