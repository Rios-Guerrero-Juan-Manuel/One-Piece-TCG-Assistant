import logging
import re

import httpx

logger = logging.getLogger(__name__)

PRICE_GUIDE_URL = (
    "https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_18.json"
)
PRODUCT_LIST_URL = (
    "https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_18.json"
)

_CARD_NUM_RE = re.compile(r"\(([A-Z0-9]+-\d+)\)")


def _effective_price(avg: float | None, trend: float | None) -> float | None:
    """Return avg when available, otherwise fall back to trend."""
    if avg is not None and avg > 0:
        return avg
    if trend is not None and trend > 0:
        return trend
    return None


class CardmarketClient:
    def __init__(self, timeout: float = 60.0):
        self._client = httpx.Client(timeout=timeout)

    def _get_json(self, url: str) -> dict:
        resp = self._client.get(url)
        resp.raise_for_status()
        return resp.json()

    def fetch_prices(self) -> dict[str, dict[str, float | None]]:
        """Download price guide + product list, return ``{card_id: {trend, avg, low}}``.

        For duplicate card numbers (foil / JP variants) the entry with the
        lowest non-null effective price wins, which typically corresponds to the
        English non-foil version.  The effective price prefers ``avg`` and
        falls back to ``trend`` when ``avg`` is unavailable.
        """
        logger.info("Downloading Cardmarket price guide ...")
        price_data = self._get_json(PRICE_GUIDE_URL)
        logger.info("Downloading Cardmarket product list ...")
        product_data = self._get_json(PRODUCT_LIST_URL)

        id_to_card_num: dict[int, str] = {}
        for prod in product_data.get("products", []):
            name = prod.get("name", "")
            m = _CARD_NUM_RE.search(name)
            if m:
                id_to_card_num[prod["idProduct"]] = m.group(1)

        best: dict[str, dict[str, float | None]] = {}
        for pg in price_data.get("priceGuides", []):
            card_num = id_to_card_num.get(pg.get("idProduct"))
            if not card_num:
                continue
            trend = pg.get("trend")
            avg = pg.get("avg")
            effective = _effective_price(avg, trend)
            if effective is None:
                continue
            existing = best.get(card_num)
            if existing is None or effective < (
                _effective_price(existing["avg_price"], existing["trend_price"])
                or float("inf")
            ):
                best[card_num] = {
                    "trend_price": trend,
                    "avg_price": avg,
                    "low_price": pg.get("low"),
                }

        logger.info("Cardmarket prices fetched: %d cards", len(best))
        return best

    def close(self):
        self._client.close()
