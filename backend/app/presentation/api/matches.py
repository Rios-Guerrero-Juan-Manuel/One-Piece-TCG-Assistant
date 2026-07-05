import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.event_bus import get_event_bus
from app.core.config import settings
from app.domain.events import MatchImported
from app.infrastructure.importers.match_importer import MatchImporter, extract_match_date
from app.infrastructure.persistence.models import CardORM, MatchORM, MatchTurnORM
from app.infrastructure.persistence.repositories.deck_repo import DeckRepository
from app.infrastructure.persistence.repositories.settings_repo import SettingsRepository
from app.infrastructure.persistence.session import get_db
from app.presentation.schemas.match_schema import (
    BatchImportResponse,
    MatchDeckAssignmentRequest,
    MatchDetailResponse,
    MatchImportResponse,
    MatchListItemResponse,
    MatchListResponse,
    TurnResponse,
)

router = APIRouter(prefix="/api/matches", tags=["matches"])


def _build_card_names(
    match: MatchORM, turns: list[MatchTurnORM], db: Session
) -> dict[str, str]:
    """Collect every card_id referenced in a match and resolve it to a name."""
    ids: set[str] = set()
    if match.leader_self:
        ids.add(match.leader_self)
    if match.leader_opp:
        ids.add(match.leader_opp)
    for t in turns:
        for cp in (t.cards_played or []):
            cid = cp.get("card_id") if isinstance(cp, dict) else None
            if cid:
                ids.add(cid)
        for a in (t.attacks or []):
            if isinstance(a, dict):
                if a.get("attacker"):
                    ids.add(a["attacker"])
                if a.get("target"):
                    ids.add(a["target"])
                for c in (a.get("counters") or []):
                    if isinstance(c, dict) and c.get("card_id"):
                        ids.add(c["card_id"])
        for c in (t.counters or []):
            if isinstance(c, dict) and c.get("card_id"):
                ids.add(c["card_id"])
        state = t.state_end or {}
        for key in ("hand", "board", "trash", "opp_hand", "opp_board", "opp_trash"):
            val = state.get(key)
            if isinstance(val, list):
                ids.update(str(v) for v in val if v)

    if not ids:
        return {}
    rows = db.execute(
        select(CardORM.card_id, CardORM.name).where(CardORM.card_id.in_(ids))
    ).all()
    return {cid: name for cid, name in rows}


