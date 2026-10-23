"""Pool enrichment endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.enrichment_service import EnrichmentService

router = APIRouter(prefix="/api/v1", tags=["enrich"])


class EnrichRequest(BaseModel):
    """Request to pre-enrich a pool of films with per-film genres."""

    slugs: list[str] = Field(..., min_length=1, max_length=500)


class EnrichResponse(BaseModel):
    """Response with enrichment results."""

    enriched_count: int = Field(..., description="Number of films successfully enriched")
    total_count: int = Field(..., description="Total slugs requested")
    results: dict[str, list[str]] = Field(
        ..., description="Mapping of slug to genres (empty list if no genres found)"
    )


@router.post("/enrich", response_model=EnrichResponse)
async def enrich_pool(
    request: EnrichRequest,
    db: AsyncSession | None = Depends(get_db),  # noqa: B008
) -> EnrichResponse:
    """
    Pre-enrich a pool of films with per-film genres from Letterboxd.

    This is optional — the /recommend endpoint will auto-enrich lazily.
    Use this endpoint to warm the cache before making recommendations,
    so recommendation latency is lower.

    Returns the genres found for each slug.
    """
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable — enrichment requires PostgreSQL",
        )

    service = EnrichmentService(db)
    results = await service.enrich_pool(request.slugs)

    enriched_count = sum(1 for genres in results.values() if genres)

    return EnrichResponse(
        enriched_count=enriched_count,
        total_count=len(request.slugs),
        results=results,
    )
