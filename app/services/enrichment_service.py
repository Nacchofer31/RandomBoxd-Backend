"""Enrichment service - manages cached film metadata from Letterboxd."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.letterboxd_scraper import scraper
from app.models.db_models import FilmEnriched


class EnrichmentService:
    """Service for enriching films with Letterboxd metadata (with cache)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_enriched_films(self, slugs: list[str]) -> dict[str, list[str]]:
        """
        Get enriched data for films, using cache when available.

        Args:
            slugs: List of film slugs to enrich

        Returns:
            Dictionary mapping slug -> genres (empty list if not enriched)
        """
        if not slugs:
            return {}

        # Check cache first
        result = await self.session.execute(
            select(FilmEnriched).where(FilmEnriched.slug.in_(slugs))
        )
        cached_films = {film.slug: film.genres for film in result.scalars().all()}

        # Identify films that need scraping
        uncached_slugs = [slug for slug in slugs if slug not in cached_films]

        # Scrape uncached films
        if uncached_slugs:
            scraped_data = await scraper.enrich_films(uncached_slugs)

            # Save to cache
            for slug, genres in scraped_data.items():
                if genres:  # Only cache if we got data
                    enriched = FilmEnriched(
                        slug=slug,
                        genres=genres,
                        enriched_at=datetime.now(UTC),
                    )
                    self.session.add(enriched)
                    cached_films[slug] = genres

            await self.session.commit()

        # Build result dict
        return {slug: cached_films.get(slug, []) for slug in slugs}

    async def enrich_pool(
        self, pool_slugs: list[str]
    ) -> dict[str, list[str]]:
        """
        Enrich a pool of films (convenience method).

        Args:
            pool_slugs: List of film slugs in the pool

        Returns:
            Dictionary mapping slug -> genres
        """
        return await self.get_enriched_films(pool_slugs)
