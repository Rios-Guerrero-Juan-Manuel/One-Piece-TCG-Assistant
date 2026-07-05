import logging
import re
import time

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_REGION_KEYS = {
    "west": "WEST",
    "west+": "WEST+",
    "west++": "WEST++",
    "east": "EAST",
    "east+": "EASTB",
}


def _strip_count_prefix(raw: str) -> str:
    return re.sub(r"^\d+x", "", raw)


def _extract_set(card_id: str) -> str:
    match = re.match(r"^([A-Za-z]+\d+)", card_id)
    if match:
        return match.group(1)
    parts = card_id.split("-")
    return parts[0] if parts else card_id


def build_card_image_url(base_url: str, card_id: str, size: str = "160w") -> str:
    set_code = _extract_set(card_id)
    return f"{base_url}/Cards/{set_code}/{card_id}-{size}.webp"


class OptcgMetaClient:
    def __init__(
        self,
        base_url: str | None = None,
        cache_ttl: int | None = None,
    ):
        self.base_url = base_url or settings.optcg_meta_base_url
        self.cache_ttl = cache_ttl or settings.meta_cache_ttl_seconds
        self._client = httpx.Client(base_url=self.base_url, timeout=60.0)
        self._stats_cache: dict[str, tuple[float, dict]] = {}
        self._cards_cache: tuple[float, dict[str, dict]] | None = None

    def get_stats(self, region: str) -> dict:
        region_key = _REGION_KEYS.get(region.lower())
        if not region_key:
            raise ValueError(f"Unknown region: {region}")
        cached = self._stats_cache.get(region_key)
        if cached and (time.time() - cached[0]) < self.cache_ttl:
            return cached[1]
        url = f"/data/stats-{region_key}.json"
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.error("Meta stats fetch failed: %s - %s", url, e)
            if cached:
                logger.warning("Returning stale cache for %s", region_key)
                return cached[1]
            raise
        self._stats_cache[region_key] = (time.time(), data)
        return data

    def get_cards_data(self) -> dict[str, dict]:
        if self._cards_cache and (time.time() - self._cards_cache[0]) < self.cache_ttl:
            return self._cards_cache[1]
        try:
            resp = self._client.get("/meta")
            resp.raise_for_status()
            html = resp.text
        except httpx.HTTPError as e:
            logger.error("Meta page fetch failed: %s", e)
            if self._cards_cache:
                return self._cards_cache[1]
            raise
        import json

        pattern = re.compile(
            r'<script[^>]*id="meta-cards-data"[^>]*>(.*?)</script>',
            re.DOTALL,
        )
        match = pattern.search(html)
        if not match:
            logger.warning("meta-cards-data block not found in page")
            cards_map: dict[str, dict] = {}
        else:
            raw = json.loads(match.group(1).strip())
            entries = raw.get("data", raw) if isinstance(raw, dict) else raw
            cards_map = {}
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, list) and len(entry) >= 2:
                        cid = entry[0]
                        cards_map[cid] = {
                            "id": cid,
                            "name": entry[1],
                            "cost": entry[2] if len(entry) > 2 else None,
                            "image_id": entry[3] if len(entry) > 3 else None,
                            "price": entry[4] if len(entry) > 4 else None,
                        }
        self._cards_cache = (time.time(), cards_map)
        return cards_map

    def clear_cache(self):
        self._stats_cache.clear()
        self._cards_cache = None

    def close(self):
        self._client.close()
