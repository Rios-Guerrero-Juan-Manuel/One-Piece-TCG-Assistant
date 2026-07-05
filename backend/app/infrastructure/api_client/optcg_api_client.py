import logging

import httpx

logger = logging.getLogger(__name__)


class OptcgApiClient:
    def __init__(self, base_url: str = "https://www.optcgapi.com", delay: float = 1.0):
        self.base_url = base_url
        self.delay = delay
        self._client = httpx.Client(base_url=base_url, timeout=30.0)

    def _get(self, path: str) -> list[dict]:
        try:
            resp = self._client.get(path)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error("API request failed: %s%s - %s", self.base_url, path, e)
            raise

    def get_all_sets(self) -> list[dict]:
        return self._get("/api/allSets/")

    def get_set_cards(self, set_id: str) -> list[dict]:
        return self._get(f"/api/sets/{set_id}/")

    def get_all_st_cards(self) -> list[dict]:
        return self._get("/api/allSTCards/")

    def get_all_promos(self) -> list[dict]:
        return self._get("/api/allPromos/")

    def get_all_don_cards(self) -> list[dict]:
        return self._get("/api/allDonCards/")

    def get_all_set_cards_bulk(self) -> list[dict]:
        return self._get("/api/allSetCards/")

    def get_card(self, card_id: str) -> list[dict]:
        return self._get(f"/api/sets/card/{card_id}/")

    def get_recent_cards(self) -> list[dict]:
        return self._get("/api/sets/card/twoweeks/")

    def close(self):
        self._client.close()
