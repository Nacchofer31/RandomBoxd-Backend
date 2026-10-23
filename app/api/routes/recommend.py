"""Movie recommendation endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schemas import RecommendationRequest, RecommendationResponse
from app.services.movie_service import EmptyPoolError, NoMatchError, movie_service

router = APIRouter(prefix="/api/v1", tags=["recommend"])


@router.post("/recommend", response_model=RecommendationResponse)
async def recommend_movie(
    request: RecommendationRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> RecommendationResponse:
    """
    Recommend a movie based on mood answers and movie pool.

    Uses deterministic scoring engine with optional pool enrichment.
    If DB is available, enriches pool with per-film genres before scoring.
    """
    try:
        return await movie_service.recommend(request, db=db)
    except EmptyPoolError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except NoMatchError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
