"""Pydantic schemas for API requests and responses."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# Enums matching mobile app domain models
class MoodEra(StrEnum):
    """Era preferences matching mobile app MoodEra enum."""

    ANY = "ANY"
    CLASSIC = "CLASSIC"  # ≤1979
    RETRO = "RETRO"  # 1980-1999
    MODERN = "MODERN"  # 2000-2014
    RECENT = "RECENT"  # 2015+


class MoodEnergy(StrEnum):
    """Energy level preferences."""

    HIGH = "HIGH"
    BALANCED = "BALANCED"
    LOW = "LOW"


class MoodCompany(StrEnum):
    """Company context preferences."""

    SOLO = "SOLO"
    DATE = "DATE"
    FRIENDS = "FRIENDS"
    FAMILY = "FAMILY"


class SearchMode(StrEnum):
    """Multi-user search mode."""

    UNION = "UNION"
    INTERSECTION = "INTERSECTION"


# Request models
class Film(BaseSchema):
    """Film model matching mobile app Film domain model."""

    slug: str = Field(..., description="Letterboxd film slug (unique identifier)")
    name: str = Field(..., description="Film title")
    release_year: int | None = Field(None, description="Release year (nullable)")
    image_url: str = Field(..., description="Poster image URL")


class MoodAnswers(BaseSchema):
    """User mood preferences from the questionnaire."""

    era: MoodEra = Field(..., description="Era preference")
    genre: str = Field(..., description="Genre preference (ANY or SPECIFIC_{genre})")
    energy: MoodEnergy = Field(..., description="Energy level preference")
    company: MoodCompany = Field(..., description="Company context preference")


class PoolContext(BaseSchema):
    """Context about the movie pool source."""

    user_names: list[str] = Field(default_factory=list, description="Usernames used for search")
    search_mode: SearchMode = Field(SearchMode.UNION, description="Multi-user search mode")
    genres: list[str] = Field(default_factory=list, description="Genre filters applied to pool")


class RecommendationRequest(BaseSchema):
    """Complete request for movie recommendation."""

    mood_answers: MoodAnswers
    movie_pool: list[Film]
    pool_context: PoolContext


# Response models
class ReasonTag(StrEnum):
    """Localizable reason tags matching mobile app MoodTag enum."""

    ERA_CLASSIC = "ERA_CLASSIC"
    ERA_RETRO = "ERA_RETRO"
    ERA_MODERN = "ERA_MODERN"
    ERA_RECENT = "ERA_RECENT"
    ERA_ANY = "ERA_ANY"
    ENERGY_HIGH = "ENERGY_HIGH"
    ENERGY_BALANCED = "ENERGY_BALANCED"
    ENERGY_LOW = "ENERGY_LOW"
    COMPANY_SOLO = "COMPANY_SOLO"
    COMPANY_DATE = "COMPANY_DATE"
    COMPANY_FRIENDS = "COMPANY_FRIENDS"
    COMPANY_FAMILY = "COMPANY_FAMILY"
    GENRE_MATCH = "GENRE_MATCH"


class RecommendationDetail(BaseSchema):
    """Detailed recommendation information."""

    film: Film
    reason_tags: list[ReasonTag] = Field(
        default_factory=list, description="Localizable reason tags"
    )
    reason_template_key: str = Field(..., description="String resource key for reason template")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    user_profile_summary: str = Field("", description="Summary of user preferences")


class RecommendationMetadata(BaseSchema):
    """Metadata about the recommendation process."""

    pool_size: int = Field(..., description="Total films in input pool")
    eligible_count: int = Field(..., description="Films that passed era filtering")
    llm_model: str | None = Field(None, description="LLM model used (if LLM layer active)")
    latency_ms: int = Field(..., description="Total processing time in milliseconds")
    enrichment_count: int = Field(0, description="Number of films enriched with per-film genres")


class RecommendationResponse(BaseSchema):
    """Complete recommendation response."""

    recommendation: RecommendationDetail
    fallback_used: bool = Field(False, description="Whether deterministic fallback was used")
    metadata: RecommendationMetadata
