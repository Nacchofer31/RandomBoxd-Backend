"""Movie recommendation service.

Orchestrates the recommendation flow:
1. Validate pool
2. Score films using deterministic engine
3. Select best film
4. Generate response with anti-hallucination validation
"""

import time

from app.core.scoring import (
    build_reason_tags,
    build_user_profile_summary,
    get_reason_template_key,
    score_films,
)
from app.models.schemas import (
    RecommendationDetail,
    RecommendationMetadata,
    RecommendationRequest,
    RecommendationResponse,
)


class EmptyPoolError(Exception):
    """Raised when the movie pool is empty."""

    pass


class NoMatchError(Exception):
    """Raised when no films match the era filter."""

    pass


class MovieService:
    """Service for generating movie recommendations."""

    async def recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        """Generate a movie recommendation based on mood answers and pool.

        Args:
            request: Complete recommendation request with mood answers and pool

        Returns:
            RecommendationResponse with selected film and metadata

        Raises:
            EmptyPoolError: If the movie pool is empty
            NoMatchError: If no films match the era filter
        """
        start_time = time.time()

        # Validate pool
        if not request.movie_pool:
            raise EmptyPoolError("Movie pool is empty")

        pool_size = len(request.movie_pool)

        # Extract pool genres from pool_context
        pool_genres = set(request.pool_context.genres)

        # Score films
        scored_films = score_films(
            pool=request.movie_pool,
            answers=request.mood_answers,
            pool_genres=pool_genres,
        )

        # Check if any films passed era filtering
        if not scored_films:
            raise NoMatchError(
                f"No films match the era filter: {request.mood_answers.era}"
            )

        eligible_count = len(scored_films)

        # Select best film (first in sorted list)
        best_film, score = scored_films[0]

        # Anti-hallucination validation: ensure film is in original pool
        pool_slugs = {film.slug for film in request.movie_pool}
        if best_film.slug not in pool_slugs:
            # This should never happen with deterministic engine, but validate anyway
            raise ValueError(
                f"Selected film {best_film.slug} not found in original pool"
            )

        # Build response
        reason_tags = build_reason_tags(request.mood_answers)
        reason_template_key = get_reason_template_key(request.mood_answers.era)
        user_profile_summary = build_user_profile_summary(request.mood_answers)

        # Calculate confidence (normalized score)
        # For now, use a simple heuristic: if score > 0, high confidence
        # In Phase 3, LLM will provide more nuanced confidence
        confidence = min(1.0, 0.7 + (score * 0.03))  # Base 0.7 + 0.03 per match

        latency_ms = int((time.time() - start_time) * 1000)

        recommendation = RecommendationDetail(
            film=best_film,
            reason_tags=reason_tags,  # type: ignore[arg-type]
            reason_template_key=reason_template_key,
            confidence=confidence,
            user_profile_summary=user_profile_summary,
        )

        metadata = RecommendationMetadata(
            pool_size=pool_size,
            eligible_count=eligible_count,
            llm_model=None,  # Deterministic engine only
            latency_ms=latency_ms,
        )

        return RecommendationResponse(
            recommendation=recommendation,
            fallback_used=True,  # Always true for deterministic engine
            metadata=metadata,
        )


# Singleton instance
movie_service = MovieService()
