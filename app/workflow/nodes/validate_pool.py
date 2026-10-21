"""Validate pool node - validates the input movie pool."""

from app.workflow.state import WorkflowState


def validate_pool(state: WorkflowState) -> dict:
    """
    Validate that the movie pool is not empty and normalize data.

    Returns updated state with:
    - validated_pool: the validated pool
    - pool_stats: statistics about the pool
    - error: if pool is empty
    """
    pool = state.movie_pool

    # Check if pool is empty
    if not pool or len(pool) == 0:
        return {
            "error": "Movie pool is empty",
            "validated_pool": [],
            "pool_stats": {"total": 0, "with_year": 0, "without_year": 0},
        }

    # Calculate statistics
    with_year = sum(1 for film in pool if film.release_year is not None)
    without_year = len(pool) - with_year

    # Deduplicate by slug (keep first occurrence)
    seen_slugs = set()
    deduplicated = []
    for film in pool:
        if film.slug not in seen_slugs:
            seen_slugs.add(film.slug)
            deduplicated.append(film)

    return {
        "validated_pool": deduplicated,
        "pool_stats": {
            "total": len(deduplicated),
            "with_year": with_year,
            "without_year": without_year,
        },
    }
