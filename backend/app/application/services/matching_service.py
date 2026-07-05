import logging

from app.domain.engines.deck.card_matcher import CardMatcher
from app.domain.models import Card
from app.infrastructure.embeddings.card_index import CardIndex
from app.infrastructure.embeddings.embedding_service import EmbeddingService
from app.infrastructure.persistence.mappers import orm_to_card
from app.infrastructure.persistence.repositories.card_repo import CardRepository
from app.infrastructure.persistence.session import SessionLocal

logger = logging.getLogger(__name__)

BATCH_SIZE = 100


class MatchingService:
    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        card_index: CardIndex | None = None,
        matcher: CardMatcher | None = None,
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        self.card_index = card_index or CardIndex()
        self.matcher = matcher or CardMatcher()

    def find_similar(self, card_id: str, top_k: int = 10) -> list[dict]:
        session = SessionLocal()
        try:
            repo = CardRepository(session)
            orm_card = repo.get_by_id(card_id)
            if not orm_card:
                return []
            query_card = orm_to_card(orm_card)
        finally:
            session.close()

        embedding = self.card_index.get_embedding(card_id)
        if embedding is None:
            text = query_card.effect or query_card.name
            embedding = self.embedding_service.embed(text)

        if not embedding:
            return []

        candidate_pairs = self.card_index.query(embedding, top_k=top_k * 3 + 1)
        if not candidate_pairs:
            return []

        candidate_ids = [cid for cid, _ in candidate_pairs]
        session = SessionLocal()
        try:
            repo = CardRepository(session)
            candidates: list[Card] = []
            for cid in candidate_ids:
                orm = repo.get_by_id(cid)
                if orm and orm.card_id != card_id:
                    candidates.append(orm_to_card(orm))
        finally:
            session.close()

        candidate_embeddings: list[list[float]] = []
        for cand in candidates:
            emb = self.card_index.get_embedding(cand.card_id)
            if emb is None:
                emb = self.embedding_service.embed(cand.effect or cand.name)
            candidate_embeddings.append(emb)

        results = self.matcher.match(
            query_card=query_card,
            candidates=candidates,
            query_embedding=embedding,
            candidate_embeddings=candidate_embeddings,
            top_k=top_k,
        )

        return [
            {
                "card_id": card.card_id,
                "name": card.name,
                "score": round(score, 4),
            }
            for card, score in results
        ]

    def index_all_cards(self) -> int:
        self.card_index.clear()
        session = SessionLocal()
        total_indexed = 0
        try:
            repo = CardRepository(session)
            skip = 0
            total = repo.get_all(skip=0, limit=1)[1]
            while skip < total:
                orm_cards, _ = repo.get_all(skip=skip, limit=BATCH_SIZE)
                batch: list[dict] = []
                for orm in orm_cards:
                    text = orm.effect or orm.name
                    batch.append(
                        {
                            "card_id": orm.card_id,
                            "name": orm.name,
                            "effect": text,
                            "embedding": None,
                        }
                    )
                texts = [b["effect"] for b in batch]
                embeddings = self.embedding_service.embed_batch(texts)
                if not embeddings or len(embeddings) != len(batch):
                    skip += BATCH_SIZE
                    continue
                for b, emb in zip(batch, embeddings, strict=True):
                    b["embedding"] = emb
                self.card_index.index_cards(batch)
                total_indexed += len(batch)
                skip += BATCH_SIZE
                logger.info("Indexed %d / %d cards", total_indexed, total)
        finally:
            session.close()
        return total_indexed
