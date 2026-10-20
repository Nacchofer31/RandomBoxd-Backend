"""Movie recommendation endpoint."""

from fastapi import APIRouter, HTTPException

from app.models.schemas import RecommendationRequest, RecommendationResponse
from app.services.movie_service import EmptyPoolError, NoMatchError, movie_service

router = APIRouter(prefix="/api/v1", tags=["recommend"])


@router.post("/recommend", response_model=RecommendationResponse)
async def recommend_movie(request: RecommendationRequest) -> RecommendationResponse:
    """
    Recommend a movie based on mood answers and movie pool.

    Uses deterministic scoring engine (Phase 2).
    Will use LLM integration in Phase 3.
    """
    try:
        return await movie_service.recommend(request)
    except EmptyPoolError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NoMatchError as e:
        raise HTTPException(status_code=404, detail=str(e))
