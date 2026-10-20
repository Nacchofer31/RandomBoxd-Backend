"""Pydantic schemas for API requests and responses (stub for Phase 2)."""

from pydantic import BaseModel

# TODO: Implement in Phase 2
# These will include:
# - MoodAnswers (era, genre, energy, company)
# - Film (slug, name, releaseYear, imageUrl)
# - PoolContext (userNames, searchMode, genres)
# - RecommendationRequest
# - RecommendationResponse


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = {"from_attributes": True}
