import time
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from app.core.database import get_db
from app.core.config import settings

logger = logging.getLogger("dataforge.health")
router = APIRouter()

@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint to verify backend system status and database connectivity.
    """
    start_time = time.time()
    db_status = "unhealthy"
    db_error = None
    
    try:
        # Check database connection by running a minimal query
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_status = "healthy"
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)
        logger.error(f"Database health check failed: {db_error}")

    latency_ms = (time.time() - start_time) * 1000
    
    # The application is considered healthy if database is healthy
    overall_status = "healthy" if db_status == "healthy" else "degraded"
    
    return {
        "status": overall_status,
        "environment": settings.ENV,
        "project": settings.PROJECT_NAME,
        "version": "0.1.0",
        "database": {
            "status": db_status,
            "latency_ms": round(latency_ms, 2),
            "error": db_error
        }
    }
