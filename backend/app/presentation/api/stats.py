from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.application.services.stats_service import StatsService
from app.infrastructure.persistence.models import MatchORM
from app.infrastructure.persistence.session import SessionLocal, get_db
from app.presentation.schemas.stats_schema import MatchupStatsResponse, StatsResponse

router = APIRouter(prefix="/api/stats", tags=["stats"])


def _service() -> StatsService:
    return StatsService(SessionLocal)


@router.get("", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    service = _service()
    stats = service.get_stats()
    actual_count = db.query(func.count(MatchORM.match_id)).scalar()
    cached_count = stats.get("total_matches", 0) if stats else 0
    if stats is None or cached_count != actual_count:
        stats = service.compute_all_stats()
    return service.enrich_with_names(db, stats)


@router.get("/matchup", response_model=MatchupStatsResponse)
async def get_matchup_stats(
    self_leader: str,
    opp_leader: str,
    db: Session = Depends(get_db),
):
    service = _service()
    stats = service.get_stats()
    actual_count = db.query(func.count(MatchORM.match_id)).scalar()
    cached_count = stats.get("total_matches", 0) if stats else 0
    if stats is None or cached_count != actual_count:
        stats = service.compute_all_stats()
    key = f"{self_leader}_vs_{opp_leader}"
    winrate = stats.get("winrate_by_matchup", {}).get(key, 0)
    return MatchupStatsResponse(
        self_leader=self_leader,
        opp_leader=opp_leader,
        winrate=winrate,
    )


@router.get("/deck/{deck_id}")
async def get_deck_stats(deck_id: str, db: Session = Depends(get_db)):
    """Return aggregate stats filtered to a single deck version."""
    service = StatsService(SessionLocal)
    stats = service.compute_deck_stats(deck_id)
    if stats is None:
        raise HTTPException(status_code=404, detail="No matches found for this deck")
    return stats
