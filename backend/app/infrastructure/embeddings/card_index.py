import logging
from pathlib import Path

import chromadb

logger = logging.getLogger(__name__)

CHROMA_PATH = str(Path(__file__).resolve().parents[3] / "data" / "chroma")
COLLECTION_NAME = "cards"


class CardIndex:
    def __init__(self, path: str = CHROMA_PATH, collection_name: str = COLLECTION_NAME):
        self.path = path
        self.collection_name = collection_name
        self._client = chromadb.PersistentClient(path=path)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def index_cards(self, cards: list[dict]) -> None:
        if not cards:
            return
        ids = [c["card_id"] for c in cards]
        embeddings = [c["embedding"] for c in cards]
        documents = [c.get("effect", "") or c.get("name", "") for c in cards]
        metadatas = [
            {"name": c.get("name", "")} for c in cards
        ]
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def query(
        self, query_embedding: list[float], top_k: int = 20
    ) -> list[tuple[str, float]]:
        if not query_embedding:
            return []
        count = self._collection.count()
        if count == 0:
            return []
        n_results = min(top_k, count)
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )
        ids = result.get("ids", [[]])
        distances = result.get("distances", [[]])
        pairs: list[tuple[str, float]] = []
        if not ids or not ids[0]:
            return pairs
        for card_id, dist in zip(ids[0], distances[0], strict=True):
            similarity = max(0.0, 1.0 - dist)
            pairs.append((card_id, similarity))
        return pairs

    def get_embedding(self, card_id: str) -> list[float] | None:
        result = self._collection.get(ids=[card_id], include=["embeddings"])
        embeddings = result.get("embeddings")
        if not embeddings:
            return None
        return list(embeddings[0])

    def clear(self) -> None:
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
