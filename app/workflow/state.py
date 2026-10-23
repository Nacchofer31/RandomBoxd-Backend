"""LangGraph workflow state definition."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.schemas import (
    Film,
    MoodAnswers,
    PoolContext,
    RecommendationDetail,
)


class UserProfile(BaseModel):
    """Extracted user preferences from mood answers."""

    era_filter: Literal["CLASSIC", "RETRO", "MODERN", "RECENT", "ANY"]
    genre_weights: dict[str, float] = Field(default_factory=dict)
    energy_affinity: dict[str, float] = Field(default_factory=dict)
    company_affinity: dict[str, float] = Field(default_factory=dict)


class WorkflowState(BaseModel):
    """State that flows through the LangGraph workflow."""

    # Input
    mood_answers: MoodAnswers
    movie_pool: list[Film]
    pool_context: PoolContext

    # Intermediate
    validated_pool: list[Film] | None = None
    pool_stats: dict[str, Any] | None = None
    user_profile: UserProfile | None = None
    enriched_genres: dict[str, list[str]] | None = None
    scored_films: list[tuple[Film, float]] | None = None
    llm_candidates: list[Film] | None = None

    # Output
    recommendation: RecommendationDetail | None = None
    llm_used: bool = False
    llm_model: str | None = None
    fallback_used: bool = False
    error: str | None = None

    # Metadata
    latency_ms: int = 0
