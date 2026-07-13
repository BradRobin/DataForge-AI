import uuid
from datetime import date, datetime
from typing import Any, Dict
from sqlalchemy import String, Text, DateTime, Date, JSON, Boolean, Float, func, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Document(Base):
    """
    SQLAlchemy model representing a collected document in the DataForge AI pipeline.
    """
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    collection_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Map 'metadata_' in python to 'metadata' in SQL to prevent naming conflict with Base.metadata
    metadata_: Mapped[Dict[str, Any] | None] = mapped_column(
        JSON,
        name="metadata",
        nullable=True,
        default=dict,
        server_default='{}'
    )
    
    hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    duplicate_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='false')
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True, default=0.0, server_default='0.0')

    def __repr__(self) -> str:
        return f"<Document id={self.id} source={self.source} hash={self.hash}>"
