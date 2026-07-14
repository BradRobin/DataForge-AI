# Changelog

All notable changes to the **DataForge AI** pipeline project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-07-14

### Added
*   **One-Click Pipeline Orchestrator**: Synchronous background worker execution running crawling, cleaning, deduplication, scoring, and packaging. Supports real-time status updates, stage-wise log tracking, immediate download caches, and active cancel triggers.
*   **Next.js Dashboard Client**: Advanced dark-themed single-page application built with CSS grids and glassmorphism styling. Features visual components for all pipeline features: Ingest monitors, real-time cleaning preview, Hamming dedup slider, interactive analytics, and multi-format downloaders.
*   **Dataset Export Engine**: Exposes dynamic database filtering (source, language, minimum quality threshold, duplicate exclusions) and outputs data packaged in JSON, CSV (with flattened metadata), or standardized Apache Parquet compiled using `pandas` and `pyarrow`.
*   **Analytics Compilation Engine**: Generates database-wide metadata including total counts, word/character averages and medians, language and source distributions, quality score buckets, timeline charts, and top 10 keywords.
*   **Quality Heuristic Evaluator**: Grades document quality out of 100 based on word count penalties, stop-word language confidence, Flesch-Kincaid readability, boilerplate line ratios, word repetition frequency, and malformed characters.
*   **SimHash Deduplication Engine**: Implements 64-bit SimHash signatures with character 3-gram shingling, Hamming distance comparisons, and database duplicate flags containing parent lineage references.
*   **Cleaning & Normalization Engine**: Word-by-word UTF-8 double-encoding repair (via Latin-1), structural HTML element removal, NFKC unicode normalization, smart punctuation standardization, and boilerplate advertisement filter lists.
*   **Extensible Data Collector**: Plugin architecture with an active `HttpCollector` featuring Robots.txt caching, domain-based crawl delay enforcement, exponential backoff retries, and duplicate URL checks.
*   **Document Schema CRUD**: Database representation of `Document` using SQLAlchemy 2.0. Prevents metadata collisions by mapping `metadata_` to a JSON column.
*   **Monorepo Foundation**: Configured Docker Compose services (`db`, `backend`, `frontend`), unified `.env` configurations, and developer startup utility script (`run_dev.ps1`).

### Changed
*   Refactored the backend clean router to consume a decoupled `clean_service.clean_batch(db, limit)` singleton, improving modular separation.
*   Updated FastAPI pipeline endpoints to utilize `Depends(get_session_factory)` for database connection factory injection, resolving connection resolution failures during unit tests.

### Fixed
*   Resolved page component tab-switching layout rendering collisions for dataset export and pipeline tabs in Next.js page workspace.
