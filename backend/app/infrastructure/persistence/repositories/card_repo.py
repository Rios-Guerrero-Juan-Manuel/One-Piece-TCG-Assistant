from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import CardORM


class CardRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self, skip=0, limit=50, filters=None):
        query = self.session.query(CardORM)
        if filters:
            if "color" in filters:
                query = query.filter(
                    CardORM.color.like(f'%"{filters["color"]}"%')
                )
            if "type" in filters:
                query = query.filter(CardORM.type == filters["type"])
            if "cost" in filters:
                query = query.filter(CardORM.cost == filters["cost"])
            if "traits" in filters:
                query = query.filter(
                    CardORM.traits.like(f'%"{filters["traits"]}"%')
                )
        total = query.count()
        cards = query.offset(skip).limit(limit).all()
        return cards, total

    def get_by_id(self, card_id):
        return self.session.query(CardORM).filter(CardORM.card_id == card_id).first()

    def existing_card_ids(self, card_ids):
        """Return the subset of ``card_ids`` that exist in the cards table."""
        if not card_ids:
            return set()
        rows = (
            self.session.query(CardORM.card_id)
            .filter(CardORM.card_id.in_(list(card_ids)))
            .all()
        )
        return {row[0] for row in rows}

    def search(self, q, limit=20):
        query = self.session.query(CardORM).filter(
            CardORM.name.ilike(f"%{q}%")
        )
        return query.limit(limit).all()

    def upsert(self, card_data):
        card = self.session.query(CardORM).filter(
            CardORM.card_id == card_data["card_id"]
        ).first()
        if card is None:
            card = CardORM(**card_data)
            self.session.add(card)
        else:
            for key, value in card_data.items():
                setattr(card, key, value)
        self.session.flush()
        return card

    def bulk_upsert(self, cards_data):
        count = 0
        for card_data in cards_data:
            self.upsert(card_data)
            count += 1
        self.session.flush()
        return count
