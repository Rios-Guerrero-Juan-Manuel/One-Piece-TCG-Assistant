from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    DeckORM,
    MatchORM,
    MatchTurnORM,
    MetaSnapshotORM,
)

_WIN_TOKENS = {"win", "won", "w", "victory"}


def _is_win(result: str | None) -> bool:
    return bool(result) and result.strip().lower() in _WIN_TOKENS


def _card_id_from_entry(entry) -> str | None:
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        cid = entry.get("card_id")
        if isinstance(cid, str):
            return cid
    return None


class MetaEngine:
    """Computes meta reports from imported matches and decks.

    The engine mirrors the ``StatsService`` style: it takes a session factory,
    opens a session, queries ORM rows directly, builds an aggregate report,
    and persists a JSON snapshot of the report on each ``compute_meta`` call.
    """

    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    # ------------------------------------------------------------------ public
    def compute_meta(self) -> dict:
        """Compute a meta report from matches + decks, persist a snapshot, return it."""
        session = self.session_factory()
        try:
            popular_decks = self._compute_popular_decks(session)
            winrates, leader_totals = self._compute_winrate_data(session)
            most_used_cards = self._compute_most_used_cards(session)
            emerging_cards, declining_cards = self._compute_card_trends(session)
            matchup_table = self._compute_matchup_table(session)
            meta_summary = self._compute_meta_summary(
                popular_decks,
                winrates,
                leader_totals,
                matchup_table,
            )
            report = {
                "popular_decks": popular_decks,
                "winrates": winrates,
                "most_used_cards": most_used_cards,
                "emerging_cards": emerging_cards,
                "declining_cards": declining_cards,
                "matchup_table": matchup_table,
                "meta_summary": meta_summary,
            }
            session.add(MetaSnapshotORM(snapshot=report))
            session.commit()
            return report
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_latest_snapshot(self) -> dict | None:
        """Return the latest persisted meta snapshot, or ``None`` if none exists."""
        session = self.session_factory()
        try:
            row = (
                session.query(MetaSnapshotORM)
                .order_by(MetaSnapshotORM.id.desc())
                .first()
            )
            return row.snapshot if row else None
        finally:
            session.close()

    # ----------------------------------------------------------- popular decks
    @staticmethod
    def _compute_popular_decks(session: Session) -> list[dict]:
        decks = session.query(DeckORM).all()
        groups: dict[str, list[str]] = {}
        for deck in decks:
            groups.setdefault(deck.leader_card_id, []).append(deck.name)
        result = [
            {
                "leader_card_id": leader,
                "deck_count": len(names),
                "deck_names": names,
            }
            for leader, names in groups.items()
        ]
        result.sort(key=lambda entry: entry["deck_count"], reverse=True)
        return result

    # ------------------------------------------------------------- winrate data
    @staticmethod
    def _compute_winrate_data(session: Session) -> tuple[dict[str, float], dict[str, int]]:
        matches = session.query(MatchORM).all()
        stats: dict[str, list[int]] = {}
        for match in matches:
            counters = stats.setdefault(match.leader_self, [0, 0])
            counters[1] += 1
            if _is_win(match.result):
                counters[0] += 1
        winrates = {
            leader: round(wins / total * 100, 2) if total else 0.0
            for leader, (wins, total) in stats.items()
        }
        totals = {leader: total for leader, (_wins, total) in stats.items()}
        return winrates, totals

    # --------------------------------------------------------- most used cards
    @staticmethod
    def _compute_most_used_cards(session: Session) -> list[dict]:
        turns = session.query(MatchTurnORM).all()
        counter: dict[str, int] = {}
        for turn in turns:
            for entry in turn.cards_played or []:
                cid = _card_id_from_entry(entry)
                if cid:
                    counter[cid] = counter.get(cid, 0) + 1
        items = sorted(counter.items(), key=lambda kv: kv[1], reverse=True)
        return [{"card_id": cid, "count": count} for cid, count in items[:20]]

    # ------------------------------------------------------------ card trends
    def _compute_card_trends(
        self,
        session: Session,
    ) -> tuple[list[dict], list[dict]]:
        matches = (
            session.query(MatchORM).order_by(MatchORM.imported_at).all()
        )
        if not matches:
            return [], []
        mid = len(matches) // 2
        older_ids = [m.match_id for m in matches[:mid]]
        newer_ids = [m.match_id for m in matches[mid:]]
        older_cards = self._count_cards_for_matches(session, older_ids)
        newer_cards = self._count_cards_for_matches(session, newer_ids)
        emerging = [
            {"card_id": cid, "count": count}
            for cid, count in newer_cards.items()
            if cid not in older_cards
        ]
        declining = [
            {"card_id": cid, "count": count}
            for cid, count in older_cards.items()
            if cid not in newer_cards
        ]
        emerging.sort(key=lambda entry: entry["count"], reverse=True)
        declining.sort(key=lambda entry: entry["count"], reverse=True)
        return emerging, declining

    @staticmethod
    def _count_cards_for_matches(
        session: Session,
        match_ids: list[str],
    ) -> dict[str, int]:
        if not match_ids:
            return {}
        turns = (
            session.query(MatchTurnORM)
            .filter(MatchTurnORM.match_id.in_(match_ids))
            .all()
        )
        counter: dict[str, int] = {}
        for turn in turns:
            for entry in turn.cards_played or []:
                cid = _card_id_from_entry(entry)
                if cid:
                    counter[cid] = counter.get(cid, 0) + 1
        return counter

    # ----------------------------------------------------------- matchup table
    @staticmethod
    def _compute_matchup_table(session: Session) -> dict[str, dict]:
        matches = session.query(MatchORM).all()
        stats: dict[tuple[str, str], list[int]] = {}
        for match in matches:
            key = (match.leader_self, match.leader_opp)
            counters = stats.setdefault(key, [0, 0])
            counters[1] += 1
            if _is_win(match.result):
                counters[0] += 1
        table: dict[str, dict] = {}
        for (self_leader, opp_leader), (wins, total) in stats.items():
            table.setdefault(self_leader, {})[opp_leader] = round(
                wins / total * 100 if total else 0.0, 2
            )
        return table

    # ----------------------------------------------------------- meta summary
    @staticmethod
    def _compute_meta_summary(
        popular_decks: list[dict],
        winrates: dict[str, float],
        leader_totals: dict[str, int],
        matchup_table: dict[str, dict],
    ) -> dict:
        most_popular = popular_decks[0]["leader_card_id"] if popular_decks else None
        total_decks = sum(d["deck_count"] for d in popular_decks)
        total_matches = sum(leader_totals.values())

        best_leader: str | None = None
        best_rate: float | None = None
        for leader, rate in winrates.items():
            if leader_totals.get(leader, 0) < 3:
                continue
            if best_rate is None or rate > best_rate:
                best_leader = leader
                best_rate = rate

        worst_matchup: dict | None = None
        worst_rate: float | None = None
        for self_leader, opps in matchup_table.items():
            for opp_leader, rate in opps.items():
                if worst_rate is None or rate < worst_rate:
                    worst_matchup = {
                        "self_leader": self_leader,
                        "opp_leader": opp_leader,
                        "winrate": rate,
                    }
                    worst_rate = rate

        return {
            "total_decks": total_decks,
            "total_matches": total_matches,
            "top_leader": best_leader or most_popular,
            "top_leader_winrate": best_rate,
            "most_popular_leader": most_popular,
            "best_performing_leader": best_leader,
            "worst_matchup": worst_matchup,
        }
