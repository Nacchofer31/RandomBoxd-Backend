"""Tests for Phase 2: Deterministic scoring engine and recommendation endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.scoring import build_reason_tags, era_matches, score_films
from app.main import app
from app.models.schemas import (
    Film,
    MoodAnswers,
    MoodCompany,
    MoodEnergy,
    MoodEra,
    PoolContext,
    RecommendationRequest,
    SearchMode,
)
from app.services.movie_service import EmptyPoolError, NoMatchError, movie_service


# Test fixtures
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
        Film(
            slug="the-godfather-1972",
            name="The Godfather",
            release_year=1972,
            image_url="https://example.com/godfather.jpg",
        ),
        Film(
            slug="back-to-the-future-1985",
            name="Back to the Future",
            release_year=1985,
            image_url="https://example.com/bttf.jpg",
        ),
        Film(
            slug="parasite-2019",
            name="Parasite",
            release_year=2019,
            image_url="https://example.com/parasite.jpg",
        ),
    ]


@pytest.fixture
def sample_request(sample_pool):
    """Sample recommendation request."""
    return RecommendationRequest(
        mood_answers=MoodAnswers(
            era=MoodEra.RECENT,
            genre="SPECIFIC_ACTION",
            energy=MoodEnergy.HIGH,
            company=MoodCompany.FRIENDS,
        ),
        movie_pool=sample_pool,
        pool_context=PoolContext(
            user_names=["user1"],
            search_mode=SearchMode.UNION,
            genres=["action", "thriller"],
        ),
    )


# Era filtering tests
def test_era_matches_classic():
    """Test classic era filtering (≤1979)."""
    assert era_matches(MoodEra.CLASSIC, 1972) is True
    assert era_matches(MoodEra.CLASSIC, 1979) is True
    assert era_matches(MoodEra.CLASSIC, 1980) is False
    assert era_matches(MoodEra.CLASSIC, 2010) is False


def test_era_matches_retro():
    """Test retro era filtering (1980-1999)."""
    assert era_matches(MoodEra.RETRO, 1980) is True
    assert era_matches(MoodEra.RETRO, 1985) is True
    assert era_matches(MoodEra.RETRO, 1999) is True
    assert era_matches(MoodEra.RETRO, 1979) is False
    assert era_matches(MoodEra.RETRO, 2000) is False


def test_era_matches_modern():
    """Test modern era filtering (2000-2014)."""
    assert era_matches(MoodEra.MODERN, 2000) is True
    assert era_matches(MoodEra.MODERN, 2010) is True
    assert era_matches(MoodEra.MODERN, 2014) is True
    assert era_matches(MoodEra.MODERN, 1999) is False
    assert era_matches(MoodEra.MODERN, 2015) is False


def test_era_matches_recent():
    """Test recent era filtering (2015+)."""
    assert era_matches(MoodEra.RECENT, 2015) is True
    assert era_matches(MoodEra.RECENT, 2019) is True
    assert era_matches(MoodEra.RECENT, 2024) is True
    assert era_matches(MoodEra.RECENT, 2014) is False


def test_era_matches_any():
    """Test ANY era matches everything."""
    assert era_matches(MoodEra.ANY, 1972) is True
    assert era_matches(MoodEra.ANY, 1985) is True
    assert era_matches(MoodEra.ANY, 2010) is True
    assert era_matches(MoodEra.ANY, 2019) is True
    assert era_matches(MoodEra.ANY, None) is True


def test_era_matches_null_year():
    """Test films with null releaseYear only match ANY era."""
    assert era_matches(MoodEra.ANY, None) is True
    assert era_matches(MoodEra.CLASSIC, None) is False
    assert era_matches(MoodEra.RETRO, None) is False
    assert era_matches(MoodEra.MODERN, None) is False
    assert era_matches(MoodEra.RECENT, None) is False


# Scoring tests
def test_score_films_recent_high_energy(sample_pool):
    """Test scoring with RECENT era and HIGH energy."""
    answers = MoodAnswers(
        era=MoodEra.RECENT,
        genre="SPECIFIC_ACTION",
        energy=MoodEnergy.HIGH,
        company=MoodCompany.FRIENDS,
    )
    pool_genres = {"action", "thriller"}

    scored = score_films(sample_pool, answers, pool_genres)

    # Should only include 2015+ films
    assert len(scored) == 2
    slugs = [film.slug for film, _ in scored]
    assert "mad-max-fury-road-2015" in slugs
    assert "parasite-2019" in slugs

    # Both should have same score (both match action + thriller)
    assert scored[0][1] == scored[1][1]

    # Should be sorted by slug (deterministic tie-break)
    assert scored[0][0].slug < scored[1][0].slug


def test_score_films_modern_era(sample_pool):
    """Test scoring with MODERN era (2000-2014)."""
    answers = MoodAnswers(
        era=MoodEra.MODERN,
        genre="ANY",
        energy=MoodEnergy.BALANCED,
        company=MoodCompany.SOLO,
    )
    pool_genres = set()

    scored = score_films(sample_pool, answers, pool_genres)

    # Should only include 2000-2014 films
    assert len(scored) == 1
    assert scored[0][0].slug == "inception-2010"


def test_score_films_classic_era(sample_pool):
    """Test scoring with CLASSIC era (≤1979)."""
    answers = MoodAnswers(
        era=MoodEra.CLASSIC,
        genre="ANY",
        energy=MoodEnergy.LOW,
        company=MoodCompany.DATE,
    )
    pool_genres = {"drama", "romance"}

    scored = score_films(sample_pool, answers, pool_genres)

    # Should only include ≤1979 films
    assert len(scored) == 1
    assert scored[0][0].slug == "the-godfather-1972"


def test_score_films_any_era(sample_pool):
    """Test scoring with ANY era (all films eligible)."""
    answers = MoodAnswers(
        era=MoodEra.ANY,
        genre="ANY",
        energy=MoodEnergy.BALANCED,
        company=MoodCompany.SOLO,
    )
    pool_genres = set()

    scored = score_films(sample_pool, answers, pool_genres)

    # Should include all films
    assert len(scored) == 5


def test_score_films_genre_affinity(sample_pool):
    """Test that genre affinity affects scoring."""
    answers = MoodAnswers(
        era=MoodEra.ANY,
        genre="ANY",
        energy=MoodEnergy.HIGH,
        company=MoodCompany.FRIENDS,
    )
    pool_genres = {"action", "thriller"}

    scored = score_films(sample_pool, answers, pool_genres)

    # Score = 4.0: HIGH energy matches action+thriller (2.0) + FRIENDS matches action+thriller (2.0)
    for _, score in scored:
        assert score == 4.0


def test_score_films_no_genre_match(sample_pool):
    """Test scoring when pool genres don't match energy/company affinity."""
    answers = MoodAnswers(
        era=MoodEra.ANY,
        genre="ANY",
        energy=MoodEnergy.HIGH,
        company=MoodCompany.FRIENDS,
    )
    pool_genres = {"romance", "documentary"}  # No match with HIGH/FRIENDS

    scored = score_films(sample_pool, answers, pool_genres)

    # All films should have score = 0.0
    for _, score in scored:
        assert score == 0.0


