import datetime

from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import CardPriceORM


class PriceRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_price(self, card_id: str) -> CardPriceORM | None:
        return (
            self.session.query(CardPriceORM)
            .filter(CardPriceORM.card_id == card_id)
            .first()
        )

    def get_prices(self, card_ids: list[str]) -> dict[str, CardPriceORM]:
        if not card_ids:
            return {}
        rows = (
            self.session.query(CardPriceORM)
            .filter(CardPriceORM.card_id.in_(card_ids))
            .all()
        )
        return {row.card_id: row for row in rows}

    def bulk_upsert(self, prices: list[dict]) -> int:
        now = datetime.datetime.now(datetime.UTC)
        count = 0
        for p in prices:
            row = (
                self.session.query(CardPriceORM)
                .filter(CardPriceORM.card_id == p["card_id"])
                .first()
            )
            if row is None:
                row = CardPriceORM(
                    card_id=p["card_id"],
                    trend_price=p.get("trend_price"),
                    avg_price=p.get("avg_price"),
                    low_price=p.get("low_price"),
                    updated_at=now,
                )
                self.session.add(row)
            else:
                row.trend_price = p.get("trend_price")
                row.avg_price = p.get("avg_price")
                row.low_price = p.get("low_price")
                row.updated_at = now
            count += 1
        self.session.flush()
        return count

    def last_updated(self) -> datetime.datetime | None:
        row = (
            self.session.query(CardPriceORM.updated_at)
            .order_by(CardPriceORM.updated_at.desc())
            .first()
        )
        return row[0] if row else None

    def count(self) -> int:
        return self.session.query(CardPriceORM).count()
