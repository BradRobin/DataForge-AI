from datetime import datetime, timedelta
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.documents.models import Document
from app.features.documents.crud import create_document
from app.features.documents.schemas import DocumentCreate

@pytest_asyncio.fixture(autouse=True)
async def clean_db(db_session: AsyncSession):
    """Ensure a clean database state for each test by deleting all documents."""
    await db_session.execute(Document.__table__.delete())
    await db_session.commit()

@pytest.mark.asyncio
async def test_analytics_overview_endpoint(client: AsyncClient, db_session: AsyncSession):
    """Test that the analytics overview endpoint returns valid JSON with correct calculations."""
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    # 1. Insert 3 documents
    doc1 = Document(
        source="web_news",
        raw_text="DataForge represents a robust data engineering framework.", # 8 words
        language="en",
        quality_score=90.0,
        collection_timestamp=today,
        duplicate_flag=False,
        hash="hash1"
    )
    
    doc2 = Document(
        source="web_news",
        raw_text="This is secondary data.", # 4 words
        language="en",
        quality_score=50.0,
        collection_timestamp=today,
        duplicate_flag=False,
        hash="hash2"
    )
    
    doc3 = Document(
        source="web_blog",
        raw_text="DataForge represents a robust data engineering framework.", # exact duplicate of doc1
        language="fr",
        quality_score=90.0,
        collection_timestamp=yesterday,
        duplicate_flag=True, # Flagged as duplicate
        hash="hash1"
    )
    
    db_session.add_all([doc1, doc2, doc3])
    await db_session.commit()
    
    # 2. Call overview endpoint
    response = await client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    analytics = response.json()
    
    # 3. Assert correct counts
    assert analytics["total_documents"] == 3
    assert analytics["unique_documents"] == 2
    assert analytics["duplicate_documents"] == 1
    assert analytics["duplicate_rate"] == 0.3333
    
    # 4. Assert length stats
    # Word count list = [7, 4, 7]
    # Mean = 18 / 3 = 6.0
    # Median = 7.0
    assert analytics["length_stats"]["avg_word_count"] == 6.0
    assert analytics["length_stats"]["median_word_count"] == 7.0
    
    # 5. Assert distributions
    assert analytics["language_distribution"] == {"en": 2, "fr": 1}
    assert analytics["source_distribution"] == {"web_news": 2, "web_blog": 1}
    
    # 6. Assert quality score stats
    # Scores = [90.0, 50.0, 90.0]
    # Mean = 230 / 3 = 76.67
    # Median = 90.0, Min = 50.0, Max = 90.0
    assert analytics["quality_stats"]["avg_score"] == 76.67
    assert analytics["quality_stats"]["median_score"] == 90.0
    assert analytics["quality_stats"]["min_score"] == 50.0
    assert analytics["quality_stats"]["max_score"] == 90.0
    
    # Buckets: one 50.0 falls in "41-60", two 90.0 fall in "81-100"
    assert analytics["quality_stats"]["buckets"]["41-60"] == 1
    assert analytics["quality_stats"]["buckets"]["81-100"] == 2
    assert analytics["quality_stats"]["buckets"]["0-20"] == 0
    
    # 7. Assert top keywords
    # Exclude stop words from unique docs (doc1 and doc2):
    # doc1 words: ["dataforge", "represents", "robust", "data", "engineering", "framework"]
    # doc2 words: ["secondary", "data"]
    # Top keyword should be "data" (frequency 2)
    top_keyword = analytics["top_keywords"][0]
    assert top_keyword["word"] == "data"
    assert top_keyword["frequency"] == 2
    
    # 8. Assert timeline
    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    assert analytics["collection_timeline"][today_str] == 2
    assert analytics["collection_timeline"][yesterday_str] == 1
