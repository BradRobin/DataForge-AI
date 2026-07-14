from fastapi import APIRouter
from app.api.v1.endpoints import health
from app.features.documents.router import router as documents_router
from app.features.ingest.router import router as ingest_router
from app.features.clean.router import router as clean_router
from app.features.dedup.router import router as dedup_router
from app.features.quality.router import router as quality_router
from app.features.analytics.router import router as analytics_router
from app.features.export.router import router as export_router

api_router = APIRouter()

# Include routers from endpoints
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
api_router.include_router(clean_router, prefix="/clean", tags=["clean"])
api_router.include_router(dedup_router, prefix="/dedup", tags=["dedup"])
api_router.include_router(quality_router, prefix="/quality", tags=["quality"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(export_router, prefix="/export", tags=["export"])

