import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.importers.match_importer import extract_match_date
from app.infrastructure.persistence.models import DeckCardORM, DeckORM, MatchORM


class DeckRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self):
        return list(self.session.scalars(select(DeckORM)))

    def get_by_id(self, deck_id: str):
        deck = self.session.get(DeckORM, deck_id)
        if deck:
            deck_cards = list(
                self.session.scalars(
                    select(DeckCardORM).where(DeckCardORM.deck_id == deck_id)
                )
            )
            return deck, deck_cards
        return None, []

    def get_by_leader(self, leader_card_id: str):
        """Get all decks for a given leader, ordered by version desc."""
        return list(
            self.session.scalars(
                select(DeckORM)
                .where(DeckORM.leader_card_id == leader_card_id)
                .order_by(DeckORM.version.desc())
            )
        )

    def get_latest_version(self, leader_card_id: str) -> int:
        """Get the highest version number for a leader."""
        decks = self.get_by_leader(leader_card_id)
        if not decks:
            return 0
        return max(d.version for d in decks)

    def auto_assign_deck(
        self,
        leader_card_id: str,
        match_date: datetime.datetime | None,
    ) -> str | None:
        """Auto-assign a deck to a match based on leader and date.

        Finds the deck version whose creation date is closest to (but not after)
        the match date. If the match predates all deck versions, returns the
        earliest version instead of the latest.
        """
        decks = self.get_by_leader(leader_card_id)
        if not decks:
            return None

        if match_date is None:
            return decks[0].deck_id

        best_deck = None
        best_diff = None
        for d in decks:
            if d.created_at is None:
                continue
            if d.created_at > match_date:
                continue
            diff = (match_date - d.created_at).total_seconds()
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best_deck = d

        if best_deck:
            return best_deck.deck_id
        return decks[-1].deck_id

    def create(self, deck_data: dict, cards: list[tuple[str, int]] | None = None):
        deck = DeckORM(**deck_data)
        self.session.add(deck)
        self.session.flush()
        if cards:
            for card_id, qty in cards:
                dc = DeckCardORM(deck_id=deck.deck_id, card_id=card_id, qty=qty)
                self.session.add(dc)
        self.session.flush()
        return deck

    def upsert(self, deck_data: dict, cards: list[tuple[str, int]] | None = None):
        deck = self.session.get(DeckORM, deck_data["deck_id"])
        if deck is None:
            deck = self.create(deck_data, cards)
        else:
            for key, value in deck_data.items():
                setattr(deck, key, value)
            if cards:
                self.session.query(DeckCardORM).filter(
                    DeckCardORM.deck_id == deck.deck_id
                ).delete()
                for card_id, qty in cards:
                    dc = DeckCardORM(deck_id=deck.deck_id, card_id=card_id, qty=qty)
                    self.session.add(dc)
            self.session.flush()
        return deck

    def create_new_version(
        self,
        leader_card_id: str,
        name: str,
        cards: list[tuple[str, int]],
        source: str | None = None,
    ) -> DeckORM:
        """Create a new version of a deck with the same leader.

        Finds the latest version for this leader, increments the version number,
        and creates a new deck entry with the same name (or appends v2, v3, etc.).
        """
        latest_version = self.get_latest_version(leader_card_id)
        new_version = latest_version + 1

        if new_version == 1:
            deck_name = name
        else:
            deck_name = f"{name} v{new_version}"

        deck_data = {
            "deck_id": f"{leader_card_id}_v{new_version}",
            "name": deck_name,
            "leader_card_id": leader_card_id,
            "source": source,
            "event": None,
            "date": None,
            "version": new_version,
        }
        return self.create(deck_data, cards)

    def assign_to_unassigned_matches(self, leader_card_id: str) -> int:
        """Assign the best deck version to matches that have no deck assigned.

        Only touches matches where ``deck_id_self IS NULL`` and
        ``leader_self`` matches the given leader.  Existing assignments are
        never overwritten, and the opponent side (``deck_id_opp``) is never
        modified.

        Returns the number of matches updated.
        """
        matches = list(
            self.session.scalars(
                select(MatchORM).where(
                    MatchORM.deck_id_self.is_(None),
                    MatchORM.leader_self == leader_card_id,
                )
            )
        )
        updated = 0
        for m in matches:
            match_date = extract_match_date(m.source_file) if m.source_file else None
            best = self.auto_assign_deck(leader_card_id, match_date)
            if best:
                m.deck_id_self = best
                updated += 1
        if updated:
            self.session.flush()
        return updated

    def delete(self, deck_id: str) -> bool:
        """Delete a deck, its cards, and nullify match references to it.

        Returns True if a deck was deleted.
        """
        deck = self.session.get(DeckORM, deck_id)
        if deck is None:
            return False

        self.session.query(DeckCardORM).filter(
            DeckCardORM.deck_id == deck_id
        ).delete(synchronize_session=False)

        matches = list(
            self.session.scalars(
                select(MatchORM).where(
                    (MatchORM.deck_id_self == deck_id)
                    | (MatchORM.deck_id_opp == deck_id)
                )
            )
        )
        for m in matches:
            if m.deck_id_self == deck_id:
                m.deck_id_self = None
            if m.deck_id_opp == deck_id:
                m.deck_id_opp = None

        self.session.delete(deck)
        self.session.flush()
        return True
