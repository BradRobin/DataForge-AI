import logging
import re
import uuid
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.documents.models import Document
from app.features.documents.crud import update_document
from app.features.documents.schemas import DocumentUpdate

logger = logging.getLogger("dataforge.quality.service")

class QualityService:
    """
    Quality Evaluation Engine for grading text quality for AI training datasets.
    """
    def __init__(self) -> None:
        self.stop_words = {
            "the", "and", "of", "to", "in", "is", "that", "it", "on", "for",
            "as", "with", "was", "at", "by", "an", "be", "this", "are", "from",
            "or", "have", "you", "but", "not", "he", "she", "they", "we", "his",
            "her", "its", "their", "my", "your", "our", "him", "them", "us"
        }
        self.vowel_pattern = re.compile(r'[aeiouy]', re.IGNORECASE)

    def evaluate_text(self, text: str) -> Dict[str, Any]:
        """
        Evaluate raw/cleaned text and calculate sub-scores and overall quality score.
        Returns a dictionary containing the final score, sub-scores, and metrics.
        """
        if not text or not text.strip():
            return {
                "quality_score": 0.0,
                "sub_scores": {
                    "length_score": 0.0,
                    "stop_word_score": 0.0,
                    "readability_score": 0.0,
                    "noise_score": 0.0,
                    "repetition_score": 0.0,
                    "malformed_score": 0.0
                },
                "metrics": {
                    "word_count": 0,
                    "sentence_count": 0,
                    "noise_ratio": 0.0,
                    "stop_word_ratio": 0.0,
                    "unique_word_ratio": 0.0,
                    "vowelless_word_ratio": 0.0
                }
            }

        # 1. Basic Tokenization
        raw_words = re.findall(r'\w+', text)
        words_lower = [w.lower() for w in raw_words]
        word_count = len(raw_words)
        
        # Sentences split by standard end punctuation
        raw_sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        sentence_count = len(raw_sentences) if raw_sentences else 1

        if word_count == 0:
            return self.evaluate_text("") # return empty stats

        # 2. Heuristics Computation
        
        # Sub-score A: Document Length (15%)
        # Reward length: penalize under 10 words, scale to 100, then scale to 1000
        if word_count < 10:
            length_score = 0.2
        elif word_count < 100:
            length_score = 0.2 + (word_count - 10) * (0.6 / 90.0)
        elif word_count < 1000:
            length_score = 0.8 + (word_count - 100) * (0.2 / 900.0)
        else:
            length_score = 1.0

        # Sub-score B: Language Confidence / Stop Words (20%)
        # Measure stop word density (Standard English contains a healthy ratio of structural stop words)
        stop_word_count = sum(1 for w in words_lower if w in self.stop_words)
        stop_word_ratio = stop_word_count / word_count
        if stop_word_ratio < 0.02:
            stop_word_score = 0.0
        elif stop_word_ratio < 0.15:
            stop_word_score = (stop_word_ratio - 0.02) / 0.13
        else:
            stop_word_score = 1.0

        # Sub-score C: Readability (20%)
        # C1: Avg word length (characters)
        total_word_chars = sum(len(w) for w in raw_words)
        avg_word_len = total_word_chars / word_count
        if 4.0 <= avg_word_len <= 7.0:
            word_len_score = 1.0
        elif avg_word_len < 4.0:
            word_len_score = max(0.0, 1.0 - (4.0 - avg_word_len) * 0.3)
        else:
            word_len_score = max(0.0, 1.0 - (avg_word_len - 7.0) * 0.2)

        # C2: Avg sentence length (words)
        avg_sentence_len = word_count / sentence_count
        if 5.0 <= avg_sentence_len <= 30.0:
            sentence_len_score = 1.0
        elif avg_sentence_len < 5.0:
            sentence_len_score = max(0.0, 1.0 - (5.0 - avg_sentence_len) * 0.1)
        else:
            sentence_len_score = max(0.0, 1.0 - (avg_sentence_len - 30.0) * 0.02)
            
        readability_score = (word_len_score + sentence_len_score) / 2.0

        # Sub-score D: Noise Ratio (15%)
        # Ratio of special characters/symbols (excluding alphanumeric and standard spaces/tabs)
        total_chars = len(text)
        alphanum_spaces = len(re.findall(r'[a-zA-Z0-9\s]', text))
        noise_chars = total_chars - alphanum_spaces
        noise_ratio = noise_chars / total_chars
        if noise_ratio <= 0.05:
            noise_score = 1.0
        elif noise_ratio <= 0.25:
            noise_score = max(0.0, 1.0 - (noise_ratio - 0.05) * 5.0)
        else:
            noise_score = 0.0

        # Sub-score E: Repeated Words / Redundancy (15%)
        # E1: Unique word ratio
        unique_words = len(set(words_lower))
        unique_word_ratio = unique_words / word_count
        if word_count < 20:
            rep_score = 1.0
        else:
            if unique_word_ratio >= 0.4:
                rep_score = 1.0
            else:
                rep_score = unique_word_ratio / 0.4
                
        # E2: Adjacent word repetition (e.g. "the the")
        consecutives = sum(1 for i in range(word_count - 1) if words_lower[i] == words_lower[i+1])
        consec_ratio = consecutives / word_count
        consec_penalty = max(0.0, 1.0 - consec_ratio * 5.0)
        
        repetition_score = rep_score * consec_penalty

        # Sub-score F: Malformed Text (15%)
        # F1: Vowelless word ratio (excluding very short acronyms of length 1)
        vowelless = sum(1 for w in raw_words if len(w) >= 2 and not self.vowel_pattern.search(w))
        vowelless_ratio = vowelless / word_count
        vowel_score = max(0.0, 1.0 - vowelless_ratio * 4.0)
        
        # F2: Capitalization ratio (excessive shouting/OCR errors)
        letters_only = len(re.findall(r'[a-zA-Z]', text))
        if letters_only > 0:
            caps_count = len(re.findall(r'[A-Z]', text))
            caps_ratio = caps_count / letters_only
            if caps_ratio > 0.30:
                caps_score = max(0.0, 1.0 - (caps_ratio - 0.30) * 2.0)
            else:
                caps_score = 1.0
        else:
            caps_score = 1.0
            
        malformed_score = (vowel_score + caps_score) / 2.0

        # 3. Overall Weighted Score Calculation
        overall_score = (
            length_score * 0.15 +
            stop_word_score * 0.20 +
            readability_score * 0.20 +
            noise_score * 0.15 +
            repetition_score * 0.15 +
            malformed_score * 0.15
        ) * 100.0

        # Apply strict length penalty multiplier for short texts to ensure they score low
        if word_count < 10:
            overall_score *= 0.3
        elif word_count < 50:
            overall_score *= 0.3 + (word_count - 10) * (0.7 / 40.0)

        return {
            "quality_score": round(overall_score, 2),
            "sub_scores": {
                "length_score": round(length_score * 100, 2),
                "stop_word_score": round(stop_word_score * 100, 2),
                "readability_score": round(readability_score * 100, 2),
                "noise_score": round(noise_score * 100, 2),
                "repetition_score": round(repetition_score * 100, 2),
                "malformed_score": round(malformed_score * 100, 2)
            },
            "metrics": {
                "word_count": word_count,
                "sentence_count": sentence_count,
                "noise_ratio": round(noise_ratio, 4),
                "stop_word_ratio": round(stop_word_ratio, 4),
                "unique_word_ratio": round(unique_word_ratio, 4),
                "vowelless_word_ratio": round(vowelless_ratio, 4)
            }
        }

    async def evaluate_document_by_id(self, db: AsyncSession, document_id: uuid.UUID) -> Document:
        """Evaluate a specific document and save the score to the database."""
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document with ID '{document_id}' not found.")

        # Run quality heuristics on cleaned_text (or raw_text if cleaned is unavailable)
        text_to_grade = doc.cleaned_text if doc.cleaned_text else doc.raw_text
        report = self.evaluate_text(text_to_grade)

        # Update quality score in database
        doc.quality_score = report["quality_score"]
        
        # Cache breakdown metrics under metadata JSON
        if doc.metadata_ is None:
            doc.metadata_ = {}
        doc.metadata_["quality_report"] = {
            "sub_scores": report["sub_scores"],
            "metrics": report["metrics"]
        }

        db.add(doc)
        await db.commit()
        return doc

    async def evaluate_batch(self, db: AsyncSession, limit: int = 100) -> int:
        """Evaluate and grade a batch of unscored documents (quality_score is null)."""
        stmt = select(Document).where(Document.quality_score == None).limit(limit)
        result = await db.execute(stmt)
        docs = result.scalars().all()
        
        processed = 0
        for doc in docs:
            text_to_grade = doc.cleaned_text if doc.cleaned_text else doc.raw_text
            report = self.evaluate_text(text_to_grade)
            
            doc.quality_score = report["quality_score"]
            if doc.metadata_ is None:
                doc.metadata_ = {}
            doc.metadata_["quality_report"] = {
                "sub_scores": report["sub_scores"],
                "metrics": report["metrics"]
            }
            db.add(doc)
            processed += 1
            
        if processed > 0:
            await db.commit()
            
        return processed

# Singleton instance of QualityService
quality_service = QualityService()
