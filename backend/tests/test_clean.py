import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.clean.service import TextCleaner
from app.features.documents.models import Document
from app.features.documents.crud import create_document
from app.features.documents.schemas import DocumentCreate

def test_cleaner_html_and_unescape():
    """Verify HTML structural elements are removed along with tag stripping and entity unescaping."""
    cleaner = TextCleaner()
    html_input = (
        "<html>"
        "<header><nav><a href='/'>Home</a></nav></header>"
        "<body>"
        "<h1>Hello World</h1>"
        "<p>This is a paragraph with a <a href='#'>link</a> &amp; some entities like &ldquo;smart quotes&rdquo;.</p>"
        "<script>console.log('ignored');</script>"
        "<footer>Copyright &copy; 2026</footer>"
        "</body>"
        "</html>"
    )
    result = cleaner.clean_document(html_input)
    # Tag structural text (nav, footer, script) should be skipped
    assert "Home" not in result
    assert "Copyright" not in result
    assert "ignored" not in result
    
    # Core content should be preserved
    assert "Hello World" in result
    # HTML tag tags should be stripped
    assert "<h1>" not in result
    # Entities should be decoded and normalized
    assert "link & some entities" in result
    assert '"smart quotes"' in result

def test_cleaner_encoding_repaired():
    """Verify double-encoded UTF-8 strings are repaired."""
    cleaner = TextCleaner()
    # 'caf\u00e9' is 'café'. 'Caf\u00c3\u00a9' is 'CafÃ©' (double-encoded 'Café')
    dirty_text = "The caf\u00e9 name is Caf\u00c3\u00a9 de Flore."
    result = cleaner.clean_document(dirty_text)
    assert "Caf\u00e9 de Flore" in result

def test_cleaner_unicode_and_punctuation():
    """Verify Unicode character flattening and standard ASCII punctuation replacement."""
    cleaner = TextCleaner()
    # em-dash (\u2014), en-dash (\u2013), smart double quotes (\u201c, \u201d)
    dirty_text = "Smart quotes \u2014 like \u201cthis\u201d \u2013 and primes `like` that."
    result = cleaner.clean_document(dirty_text)
    assert "Smart quotes - like \"this\" - and primes 'like' that." in result
    
    # NFKC ligature flattening for '\ufb01' (ﬁ)
    ligature_text = "The \ufb01ne line."
    result_lig = cleaner.clean_document(ligature_text)
    assert "The fine line." in result_lig

def test_cleaner_boilerplate_and_ad_filters():
    """Verify lines containing boilerplate links, ads, and cookie policies are removed."""
    cleaner = TextCleaner()
    raw_content = (
        "This website uses cookies to ensure you get the best experience.\n"
        "Please read our cookie policy.\n"
        "Main Article Header\n"
        "This is the actual page content of our main article.\n"
        "ADVERTISEMENT\n"
        "Buy now for a special discount!\n"
        "Home | About | Blog | Contact Us\n"
        "Follow us on Twitter\n"
        "Sign in or register to comment."
    )
    result = cleaner.clean_document(raw_content)
    
    # Disclaimers and ads should be stripped
    assert "uses cookies" not in result
    assert "ADVERTISEMENT" not in result
    assert "Buy now" not in result
    assert "Home | About" not in result
    assert "Sign in" not in result
    
    # Important content should be kept
    assert "Main Article Header" in result
    assert "This is the actual page content" in result

@pytest.mark.asyncio
async def test_clean_text_endpoint(client: AsyncClient):
    """Test the raw text cleaning API endpoint."""
    payload = {
        "text": "<html><body>Hello &ldquo;World&rdquo;!</body></html>"
    }
    response = await client.post("/api/v1/clean/text", json=payload)
    assert response.status_code == 200
    assert response.json()["cleaned_text"] == 'Hello "World"!'

@pytest.mark.asyncio
async def test_clean_document_by_id_endpoint(client: AsyncClient, db_session: AsyncSession):
    """Test cleaning a stored document updates database state but preserves original raw text."""
    doc_in = DocumentCreate(
        source="test_cleaner",
        raw_text="<html><body>Original Raw <p>Content</p></body></html>",
        quality_score=0.5
    )
    db_doc = await create_document(db_session, doc_in)
    
    response = await client.post(f"/api/v1/clean/{db_doc.id}")
    assert response.status_code == 200
    res_data = response.json()
    
    # Cleaned text should be set
    assert res_data["cleaned_text"] == "Original Raw Content"
    
    # Verify in DB
    stmt = select(Document).where(Document.id == db_doc.id)
    res = await db_session.execute(stmt)
    updated_doc = res.scalar_one()
    
    assert updated_doc.cleaned_text == "Original Raw Content"
    # Raw text must remain completely unchanged!
    assert updated_doc.raw_text == "<html><body>Original Raw <p>Content</p></body></html>"

@pytest.mark.asyncio
async def test_clean_batch_run_endpoint(client: AsyncClient, db_session: AsyncSession):
    """Test cleaning all un-cleaned documents in a batch."""
    # Insert two raw documents
    doc_1 = await create_document(db_session, DocumentCreate(
        source="batch_1",
        raw_text="<p>Document 1 text</p>"
    ))
    doc_2 = await create_document(db_session, DocumentCreate(
        source="batch_2",
        raw_text="<div>Document 2 text</div>"
    ))
    
    # Run batch clean endpoint
    response = await client.post("/api/v1/clean/batch/run", json={"limit": 10})
    assert response.status_code == 200
    assert response.json()["processed_count"] >= 2
    
    # Verify both are cleaned
    stmt = select(Document).where(Document.id.in_([doc_1.id, doc_2.id]))
    res = await db_session.execute(stmt)
    updated_docs = res.scalars().all()
    
    for doc in updated_docs:
        assert doc.cleaned_text is not None
        assert "text" in doc.cleaned_text
        assert "<p>" not in doc.cleaned_text
        assert "<div>" not in doc.cleaned_text
