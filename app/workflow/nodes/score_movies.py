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

    If enriched_genres is available in the state, uses per-film genres
    for more accurate scoring. Otherwise falls back to pool-level genres.

    Returns:
        dict with scored_films sorted by (-score, slug ascending)
    """
    pool = state.validated_pool
    profile = state.user_profile
    answers = state.mood_answers
    pool_genres = set(state.pool_context.genres)
    enriched_genres = state.enriched_genres

    if not pool or not profile:
        return {"scored_films": []}

    era_enum = MoodEra(profile.era_filter)

    # Extract requested genre slug (if any)
    genre_slug = None
    if answers.genre != "ANY":
        genre_slug = answers.genre.replace("SPECIFIC_", "").lower()

    profile_genre_score = sum(profile.genre_weights.values())

    scored = []
    for film in pool:
        if not era_matches(era_enum, film.release_year):
            continue

        # Determine effective genres for this film
        if enriched_genres and film.slug in enriched_genres:
            effective_genres = set(enriched_genres[film.slug])
        else:
            effective_genres = pool_genres

        # Per-film soft scores based on effective genres
        energy_score = compute_genre_affinity_score(
            effective_genres, set(profile.energy_affinity.keys())
        )
        company_score = compute_genre_affinity_score(
            effective_genres, set(profile.company_affinity.keys())
        )

        # Genre bonus: higher when using enriched per-film genres
        genre_bonus = 0.0
        if genre_slug and genre_slug in effective_genres:
            genre_bonus = 1.0

        total_score = energy_score + company_score + genre_bonus + profile_genre_score
        scored.append((film, total_score))

    # Sort by (-score, slug ascending) for deterministic ordering
    scored.sort(key=lambda x: (-x[1], x[0].slug))

    return {"scored_films": scored}
