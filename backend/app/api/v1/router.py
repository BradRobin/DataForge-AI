from fastapi import APIRouter
from app.api.v1.endpoints import health
from app.features.documents.router import router as documents_router

api_router = APIRouter()

# Include routers from endpoints
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])

