import asyncio
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.documents.models import Document
from app.features.documents.crud import create_document
from app.features.documents.schemas import DocumentCreate
from app.features.ingest.base import BaseCollector

logger = logging.getLogger("dataforge.ingest.http")

class HttpCollector(BaseCollector):
    """
    Asynchronous Web Scraper Collector for DataForge AI.
    Complies with robots.txt, respects crawl-delays, prevents duplicate URLs, and retries with backoff.
    """
    def __init__(self, user_agent: str = "DataForgeBot", default_delay: float = 1.0):
        self.user_agent = user_agent
        self.default_delay = default_delay
        self.robots_cache: Dict[str, RobotFileParser] = {}
        self.last_crawl_time: Dict[str, float] = {}

    @property
    def name(self) -> str:
        return "http_collector"

    def _strip_html(self, html: str) -> str:
        """Strip HTML tags and normalize whitespace."""
        # Remove script and style elements
        html = re.sub(r'<(script|style)\b[^>]*>([\s\S]*?)</\1>', '', html)
        # Remove HTML comments
        html = re.sub(r'<!--[\s\S]*?-->', '', html)
        # Remove tags
        text = re.sub(r'<[^>]+>', ' ', html)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _extract_title(self, html: str) -> Optional[str]:
        """Extract title from HTML text."""
        match = re.search(r'<title\b[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if match:
            # strip any HTML tag if inside title and return
            title_text = re.sub(r'<[^>]+>', '', match.group(1))
            return re.sub(r'\s+', ' ', title_text).strip()
        return None

    async def _get_robots_parser(self, client: httpx.AsyncClient, domain_url: str) -> RobotFileParser:
        """Fetch and cache robots.txt for the domain."""
        parsed = urlparse(domain_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        if domain in self.robots_cache:
            return self.robots_cache[domain]

        robots_url = f"{domain}/robots.txt"
        parser = RobotFileParser()
        logger.info(f"Fetching robots.txt from: {robots_url}")
        
        try:
            # Retry robots.txt fetch once
            response = await client.get(robots_url, timeout=5.0)
            if response.status_code == 200:
                parser.parse(response.text.splitlines())
            else:
                parser.parse([]) # Allow all if not found (404)
        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt for {domain}: {e}. Defaulting to allow all.")
            parser.parse([]) # Allow all on failure
            
        self.robots_cache[domain] = parser
        return parser

    async def _is_allowed(self, client: httpx.AsyncClient, url: str) -> bool:
        """Check if URL is allowed under robots.txt."""
        try:
            parser = await self._get_robots_parser(client, url)
            return parser.can_fetch(self.user_agent, url)
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {e}. Allowing.")
            return True

    def _get_crawl_delay(self, url: str) -> float:
        """Retrieve robots.txt crawl-delay or return default."""
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        parser = self.robots_cache.get(domain)
        if parser:
            try:
                delay = parser.crawl_delay(self.user_agent)
                if delay:
                    return float(delay)
            except Exception:
                pass
        return self.default_delay

    async def _wait_for_rate_limit(self, url: str):
        """Enforce per-domain rate limiting / crawl delay."""
        parsed = urlparse(url)
        domain = parsed.netloc
        delay = self._get_crawl_delay(url)
        
        now = time.time()
        last_time = self.last_crawl_time.get(domain, 0.0)
        elapsed = now - last_time
        
        if elapsed < delay:
            sleep_time = delay - elapsed
            logger.info(f"Rate limiting domain '{domain}': sleeping for {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)
            
        self.last_crawl_time[domain] = time.time()

    async def fetch_with_retry(self, client: httpx.AsyncClient, url: str, retries: int = 3) -> httpx.Response:
        """Fetch URL with exponential backoff on retryable HTTP errors or network timeouts."""
        delay = 1.0
        for attempt in range(retries + 1):
            try:
                response = await client.get(url, timeout=10.0)
                if response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"Server Error {response.status_code}", 
                        request=response.request, 
                        response=response
                    )
                return response
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                if attempt == retries:
                    logger.error(f"All retry attempts failed for {url}: {e}")
                    raise e
                logger.warning(f"Error fetching {url}: {e}. Retrying {attempt+1}/{retries} in {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2.0
        raise Exception(f"Failed to fetch {url}")

    async def collect(self, db: AsyncSession, **kwargs: Any) -> List[Document]:
        """
        Collect documents from seed URLs.
        Params:
          - urls: List[str] (required)
          - retries: int (default 3)
        """
        urls: List[str] = kwargs.get("urls", [])
        retries: int = kwargs.get("retries", 3)
        
        collected_documents: List[Document] = []
        
        async with httpx.AsyncClient(headers={"User-Agent": self.user_agent}) as client:
            for url in urls:
                try:
                    # 1. Duplicate URL prevention: Check if URL already crawled in database
                    stmt = select(Document).where(Document.url == url).limit(1)
                    res = await db.execute(stmt)
                    if res.scalar_one_or_none() is not None:
                        logger.info(f"Duplicate URL skipped (already exists in database): {url}")
                        continue

                    # 2. robots.txt awareness check
                    allowed = await self._is_allowed(client, url)
                    if not allowed:
                        logger.warning(f"Robots.txt disallowed crawling of: {url}")
                        continue

                    # 3. Rate limiting / crawl delay sleep
                    await self._wait_for_rate_limit(url)

                    # 4. Fetch with retries
                    logger.info(f"Crawling URL: {url}")
                    response = await self.fetch_with_retry(client, url, retries=retries)
                    
                    if response.status_code != 200:
                        logger.error(f"Skipping url {url}: HTTP status {response.status_code}")
                        continue

                    # 5. Extract and parse document text
                    raw_content = response.text
                    title = self._extract_title(raw_content) or f"Crawled Document - {urlparse(url).netloc}"
                    cleaned_text = self._strip_html(raw_content)
                    
                    # 6. Save in database
                    doc_create = DocumentCreate(
                        source=self.name,
                        url=url,
                        title=title,
                        raw_text=raw_content,
                        cleaned_text=cleaned_text,
                        metadata={
                            "crawled_at": datetime.utcnow().isoformat(),
                            "content_type": response.headers.get("content-type", "")
                        },
                        quality_score=1.0
                    )
                    
                    db_doc = await create_document(db, doc_create)
                    collected_documents.append(db_doc)
                    logger.info(f"Successfully collected document from: {url} (ID: {db_doc.id})")
                    
                except Exception as e:
                    logger.error(f"Error processing URL {url}: {e}", exc_info=True)
                    # Proceed with remaining URLs in case of individual failures
                    continue
                    
        return collected_documents
