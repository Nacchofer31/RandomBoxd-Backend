"""Deterministic scoring engine for movie recommendations.

This is the fallback engine that always works, even without LLM.
Based on the mobile app's MoodResolver logic (see Engram randomboxd project).

Key design decisions:
- Era is a HARD GATE (eligibility filter), not a scoring component
- Energy and company are SOFT WEIGHTS applied at pool level
- Genre affinity is pool-level (we don't have per-film genres)
- Tie-break is deterministic: (-score, slug ascending)
"""

from app.models.schemas import Film, MoodAnswers, MoodCompany, MoodEnergy, MoodEra

# Genre affinity weights for energy levels
ENERGY_GENRE_WEIGHTS: dict[MoodEnergy, set[str]] = {
    MoodEnergy.HIGH: {
        "action",
        "adventure",
        "thriller",
        "horror",
        "science-fiction",
        "war",
        "crime",
        "western",
        "mystery",
    },
    MoodEnergy.LOW: {
        "drama",
        "romance",
        "documentary",
        "family",
        "music",
        "history",
    },
    MoodEnergy.BALANCED: set(),  # Neutral, no affinity
}

# Genre affinity weights for company context
COMPANY_GENRE_WEIGHTS: dict[MoodCompany, set[str]] = {
    MoodCompany.DATE: {"romance", "drama", "comedy"},
    MoodCompany.FAMILY: {"animation", "family", "adventure", "comedy"},
    MoodCompany.FRIENDS: {"comedy", "horror", "action", "thriller"},
    MoodCompany.SOLO: set(),  # Neutral, no affinity
}

# Score values for affinity matches
WEIGHT_PER_MATCH: float = 1.0

# Era year ranges
ERA_RANGES: dict[MoodEra, tuple[int | None, int | None]] = {
    MoodEra.CLASSIC: (None, 1979),
    MoodEra.RETRO: (1980, 1999),
    MoodEra.MODERN: (2000, 2014),
    MoodEra.RECENT: (2015, None),
    MoodEra.ANY: (None, None),
}

# Reason template keys
REASON_TEMPLATE_KEYS: dict[str, str] = {
    MoodEra.CLASSIC: "mood_reason_classic",
    MoodEra.RETRO: "mood_reason_retro",
    MoodEra.MODERN: "mood_reason_modern",
    MoodEra.RECENT: "mood_reason_recent",
    MoodEra.ANY: "mood_reason_any",
}


def era_matches(era: MoodEra, release_year: int | None) -> bool:
    """Check if a film's release year matches the era filter.

    Films with null releaseYear are only eligible for ANY era.
    """
    if era == MoodEra.ANY:
        return True

    if release_year is None:
        return False

    min_year, max_year = ERA_RANGES[era]
    if min_year is not None and release_year < min_year:
        return False
    return not (max_year is not None and release_year > max_year)


def compute_genre_affinity_score(
    pool_genres: set[str], affinity_genres: set[str]
) -> float:
    """Compute pool-level genre affinity score.

    Counts how many pool genres match the affinity set.
    """
    if not affinity_genres:
        return 0.0
    matches = pool_genres & affinity_genres
    return len(matches) * WEIGHT_PER_MATCH


def score_films(
    pool: list[Film],
    answers: MoodAnswers,
    pool_genres: set[str],
) -> list[tuple[Film, float]]:
    """Score all films in the pool based on mood answers.

    Returns a list of (film, score) tuples sorted by:
    1. Score descending (best first)
    2. Slug ascending (deterministic tie-break)

    Films that don't pass the era filter are excluded entirely.
    """
    scored: list[tuple[Film, float]] = []

    energy_affinity = ENERGY_GENRE_WEIGHTS.get(answers.energy, set())
    company_affinity = COMPANY_GENRE_WEIGHTS.get(answers.company, set())

    energy_score = compute_genre_affinity_score(pool_genres, energy_affinity)
    company_score = compute_genre_affinity_score(pool_genres, company_affinity)
    base_score = energy_score + company_score

    for film in pool:
        if not era_matches(answers.era, film.release_year):
            continue  # Hard gate: era filter
        scored.append((film, base_score))

    # Sort by (-score, slug) for deterministic ordering
    scored.sort(key=lambda x: (-x[1], x[0].slug))
    return scored


def build_reason_tags(answers: MoodAnswers) -> list[str]:
    """Build the list of reason tags based on mood answers.

    These tags are used by the mobile app to render localized reason text.
    """
    tags: list[str] = []

    # Era tag
    era_tag_map = {
        MoodEra.CLASSIC: "ERA_CLASSIC",
        MoodEra.RETRO: "ERA_RETRO",
        MoodEra.MODERN: "ERA_MODERN",
        MoodEra.RECENT: "ERA_RECENT",
        MoodEra.ANY: "ERA_ANY",
    }
    tags.append(era_tag_map[answers.era])

    # Energy tag
    energy_tag_map = {
        MoodEnergy.HIGH: "ENERGY_HIGH",
        MoodEnergy.BALANCED: "ENERGY_BALANCED",
        MoodEnergy.LOW: "ENERGY_LOW",
    }
    tags.append(energy_tag_map[answers.energy])

    # Company tag
    company_tag_map = {
        MoodCompany.SOLO: "COMPANY_SOLO",
        MoodCompany.DATE: "COMPANY_DATE",
        MoodCompany.FRIENDS: "COMPANY_FRIENDS",
        MoodCompany.FAMILY: "COMPANY_FAMILY",
    }
    tags.append(company_tag_map[answers.company])

    # Genre match tag (if specific genre requested)
    if answers.genre != "ANY":
        tags.append("GENRE_MATCH")

    return tags


def get_reason_template_key(era: MoodEra) -> str:
    """Get the string resource key for the reason template."""
    return REASON_TEMPLATE_KEYS[era]


def build_user_profile_summary(answers: MoodAnswers) -> str:
    """Build a human-readable summary of user preferences.

    Note: This is for metadata/debugging only. The mobile app uses
    reason_tags + templates for actual user-facing text.
    """
    parts: list[str] = []

    era_descriptions = {
        MoodEra.ANY: "any era",
        MoodEra.CLASSIC: "classic films (pre-1980)",
        MoodEra.RETRO: "retro films (1980s-1990s)",
        MoodEra.MODERN: "modern films (2000-2014)",
        MoodEra.RECENT: "recent films (2015+)",
    }
    parts.append(era_descriptions[answers.era])

    if answers.genre != "ANY":
        genre_name = answers.genre.replace("SPECIFIC_", "").lower().replace("_", " ")
        parts.append(f"{genre_name} genre")

    energy_descriptions = {
        MoodEnergy.HIGH: "high energy",
        MoodEnergy.BALANCED: "balanced energy",
        MoodEnergy.LOW: "low energy / relaxed",
    }
    parts.append(energy_descriptions[answers.energy])

    company_descriptions = {
        MoodCompany.SOLO: "solo viewing",
        MoodCompany.DATE: "date night",
        MoodCompany.FRIENDS: "with friends",
        MoodCompany.FAMILY: "with family",
    }
    parts.append(company_descriptions[answers.company])

    return ", ".join(parts)
