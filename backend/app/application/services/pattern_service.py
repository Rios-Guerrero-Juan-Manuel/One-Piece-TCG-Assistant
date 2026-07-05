from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.application.event_bus import get_event_bus
from app.domain.engines.match.pattern_detector import PatternDetector
from app.domain.events import PatternsDetected
from app.domain.models import Action, Match, Player, Turn
from app.infrastructure.persistence.models import MatchORM, MatchTurnORM, PatternORM

_WIN_TOKENS = {"win", "won", "w", "victory"}
_LOSS_TOKENS = {"loss", "lose", "lost", "l", "defeat", "defeated"}


class PatternService:
    """Fetches matches from DB, detects patterns, persists them, publishes event."""

    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory
        self._detector = PatternDetector()

    def detect_and_save(self) -> list[dict]:
        """Fetch all matches from DB, detect patterns, save to patterns table, publish event."""
        session = self.session_factory()
        try:
            match_orms = session.query(MatchORM).all()
            matches = [self._orm_to_match(session, orm) for orm in match_orms]
            patterns = self._detector.detect_patterns(matches)
            self._persist_patterns(session, patterns)
            session.commit()
            get_event_bus().publish(
                "PatternsDetected",
                PatternsDetected(pattern_count=len(patterns)),
            )
            return patterns
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_patterns(self) -> list[dict]:
        """Get persisted patterns from DB."""
        session = self.session_factory()
        try:
            rows = session.query(PatternORM).all()
            return [
                {
                    "pattern_id": r.pattern_id,
                    "filter": dict(r.filter or {}),
                    "description": r.description,
                    "severity": r.severity,
                }
                for r in rows
            ]
        finally:
            session.close()

    def _orm_to_match(self, session: Session, match_orm: MatchORM) -> Match:
        turns_orm = (
            session.query(MatchTurnORM)
            .filter(MatchTurnORM.match_id == match_orm.match_id)
            .order_by(MatchTurnORM.turn_no)
            .all()
        )
        turns = [self._orm_to_turn(t) for t in turns_orm]
        players = [
            Player(
                user="self",
                leader_card_id=match_orm.leader_self,
                goes_first=True,
                is_self=True,
            ),
            Player(
                user=match_orm.opponent_user or "opponent",
                leader_card_id=match_orm.leader_opp,
                goes_first=False,
                is_self=False,
            ),
        ]
        winner_idx = self._resolve_winner_idx(match_orm.result)
        return Match(
            match_id=match_orm.match_id,
            room_id=match_orm.room_id,
            version=match_orm.version,
            source_file=match_orm.source_file,
            players=players,
            turns=turns,
            winner_idx=winner_idx,
            reason=match_orm.reason,
            duration_turns=match_orm.duration_turns,
        )

    @staticmethod
    def _orm_to_turn(turn_orm: MatchTurnORM) -> Turn:
        actions: list[Action] = []
        for card in turn_orm.cards_played or []:
            if isinstance(card, dict):
                actions.append(
                    Action(
                        type="deploy",
                        card_id=card.get("card_id"),
                        cost=card.get("cost"),
                    )
                )
            elif isinstance(card, str):
                actions.append(Action(type="deploy", card_id=card))
        for attack in turn_orm.attacks or []:
            if isinstance(attack, dict):
                actions.append(
                    Action(
                        type="attack_resolve",
                        card_id=attack.get("card_id"),
                        target_card_id=attack.get("target_card_id"),
                        power=attack.get("power"),
                        counter_value=attack.get("counter_value"),
                    )
                )
            elif isinstance(attack, str):
                actions.append(Action(type="attack_resolve", card_id=attack))
        for counter in turn_orm.counters or []:
            if isinstance(counter, dict):
                actions.append(
                    Action(
                        type="counter",
                        card_id=counter.get("card_id"),
                        power=counter.get("power"),
                        counter_value=counter.get("counter_value"),
                    )
                )
            elif isinstance(counter, str):
                actions.append(Action(type="counter", card_id=counter))
        don_drawn = turn_orm.don_drawn or 0
        return Turn(
            turn_no=turn_orm.turn_no,
            player_idx=turn_orm.player_idx,
            don_drawn=don_drawn,
            don_available=don_drawn,
            don_unused_at_end=turn_orm.don_unused or 0,
            actions=actions,
            errors=list(turn_orm.errors or []),
            state_end=dict(turn_orm.state_end or {}),
        )

    @staticmethod
    def _resolve_winner_idx(result: str | None) -> int | None:
        if result is None:
            return None
        normalized = result.strip().lower()
        if normalized in _WIN_TOKENS:
            return 0
        if normalized in _LOSS_TOKENS:
            return 1
        return None

    @staticmethod
    def _persist_patterns(session: Session, patterns: list[dict]) -> None:
        session.query(PatternORM).delete()
        for p in patterns:
            session.add(
                PatternORM(
                    pattern_id=p["pattern_id"],
                    filter=p["filter"],
                    description=p["description"],
                    severity=p["severity"],
                )
            )
        session.flush()