@router.get("", response_model=MatchListResponse)
async def list_matches(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    total = len(list(db.scalars(select(MatchORM))))
    matches = list(
        db.scalars(
            select(MatchORM)
            .order_by(
                MatchORM.played_at.desc(),
                MatchORM.imported_at.desc(),
                MatchORM.match_id.desc(),
            )
            .offset(skip)
            .limit(limit)
        )
    )
    return MatchListResponse(
        matches=[MatchListItemResponse.model_validate(m) for m in matches],
        total=total,
    )


@router.get("/{match_id}", response_model=MatchDetailResponse)
async def get_match(match_id: str, db: Session = Depends(get_db)):
    match = db.get(MatchORM, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    turns = list(
        db.scalars(
            select(MatchTurnORM)
            .where(MatchTurnORM.match_id == match_id)
            .order_by(MatchTurnORM.turn_no)
        )
    )
    return MatchDetailResponse(
        match_id=match.match_id,
        room_id=match.room_id,
        version=match.version,
        source_file=match.source_file,
        leader_self=match.leader_self,
        leader_opp=match.leader_opp,
        opponent_user=match.opponent_user,
        result=match.result,
        reason=match.reason,
        duration_turns=match.duration_turns,
        deck_id_self=match.deck_id_self,
        deck_id_opp=match.deck_id_opp,
        self_player_idx=match.self_player_idx,
        turns=[
            TurnResponse(
                turn_no=t.turn_no,
                player_idx=t.player_idx,
                don_drawn=t.don_drawn,
                don_unused=t.don_unused,
                cards_played=t.cards_played or [],
                attacks=t.attacks or [],
                counters=t.counters or [],
                errors=t.errors or [],
                state_end=t.state_end or {},
            )
            for t in turns
        ],
        card_names=_build_card_names(match, turns, db),
    )


@router.get("/{match_id}/analysis")
async def analyze_match(match_id: str, db: Session = Depends(get_db)):
    match = db.get(MatchORM, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    turns_orm = list(
        db.scalars(
            select(MatchTurnORM)
            .where(MatchTurnORM.match_id == match_id)
            .order_by(MatchTurnORM.turn_no)
        )
    )

    from app.domain.engines.match.turn_analyzer import TurnAnalyzer
    from app.domain.models import Turn

    turns_domain: list[Turn] = []
    for t in turns_orm:
        don_drawn = t.don_drawn or 0
        turns_domain.append(Turn(
            turn_no=t.turn_no,
            player_idx=t.player_idx,
            don_drawn=don_drawn,
            don_available=don_drawn,
            don_unused_at_end=t.don_unused or 0,
            actions=[],
            errors=list(t.errors or []),
            state_end=dict(t.state_end or {}),
        ))

    analyzer = TurnAnalyzer()
    analyzer.analyze_turns(turns_domain)
    all_issues: list[dict] = []
    for turn in turns_domain:
        for issue in turn.errors:
            all_issues.append({
                "turn": turn.turn_no,
                "player_idx": turn.player_idx,
                "description": issue,
            })

    return {
        "match_id": match_id,
        "total_issues": len(all_issues),
        "issues": all_issues,
    }


def _get_self_user(db: Session) -> str | None:
    repo = SettingsRepository(db)
    return repo.get("self_user", settings.self_user) or None


def _require_self_user(db: Session) -> str:
    """Return the configured self_user or raise HTTP 400."""
    self_user = _get_self_user(db)
    if not self_user:
        raise HTTPException(
            status_code=400,
            detail="You must configure your simulator username in Settings "
            "before importing matches.",
        )
    return self_user


@router.post("/import", response_model=MatchImportResponse)
async def import_match(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    self_user = _require_self_user(db)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)

    original_filename = file.filename or "uploaded.log"
    importer = MatchImporter()
    try:
        match = importer.import_file(
            tmp_path, self_user=self_user, original_filename=original_filename
        )
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to parse: {e}"
        ) from e
    finally:
        tmp_path.unlink(missing_ok=True)

    if match is None:
        raise HTTPException(status_code=400, detail="No match data found")

    get_event_bus().publish(
        "MatchImported",
        MatchImported(match_id=match.match_id),
    )

    self_leader = ""
    opp_leader = ""
    for p in match.players:
        if p.is_self:
            self_leader = p.leader_card_id
        else:
            opp_leader = p.leader_card_id
    if not self_leader and match.players:
        self_leader = match.players[0].leader_card_id
        if len(match.players) > 1:
            opp_leader = match.players[1].leader_card_id

    result_str = "unknown"
    if match.winner_idx is not None and match.players:
        self_idx = None
        for i, p in enumerate(match.players):
            if p.is_self:
                self_idx = i
                break
        if self_idx is None:
            self_idx = 0
        if match.winner_idx - 1 == self_idx:
            result_str = "win"
        else:
            result_str = "loss"

    match_date = extract_match_date(original_filename)

    match_orm = db.get(MatchORM, match.match_id)
    deck_id_self = None
    if match_orm:
        if match_orm.deck_id_self is None and self_leader:
            deck_id_self = DeckRepository(db).auto_assign_deck(self_leader, match_date)
            match_orm.deck_id_self = deck_id_self
            db.commit()
        else:
            deck_id_self = match_orm.deck_id_self
    deck_id_opp = None

    return MatchImportResponse(
        match_id=match.match_id,
        source_file=original_filename,
        result=result_str,
        turns=len(match.turns),
        leader_self=self_leader,
        leader_opp=opp_leader,
        deck_id_self=deck_id_self,
        deck_id_opp=deck_id_opp,
    )


@router.post("/import-batch", response_model=BatchImportResponse)
async def import_matches_batch(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    self_user = _require_self_user(db)
    importer = MatchImporter()

    results: list[dict] = []
    imported_count = 0
    error_count = 0

    for file in files:
        try:
            content = await file.read()
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("latin-1")

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(text)
                tmp_path = Path(tmp.name)

            original_filename = file.filename or "uploaded.log"
            try:
                match = importer.import_file(
                    tmp_path,
                    self_user=self_user,
                    original_filename=original_filename,
                )
                if match:
                    imported_count += 1
                    results.append({
                        "filename": original_filename,
                        "success": True,
                        "match_id": match.match_id,
                        "turns": len(match.turns),
                    })
                else:
                    error_count += 1
                    results.append({
                        "filename": original_filename,
                        "success": False,
                        "error": "No match data found",
                    })
            finally:
                tmp_path.unlink(missing_ok=True)
        except Exception as e:
            error_count += 1
            results.append({
                "filename": file.filename or "unknown",
                "success": False,
                "error": str(e),
            })

    if imported_count > 0:
        all_matches = list(db.scalars(select(MatchORM)))
        for m in all_matches:
            if m.deck_id_self is None and m.leader_self:
                match_date = extract_match_date(m.source_file) if m.source_file else None
                m.deck_id_self = DeckRepository(db).auto_assign_deck(m.leader_self, match_date)
        db.commit()

        get_event_bus().publish(
            "MatchImported",
            MatchImported(match_id="batch"),
        )

    return BatchImportResponse(
        imported=imported_count,
        errors=error_count,
        total=len(files),
        results=results,
    )


@router.post("/import-directory", response_model=BatchImportResponse)
async def import_directory(db: Session = Depends(get_db)):
    self_user = _require_self_user(db)

    importer = MatchImporter()
    result = importer.import_directory(self_user=self_user)

    all_matches = list(db.scalars(select(MatchORM)))
    for m in all_matches:
        if m.deck_id_self is None and m.leader_self:
            match_date = extract_match_date(m.source_file) if m.source_file else None
            m.deck_id_self = DeckRepository(db).auto_assign_deck(m.leader_self, match_date)
    db.commit()

    get_event_bus().publish(
        "MatchImported",
        MatchImported(match_id="batch"),
    )

    return BatchImportResponse(**result)


@router.put("/{match_id}/deck-assignment")
async def assign_match_deck(
    match_id: str,
    request: MatchDeckAssignmentRequest,
    db: Session = Depends(get_db),
):
    """Manually assign or change the deck associated with a match."""
    match = db.get(MatchORM, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.deck_id_self = request.deck_id_self
    match.deck_id_opp = request.deck_id_opp
    db.commit()

    return {
        "match_id": match_id,
        "deck_id_self": match.deck_id_self,
        "deck_id_opp": match.deck_id_opp,
    }


@router.post("/{match_id}/auto-assign-deck")
async def auto_assign_match_deck(match_id: str, db: Session = Depends(get_db)):
    """Auto-assign the player's deck to a match based on leader and match date.

    The opponent's deck is never guessed: the opponent's leader (from the log)
    is real data, but their decklist is unknown. Use the manual deck-assignment
    endpoint to annotate ``deck_id_opp`` if it is ever known.
    """
    match = db.get(MatchORM, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match_date = extract_match_date(match.source_file) if match.source_file else None

    if match.leader_self:
        match.deck_id_self = DeckRepository(db).auto_assign_deck(match.leader_self, match_date)

    db.commit()

    return {
        "match_id": match_id,
        "deck_id_self": match.deck_id_self,
        "deck_id_opp": match.deck_id_opp,
    }
