"""Movie recommendation service.

Orchestrates the recommendation flow using LangGraph workflow:
1. Validate pool
2. Extract user preferences
3. Score films
4. Generate final recommendation with anti-hallucination validation
"""

import time

from app.models.schemas import (
    RecommendationMetadata,
    RecommendationRequest,
    RecommendationResponse,
)
from app.workflow.graph import recommendation_workflow


class EmptyPoolError(Exception):
    """Raised when the movie pool is empty."""

    pass


class NoMatchError(Exception):
    """Raised when no films match the era filter."""

    pass


class MovieService:
    """Service for generating movie recommendations using LangGraph workflow."""

    async def recommend(self, request: RecommendationRequest) -> RecommendationResponse:
        """Generate a movie recommendation based on mood answers and pool.

        Uses LangGraph workflow to orchestrate:
        - validate_pool → extract_preferences → score_movies → final_recommendation

        Args:
            request: Complete recommendation request with mood answers and pool

        Returns:
            RecommendationResponse with selected film and metadata

        Raises:
            EmptyPoolError: If the movie pool is empty
            NoMatchError: If no films match the era filter
        """
        start_time = time.time()

        # Initialize workflow state
        initial_state = {
            "mood_answers": request.mood_answers,
            "movie_pool": request.movie_pool,
            "pool_context": request.pool_context,
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
        )

        return RecommendationResponse(
            recommendation=final_state["recommendation"],
            fallback_used=final_state.get("fallback_used", True),
            metadata=metadata,
        )


# Singleton instance
movie_service = MovieService()
