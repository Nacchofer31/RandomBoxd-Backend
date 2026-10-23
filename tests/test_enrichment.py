"""Tests for pool enrichment functionality."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.letterboxd_scraper import LetterboxdScraper
from app.main import app
from app.models.schemas import (
    Film,
    MoodAnswers,
    MoodCompany,
    MoodEnergy,
    MoodEra,
    PoolContext,
    RecommendationRequest,
)
from app.services.enrichment_service import EnrichmentService


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def enrichment_service(mock_db_session):
    """Enrichment service with mock DB."""
    return EnrichmentService(mock_db_session)


@pytest.fixture
def sample_pool():
    """Sample movie pool for testing."""
    return [
        Film(
            slug="mad-max-fury-road-2015",
            name="Mad Max: Fury Road",
            release_year=2015,
            image_url="https://example.com/madmax.jpg",
        ),
        Film(
            slug="inception-2010",
            name="Inception",
            release_year=2010,
            image_url="https://example.com/inception.jpg",
        ),
    ]


class TestEnrichmentService:
    """Tests for EnrichmentService."""

    async def test_enrich_pool_with_cache_hit(
        self, enrichment_service, mock_db_session, sample_pool
    ):
        """Test that cached films are returned without scraping."""
        # Mock cached films in database
        cached_result = MagicMock()
        cached_result.scalars.return_value.all.return_value = [
            MagicMock(
                slug="mad-max-fury-road-2015",
                genres=["action", "adventure"],
                enriched_at=datetime.now(UTC),
            )
        ]
        mock_db_session.execute.return_value = cached_result

        slugs = ["mad-max-fury-road-2015", "inception-2010"]
        await enrichment_service.enrich_pool(slugs)

        # Should have called execute to check cache
        assert mock_db_session.execute.called
        # Should NOT have called commit (no new films to cache)
        # (only inception-2010 would need scraping, but we're mocking it)

    async def test_enrich_pool_with_cache_miss(
        self, enrichment_service, mock_db_session
    ):
        """Test that uncached films are scraped and cached."""
        # Mock empty cache
        cached_result = MagicMock()
        cached_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = cached_result

        # Mock scraper
        with patch(
            "app.services.enrichment_service.scraper.get_film_genres",
            new_callable=AsyncMock,
        ) as mock_scraper:
            mock_scraper.return_value = ["action", "thriller"]

            slugs = ["inception-2010"]
            result = await enrichment_service.enrich_pool(slugs)

            # Should have called scraper
            assert mock_scraper.called
            # Should have committed to cache
            assert mock_db_session.commit.called
            # Result should contain scraped genres
            assert "inception-2010" in result
            assert result["inception-2010"] == ["action", "thriller"]

    async def test_enrich_pool_partial_cache(
        self, enrichment_service, mock_db_session
    ):
        """Test that only uncached films are scraped."""
        # Mock partial cache
        cached_result = MagicMock()
        cached_result.scalars.return_value.all.return_value = [
            MagicMock(
                slug="mad-max-fury-road-2015",
                genres=["action"],
                enriched_at=datetime.now(UTC),
            )
        ]
        mock_db_session.execute.return_value = cached_result

        # Mock scraper for uncached film
        with patch(
            "app.services.enrichment_service.scraper.get_film_genres",
            new_callable=AsyncMock,
        ) as mock_scraper:
            mock_scraper.return_value = ["sci-fi", "thriller"]

            slugs = ["mad-max-fury-road-2015", "inception-2010"]
            result = await enrichment_service.enrich_pool(slugs)

            # Should have both films in result
            assert "mad-max-fury-road-2015" in result
            assert "inception-2010" in result


class TestLetterboxdScraper:
    """Tests for LetterboxdScraper."""

    async def test_get_film_genres_success(self):
        """Test successful genre scraping."""
        scraper = LetterboxdScraper()

        # Mock HTML response with genres
        mock_html = """
        <html>
        <div id="tab-genres">
            <a href="/films/genre/action/">Action</a>
            <a href="/films/genre/thriller/">Thriller</a>
        </div>
        </html>
        """

        # Mock the client
        with patch.object(scraper, 'client') as mock_client:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()

            genres = await scraper.get_film_genres("inception")

            assert "action" in genres
            assert "thriller" in genres

    async def test_get_film_genres_no_genres_section(self):
        """Test scraping when no genres section exists."""
        scraper = LetterboxdScraper()

        # Mock HTML without genres
        mock_html = "<html><body>No genres here</body></html>"

        with patch.object(scraper, 'client') as mock_client:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()

            genres = await scraper.get_film_genres("some-film")

            assert genres == []

    async def test_get_film_genres_http_error(self):
        """Test that HTTP errors return empty list."""
        scraper = LetterboxdScraper()

        with patch.object(scraper, 'client') as mock_client:
            mock_client.get = AsyncMock(side_effect=Exception("HTTP Error"))
            mock_client.aclose = AsyncMock()

            genres = await scraper.get_film_genres("some-film")

            assert genres == []


class TestRecommendEndpointWithEnrichment:
    """Tests for /recommend endpoint with enrichment."""

    async def test_recommend_with_enrichment(self, sample_pool):
        """Test that recommend endpoint uses enrichment when DB is available."""
        request = RecommendationRequest(
            mood_answers=MoodAnswers(
                era=MoodEra.RECENT,
                genre="ANY",
                energy=MoodEnergy.HIGH,
                company=MoodCompany.FRIENDS,
            ),
            movie_pool=sample_pool,
            pool_context=PoolContext(
                user_names=["user1"],
                search_mode="UNION",
                genres=["action"],
            ),
        )

        # Mock DB session
        AsyncMock(spec=AsyncSession)

        # Mock enrichment service
        with patch(
            "app.services.movie_service.EnrichmentService"
        ) as mock_enrichment_service:
            mock_enrichment = AsyncMock()
            mock_enrichment.enrich_pool.return_value = {
                "mad-max-fury-road-2015": ["action", "adventure"],
                "inception-2010": ["sci-fi", "thriller"],
            }
            mock_enrichment_service.return_value = mock_enrichment

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/recommend",
                    json=request.model_dump(),
                )

            assert response.status_code == 200
            data = response.json()
            assert "metadata" in data
            # Enrichment count should be 2 (both films enriched)
            assert data["metadata"]["enrichmentCount"] == 2

    async def test_recommend_without_db(self, sample_pool):
        """Test that recommend endpoint works without DB (no enrichment)."""
        request = RecommendationRequest(
            mood_answers=MoodAnswers(
                era=MoodEra.RECENT,
                genre="ANY",
                energy=MoodEnergy.HIGH,
                company=MoodCompany.FRIENDS,
            ),
            movie_pool=sample_pool,
            pool_context=PoolContext(
                user_names=["user1"],
                search_mode="UNION",
                genres=["action"],
            ),
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/recommend",
                json=request.model_dump(),
            )

        assert response.status_code == 200
        data = response.json()
        assert "metadata" in data
        # Enrichment count should be 0 (no DB, no enrichment)
        assert data["metadata"]["enrichmentCount"] == 0
