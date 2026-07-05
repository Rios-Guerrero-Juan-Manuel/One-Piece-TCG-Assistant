from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.domain.engines.match.statistics import StatisticsEngine
from app.domain.models import Action, Match, Player, Turn
from app.infrastructure.persistence.models import (
    CardORM,
    DeckORM,
    MatchORM,
    MatchStatsORM,
    MatchTurnORM,
)

_WIN_TOKENS = {"win", "won", "w", "victory"}
_LOSS_TOKENS = {"loss", "lose", "lost", "l", "defeat", "defeated"}

_STATS_ROW_ID = ""


class StatsService:
    """Aggregates match statistics and persists them to the database.

    A pseudo-primary key ``match_id=""`` is used to store the aggregate stats
    row in ``match_stats`` separate from any per-match computed stats.
    """

    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory
        self._engine = StatisticsEngine()

    def compute_all_stats(self) -> dict:
        session = self.session_factory()
        try:
            match_orms = session.query(MatchORM).all()
            matches = [self._orm_to_match(session, orm) for orm in match_orms]
            stats = self._engine.compute_stats(matches)
            self._persist_stats(session, stats)
            session.commit()
            return stats
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_stats(self) -> dict | None:
        session = self.session_factory()
        try:
            row = (
                session.query(MatchStatsORM)
                .filter(MatchStatsORM.match_id == _STATS_ROW_ID)
                .first()
            )
            return row.stats if row else None
        finally:
            session.close()

    def compute_deck_stats(self, deck_id: str) -> dict | None:
        """Compute stats for matches assigned to a specific deck version."""
        session = self.session_factory()
        try:
            match_orms = (
                session.query(MatchORM)
                .filter(MatchORM.deck_id_self == deck_id)
                .all()
            )
            if not match_orms:
                return None
            matches = [self._orm_to_match(session, orm) for orm in match_orms]
            return self._engine.compute_stats(matches)
        finally:
            session.close()

    def enrich_with_names(self, session: Session, stats: dict) -> dict:
        """Resolve card and deck IDs in stats to human-readable names.

        Adds ``card_names`` (card_id -> name) and ``deck_names`` (deck_id ->
        name) maps covering every identifier referenced by the stats payload.
        Names are resolved on read so renames propagate without recomputation.
        """
        card_ids: set[str] = set()
        card_ids.update(stats.get("winrate_by_leader", {}).keys())
        card_ids.update(stats.get("leaders_used", {}).keys())
        for opp_map in stats.get("winrate_by_deck_vs_opp_leader", {}).values():
            card_ids.update(opp_map.keys())
        for c in stats.get("most_played_cards", []):
            if c.get("card_id"):
                card_ids.add(c["card_id"])

        deck_ids: set[str] = set()
        deck_ids.update(stats.get("winrate_by_deck", {}).keys())
        deck_ids.update(stats.get("winrate_by_deck_vs_opp_leader", {}).keys())

        card_names: dict[str, str] = {}
        if card_ids:
            rows = (
                session.query(CardORM.card_id, CardORM.name)
                .filter(CardORM.card_id.in_(card_ids))
                .all()
            )
            card_names = {cid: name for cid, name in rows}

        deck_names: dict[str, str] = {}
        if deck_ids:
            rows = (
                session.query(DeckORM.deck_id, DeckORM.name)
                .filter(DeckORM.deck_id.in_(deck_ids))
                .all()
            )
            deck_names = {did: name for did, name in rows}

        stats = dict(stats)
        stats["card_names"] = card_names
        stats["deck_names"] = deck_names
        return stats

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
            deck_id_self=match_orm.deck_id_self,
        )

    @staticmethod
    def _orm_to_turn(turn_orm: MatchTurnORM) -> Turn:
        actions: list[Action] = []
        for card in turn_orm.cards_played or []:
            if isinstance(card, dict):
                actions.append(Action(
                    type="deploy",
                    card_id=card.get("card_id"),
                    cost=card.get("cost"),
                ))
            elif isinstance(card, str):
                actions.append(Action(type="deploy", card_id=card))
        for attack in turn_orm.attacks or []:
            if isinstance(attack, dict):
                actions.append(Action(
                    type="attack_resolve",
                    card_id=attack.get("card_id"),
                    target_card_id=attack.get("target_card_id"),
                    power=attack.get("power"),
                    counter_value=attack.get("counter_value"),
                ))
            elif isinstance(attack, str):
                actions.append(Action(type="attack_resolve", card_id=attack))
        for counter in turn_orm.counters or []:
            if isinstance(counter, dict):
                actions.append(Action(
                    type="counter",
                    card_id=counter.get("card_id"),
                    power=counter.get("power"),
                    counter_value=counter.get("counter_value"),
                ))
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

    def _persist_stats(self, session: Session, stats: dict) -> None:
        row = (
            session.query(MatchStatsORM)
            .filter(MatchStatsORM.match_id == _STATS_ROW_ID)
            .first()
        )
        if row is not None:
            row.stats = stats
        else:
            session.add(MatchStatsORM(match_id=_STATS_ROW_ID, stats=stats))
        session.flush()