# Reason tags tests
def test_build_reason_tags_recent_high_friends():
    """Test reason tags for RECENT + HIGH + FRIENDS."""
    answers = MoodAnswers(
        era=MoodEra.RECENT,
        genre="SPECIFIC_ACTION",
        energy=MoodEnergy.HIGH,
        company=MoodCompany.FRIENDS,
    )

    tags = build_reason_tags(answers)

    assert "ERA_RECENT" in tags
    assert "ENERGY_HIGH" in tags
    assert "COMPANY_FRIENDS" in tags
    assert "GENRE_MATCH" in tags


def test_build_reason_tags_any_genre():
    """Test reason tags when genre is ANY."""
    answers = MoodAnswers(
        era=MoodEra.MODERN,
        genre="ANY",
        energy=MoodEnergy.LOW,
        company=MoodCompany.DATE,
    )

    tags = build_reason_tags(answers)

    assert "ERA_MODERN" in tags
    assert "ENERGY_LOW" in tags
    assert "COMPANY_DATE" in tags
    assert "GENRE_MATCH" not in tags  # ANY genre shouldn't add tag


# Service tests
@pytest.mark.asyncio
async def test_service_recommend_success(sample_request):
    """Test successful recommendation."""
    response = await movie_service.recommend(sample_request)

    assert response.recommendation.film.slug in [
        "mad-max-fury-road-2015",
        "parasite-2019",
    ]
    assert response.recommendation.confidence >= 0.7
    assert response.metadata.pool_size == 5
    assert response.metadata.eligible_count == 2
    assert response.metadata.llm_model is None
    assert response.fallback_used is True
    assert len(response.recommendation.reason_tags) > 0


