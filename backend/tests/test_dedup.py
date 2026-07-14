import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.documents.models import Document
from app.features.documents.crud import create_document
from app.features.documents.schemas import DocumentCreate
from app.features.dedup.simhash import compute_simhash, hamming_distance

@pytest_asyncio.fixture(autouse=True)
async def clean_db(db_session: AsyncSession):
    """Ensure a clean database state for each test by deleting all documents."""
    await db_session.execute(Document.__table__.delete())
    await db_session.commit()

def test_simhash_similarity():
    """Verify SimHash and Hamming distance behavior on identical, similar, and different texts."""
    text_1 = "The quick brown fox jumps over the lazy dog to find some food."
    text_2 = "The quick brown fox jumps over the lazy dog to find some food." # identical
    text_3 = "The quick brown fox jumps over the lazy cat to find some food." # near duplicate (dog -> cat)
    text_4 = "Python is a high-level programming language used widely for artificial intelligence." # different
    
    sh1 = compute_simhash(text_1)
    sh2 = compute_simhash(text_2)
    sh3 = compute_simhash(text_3)
    sh4 = compute_simhash(text_4)
    
    # Identical texts must have Hamming distance 0
    assert hamming_distance(sh1, sh2) == 0
    
    # Highly similar texts should have low Hamming distance (<= 6 for character 3-grams on short text)
    dist_near = hamming_distance(sh1, sh3)
    assert dist_near <= 6
    assert dist_near > 0
    
    # Completely different texts should have high Hamming distance
    dist_diff = hamming_distance(sh1, sh4)
    assert dist_diff > 10

@pytest.mark.asyncio
async def test_exact_duplicate_detection(client: AsyncClient, db_session: AsyncSession):
    """Test that exact duplicates are flagged with duplicate_type='exact'."""
    # Insert two documents with identical raw text and hashes
    doc1_in = DocumentCreate(
        source="test_dedup",
        raw_text="This is a unique sentence for exact duplicate test.",
        hash="exacthash123"
    )
    doc2_in = DocumentCreate(
        source="test_dedup",
        raw_text="This is a unique sentence for exact duplicate test.",
        hash="exacthash123"
    )
    
    d1 = await create_document(db_session, doc1_in)
    d2 = await create_document(db_session, doc2_in)
    
    # Manually reset duplicate flags to false to test the deduplication job run
    d1.duplicate_flag = False
    d2.duplicate_flag = False
    db_session.add(d1)
    db_session.add(d2)
    await db_session.commit()
    
    # Run deduplication
    response = await client.post("/api/v1/dedup/run", json={"threshold": 12})
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["exact_duplicates_found"] == 1
    assert res_data["near_duplicates_found"] == 0
    assert res_data["total_duplicates"] == 1
    
    # Verify in DB
    # First document should remain unique
    stmt1 = select(Document).where(Document.id == d1.id)
    res1 = await db_session.execute(stmt1)
    doc1 = res1.scalar_one()
    assert doc1.duplicate_flag is False
    
    # Second document should be flagged as exact duplicate of the first
    stmt2 = select(Document).where(Document.id == d2.id)
    res2 = await db_session.execute(stmt2)
    doc2 = res2.scalar_one()
    assert doc2.duplicate_flag is True
    assert doc2.metadata_["duplicate_type"] == "exact"
    assert doc2.metadata_["duplicate_of"] == str(d1.id)

