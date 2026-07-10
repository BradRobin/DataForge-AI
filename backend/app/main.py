import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import get_db
from app.api.router import api_router
from app.api.v1.endpoints.health import health_check

# Initialize Logging
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger("dataforge.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} in environment: {settings.ENV}")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI Data Engineering Pipeline for Training & Evaluation Datasets",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to allowed frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root level health check for simple balancer mapping
@app.get("/health", tags=["health"])
async def root_health(db: AsyncSession = Depends(get_db)):
    return await health_check(db)

# Include central versioned API router under '/api/v1' prefix
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root_welcome():
    return {
        "message": f"Welcome to the {settings.PROJECT_NAME} API",
        "docs": "/docs",
        "health": "/health"
    }
