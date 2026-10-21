"""Final recommendation node - selects the best film and validates anti-hallucination."""


from app.core.scoring import (
    build_reason_tags,
    build_user_profile_summary,
    get_reason_template_key,
)
from app.models.schemas import MoodEra, RecommendationDetail
from app.workflow.state import WorkflowState


def final_recommendation(state: WorkflowState) -> dict:
    """
    Select the top-ranked film and build the final recommendation.

    Validates anti-hallucination: the selected film MUST be in the original pool.
    If validation fails or no films are eligible, returns an error.

    Returns:
        dict with recommendation, fallback_used, llm_used, llm_model, latency_ms
    """
    scored_films = state.scored_films

    # Check if we have any eligible films
    if not scored_films or len(scored_films) == 0:
        return {
            "error": f"No films match the era filter: {state.mood_answers.era.value}",
            "recommendation": None,
            "fallback_used": True,
        }

    # Select the top-ranked film (first in sorted list)
    best_film, score = scored_films[0]

    # Anti-hallucination validation: ensure film is in the original pool
    pool_slugs = {film.slug for film in state.movie_pool}
    if best_film.slug not in pool_slugs:
        return {
            "error": (
                f"Anti-hallucination violation: selected film "
                f"{best_film.slug} not in original pool"
            ),
            "recommendation": None,
            "fallback_used": True,
        }

    # Build reason tags and template
    reason_tags = build_reason_tags(state.mood_answers)
    era_enum = MoodEra(state.mood_answers.era.value)
    reason_template_key = get_reason_template_key(era_enum)
    user_profile_summary = build_user_profile_summary(state.mood_answers)

    # Calculate confidence (heuristic: base 0.7 + 0.03 per score point)
    confidence = min(1.0, 0.7 + (score * 0.03))

    # Build the recommendation detail
    recommendation = RecommendationDetail(
        film=best_film,
        reason_tags=reason_tags,  # type: ignore[arg-type]
        reason_template_key=reason_template_key,
        confidence=confidence,
        user_profile_summary=user_profile_summary,
    )

    return {
        "recommendation": recommendation,
        "fallback_used": True,  # Phase 3 initial: always deterministic
        "llm_used": state.llm_used,
        "llm_model": state.llm_model,
    }
