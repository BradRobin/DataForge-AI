import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.features.documents.models import Document
from app.features.documents.crud import compute_hash

@pytest.mark.asyncio
async def test_create_document(client: AsyncClient, db_session: AsyncSession):
    """Test creating a document and auto-generating its hash."""
    doc_data = {
        "source": "test_scrape",
        "raw_text": "This is raw test text for document creation.",
        "title": "Test Title",
        "url": "http://example.com/test",
        "author": "Author Name",
        "language": "en",
        "publication_date": "2026-07-13",
        "metadata": {"tags": ["test", "ai"]},
        "quality_score": 0.85
    }
    
    response = await client.post("/api/v1/documents/", json=doc_data)
    assert response.status_code == 201
    res_data = response.json()
    
    # Assert return fields
    assert "id" in res_data
    assert res_data["source"] == doc_data["source"]
    assert res_data["raw_text"] == doc_data["raw_text"]
    assert res_data["title"] == doc_data["title"]
    assert res_data["url"] == doc_data["url"]
    assert res_data["author"] == doc_data["author"]
    assert res_data["language"] == doc_data["language"]
    assert res_data["publication_date"] == doc_data["publication_date"]
    assert res_data["metadata"] == doc_data["metadata"]
    assert res_data["quality_score"] == doc_data["quality_score"]
    assert res_data["duplicate_flag"] is False
    assert "collection_timestamp" in res_data
    
    # Verify hash is computed
    expected_hash = compute_hash(doc_data["raw_text"])
    assert res_data["hash"] == expected_hash

    # Verify db persistence
    doc_id = uuid.UUID(res_data["id"])
    stmt = select(Document).where(Document.id == doc_id)
    db_result = await db_session.execute(stmt)
    db_doc = db_result.scalar_one_or_none()
    assert db_doc is not None
    assert db_doc.source == "test_scrape"
    assert db_doc.hash == expected_hash

@pytest.mark.asyncio
async def test_create_duplicate_document(client: AsyncClient):
    """Test that creating a document with the same hash sets duplicate_flag to True."""
    doc_data_1 = {
        "source": "scrape_a",
        "raw_text": "Unique text to test duplicates."
    }
    doc_data_2 = {
        "source": "scrape_b",
        "raw_text": "Unique text to test duplicates." # same raw_text => same hash
    }
    
    # Insert first
    response_1 = await client.post("/api/v1/documents/", json=doc_data_1)
    assert response_1.status_code == 201
    assert response_1.json()["duplicate_flag"] is False
    
    # Insert second
    response_2 = await client.post("/api/v1/documents/", json=doc_data_2)
    assert response_2.status_code == 201
    assert response_2.json()["duplicate_flag"] is True

@pytest.mark.asyncio
async def test_read_document(client: AsyncClient):
    """Test retrieving a single document by UUID."""
    doc_data = {
        "source": "read_test",
        "raw_text": "Retrieve me please."
    }
    
    # Insert
    create_response = await client.post("/api/v1/documents/", json=doc_data)
    assert create_response.status_code == 201
    doc_id = create_response.json()["id"]
    
    # Read existing
    read_response = await client.get(f"/api/v1/documents/{doc_id}")
    assert read_response.status_code == 200
    assert read_response.json()["raw_text"] == "Retrieve me please."
    
    # Read non-existent
    bad_id = str(uuid.uuid4())
    bad_response = await client.get(f"/api/v1/documents/{bad_id}")
    assert bad_response.status_code == 404

@pytest.mark.asyncio
async def test_read_documents_list(client: AsyncClient):
    """Test retrieving a list of documents."""
    doc_data = {
        "source": "list_test",
        "raw_text": "List test item."
    }
    # Ensure there is at least one
    await client.post("/api/v1/documents/", json=doc_data)
    
    response = await client.get("/api/v1/documents/?skip=0&limit=10")
    assert response.status_code == 200
    res_list = response.json()
    assert isinstance(res_list, list)
    assert len(res_list) >= 1

@pytest.mark.asyncio
async def test_update_document(client: AsyncClient):
    """Test updating document attributes."""
    doc_data = {
        "source": "original_source",
        "raw_text": "Original raw text."
    }
    
    # Insert
    create_response = await client.post("/api/v1/documents/", json=doc_data)
    doc_id = create_response.json()["id"]
    
    # Update
    update_payload = {
        "cleaned_text": "Cleaned up text.",
        "quality_score": 0.99,
        "metadata": {"cleaned": True}
    }
    update_response = await client.put(f"/api/v1/documents/{doc_id}", json=update_payload)
    assert update_response.status_code == 200
    res_data = update_response.json()
    assert res_data["cleaned_text"] == "Cleaned up text."
    assert res_data["quality_score"] == 0.99
    assert res_data["metadata"] == {"cleaned": True}
    assert res_data["source"] == "original_source"  # remained unchanged

@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient):
    """Test deleting a document."""
    doc_data = {
        "source": "delete_test",
        "raw_text": "Delete this text."
    }
    
    # Insert
    create_response = await client.post("/api/v1/documents/", json=doc_data)
    doc_id = create_response.json()["id"]
    
    # Delete
    delete_response = await client.delete(f"/api/v1/documents/{doc_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "success"
    
    # Verify gone
    read_response = await client.get(f"/api/v1/documents/{doc_id}")
    assert read_response.status_code == 404
