from fastapi import APIRouter

from app.application.services.recommendation_service import RecommendationService
from app.infrastructure.persistence.session import SessionLocal
from app.presentation.schemas.recommendation_schema import RecommendationResponse

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def _service() -> RecommendationService:
    return RecommendationService(SessionLocal)


@router.get("/{deck_id}", response_model=list[RecommendationResponse])
async def get_recommendations(deck_id: str):
    return _service().get_recommendations(deck_id)


@router.post("/{deck_id}/generate", response_model=list[RecommendationResponse])
async def generate_recommendations(deck_id: str):
    return _service().generate_recommendations(deck_id)
