
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.application.services.matching_service import MatchingService
from app.core.config import BASE_DIR
from app.infrastructure.persistence.repositories.card_repo import CardRepository
from app.infrastructure.persistence.session import get_db
from app.presentation.schemas.card_schema import (
    CardListResponse,
    CardResponse,
    CardSimilarityResponse,
    CardSimilarListResponse,
)

router = APIRouter(prefix="/api/cards", tags=["cards"])


@router.get("", response_model=CardListResponse)
async def list_cards(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    color: str | None = None,
    type: str | None = None,
    cost: int | None = None,
    traits: str | None = None,
    db: Session = Depends(get_db),
):
    repo = CardRepository(db)
    filters: dict = {}
    if color:
        filters["color"] = color
    if type:
        filters["type"] = type
    if cost is not None:
        filters["cost"] = cost
    if traits:
        filters["traits"] = traits
    cards, total = repo.get_all(skip=skip, limit=limit, filters=filters)
    return CardListResponse(
        cards=[CardResponse.model_validate(c) for c in cards],
        total=total,
    )


@router.get("/search", response_model=CardListResponse)
async def search_cards(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    repo = CardRepository(db)
    cards = repo.search(q, limit=limit)
    return CardListResponse(
        cards=[CardResponse.model_validate(c) for c in cards],
        total=len(cards),
    )


@router.get("/{card_id}", response_model=CardResponse)
async def get_card(card_id: str, db: Session = Depends(get_db)):
    repo = CardRepository(db)
    card = repo.get_by_id(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return CardResponse.model_validate(card)


@router.get("/{card_id}/similar", response_model=CardSimilarListResponse)
async def get_similar_cards(
    card_id: str,
    top_k: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    repo = CardRepository(db)
    card = repo.get_by_id(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    service = MatchingService()
    results = service.find_similar(card_id, top_k=top_k)
    return CardSimilarListResponse(
        query_card_id=card_id,
        results=[CardSimilarityResponse(**r) for r in results],
    )


_LOCAL_IMAGES = BASE_DIR.parent / "Datos" / "1.40a" / "Cards"


@router.get("/{card_id}/image")
async def get_card_image(card_id: str, db: Session = Depends(get_db)):
    """Serve card image: optcgapi.com URL or local fallback from Datos/1.40a/Cards/."""
    repo = CardRepository(db)
    card = repo.get_by_id(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    local_path = _LOCAL_IMAGES / f"{card_id}.jpg"
    if local_path.exists():
        return FileResponse(str(local_path), media_type="image/jpeg")

    raise HTTPException(status_code=404, detail="Image not available locally")
