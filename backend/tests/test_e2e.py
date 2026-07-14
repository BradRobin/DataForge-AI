import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.documents.models import Document

@pytest.mark.asyncio
async def test_end_to_end_data_engineering_pipeline(client: AsyncClient, db_session: AsyncSession):
    """
    E2E Integration Test simulating a programmatic step-by-step run of all
    DataForge AI API layers: Create -> Clean -> Dedup -> Score -> Analytics -> Export.
    """
    
    # Ensure clean database state
    await db_session.execute(Document.__table__.delete())
    await db_session.commit()

    # ====================================================
    # 1. Create Document (Ingestion Simulation)
    # ====================================================
    # Document 1: Parent source document
    doc1_payload = {
        "title": "E2E Master Document",
        "url": "http://e2esite.com/master",
        "source": "e2e_collector",
        "raw_text": "<html>\n<head><title>E2E Master</title></head>\n<body>\nThis is a pristine document containing detailed data engineering instructions.\nSponsored advertisement.\nTerms of Service\n</body>\n</html>"
    }
    
    res1 = await client.post("/api/v1/documents/", json=doc1_payload)
    assert res1.status_code == 201
    doc1_data = res1.json()
    doc1_id = doc1_data["id"]
    assert doc1_id is not None
    assert doc1_data["duplicate_flag"] is False

    # Document 2: Near-duplicate of Document 1
    doc2_payload = {
        "title": "E2E Duplicate Document",
        "url": "http://e2esite.com/duplicate",
        "source": "e2e_collector",
        "raw_text": "<html>\n<body>\nThis is a pristine document containing detailed data engineering instructions.\nSponsored advertisement.\nTerms of Service\n</body>\n</html>"
    }
    
    res2 = await client.post("/api/v1/documents/", json=doc2_payload)
    assert res2.status_code == 201
    doc2_data = res2.json()
    doc2_id = doc2_data["id"]

    # ====================================================
    # 2. Clean & Normalize Documents
    # ====================================================
    # Clean Document 1
    clean_res1 = await client.post(f"/api/v1/clean/{doc1_id}")
    assert clean_res1.status_code == 200
    cleaned_doc1 = clean_res1.json()
    
    # Assert boilerplate, ads, and HTML elements are stripped
    assert "<html>" not in cleaned_doc1["cleaned_text"]
    assert "Sponsored advertisement" not in cleaned_doc1["cleaned_text"]
    assert "Terms of Service" not in cleaned_doc1["cleaned_text"]
    assert "pristine document containing detailed data" in cleaned_doc1["cleaned_text"]

    # Clean Document 2
    clean_res2 = await client.post(f"/api/v1/clean/{doc2_id}")
    assert clean_res2.status_code == 200

    # ====================================================
    # 3. Deduplication (SHA-256 and SimHash)
    # ====================================================
    # Trigger deduplication run
    dedup_res = await client.post("/api/v1/dedup/run", json={"threshold": 15})
    assert dedup_res.status_code == 200
    
    # Force SQLAlchemy to expire the cached objects in the session so that
    # client.get calls correctly fetch the modified duplicate states from the database.
    db_session.expire_all()

    # Retrieve Document 2 to verify duplicate flag and parent lineage link
    status_res2 = await client.get(f"/api/v1/documents/{doc2_id}")
    assert status_res2.status_code == 200
    updated_doc2 = status_res2.json()
    
    assert updated_doc2["duplicate_flag"] is True
    assert updated_doc2["metadata"]["duplicate_type"] in ["exact", "near"]
    assert updated_doc2["metadata"]["duplicate_of"] == str(doc1_id)

    # ====================================================
    # 4. Quality Heuristics Evaluation
    # ====================================================
    # Grade Document 1
    quality_res = await client.post(f"/api/v1/quality/{doc1_id}")
    assert quality_res.status_code == 200
    graded_doc1 = quality_res.json()
    assert graded_doc1["quality_score"] > 10.0 # Standard length and content gives decent score

    # ====================================================
    # 5. Compile Analytics
    # ====================================================
    db_session.expire_all()
    analytics_res = await client.get("/api/v1/analytics/overview")
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()
    assert analytics["total_documents"] == 2
    assert analytics["duplicate_documents"] == 1

    # ====================================================
    # 6. Filtered Dataset Export
    # ====================================================
    # Export JSON excluding duplicates
    export_res = await client.get("/api/v1/export/export?format_type=json&exclude_duplicates=true")
    assert export_res.status_code == 200
    export_json = export_res.json()
    
    # Assert only the unique master document is exported
    assert len(export_json) == 1
    assert export_json[0]["id"] == str(doc1_id)
    assert export_json[0]["duplicate_flag"] is False
