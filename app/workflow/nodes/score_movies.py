"""Score movies node - applies deterministic scoring to the pool."""

from app.core.scoring import (
    compute_genre_affinity_score,
    era_matches,
)
from app.models.schemas import MoodEra
from app.workflow.state import WorkflowState


def score_movies(state: WorkflowState) -> dict:
    """
    Score all films in the validated pool based on the user profile.

    Era is a hard gate (eligibility filter).
    Energy, company, and genre are soft weights applied at pool level.

    Returns:
        dict with scored_films sorted by (-score, slug ascending)
    """
    pool = state.validated_pool
    profile = state.user_profile
    answers = state.mood_answers
    pool_genres = set(state.pool_context.genres)

    if not pool or not profile:
        return {"scored_films": []}

    # Compute pool-level soft scores
    energy_score = compute_genre_affinity_score(pool_genres, set(profile.energy_affinity.keys()))
    company_score = compute_genre_affinity_score(pool_genres, set(profile.company_affinity.keys()))
    base_score = energy_score + company_score

    # Add specific genre bonus if requested
    genre_bonus = 0.0
    if answers.genre != "ANY":
        # Extract genre slug from SPECIFIC_XXX format
        genre_slug = answers.genre.replace("SPECIFIC_", "").lower()
        if genre_slug in pool_genres:
            genre_bonus = 1.0

    # Add profile-level genre weights (from LLM or deterministic)
    profile_genre_score = sum(profile.genre_weights.values())

    total_base = base_score + genre_bonus + profile_genre_score

    # Apply era filter (hard gate) and assign scores
    scored = []
    era_enum = MoodEra(profile.era_filter)

    for film in pool:
        if not era_matches(era_enum, film.release_year):
            continue
        scored.append((film, total_base))

    # Sort by (-score, slug ascending) for deterministic ordering
    scored.sort(key=lambda x: (-x[1], x[0].slug))

    return {"scored_films": scored}
