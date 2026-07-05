from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.application.services.global_meta_service import GlobalMetaService
from app.application.services.meta_engine import MetaEngine
from app.application.services.pattern_service import PatternService
from app.infrastructure.api_client.optcg_meta_client import OptcgMetaClient
from app.infrastructure.persistence.session import SessionLocal, get_db
from app.presentation.schemas.meta_schema import (
    GlobalLeaderStat,
    GlobalMetaResponse,
    MetaReportResponse,
)

router = APIRouter(prefix="/api/meta", tags=["meta"])


def _engine() -> MetaEngine:
    return MetaEngine(SessionLocal)


def _pattern_service() -> PatternService:
    return PatternService(SessionLocal)


_meta_client: OptcgMetaClient | None = None


def _global_service() -> GlobalMetaService:
    global _meta_client
    if _meta_client is None:
        _meta_client = OptcgMetaClient()
    return GlobalMetaService(_meta_client)


@router.get("/report", response_model=MetaReportResponse)
async def get_meta_report(db: Session = Depends(get_db)):
    engine = _engine()
    snapshot = engine.get_latest_snapshot()
    if snapshot is None:
        snapshot = engine.compute_meta()
    return snapshot


@router.get("/decks")
async def get_popular_decks(db: Session = Depends(get_db)):
    engine = _engine()
    snapshot = engine.get_latest_snapshot()
    if snapshot is None:
        snapshot = engine.compute_meta()
    return snapshot.get("popular_decks", [])


@router.post("/compute", response_model=MetaReportResponse)
async def compute_meta(db: Session = Depends(get_db)):
    engine = _engine()
    return engine.compute_meta()


@router.get("/patterns")
async def get_patterns(db: Session = Depends(get_db)):
    service = _pattern_service()
    return service.get_patterns()


@router.post("/patterns/detect")
async def detect_patterns(db: Session = Depends(get_db)):
    service = _pattern_service()
    return service.detect_and_save()


@router.get("/global", response_model=GlobalMetaResponse)
async def get_global_meta(
    region: str = Query("west", pattern=r"^(west|west\+|west\+\+|east|east\+)$"),
    view: str = Query("overall", pattern=r"^(overall|winrate|steady)$"),
    turn: str = Query("combined", pattern=r"^(combined|first|second)$"),
):
    service = _global_service()
    result = service.get_global_meta(region=region, view=view, turn_order=turn)
    return GlobalMetaResponse(
        leaders=[
            GlobalLeaderStat(
                card_id=leader.card_id,
                name=leader.name,
                image_url=leader.image_url,
                wins=leader.wins,
                losses=leader.losses,
                matches=leader.matches,
                winrate=leader.winrate,
                bayesian_winrate=leader.bayesian_winrate,
                tier=leader.tier,
                avg_matchup_wr=leader.avg_matchup_wr,
                balance_score=leader.balance_score,
                overall_score=leader.overall_score,
            )
            for leader in result.leaders
        ],
        tiers=result.tiers,
        total_matches=result.total_matches,
        total_wins=result.total_wins,
        total_losses=result.total_losses,
        timestamp=result.timestamp,
        region=result.region,
        ranking=result.ranking,
        game_mode=result.game_mode,
    )


@router.get("/global/matrix")
async def get_global_matrix(
    region: str = Query("west", pattern=r"^(west|west\+|west\+\+|east|east\+)$"),
    turn: str = Query("combined", pattern=r"^(combined|first|second)$"),
):
    service = _global_service()
    return service.get_matchup_matrix(region=region, turn_order=turn)
