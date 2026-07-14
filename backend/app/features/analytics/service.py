import collections
import logging
import re
import statistics
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.documents.models import Document

logger = logging.getLogger("dataforge.analytics.service")

class AnalyticsService:
    """
    Analytics Engine for generating detailed statistics and metrics about the dataset.
    """
    def __init__(self) -> None:
        self.stop_words = {
            "the", "and", "of", "to", "in", "is", "that", "it", "on", "for",
            "as", "with", "was", "at", "by", "an", "be", "this", "are", "from",
            "or", "have", "you", "but", "not", "he", "she", "they", "we", "his",
            "her", "its", "their", "my", "your", "our", "him", "them", "us"
        }

    async def get_dataset_analytics(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Generate dataset-wide analytics, distributions, quality summaries, timelines, and common keywords.
        Returns a structured dictionary of metrics.
        """
        stmt = select(Document)
        result = await db.execute(stmt)
        documents = result.scalars().all()
        
        total_docs = len(documents)
        
        if total_docs == 0:
            return {
                "total_documents": 0,
                "unique_documents": 0,
                "duplicate_documents": 0,
                "duplicate_rate": 0.0,
                "length_stats": {
                    "avg_word_count": 0.0,
                    "median_word_count": 0.0,
                    "avg_char_count": 0.0,
                    "median_char_count": 0.0
                },
                "language_distribution": {},
                "source_distribution": {},
                "quality_stats": {
                    "avg_score": 0.0,
                    "median_score": 0.0,
                    "min_score": 0.0,
                    "max_score": 0.0,
                    "buckets": {
                        "0-20": 0,
                        "21-40": 0,
                        "41-60": 0,
                        "61-80": 0,
                        "81-100": 0
                    }
                },
                "top_keywords": [],
                "collection_timeline": {}
            }

        # 1. Duplicate Calculations
        duplicate_docs = sum(1 for d in documents if d.duplicate_flag)
        unique_docs = total_docs - duplicate_docs
        duplicate_rate = round(duplicate_docs / total_docs, 4)

        # 2. Document Length Stats (Words and Characters)
        word_counts: List[int] = []
        char_counts: List[int] = []
        
        all_words: List[str] = []
        
        for doc in documents:
            text = doc.cleaned_text if doc.cleaned_text else doc.raw_text
            text = text if text else ""
            
            # Words
            words = re.findall(r'\w+', text.lower())
            word_counts.append(len(words))
            char_counts.append(len(text))
            
            # Aggregate words for keyword search (limit to unique/original documents to prevent skew)
            if not doc.duplicate_flag:
                all_words.extend([w for w in words if w not in self.stop_words and len(w) > 2])

        avg_word_count = round(statistics.mean(word_counts), 2)
        median_word_count = round(statistics.median(word_counts), 2)
        avg_char_count = round(statistics.mean(char_counts), 2)
        median_char_count = round(statistics.median(char_counts), 2)

        # 3. Distributions (Language and Ingestion Source)
        languages = [d.language if d.language else "unknown" for d in documents]
        lang_dist = dict(collections.Counter(languages))
        
        sources = [d.source if d.source else "unknown" for d in documents]
        source_dist = dict(collections.Counter(sources))

        # 4. Quality Score Distribution
        quality_scores = [d.quality_score for d in documents if d.quality_score is not None]
        
        # Buckets initialization
        buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
        
        if quality_scores:
            avg_quality = round(statistics.mean(quality_scores), 2)
            median_quality = round(statistics.median(quality_scores), 2)
            min_quality = round(min(quality_scores), 2)
            max_quality = round(max(quality_scores), 2)
            
            # Distribute into buckets
            for score in quality_scores:
                if score <= 20.0:
                    buckets["0-20"] += 1
                elif score <= 40.0:
                    buckets["21-40"] += 1
                elif score <= 60.0:
                    buckets["41-60"] += 1
                elif score <= 80.0:
                    buckets["61-80"] += 1
                else:
                    buckets["81-100"] += 1
        else:
            avg_quality = 0.0
            median_quality = 0.0
            min_quality = 0.0
            max_quality = 0.0

        # 5. Top Keywords (frequencies of non-stop words)
        word_counter = collections.Counter(all_words)
        top_keywords = [{"word": word, "frequency": count} for word, count in word_counter.most_common(10)]

        # 6. Collection Timeline (grouped by day)
        dates: List[str] = []
        for doc in documents:
            if doc.collection_timestamp:
                dates.append(doc.collection_timestamp.strftime("%Y-%m-%d"))
                
        timeline = dict(collections.Counter(dates))
        # Sort timeline by date string key
        sorted_timeline = dict(sorted(timeline.items()))

        return {
            "total_documents": total_docs,
            "unique_documents": unique_docs,
            "duplicate_documents": duplicate_docs,
            "duplicate_rate": duplicate_rate,
            "length_stats": {
                "avg_word_count": avg_word_count,
                "median_word_count": median_word_count,
                "avg_char_count": avg_char_count,
                "median_char_count": median_char_count
            },
            "language_distribution": lang_dist,
            "source_distribution": source_dist,
            "quality_stats": {
                "avg_score": avg_quality,
                "median_score": median_quality,
                "min_score": min_quality,
                "max_score": max_quality,
                "buckets": buckets
            },
            "top_keywords": top_keywords,
            "collection_timeline": sorted_timeline
        }

# Singleton instance of AnalyticsService
analytics_service = AnalyticsService()
