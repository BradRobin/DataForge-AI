import csv
import io
import pytest
import pytest_asyncio
import pandas as pd
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.documents.models import Document

@pytest_asyncio.fixture(autouse=True)
async def clean_db(db_session: AsyncSession):
    """Ensure a clean database state for each test by deleting all documents."""
    await db_session.execute(Document.__table__.delete())
    await db_session.commit()

@pytest.mark.asyncio
async def test_dataset_export_json(client: AsyncClient, db_session: AsyncSession):
    """Test exporting dataset to JSON format."""
    d1 = Document(source="src1", raw_text="text1", language="en", quality_score=90.0, duplicate_flag=False, hash="h1")
    d2 = Document(source="src2", raw_text="text2", language="fr", quality_score=40.0, duplicate_flag=True, hash="h2")
    db_session.add_all([d1, d2])
    await db_session.commit()
    
    response = await client.get("/api/v1/export?format=json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    
    data = response.json()
    assert len(data) == 2
    assert data[0]["source"] == "src1"
    assert data[1]["duplicate_flag"] is True

@pytest.mark.asyncio
async def test_dataset_export_csv(client: AsyncClient, db_session: AsyncSession):
    """Test exporting dataset to CSV format."""
    d1 = Document(source="src1", raw_text="text1", language="en", quality_score=90.0, duplicate_flag=False, hash="h1")
    db_session.add(d1)
    await db_session.commit()
    
    response = await client.get("/api/v1/export?format=csv")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    
    csv_bytes = response.content
    csv_str = csv_bytes.decode("utf-8")
    
    f = io.StringIO(csv_str)
    reader = csv.DictReader(f)
    rows = list(reader)
    
    assert len(rows) == 1
    assert rows[0]["source"] == "src1"
    assert rows[0]["raw_text"] == "text1"
    assert float(rows[0]["quality_score"]) == 90.0

@pytest.mark.asyncio
async def test_dataset_export_parquet(client: AsyncClient, db_session: AsyncSession):
    """Test exporting dataset to Parquet format and loading it into Pandas."""
    d1 = Document(source="src1", raw_text="text1", language="en", quality_score=90.0, duplicate_flag=False, hash="h1")
    d2 = Document(source="src2", raw_text="text2", language="fr", quality_score=40.0, duplicate_flag=True, hash="h2")
    db_session.add_all([d1, d2])
    await db_session.commit()
    
    response = await client.get("/api/v1/export?format=parquet")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    
    parquet_bytes = response.content
    buffer = io.BytesIO(parquet_bytes)
    
    # Load into Pandas DataFrame to verify Parquet format validity
    df = pd.read_parquet(buffer)
    
    assert len(df) == 2
    assert list(df["source"]) == ["src1", "src2"]
    assert list(df["language"]) == ["en", "fr"]

@pytest.mark.asyncio
async def test_dataset_export_filters(client: AsyncClient, db_session: AsyncSession):
    """Test that all dynamic filters are correctly applied during export."""
    d1 = Document(source="news", raw_text="text1", language="en", quality_score=90.0, duplicate_flag=False, hash="h1")
    d2 = Document(source="blog", raw_text="text2", language="en", quality_score=50.0, duplicate_flag=False, hash="h2")
    d3 = Document(source="news", raw_text="text3", language="fr", quality_score=95.0, duplicate_flag=True, hash="h3")
    
    db_session.add_all([d1, d2, d3])
    await db_session.commit()
    
    # 1. Filter by source
    res = await client.get("/api/v1/export?format=json&source=news")
    assert res.status_code == 200
    assert len(res.json()) == 2
    
    # 2. Filter by language
    res = await client.get("/api/v1/export?format=json&language=fr")
    assert res.status_code == 200
    assert len(res.json()) == 1
    
    # 3. Filter by quality threshold
    res = await client.get("/api/v1/export?format=json&min_quality=80.0")
    assert res.status_code == 200
    assert len(res.json()) == 2 # d1 and d3
    
    # 4. Exclude duplicates
    res = await client.get("/api/v1/export?format=json&exclude_duplicates=true")
    assert res.status_code == 200
    assert len(res.json()) == 2 # d1 and d2
    
    # 5. Combined filters
    res = await client.get("/api/v1/export?format=json&source=news&exclude_duplicates=true")
    assert res.status_code == 200
    assert len(res.json()) == 1 # only d1
    
    # 6. Expect 400 Bad Request if no documents match
    res = await client.get("/api/v1/export?format=json&language=de")
    assert res.status_code == 400
    assert "No documents found matching the specified filters" in res.json()["detail"]
