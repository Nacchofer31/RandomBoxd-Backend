"""Extract preferences node - maps mood answers to structured user profile.

Has two paths:
- Deterministic (default): pure mapping based on the mobile app's rules
- LLM-enhanced (optional): sends answers to LLM for richer profile inference
"""

from typing import Any

from pydantic import BaseModel, Field

from app.core.llm import get_llm_client
from app.core.scoring import (
    COMPANY_GENRE_WEIGHTS,
    ENERGY_GENRE_WEIGHTS,
    WEIGHT_PER_MATCH,
)
from app.models.schemas import MoodAnswers
from app.workflow.state import UserProfile


class LLMPreferenceInference(BaseModel):
    """Structured output schema for LLM preference extraction."""

    reasoning: str = Field(description="Brief reasoning about user preferences (max 2 sentences)")
    extra_genre_weights: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Additional genre weights beyond the deterministic mapping, "
            "values between -1.0 and 1.0"
        ),
    )
    energy_notes: str = Field(default="", description="Notes about energy preferences")
    company_notes: str = Field(default="", description="Notes about company preferences")


def _extract_genre_from_answer(genre_answer: str) -> str | None:
    """Extract the genre slug from a genre answer like 'SPECIFIC_ACTION' -> 'action'."""
    if genre_answer == "ANY":
        return None
    if genre_answer.startswith("SPECIFIC_"):
        return genre_answer.replace("SPECIFIC_", "").lower()
    return None


def _build_deterministic_profile(answers: MoodAnswers) -> UserProfile:
    """Build a user profile using deterministic rules (no LLM)."""
    # Genre weights: strong signal if a specific genre was requested
    genre_weights: dict[str, float] = {}
    specific_genre = _extract_genre_from_answer(answers.genre)
    if specific_genre:
        genre_weights[specific_genre] = 2.0  # Strong signal for specific genre

    # Energy affinity: pool-level genre weights based on energy level
    energy_genres = ENERGY_GENRE_WEIGHTS.get(answers.energy, set())
    energy_affinity = {g: WEIGHT_PER_MATCH for g in energy_genres}

    # Company affinity: pool-level genre weights based on company context
    company_genres = COMPANY_GENRE_WEIGHTS.get(answers.company, set())
    company_affinity = {g: WEIGHT_PER_MATCH for g in company_genres}

    return UserProfile(
        era_filter=answers.era.value,
        genre_weights=genre_weights,
        energy_affinity=energy_affinity,
        company_affinity=company_affinity,
    )


async def _build_llm_enhanced_profile(
    answers: MoodAnswers,
) -> tuple[UserProfile, str, Any]:
    """
    Build a user profile with LLM-enhanced reasoning.

    Returns:
        Tuple of (UserProfile, model_name, llm_response)
    """
    llm = get_llm_client()
    structured_llm = llm.with_structured_output(LLMPreferenceInference)

    prompt = (
        "You are helping recommend a movie based on a user's mood preferences.\n\n"
        f"User answers:\n"
        f"- Era preference: {answers.era.value}\n"
        f"- Genre preference: {answers.genre}\n"
        f"- Energy level: {answers.energy.value}\n"
        f"- Company: {answers.company.value}\n\n"
        "Based on these answers, infer any additional genre preferences "
        "or nuances that would help pick the best movie. "
        "Keep reasoning brief and focused."
    )

    try:
        inference: LLMPreferenceInference = await structured_llm.ainvoke(prompt)
    except Exception:
        # If LLM fails, fall back to deterministic
        return _build_deterministic_profile(answers), "", None

    # Start with deterministic base, then layer on LLM insights
    profile = _build_deterministic_profile(answers)

    # Merge LLM-inferred genre weights (clamped to [-1.0, 1.0])
    for genre, weight in inference.extra_genre_weights.items():
        clamped = max(-1.0, min(1.0, weight))
        profile.genre_weights[genre.lower()] = (
            profile.genre_weights.get(genre.lower(), 0.0) + clamped
        )

    # Extract model name for metadata
    model_name = getattr(llm, "model_name", None) or getattr(llm, "model", "") or ""

    return profile, str(model_name), inference


async def extract_preferences(state) -> dict:
    """
    Extract user preferences from mood answers.

    Uses deterministic mapping by default. When LLM is available and enabled,
    enhances the profile with LLM reasoning while keeping deterministic base.
    """
    answers = state.mood_answers

    # For Phase 3 initial: always use deterministic. LLM path will be
    # activated via a feature flag / config in a later iteration.
    profile = _build_deterministic_profile(answers)

    return {
        "user_profile": profile,
        "llm_used": False,
        "llm_model": None,
    }
