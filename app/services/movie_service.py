"""Movie recommendation service.

Orchestrates the recommendation flow using LangGraph workflow:
1. Enrich pool with per-film genres (if DB available)
2. Validate pool
3. Extract user preferences
4. Score films
5. Generate final recommendation with anti-hallucination validation
"""

import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import (
    RecommendationMetadata,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services.enrichment_service import EnrichmentService
from app.workflow.graph import recommendation_workflow


class EmptyPoolError(Exception):
    """Raised when the movie pool is empty."""

    pass


class NoMatchError(Exception):
    """Raised when no films match the era filter."""

    pass


class MovieService:
    """Service for generating movie recommendations using LangGraph workflow."""

    async def recommend(
        self, request: RecommendationRequest, db: AsyncSession | None = None
    ) -> RecommendationResponse:
        """Generate a movie recommendation based on mood answers and pool.

        Uses LangGraph workflow to orchestrate:
        - enrich_pool (optional) → validate_pool → extract_preferences
          → score_movies → final_recommendation

        Args:
            request: Complete recommendation request with mood answers and pool
            db: Optional database session for pool enrichment. If provided, enriches
                the pool with per-film genres before scoring.

        Returns:
            RecommendationResponse with selected film and metadata

        Raises:
            EmptyPoolError: If the movie pool is empty
            NoMatchError: If no films match the era filter
        """
        start_time = time.time()

        # Enrich pool with per-film genres if DB is available
        enriched_genres = None
        enrichment_count = 0

        if db and request.movie_pool:
            try:
                enrichment_service = EnrichmentService(db)
                slugs = [film.slug for film in request.movie_pool]
                enriched_genres = await enrichment_service.enrich_pool(slugs)
                enrichment_count = len([g for g in enriched_genres.values() if g])
            except Exception:
                # If enrichment fails, continue without it (graceful degradation)
                enriched_genres = None

        # Initialize workflow state
        initial_state = {
            "mood_answers": request.mood_answers,
            "movie_pool": request.movie_pool,
            "pool_context": request.pool_context,
            "enriched_genres": enriched_genres,
        }

        # Execute workflow
        final_state = await recommendation_workflow.ainvoke(initial_state)

        # Check for errors
        if final_state.get("error"):
            if "empty" in final_state["error"].lower():
                raise EmptyPoolError(final_state["error"])
            elif "no films match" in final_state["error"].lower():
                raise NoMatchError(final_state["error"])
            else:
                raise ValueError(final_state["error"])

        # Validate we have a recommendation
        if not final_state.get("recommendation"):
            raise ValueError("Workflow completed without generating a recommendation")

        latency_ms = int((time.time() - start_time) * 1000)

        # Build metadata
        metadata = RecommendationMetadata(
            pool_size=len(request.movie_pool),
            eligible_count=len(final_state.get("scored_films", [])),
            llm_model=final_state.get("llm_model"),
            latency_ms=latency_ms,
            enrichment_count=enrichment_count,
        )

        return RecommendationResponse(
            recommendation=final_state["recommendation"],
            fallback_used=final_state.get("fallback_used", True),
            metadata=metadata,
        )


# Singleton instance
movie_service = MovieService()
