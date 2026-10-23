"""SQLAlchemy database models."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class FilmEnriched(Base):
    """
    Cached film enrichment data from Letterboxd scraping.

    Stores genres per film to improve scoring accuracy.
    """

    __tablename__ = "films_enriched"

    slug: Mapped[str] = mapped_column(String(255), primary_key=True)
    genres: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    enriched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<FilmEnriched(slug={self.slug}, genres={self.genres})>"