@pytest.mark.asyncio
async def test_near_duplicate_detection(client: AsyncClient, db_session: AsyncSession):
    """Test that near-duplicates are flagged with duplicate_type='near'."""
    # Insert two highly similar documents
    doc1_in = DocumentCreate(
        source="test_dedup",
        raw_text="DataForge AI is a high-throughput data engineering pipeline for cleaning text datasets.",
        hash="hash_a"
    )
    doc2_in = DocumentCreate(
        source="test_dedup",
        raw_text="DataForge AI is a high-throughput data processing pipeline for cleaning text datasets.", # processing instead of engineering
        hash="hash_b"
    )
    
    d1 = await create_document(db_session, doc1_in)
    d2 = await create_document(db_session, doc2_in)
    
    # Reset duplicate flags
    d1.duplicate_flag = False
    d2.duplicate_flag = False
    db_session.add(d1)
    db_session.add(d2)
    await db_session.commit()
    
    # Run deduplication with threshold 12
    response = await client.post("/api/v1/dedup/run", json={"threshold": 12})
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["near_duplicates_found"] == 1
    assert res_data["total_duplicates"] == 1
    
    # Verify in DB
    stmt2 = select(Document).where(Document.id == d2.id)
    res2 = await db_session.execute(stmt2)
    doc2 = res2.scalar_one()
    assert doc2.duplicate_flag is True
    assert doc2.metadata_["duplicate_type"] == "near"
    assert doc2.metadata_["duplicate_of"] == str(d1.id)
    assert "similarity_distance" in doc2.metadata_
    assert doc2.metadata_["similarity_distance"] <= 12

@pytest.mark.asyncio
async def test_false_positive_prevention(client: AsyncClient, db_session: AsyncSession):
    """Test that completely different documents are not flagged as duplicates."""
    doc1_in = DocumentCreate(
        source="test_dedup",
        raw_text="The solar system consists of the Sun and the objects that orbit it.",
        hash="hash_sun"
    )
    doc2_in = DocumentCreate(
        source="test_dedup",
        raw_text="FastAPI is a modern web framework for building APIs with Python.",
        hash="hash_fastapi"
    )
    
    d1 = await create_document(db_session, doc1_in)
    d2 = await create_document(db_session, doc2_in)
    
    d1.duplicate_flag = False
    d2.duplicate_flag = False
    db_session.add(d1)
    db_session.add(d2)
    await db_session.commit()
    
    response = await client.post("/api/v1/dedup/run", json={"threshold": 12})
    assert response.status_code == 200
    assert response.json()["total_duplicates"] == 0
    
    # Verify both remain unique
    stmt = select(Document).where(Document.id.in_([d1.id, d2.id]))
    res = await db_session.execute(stmt)
    docs = res.scalars().all()
    for doc in docs:
        assert doc.duplicate_flag is False

@pytest.mark.asyncio
async def test_dedup_stats(client: AsyncClient, db_session: AsyncSession):
    """Test duplicate statistics calculations."""
    # Ensure database starts clean for this test
    # We can delete all documents
    await db_session.execute(Document.__table__.delete())
    await db_session.commit()
    
    # Insert 3 documents: 1 original, 1 exact duplicate, 1 near duplicate
    d1 = await create_document(db_session, DocumentCreate(
        source="stats_test",
        raw_text="Unique text for stats test original doc.",
        hash="unique1"
    ))
    
    d2 = await create_document(db_session, DocumentCreate(
        source="stats_test",
        raw_text="Unique text for stats test original doc.", # exact
        hash="unique1"
    ))
    
    d3 = await create_document(db_session, DocumentCreate(
        source="stats_test",
        raw_text="Unique text for stats test near doc.", # near
        hash="unique2"
    ))
    
    # Reset flags and run dedup
    d1.duplicate_flag = False
    d2.duplicate_flag = False
    d3.duplicate_flag = False
    db_session.add_all([d1, d2, d3])
    await db_session.commit()
    
    # Run
    await client.post("/api/v1/dedup/run", json={"threshold": 12})
    
    # Query stats
    response = await client.get("/api/v1/dedup/stats")
    assert response.status_code == 200
    stats = response.json()
    
    assert stats["total_documents"] == 3
    assert stats["unique_documents"] == 1
    assert stats["exact_duplicates"] == 1
    assert stats["near_duplicates"] == 1
    assert stats["total_duplicates"] == 2
    assert stats["duplicate_ratio"] == 0.6667
