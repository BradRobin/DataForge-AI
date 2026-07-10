import pytest
from httpx import AsyncClient

# Mark all tests in this module as asynchronous
pytestmark = pytest.mark.asyncio

async def test_root_welcome(client: AsyncClient):
    """
    Test that the root welcome endpoint is accessible and returns welcome metadata.
    """
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Welcome to the DataForge AI API" in data["message"]
    assert data["docs"] == "/docs"
    assert data["health"] == "/health"

async def test_root_health(client: AsyncClient):
    """
    Test that the root level health check endpoint is active and reports healthy status.
    """
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["project"] == "DataForge AI"
    assert data["database"]["status"] == "healthy"
    assert "latency_ms" in data["database"]
    assert data["database"]["error"] is None

async def test_v1_health(client: AsyncClient):
    """
    Test that the versioned v1 health check endpoint works identically.
    """
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"]["status"] == "healthy"
    assert data["environment"] == "development"
    assert data["version"] == "0.1.0"
