import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.documents.models import Document
from app.features.documents.crud import create_document
from app.features.documents.schemas import DocumentCreate
from app.features.quality.service import quality_service

@pytest_asyncio.fixture(autouse=True)
async def clean_db(db_session: AsyncSession):
    """Ensure a clean database state for each test by deleting all documents."""
    await db_session.execute(Document.__table__.delete())
    await db_session.commit()

def test_quality_grading_high_vs_poor():
    """Verify that the grading engine scores high-quality English text highly and poor-quality text lowly."""
    # 1. High-quality standard English text
    high_quality_text = (
        "The Genotype-Tissue Expression (GTEx) project is a collaborative effort "
        "designed to study human gene expression and regulation across multiple "
        "non-diseased donor tissues. By analyzing RNA-sequence data from hundreds "
        "of individuals, researchers can identify genetic variations that correlate "
        "with changes in gene expression levels. This database provides crucial "
        "insights into how genetic variation influences tissue-specific transcriptomes "
        "and potentially leads to disease susceptibility in different populations."
    )
    res_high = quality_service.evaluate_text(high_quality_text)
    assert res_high["quality_score"] >= 80.0
    
    # 2. Poor-quality: Very short text
    short_text = "Short text."
    res_short = quality_service.evaluate_text(short_text)
    assert res_short["quality_score"] < 40.0
    
    # 3. Poor-quality: Repetitive word stuffing
    rep_text = "the the the the the the the the the the the the the the the the the the the the the the the the"
    res_rep = quality_service.evaluate_text(rep_text)
    assert res_rep["quality_score"] < 40.0
    
    # 4. Poor-quality: Code snippet / mathematical markup (high noise)
    code_text = (
        "if (x === 10) { console.log('value is ten'); } else { return false; }; "
        "function compute(a, b) { return a * b / (a - b); }; [0, 1, 2, 3, 4].map(x => x ** 2);"
    )
    res_code = quality_service.evaluate_text(code_text)
    assert res_code["quality_score"] < 50.0
    
    # 5. Poor-quality: Gibberish (vowelless words)
    gibberish_text = "qwrtpsdfghjklzxcvbnm pyfgcrsv dhtnls"
    res_gib = quality_service.evaluate_text(gibberish_text)
    assert res_gib["quality_score"] < 40.0

@pytest.mark.asyncio
async def test_quality_text_endpoint(client: AsyncClient):
    """Test the raw text grading API endpoint."""
    payload = {
        "text": "This is a standard English sentence with good readability and formatting."
    }
    response = await client.post("/api/v1/quality/text", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert "quality_score" in res_data
    assert "sub_scores" in res_data
    assert "metrics" in res_data

@pytest.mark.asyncio
async def test_quality_document_by_id_endpoint(client: AsyncClient, db_session: AsyncSession):
    """Test that evaluating a stored document saves the quality score to the database."""
    doc_in = DocumentCreate(
        source="test_quality",
        raw_text="The Genotype-Tissue Expression project is designed to study human gene expression."
    )
    db_doc = await create_document(db_session, doc_in)
    
    # Call endpoint
    response = await client.post(f"/api/v1/quality/{db_doc.id}")
    assert response.status_code == 200
    res_data = response.json()
    
    assert res_data["quality_score"] is not None
    assert res_data["quality_score"] > 0.0
    
    # Verify in DB
    stmt = select(Document).where(Document.id == db_doc.id)
    res = await db_session.execute(stmt)
    updated_doc = res.scalar_one()
    
    assert updated_doc.quality_score == res_data["quality_score"]
    assert "quality_report" in updated_doc.metadata_
    assert "sub_scores" in updated_doc.metadata_["quality_report"]

@pytest.mark.asyncio
async def test_quality_batch_run_endpoint(client: AsyncClient, db_session: AsyncSession):
    """Test batch quality evaluation of unscored documents."""
    # Insert two unscored documents
    doc1 = await create_document(db_session, DocumentCreate(
        source="batch_q1",
        raw_text="This is document number one for batch evaluation."
    ))
    doc2 = await create_document(db_session, DocumentCreate(
        source="batch_q2",
        raw_text="This is document number two for batch evaluation."
    ))
    
    # Ensure they have None quality score
    doc1.quality_score = None
    doc2.quality_score = None
    db_session.add_all([doc1, doc2])
    await db_session.commit()
    
    # Run batch evaluation endpoint
    response = await client.post("/api/v1/quality/batch/run", json={"limit": 10})
    assert response.status_code == 200
    assert response.json()["processed_count"] >= 2
    
    # Verify both documents are scored
    stmt = select(Document).where(Document.id.in_([doc1.id, doc2.id]))
    res = await db_session.execute(stmt)
    docs = res.scalars().all()
    for doc in docs:
        assert doc.quality_score is not None
        assert doc.quality_score > 0.0
