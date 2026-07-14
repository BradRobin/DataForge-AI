import asyncio
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.ingest.service import ingest_service
from app.features.clean.service import clean_service
from app.features.dedup.service import dedup_service
from app.features.quality.service import quality_service
from app.features.export.service import export_service

logger = logging.getLogger("dataforge.pipeline.service")

class PipelineService:
    """
    Pipeline Orchestrator Engine for coordinating the sequential data cleaning process.
    """
    def __init__(self) -> None:
        self.pipelines: Dict[str, Dict[str, Any]] = {}
        self.cancel_events: Dict[str, asyncio.Event] = {}
        self.exports: Dict[str, Tuple[bytes, str, str]] = {}

    def get_pipeline_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve status details of a specific pipeline job."""
        return self.pipelines.get(pipeline_id)

    def get_pipeline_export(self, pipeline_id: str) -> Optional[Tuple[bytes, str, str]]:
        """Retrieve cached export package results from a completed pipeline job."""
        return self.exports.get(pipeline_id)

    async def cancel_pipeline(self, pipeline_id: str) -> bool:
        """Trigger cancellation for a running pipeline job."""
        if pipeline_id not in self.pipelines:
            return False
            
        status = self.pipelines[pipeline_id]
        if status["status"] not in ["running", "started"]:
            return False

        if pipeline_id in self.cancel_events:
            self.cancel_events[pipeline_id].set()
            
        status["status"] = "cancelled"
        status["stage"] = "cancelled"
        logger.info(f"Pipeline job '{pipeline_id}' cancelled by user request.")
        return True

    async def start_pipeline_job(
        self,
        db_factory: Callable[[], AsyncSession],
        urls: List[str],
        threshold: int = 12,
        export_format: str = "parquet"
    ) -> str:
        """
        Configure and spawn a background sequential data pipeline job.
        Returns the pipeline UUID.
        """
        pipeline_id = str(uuid.uuid4())
        
        self.pipelines[pipeline_id] = {
            "pipeline_id": pipeline_id,
            "status": "running",
            "stage": "queued",
            "progress": 0.0,
            "collected_count": 0,
            "error": None
        }
        
        self.cancel_events[pipeline_id] = asyncio.Event()
        
        # Schedule the background worker task
        asyncio.create_task(
            self._run_pipeline_worker(
                pipeline_id=pipeline_id,
                db_factory=db_factory,
                urls=urls,
                threshold=threshold,
                export_format=export_format
            )
        )
        
        return pipeline_id

    async def _run_pipeline_worker(
        self,
        pipeline_id: str,
        db_factory: Callable[[], AsyncSession],
        urls: List[str],
        threshold: int,
        export_format: str
    ) -> None:
        """
        Background task coordinating sequential execution of all pipeline feature stages.
        """
        logger.info(f"Pipeline job '{pipeline_id}' worker started.")
        status = self.pipelines[pipeline_id]
        cancel_event = self.cancel_events[pipeline_id]

        try:
            # ----------------------------------------------------
            # 1. Collect (Ingest) Stage
            # ----------------------------------------------------
            status["stage"] = "collect"
            status["progress"] = 10.0
            logger.info(f"Pipeline '{pipeline_id}': Starting data collection.")
            
            # Start ingestion background job
            job_id = ingest_service.trigger_job("http_collector", db_factory, urls)
            
            # Poll ingest progress and check cancellation
            while True:
                if cancel_event.is_set():
                    status["status"] = "cancelled"
                    status["stage"] = "cancelled"
                    return
                    
                ingest_status = ingest_service.get_job_status(job_id)
                if not ingest_status:
                    break
                    
                status["collected_count"] = ingest_status["collected_count"]
                
                # Check completion or failures
                if ingest_status["status"] == "completed":
                    break
                elif ingest_status["status"] == "failed":
                    raise Exception(f"Ingest crawler failed: {ingest_status.get('error', 'unknown error')}")
                    
                await asyncio.sleep(0.5)

            # ----------------------------------------------------
            # 2. Clean & Normalize Stage
            # ----------------------------------------------------
            if cancel_event.is_set():
                status["status"] = "cancelled"
                status["stage"] = "cancelled"
                return

            status["stage"] = "clean"
            status["progress"] = 35.0
            logger.info(f"Pipeline '{pipeline_id}': Executing document cleaning.")
            
            async with db_factory() as db:
                await clean_service.clean_batch(db=db)

            # ----------------------------------------------------
            # 3. Deduplicate Stage
            # ----------------------------------------------------
            if cancel_event.is_set():
                status["status"] = "cancelled"
                status["stage"] = "cancelled"
                return

            status["stage"] = "deduplicate"
            status["progress"] = 55.0
            logger.info(f"Pipeline '{pipeline_id}': Executing SimHash deduplication.")
            
            async with db_factory() as db:
                await dedup_service.run_deduplication(db=db, threshold=threshold)

            # ----------------------------------------------------
            # 4. Quality Evaluation Stage
            # ----------------------------------------------------
            if cancel_event.is_set():
                status["status"] = "cancelled"
                status["stage"] = "cancelled"
                return

            status["stage"] = "quality"
            status["progress"] = 75.0
            logger.info(f"Pipeline '{pipeline_id}': Executing quality heuristics grading.")
            
            async with db_factory() as db:
                await quality_service.evaluate_batch(db=db)

            # ----------------------------------------------------
            # 5. Dataset Export Stage
            # ----------------------------------------------------
            if cancel_event.is_set():
                status["status"] = "cancelled"
                status["stage"] = "cancelled"
                return

            status["stage"] = "export"
            status["progress"] = 90.0
            logger.info(f"Pipeline '{pipeline_id}': Generating final export package ({export_format}).")
            
            async with db_factory() as db:
                file_bytes, media_type, filename = await export_service.export_dataset(
                    db=db,
                    format_type=export_format,
                    exclude_duplicates=True
                )
                self.exports[pipeline_id] = (file_bytes, media_type, filename)

            # Complete pipeline
            status["status"] = "completed"
            status["stage"] = "completed"
            status["progress"] = 100.0
            logger.info(f"Pipeline '{pipeline_id}' successfully completed.")

        except Exception as e:
            logger.error(f"Pipeline job '{pipeline_id}' encountered error: {str(e)}")
            status["status"] = "failed"
            status["error"] = str(e)
        finally:
            if pipeline_id in self.cancel_events:
                del self.cancel_events[pipeline_id]

# Singleton instance of PipelineService
pipeline_service = PipelineService()
