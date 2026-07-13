import asyncio
import pytest
import httpx
from unittest.mock import patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.documents.models import Document

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

@pytest.mark.asyncio
async def test_successful_ingest(client: AsyncClient, db_session: AsyncSession):
    """Test successful collection of a document and database storage."""
    mock_responses = {
        "http://mocksite.com/robots.txt": make_mock_response("User-agent: *\nAllow: /", url="http://mocksite.com/robots.txt"),
        "http://mocksite.com/doc1": make_mock_response("<html><head><title>Mock Title</title></head><body>This is the mock text page content.</body></html>", url="http://mocksite.com/doc1")
    }

    async def mock_get(self_client, url, *args, **kwargs):
        url_str = str(url)
        # If it's a test client request to the local application, pass it through
        if url_str.startswith("http://test") or url_str.startswith("/"):
            return await original_get(self_client, url, *args, **kwargs)
        # Otherwise, serve from our mock responses
        if url_str in mock_responses:
            return mock_responses[url_str]
        return make_mock_response("", status_code=404, url=url_str)

    with patch("httpx.AsyncClient.get", new=mock_get):
        response = await client.post("/api/v1/ingest/trigger", json={
            "urls": ["http://mocksite.com/doc1"],
            "retries": 1
        })
        assert response.status_code == 202
        job_id = response.json()["job_id"]

        # Poll the status endpoint until completed
        job_status = "pending"
        data = {}
        for _ in range(50):
            status_res = await client.get(f"/api/v1/ingest/status/{job_id}")
            assert status_res.status_code == 200
            data = status_res.json()
            job_status = data["status"]
            if job_status in ["completed", "failed"]:
                break
            await asyncio.sleep(0.05)

        assert job_status == "completed"
        assert data["collected_count"] == 1
        
        # Verify db persistence
        stmt = select(Document).where(Document.url == "http://mocksite.com/doc1")
        res = await db_session.execute(stmt)
        doc = res.scalar_one_or_none()
        assert doc is not None
        assert doc.title == "Mock Title"
        assert "mock text page content" in doc.cleaned_text
        assert doc.source == "http_collector"

@pytest.mark.asyncio
async def test_duplicate_url_prevention(client: AsyncClient, db_session: AsyncSession):
    """Test that URLs already crawled are not crawled again."""
    mock_responses = {
        "http://duplicatesite.com/robots.txt": make_mock_response("User-agent: *\nAllow: /", url="http://duplicatesite.com/robots.txt"),
        "http://duplicatesite.com/unique-url": make_mock_response("<html><title>Unique</title><body>Original content</body></html>", url="http://duplicatesite.com/unique-url")
    }

    async def mock_get(self_client, url, *args, **kwargs):
        url_str = str(url)
        if url_str.startswith("http://test") or url_str.startswith("/"):
            return await original_get(self_client, url, *args, **kwargs)
        if url_str in mock_responses:
            return mock_responses[url_str]
        return make_mock_response("", status_code=404, url=url_str)

    with patch("httpx.AsyncClient.get", new=mock_get):
        # 1. First crawl trigger
        res1 = await client.post("/api/v1/ingest/trigger", json={
            "urls": ["http://duplicatesite.com/unique-url"]
        })
        job_id1 = res1.json()["job_id"]

        # Wait for completion
        for _ in range(50):
            status_res = await client.get(f"/api/v1/ingest/status/{job_id1}")
            if status_res.json()["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(0.05)

        assert status_res.json()["status"] == "completed"
        assert status_res.json()["collected_count"] == 1

        # 2. Second crawl trigger for same URL
        res2 = await client.post("/api/v1/ingest/trigger", json={
            "urls": ["http://duplicatesite.com/unique-url"]
        })
        job_id2 = res2.json()["job_id"]

        # Wait for completion
        for _ in range(50):
            status_res2 = await client.get(f"/api/v1/ingest/status/{job_id2}")
            if status_res2.json()["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(0.05)

        assert status_res2.json()["status"] == "completed"
        # Collected count should be 0 because it's a duplicate URL!
        assert status_res2.json()["collected_count"] == 0

@pytest.mark.asyncio
async def test_retry_on_failure(client: AsyncClient):
    """Test retry logic on transient server errors."""
    attempts = 0

    async def mock_get(self_client, url, *args, **kwargs):
        nonlocal attempts
        url_str = str(url)
        if url_str.startswith("http://test") or url_str.startswith("/"):
            return await original_get(self_client, url, *args, **kwargs)
            
        if url_str == "http://retrysite.com/robots.txt":
            return make_mock_response("User-agent: *\nAllow: /", url=url_str)
        
        if url_str == "http://retrysite.com/fail-then-succeed":
            attempts += 1
            if attempts < 3:
                # Return a 500 Server Error response to trigger retry
                return make_mock_response("Server Error", status_code=500, url=url_str)
            # Succeed on the 3rd attempt
            return make_mock_response("<html><title>Retry Success</title><body>Content after retries</body></html>", url=url_str)
        return make_mock_response("", status_code=404, url=url_str)

    original_sleep = asyncio.sleep

    async def mock_sleep(delay, *args, **kwargs):
        if delay >= 0.1:
            await original_sleep(0)
        else:
            await original_sleep(delay, *args, **kwargs)

    # Use custom sleep mock to make retry delays fast while letting polling loop yield control
    with patch("httpx.AsyncClient.get", new=mock_get), \
         patch("asyncio.sleep", new=mock_sleep):
         
        response = await client.post("/api/v1/ingest/trigger", json={
            "urls": ["http://retrysite.com/fail-then-succeed"],
            "retries": 3
        })
        job_id = response.json()["job_id"]

        # Poll status
        for _ in range(50):
            status_res = await client.get(f"/api/v1/ingest/status/{job_id}")
            if status_res.json()["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(0.05)

        assert status_res.json()["status"] == "completed"
        assert status_res.json()["collected_count"] == 1
        assert attempts == 3  # Failed twice, succeeded on the third attempt

@pytest.mark.asyncio
async def test_robots_txt_disallowed(client: AsyncClient):
    """Test that URLs disallowed by robots.txt are skipped."""
    mock_responses = {
        "http://blockedsite.com/robots.txt": make_mock_response("User-agent: *\nDisallow: /blocked-path", url="http://blockedsite.com/robots.txt"),
        "http://blockedsite.com/blocked-path/doc": make_mock_response("<html><body>Blocked Content</body></html>", url="http://blockedsite.com/blocked-path/doc")
    }

    async def mock_get(self_client, url, *args, **kwargs):
        url_str = str(url)
        if url_str.startswith("http://test") or url_str.startswith("/"):
            return await original_get(self_client, url, *args, **kwargs)
        if url_str in mock_responses:
            return mock_responses[url_str]
        return make_mock_response("", status_code=404, url=url_str)

    with patch("httpx.AsyncClient.get", new=mock_get):
        response = await client.post("/api/v1/ingest/trigger", json={
            "urls": ["http://blockedsite.com/blocked-path/doc"]
        })
        job_id = response.json()["job_id"]

        for _ in range(50):
            status_res = await client.get(f"/api/v1/ingest/status/{job_id}")
            if status_res.json()["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(0.05)

        assert status_res.json()["status"] == "completed"
        # Collected count must be 0 because it was disallowed!
        assert status_res.json()["collected_count"] == 0
