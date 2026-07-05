import datetime
import logging

from sqlalchemy.orm import Session

from app.infrastructure.api_client.cardmarket_client import CardmarketClient
from app.infrastructure.persistence.repositories.price_repo import PriceRepository

logger = logging.getLogger(__name__)


class PriceService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = PriceRepository(session)

    def ensure_fresh(self) -> None:
        """Download prices if the stored data is older than today."""
        last = self.repo.last_updated()
        today = datetime.datetime.now(datetime.UTC).date()
        if last and last.date() >= today:
            return
        self.refresh()

    def refresh(self) -> int:
        """Download from Cardmarket and upsert into the database.

        Returns the number of price rows stored.
        """
        client = CardmarketClient()
        try:
            prices_map = client.fetch_prices()
        finally:
            client.close()

        rows = [
            {"card_id": cid, **vals}
            for cid, vals in prices_map.items()
        ]
        count = self.repo.bulk_upsert(rows)
        self.session.commit()
        logger.info("Price DB refreshed: %d rows", count)
        return count

    def get_prices(self, card_ids: list[str]) -> dict[str, dict[str, float | None]]:
        rows = self.repo.get_prices(card_ids)
        return {
            cid: {
                "trend_price": row.trend_price,
                "avg_price": row.avg_price,
                "low_price": row.low_price,
            }
            for cid, row in rows.items()
        }
