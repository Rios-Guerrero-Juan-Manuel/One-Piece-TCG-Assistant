from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.application.event_bus import get_event_bus
from app.domain.models import Card, Deck, DeckScore
from app.infrastructure.persistence.models import DeckScoreORM
from app.infrastructure.persistence.repositories.card_repo import CardRepository
from app.infrastructure.persistence.repositories.collection_repo import CollectionRepository
from app.infrastructure.persistence.repositories.deck_repo import DeckRepository

logger = logging.getLogger(__name__)

KEY_ROLES = {"engine", "early_blocker", "removal", "searcher"}

WEIGHTS = {
    "consistency": 0.25,
    "curve": 0.20,
    "collection": 0.15,
    "synergy": 0.25,
    "matchups": 0.15,
}

IDEAL_CURVE = {"c0_1": 20, "c2_3": 40, "c4_5": 25, "c6plus": 15}


class ScoringEngine:
    """Deck scoring engine 0-100."""

    VERSION = 1

    def __init__(
        self,
        session_factory: Callable[[], Session],
        auto_subscribe: bool = True,
    ):
        self.session_factory = session_factory
        if auto_subscribe:
            get_event_bus().subscribe("DeckUpdated", self._on_deck_updated)

    def _on_deck_updated(self, payload):
        deck_id = payload.get("deck_id") if isinstance(payload, dict) else None
        if deck_id:
            self.score_deck(deck_id)

    def score_deck(self, deck_id: str) -> DeckScore:
        session = self.session_factory()
        try:
            deck_repo = DeckRepository(session)
            card_repo = CardRepository(session)
            collection_repo = CollectionRepository(session)

            deck_orm, deck_cards_orm = deck_repo.get_by_id(deck_id)
            if deck_orm is None:
                raise ValueError(f"Deck not found: {deck_id}")

            deck = self._to_domain_deck(deck_orm, deck_cards_orm)

            cards: dict[str, Card] = {}
            for card_id, _ in deck.cards:
                if card_id not in cards:
                    card_orm = card_repo.get_by_id(card_id)
                    if card_orm:
                        cards[card_id] = self._to_domain_card(card_orm)

            leader_orm = card_repo.get_by_id(deck.leader_card_id)
            leader = self._to_domain_card(leader_orm) if leader_orm else None

            consistency = self._score_consistency(deck, cards)
            curve = self._score_curve(deck, cards)
            collection = self._score_collection(deck, collection_repo)
            synergy = self._score_synergy(deck, cards, leader)
            matchups = 50

            overall = round(
                consistency * WEIGHTS["consistency"]
                + curve * WEIGHTS["curve"]
                + collection * WEIGHTS["collection"]
                + synergy * WEIGHTS["synergy"]
                + matchups * WEIGHTS["matchups"]
            )

            score = DeckScore(
                deck_id=deck_id,
                overall=overall,
                breakdown={
                    "consistency": consistency,
                    "curve": curve,
                    "collection": collection,
                    "synergy": synergy,
                    "matchups": matchups,
                },
                version=self.VERSION,
            )

            self._save_score(session, score)
            session.commit()
            return score
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _score_consistency(self, deck: Deck, cards: dict[str, Card]) -> int:
        unique_count = len(deck.cards)
        if unique_count == 0:
            return 0
        total_qty = sum(qty for _, qty in deck.cards)
        avg_copies = total_qty / unique_count

        searcher_count = 0
        engine_count = 0
        for card_id, _ in deck.cards:
            card = cards.get(card_id)
            if card is None:
                continue
            if "searcher" in card.roles:
                searcher_count += 1
            if "engine" in card.roles:
                engine_count += 1

        score = min(100, int(searcher_count * 10 + engine_count * 5 + avg_copies * 15))
        return max(0, score)

    def _score_curve(self, deck: Deck, cards: dict[str, Card]) -> int:
        total_qty = sum(qty for _, qty in deck.cards)
        if total_qty == 0:
            return 0

        c0_1 = c2_3 = c4_5 = c6plus = 0

        for card_id, qty in deck.cards:
            card = cards.get(card_id)
            if card is None or card.cost is None:
                continue
            cost = card.cost
            if cost <= 1:
                c0_1 += qty
            elif cost <= 3:
                c2_3 += qty
            elif cost <= 5:
                c4_5 += qty
            else:
                c6plus += qty

        c0_1_pct = (c0_1 / total_qty) * 100
        c2_3_pct = (c2_3 / total_qty) * 100
        c4_5_pct = (c4_5 / total_qty) * 100
        c6plus_pct = (c6plus / total_qty) * 100

        raw = (
            100
            - abs(c0_1_pct - IDEAL_CURVE["c0_1"])
            - abs(c2_3_pct - IDEAL_CURVE["c2_3"])
            - abs(c4_5_pct - IDEAL_CURVE["c4_5"])
            - abs(c6plus_pct - IDEAL_CURVE["c6plus"])
        )
        return max(0, min(100, int(round(raw))))

    def _score_collection(self, deck: Deck, collection_repo: CollectionRepository) -> int:
        owned_in_deck = 0
        total_in_deck = 0
        for card_id, qty in deck.cards:
            total_in_deck += qty
            owned = collection_repo.get_owned(card_id)
            owned_in_deck += min(owned, qty)

        if total_in_deck == 0:
            return 0
        return int((owned_in_deck / total_in_deck) * 100)

    def _score_synergy(self, deck: Deck, cards: dict[str, Card], leader: Card | None) -> int:
        color_match_pct = self._color_match(deck, cards, leader)
        role_diversity_score = self._role_diversity(cards)
        trait_overlap_score = self._trait_overlap(deck, cards, leader)

        return int(
            color_match_pct * 0.3
            + role_diversity_score * 0.4
            + trait_overlap_score * 0.3
        )

    def _color_match(self, deck: Deck, cards: dict[str, Card], leader: Card | None) -> float:
        if leader is None:
            return 0.0
        leader_colors = set(leader.color)
        if not leader_colors:
            return 0.0
        total_qty = sum(qty for _, qty in deck.cards)
        if total_qty == 0:
            return 0.0
        matching_qty = 0
        for card_id, qty in deck.cards:
            card = cards.get(card_id)
            if card is None:
                continue
            if set(card.color) & leader_colors:
                matching_qty += qty
        return (matching_qty / total_qty) * 100

    def _role_diversity(self, cards: dict[str, Card]) -> float:
        found_roles: set[str] = set()
        for card in cards.values():
            found_roles.update(card.roles)
        diversity = len(KEY_ROLES & found_roles)
        return (diversity / len(KEY_ROLES)) * 100

    def _trait_overlap(self, deck: Deck, cards: dict[str, Card], leader: Card | None) -> float:
        if leader is None:
            return 0.0
        leader_traits = set(leader.traits)
        if not leader_traits:
            return 0.0
        total_qty = sum(qty for _, qty in deck.cards)
        if total_qty == 0:
            return 0.0
        overlap_qty = 0
        for card_id, qty in deck.cards:
            card = cards.get(card_id)
            if card is None:
                continue
            if set(card.traits) & leader_traits:
                overlap_qty += qty
        return (overlap_qty / total_qty) * 100

    def _save_score(self, session: Session, score: DeckScore) -> None:
        existing = session.get(DeckScoreORM, score.deck_id)
        if existing:
            existing.overall = score.overall
            existing.breakdown = score.breakdown
            existing.version = score.version
        else:
            session.add(
                DeckScoreORM(
                    deck_id=score.deck_id,
                    overall=score.overall,
                    breakdown=score.breakdown,
                    version=score.version,
                )
            )
        session.flush()

    def _to_domain_deck(self, deck_orm, deck_cards_orm) -> Deck:
        cards = [(dc.card_id, dc.qty) for dc in deck_cards_orm]
        return Deck(
            deck_id=deck_orm.deck_id,
            name=deck_orm.name,
            leader_card_id=deck_orm.leader_card_id,
            source=deck_orm.source,
            event=deck_orm.event,
            date=deck_orm.date,
            cards=cards,
        )

    def _to_domain_card(self, card_orm) -> Card:
        return Card(
            card_id=card_orm.card_id,
            name=card_orm.name,
            cost=card_orm.cost,
            power=card_orm.power,
            counter=card_orm.counter,
            type=card_orm.type,
            color=card_orm.color or [],
            traits=card_orm.traits or [],
            attribute=card_orm.attribute,
            keywords=card_orm.keywords or [],
            roles=card_orm.roles or [],
            effect=card_orm.effect,
            life=card_orm.life,
            set_id=card_orm.set_id,
            set_name=card_orm.set_name,
            rarity=card_orm.rarity,
            image_url=card_orm.image_url,
            unlimited_copies=card_orm.unlimited_copies,
        )
