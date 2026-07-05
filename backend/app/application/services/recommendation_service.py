from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.application.event_bus import get_event_bus
from app.domain.engines.recommendation.recommendation_engine import RecommendationEngine
from app.domain.events import DeckUpdated
from app.domain.models import Card, Deck
from app.infrastructure.persistence.mappers import orm_to_card
from app.infrastructure.persistence.models import (
    CardORM,
    CollectionORM,
    DeckCardORM,
    DeckORM,
    PatternORM,
    RecommendationORM,
)

logger = logging.getLogger(__name__)


class RecommendationService:
    """Orchestrates RecommendationEngine: loads data from DB, generates
    recommendations, persists them, and publishes events.
    """

    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory
        self._engine = RecommendationEngine()

    def generate_recommendations(self, deck_id: str) -> list[dict]:
        session = self.session_factory()
        try:
            deck = self._load_deck(session, deck_id)
            if deck is None:
                return []
            cards = self._load_all_cards(session)
            collection = self._load_collection(session)
            patterns = self._load_patterns(session)
            recs = self._engine.recommend(
                deck=deck,
                cards=cards,
                collection=collection,
                patterns=patterns,
            )
            self._persist_recommendations(session, deck_id, recs)
            session.commit()
            get_event_bus().publish(
                "DeckUpdated",
                DeckUpdated(deck_id=deck_id),
            )
            return [self._rec_to_dict(r) for r in recs]
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_recommendations(self, deck_id: str) -> list[dict]:
        session = self.session_factory()
        try:
            rows = (
                session.query(RecommendationORM)
                .filter(RecommendationORM.deck_id == deck_id)
                .order_by(RecommendationORM.score.desc())
                .all()
            )
            return [self._orm_to_dict(r) for r in rows]
        finally:
            session.close()

    def _load_deck(self, session: Session, deck_id: str) -> Deck | None:
        deck_orm = session.get(DeckORM, deck_id)
        if deck_orm is None:
            return None
        card_rows = (
            session.query(DeckCardORM)
            .filter(DeckCardORM.deck_id == deck_id)
            .all()
        )
        cards = [(r.card_id, r.qty) for r in card_rows]
        return Deck(
            deck_id=deck_orm.deck_id,
            name=deck_orm.name,
            leader_card_id=deck_orm.leader_card_id,
            source=deck_orm.source,
            event=deck_orm.event,
            date=deck_orm.date,
            cards=cards,
        )

    def _load_all_cards(self, session: Session) -> dict[str, Card]:
        rows = session.query(CardORM).all()
        return {r.card_id: orm_to_card(r) for r in rows}

    def _load_collection(self, session: Session) -> dict[str, int]:
        rows = session.query(CollectionORM).all()
        return {r.card_id: r.owned for r in rows if r.owned > 0}

    def _load_patterns(self, session: Session) -> list[dict]:
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

    def _persist_recommendations(
        self,
        session: Session,
        deck_id: str,
        recs: list,
    ) -> None:
        session.query(RecommendationORM).filter(
            RecommendationORM.deck_id == deck_id
        ).delete()
        for r in recs:
            rec_id = self._make_rec_id(deck_id, r)
            session.add(RecommendationORM(
                rec_id=rec_id,
                deck_id=deck_id,
                type="substitution",
                changes=[
                    {"card_out": r.card_out, "card_in": r.card_in, "qty": r.qty}
                ],
                score=r.score,
                rationale_payload={
                    **r.rationale_payload,
                    "card_out": r.card_out,
                    "card_in": r.card_in,
                    "qty": r.qty,
                    "score": r.score,
                },
            ))
        session.flush()

    @staticmethod
    def _make_rec_id(deck_id: str, rec) -> str:
        raw = f"{deck_id}:{rec.card_out}:{rec.card_in}"
        h = hashlib.sha256(raw.encode()).hexdigest()[:12]
        return f"rec_{h}"

    @staticmethod
    def _rec_to_dict(rec) -> dict:
        return {
            "rec_id": RecommendationService._make_rec_id("", rec),
            "card_out": rec.card_out,
            "card_in": rec.card_in,
            "qty": rec.qty,
            "score": rec.score,
            "rationale": rec.rationale_payload,
        }

    @staticmethod
    def _orm_to_dict(orm: RecommendationORM) -> dict:
        changes = orm.changes or []
        change = changes[0] if changes else {}
        return {
            "rec_id": orm.rec_id,
            "deck_id": orm.deck_id,
            "card_out": change.get("card_out"),
            "card_in": change.get("card_in"),
            "qty": change.get("qty", 1),
            "score": orm.score,
            "rationale": orm.rationale_payload or {},
            "created_at": orm.created_at.isoformat() if orm.created_at else None,
        }
