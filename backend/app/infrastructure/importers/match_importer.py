import datetime
import logging
import re
from pathlib import Path

from sqlalchemy import select

from app.domain.engines.match.turn_analyzer import TurnAnalyzer
from app.domain.models import Action, Match
from app.domain.parser.match_parser import MatchParser, _normalize_user, _user_is_self
from app.infrastructure.persistence.models import CardORM, MatchORM, MatchTurnORM
from app.infrastructure.persistence.session import SessionLocal, init_db

logger = logging.getLogger(__name__)

LOGS_DIR = Path(__file__).resolve().parents[4] / "Datos" / "CombatLogs"


def extract_match_date(source_file: str) -> datetime.datetime | None:
    """Extract date from match source filename like '2026-06-23T18_20_36.txt'."""
    match = re.search(r"(\d{4}-\d{2}-\d{2})[T_](\d{2})[_\.](\d{2})[_\.](\d{2})", source_file)
    if match:
        try:
            return datetime.datetime(
                int(match.group(1)[:4]),
                int(match.group(1)[5:7]),
                int(match.group(1)[8:10]),
                int(match.group(2)),
                int(match.group(3)),
                int(match.group(4)),
            )
        except (ValueError, IndexError):
            return None
    return None


def _build_attacks(
    actions: list[Action], name_map: dict[str, str]
) -> tuple[list[dict], list[dict]]:
    """Group raw actions into complete attack objects with outcomes and nested counters.

    Each attack embeds the counters used by the defender during that combat and
    its resolution (hit / failed / destroyed). The ``vs`` (attack_resolve) line
    is treated as the authoritative source for the two cards and their powers.

    Returns ``(attacks, loose_counters)``: counters that appear without a
    preceding attack declaration are returned separately.
    """
    attacks: list[dict] = []
    pending: dict | None = None
    loose_counters: list[dict] = []

    def _new_pending(attacker=None, target=None) -> dict:
        return {
            "attacker": attacker,
            "attacker_name": name_map.get(attacker) if attacker else None,
            "target": target,
            "target_name": name_map.get(target) if target else None,
            "attacker_power": None,
            "defender_power": None,
            "result": None,
            "damage": None,
            "counters": [],
        }

    def _close() -> None:
        nonlocal pending
        if pending is not None:
            attacks.append(pending)
            pending = None

    for a in actions:
        if a.type == "attack":
            _close()
            pending = _new_pending(a.card_id, a.target_card_id)
        elif a.type == "attack_resolve":
            if pending is None:
                pending = _new_pending(a.card_id, a.target_card_id)
            if a.card_id:
                pending["attacker"] = a.card_id
                pending["attacker_name"] = name_map.get(a.card_id)
            if a.target_card_id:
                pending["target"] = a.target_card_id
                pending["target_name"] = name_map.get(a.target_card_id)
            pending["attacker_power"] = a.power
            pending["defender_power"] = a.counter_value
        elif a.type == "counter":
            counter = {
                "card_id": a.card_id,
                "name": name_map.get(a.card_id) if a.card_id else None,
                "value": a.counter_value,
                "actor": a.actor,
            }
            if pending is not None:
                pending["counters"].append(counter)
            else:
                loose_counters.append(counter)
        elif a.type == "damage":
            if pending is not None:
                pending["result"] = "hit"
                pending["damage"] = a.amount if a.amount is not None else 1
                _close()
        elif a.type == "attack_fail":
            if pending is not None:
                pending["result"] = "failed"
                _close()
        elif a.type == "destroy":
            if pending is not None:
                pending["result"] = "destroyed"
                _close()
    _close()
    return attacks, loose_counters


