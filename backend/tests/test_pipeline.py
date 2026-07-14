import asyncio
import pytest
import pytest_asyncio
import httpx
from unittest.mock import patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.documents.models import Document
from app.features.pipeline.service import pipeline_service

# Keep a reference to the original get method of httpx.AsyncClient
original_get = httpx.AsyncClient.get

def make_mock_response(text: str, status_code: int = 200, url: str = "http://mocksite.com") -> httpx.Response:
    """Helper to construct a real httpx.Response object."""
    return httpx.Response(
        status_code=status_code,
        content=text.encode("utf-8"),
        headers={"content-type": "text/html"},
        request=httpx.Request("GET", url)
    )

@pytest_asyncio.fixture(autouse=True)
async def clean_db(db_session: AsyncSession):
    """Ensure a clean database state for each test by deleting all documents."""
    await db_session.execute(Document.__table__.delete())
    await db_session.commit()

@pytest.mark.asyncio
async def test_pipeline_orchestrator_success(client: AsyncClient):
    """Test that the one-click pipeline triggers, runs to completion, and exports the data."""
    mock_responses = {
        "http://mocksite.com/robots.txt": make_mock_response("User-agent: *\nAllow: /", url="http://mocksite.com/robots.txt"),
        "http://mocksite.com/doc1": make_mock_response("<html><head><title>Mock Title</title></head><body>DataForge represents a robust data engineering framework.</body></html>", url="http://mocksite.com/doc1")
    }

    async def mock_get(self_client, url, *args, **kwargs):
        url_str = str(url)
        # Pass through local test client API calls
        if url_str.startswith("http://test") or url_str.startswith("/"):
            return await original_get(self_client, url, *args, **kwargs)
        # Serve external mock requests
        if url_str in mock_responses:
            return mock_responses[url_str]
        return make_mock_response("", status_code=404, url=url_str)

    with patch("httpx.AsyncClient.get", new=mock_get):
        # 1. Trigger the pipeline run
        payload = {
            "urls": ["http://mocksite.com/doc1"],
            "threshold": 12,
            "export_format": "json"
        }
        
        response = await client.post("/api/v1/pipeline/run", json=payload)
        assert response.status_code == 202
        res_data = response.json()
        pipeline_id = res_data["pipeline_id"]
        assert pipeline_id is not None
        
        # 2. Poll pipeline status until it is completed (timeout after 10 seconds)
        max_retries = 20
        completed = False
        
        for _ in range(max_retries):
            status_res = await client.get(f"/api/v1/pipeline/status/{pipeline_id}")
            assert status_res.status_code == 200
            status_data = status_res.json()
            
            if status_data["status"] == "completed":
                completed = True
                break
            elif status_data["status"] == "failed":
                pytest.fail(f"Pipeline job failed: {status_data['error']}")
                
            await asyncio.sleep(0.5)
            
        assert completed is True
        
        # 3. Verify final statistics in status
        status_res = await client.get(f"/api/v1/pipeline/status/{pipeline_id}")
        status_data = status_res.json()
        assert status_data["progress"] == 100.0
        assert status_data["stage"] == "completed"
        assert status_data["collected_count"] > 0
        
        # 4. Download and verify the generated export package
        download_res = await client.get(f"/api/v1/pipeline/download/{pipeline_id}")
        assert download_res.status_code == 200
        assert download_res.headers["content-type"] == "application/json"
        
        export_json = download_res.json()
        assert len(export_json) > 0
        assert export_json[0]["source"] == "http_collector"
        assert "dataforge" in export_json[0]["raw_text"].lower()

@pytest.mark.asyncio
async def test_pipeline_orchestrator_cancellation(client: AsyncClient):
    """Test that a running pipeline can be successfully cancelled."""
    mock_responses = {
        "http://mocksite.com/robots.txt": make_mock_response("User-agent: *\nAllow: /", url="http://mocksite.com/robots.txt"),
        "http://mocksite.com/doc1": make_mock_response("<html><body>Content</body></html>", url="http://mocksite.com/doc1")
    }

    async def mock_get(self_client, url, *args, **kwargs):
        url_str = str(url)
        if url_str.startswith("http://test") or url_str.startswith("/"):
            return await original_get(self_client, url, *args, **kwargs)
        if url_str in mock_responses:
            return mock_responses[url_str]
        return make_mock_response("", status_code=404, url=url_str)

    with patch("httpx.AsyncClient.get", new=mock_get):
        payload = {
            "urls": ["http://mocksite.com/doc1"],
            "threshold": 12,
            "export_format": "json"
        }
        
        # 1. Start pipeline run
        response = await client.post("/api/v1/pipeline/run", json=payload)
        assert response.status_code == 202
        pipeline_id = response.json()["pipeline_id"]
        
        # 2. Cancel the running pipeline immediately
        cancel_res = await client.post(f"/api/v1/pipeline/cancel/{pipeline_id}")
        assert cancel_res.status_code == 200
        assert cancel_res.json() == {"cancelled": True}
        
        # 3. Retrieve status and assert cancelled state
        status_res = await client.get(f"/api/v1/pipeline/status/{pipeline_id}")
        status_data = status_res.json()
        assert status_data["status"] == "cancelled"
        assert status_data["stage"] == "cancelled"