@pytest.mark.asyncio
async def test_service_empty_pool():
    """Test that empty pool raises EmptyPoolError."""
    request = RecommendationRequest(
        mood_answers=MoodAnswers(
            era=MoodEra.RECENT,
            genre="ANY",
            energy=MoodEnergy.HIGH,
            company=MoodCompany.SOLO,
        ),
        movie_pool=[],
        pool_context=PoolContext(),
    )

    with pytest.raises(EmptyPoolError):
        await movie_service.recommend(request)


@pytest.mark.asyncio
async def test_service_no_match():
    """Test that no matching films raises NoMatchError."""
    request = RecommendationRequest(
        mood_answers=MoodAnswers(
            era=MoodEra.CLASSIC,  # ≤1979
            genre="ANY",
            energy=MoodEnergy.HIGH,
            company=MoodCompany.SOLO,
        ),
        movie_pool=[
            Film(
                slug="inception-2010",
                name="Inception",
                release_year=2010,
                image_url="https://example.com/inception.jpg",
            ),
        ],
        pool_context=PoolContext(),
    )

    with pytest.raises(NoMatchError):
        await movie_service.recommend(request)


# Endpoint tests
@pytest.mark.asyncio
async def test_endpoint_recommend_success(sample_request):
    """Test /api/v1/recommend endpoint success."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/recommend", json=sample_request.model_dump())

    assert response.status_code == 200
    data = response.json()
    assert "recommendation" in data
    assert "film" in data["recommendation"]
    # JSON response uses camelCase (API contract with mobile app)
    assert "reasonTags" in data["recommendation"]
    assert "reasonTemplateKey" in data["recommendation"]
    assert "metadata" in data


@pytest.mark.asyncio
async def test_endpoint_recommend_empty_pool():
    """Test /api/v1/recommend with empty pool returns 400."""
    request = RecommendationRequest(
        mood_answers=MoodAnswers(
            era=MoodEra.RECENT,
            genre="ANY",
            energy=MoodEnergy.HIGH,
            company=MoodCompany.SOLO,
        ),
        movie_pool=[],
        pool_context=PoolContext(),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/recommend", json=request.model_dump())

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_endpoint_recommend_no_match():
    """Test /api/v1/recommend with no matching films returns 404."""
    request = RecommendationRequest(
        mood_answers=MoodAnswers(
            era=MoodEra.CLASSIC,
            genre="ANY",
            energy=MoodEnergy.HIGH,
            company=MoodCompany.SOLO,
        ),
        movie_pool=[
            Film(
                slug="inception-2010",
                name="Inception",
                release_year=2010,
                image_url="https://example.com/inception.jpg",
            ),
        ],
        pool_context=PoolContext(),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/recommend", json=request.model_dump())

    assert response.status_code == 404
    assert "no films match" in response.json()["detail"].lower()


# Anti-hallucination test
@pytest.mark.asyncio
async def test_anti_hallucination_validation(sample_request):
    """Test that recommended film is always from the pool."""
    response = await movie_service.recommend(sample_request)

    pool_slugs = {film.slug for film in sample_request.movie_pool}
    assert response.recommendation.film.slug in pool_slugs


# Determinism test
@pytest.mark.asyncio
async def test_deterministic_scoring(sample_request):
    """Test that scoring is deterministic (same input = same output)."""
    response1 = await movie_service.recommend(sample_request)
    response2 = await movie_service.recommend(sample_request)

    assert response1.recommendation.film.slug == response2.recommendation.film.slug
    assert response1.recommendation.confidence == response2.recommendation.confidence