class MatchImporter:
    def __init__(self, parser: MatchParser | None = None):
        self.parser = parser or MatchParser()
        self.turn_analyzer = TurnAnalyzer()

    def import_file(
        self,
        file_path: Path,
        self_user: str | None = None,
        original_filename: str | None = None,
    ) -> Match | None:
        text = file_path.read_text(encoding="utf-8")
        match = self.parser.parse(text, self_user=self_user)
        if original_filename:
            match.source_file = original_filename
            match.match_id = Path(original_filename).stem
        else:
            match.source_file = file_path.name
            match.match_id = file_path.stem

        self.turn_analyzer.analyze_turns(match.turns)

        self._save(match, self_user=self_user)
        return match

    def import_directory(
        self,
        directory: Path | None = None,
        self_user: str | None = None,
    ) -> dict:
        init_db()
        directory = directory or LOGS_DIR
        all_files = []
        for f in sorted(directory.iterdir()):
            if f.is_file() and f.suffix in (".txt", ".log"):
                all_files.append(f)
        auto_saved = directory / "AutoSaved"
        if auto_saved.is_dir():
            for f in sorted(auto_saved.iterdir()):
                if f.is_file() and f.suffix in (".txt", ".log"):
                    all_files.append(f)

        imported = 0
        errors = 0
        for f in all_files:
            try:
                m = self.import_file(f, self_user=self_user)
                if m:
                    imported += 1
            except Exception:
                logger.exception("Failed to import %s", f)
                errors += 1

        return {"imported": imported, "errors": errors, "total": len(all_files)}

    def _save(self, match: Match, self_user: str | None = None) -> None:
        session = SessionLocal()
        try:
            existing = session.get(MatchORM, match.match_id)
            if existing:
                session.query(MatchTurnORM).filter(
                    MatchTurnORM.match_id == match.match_id
                ).delete()
                session.delete(existing)
                session.flush()

            self_player = None
            opp_player = None
            self_player_idx = None
            for i, p in enumerate(match.players):
                if p.is_self:
                    self_player = p
                    self_player_idx = i + 1
                else:
                    opp_player = p

            if self_player is None and match.players:
                if self_user:
                    norm_self = _normalize_user(self_user)
                    for i, p in enumerate(match.players):
                        if _user_is_self(norm_self, _normalize_user(p.user)):
                            self_player = p
                            self_player_idx = i + 1
                            opp_player = match.players[1 - i] if len(match.players) > 1 else None
                            break
                if self_player is None:
                    logger.warning(
                        "No self_player identified for %s — falling back to "
                        "players[0]. Check SELF_USER setting.",
                        match.match_id,
                    )
                    self_player = match.players[0]
                    self_player_idx = 1
                    if len(match.players) > 1:
                        opp_player = match.players[1]

            if self_player is None:
                self_player = match.players[0] if match.players else None

            leader_self = self_player.leader_card_id if self_player else ""
            leader_opp = opp_player.leader_card_id if opp_player else ""

            result = "unknown"
            if match.winner_idx is not None:
                if self_player and match.players:
                    self_idx = None
                    for i, p in enumerate(match.players):
                        if p.is_self:
                            self_idx = i
                            break
                    if self_idx is None:
                        self_idx = 0
                    if match.winner_idx - 1 == self_idx:
                        result = "win"
                    else:
                        result = "loss"

            # Collect every card id referenced in the match to resolve names in
            # a single query, so the frontend needs no extra requests.
            all_card_ids: set[str] = set()
            if leader_self:
                all_card_ids.add(leader_self)
            if leader_opp:
                all_card_ids.add(leader_opp)
            for turn in match.turns:
                for a in turn.actions:
                    if a.card_id:
                        all_card_ids.add(a.card_id)
                    if a.target_card_id:
                        all_card_ids.add(a.target_card_id)
                for key in ("hand", "board", "trash", "opp_hand", "opp_board", "opp_trash"):
                    val = turn.state_end.get(key)
                    if isinstance(val, list):
                        all_card_ids.update(val)

            name_map: dict[str, str] = {}
            if all_card_ids:
                rows = session.execute(
                    select(CardORM.card_id, CardORM.name).where(
                        CardORM.card_id.in_(all_card_ids)
                    )
                ).all()
                name_map = {cid: name for cid, name in rows}

            played_dt = extract_match_date(match.source_file)
            match_orm = MatchORM(
                match_id=match.match_id,
                room_id=match.room_id,
                version=match.version,
                source_file=match.source_file,
                leader_self=leader_self,
                leader_opp=leader_opp,
                opponent_user=opp_player.user if opp_player else None,
                result=result,
                reason=match.reason,
                duration_turns=match.duration_turns,
                played_at=played_dt.isoformat() if played_dt else None,
                self_player_idx=self_player_idx,
            )
            session.add(match_orm)

            for turn in match.turns:
                attacks, loose_counters = _build_attacks(turn.actions, name_map)
                cards_played = [
                    {
                        "card_id": a.card_id,
                        "name": name_map.get(a.card_id) if a.card_id else None,
                    }
                    for a in turn.actions
                    if a.type == "deploy"
                ]

                turn_orm = MatchTurnORM(
                    match_id=match.match_id,
                    turn_no=turn.turn_no,
                    player_idx=turn.player_idx,
                    don_drawn=turn.don_drawn,
                    don_unused=turn.don_unused_at_end,
                    cards_played=cards_played,
                    attacks=attacks,
                    counters=loose_counters,
                    errors=turn.errors,
                    state_end=turn.state_end or {},
                )
                session.add(turn_orm)

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
