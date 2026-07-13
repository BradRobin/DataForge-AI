import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.features.ingest.base import BaseCollector
from app.features.ingest.http_collector import HttpCollector

logger = logging.getLogger("dataforge.ingest.service")

class IngestService:
    """
    Service for managing ingestion jobs and registry of collection plugins.
    """
    def __init__(self) -> None:
        self._collectors: Dict[str, BaseCollector] = {}
        self.jobs: Dict[str, Dict[str, Any]] = {}
        
        # Register default collectors
        self.register_collector(HttpCollector())

    def register_collector(self, collector: BaseCollector) -> None:
        """Register a new collection plugin."""
        self._collectors[collector.name] = collector
        logger.info(f"Registered ingest collector: {collector.name}")

    def get_collector(self, name: str) -> BaseCollector:
        """Retrieve a registered collector by name."""
        collector = self._collectors.get(name)
        if not collector:
            raise ValueError(f"Collector '{name}' is not registered.")
        return collector

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the details/status of a collection job."""
        return self.jobs.get(job_id)

    async def _run_job_async(
        self, 
        job_id: str, 
        collector_name: str, 
        session_factory: async_sessionmaker[AsyncSession], 
        urls: List[str], 
        **kwargs: Any
    ) -> None:
        """Asynchronous execution task for data collection."""
        self.jobs[job_id]["status"] = "running"
        self.jobs[job_id]["started_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Starting ingest job {job_id} using {collector_name}")
        
        try:
            collector = self.get_collector(collector_name)
            
            # Obtain DB session
            async with session_factory() as db:
                try:
                    documents = await collector.collect(db=db, urls=urls, **kwargs)
                    
                    self.jobs[job_id]["status"] = "completed"
                    self.jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
                    self.jobs[job_id]["collected_count"] = len(documents)
                    self.jobs[job_id]["document_ids"] = [str(doc.id) for doc in documents]
                    
                    logger.info(f"Ingest job {job_id} completed successfully. Collected {len(documents)} documents.")
                except Exception as e:
                    await db.rollback()
                    raise e
        except Exception as e:
            logger.error(f"Ingest job {job_id} failed: {e}", exc_info=True)
            self.jobs[job_id]["status"] = "failed"
            self.jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
            self.jobs[job_id]["error"] = str(e)

    def trigger_job(
        self, 
        collector_name: str, 
        session_factory: async_sessionmaker[AsyncSession], 
        urls: List[str], 
        **kwargs: Any
    ) -> str:
        """
        Trigger an ingestion job. Generates a job ID and starts it as a background task.
        """
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "id": job_id,
            "collector": collector_name,
            "status": "pending",
            "urls": urls,
            "collected_count": 0,
            "error": None,
            "started_at": None,
            "completed_at": None
        }
        
        # Start background task using asyncio
        asyncio.create_task(
            self._run_job_async(
                job_id=job_id,
                collector_name=collector_name,
                session_factory=session_factory,
                urls=urls,
                **kwargs
            )
        )
        
        return job_id

# Singleton instance of IngestService to persist state across endpoints
ingest_service = IngestService()
