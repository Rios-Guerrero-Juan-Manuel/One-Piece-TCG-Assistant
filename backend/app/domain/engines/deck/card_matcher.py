import math

from app.domain.models import Card


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _jaccard(a: list[str], b: list[str]) -> float:
    set_a = set(a)
    set_b = set(b)
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


class CardMatcher:
    def __init__(self, weights: dict[str, float] | None = None):
        if weights is None:
            weights = {"embedding": 0.5, "struct": 0.3, "roles": 0.2}
        self.weights = weights

    def _struct_similarity(self, query: Card, candidate: Card) -> float:
        score = 0.0
        if query.type == candidate.type:
            score += 0.3
        q_cost = query.cost if query.cost is not None else 0
        c_cost = candidate.cost if candidate.cost is not None else 0
        cost_diff = abs(q_cost - c_cost)
        if cost_diff <= 1:
            score += 0.25
        elif cost_diff <= 2:
            score += 0.1
        q_power = query.power if query.power is not None else 0
        c_power = candidate.power if candidate.power is not None else 0
        if abs(q_power - c_power) <= 1000:
            score += 0.2
        score += _jaccard(query.keywords, candidate.keywords) * 0.15
        score += _jaccard(query.traits, candidate.traits) * 0.1
        return min(score, 1.0)

    def match(
        self,
        query_card: Card,
        candidates: list[Card],
        query_embedding: list[float],
        candidate_embeddings: list[list[float]],
        top_k: int = 10,
    ) -> list[tuple[Card, float]]:
        w1 = self.weights.get("embedding", 0.5)
        w2 = self.weights.get("struct", 0.3)
        w3 = self.weights.get("roles", 0.2)

        scored: list[tuple[Card, float]] = []
        for i, candidate in enumerate(candidates):
            if i >= len(candidate_embeddings):
                continue
            sim_embedding = _cosine_similarity(query_embedding, candidate_embeddings[i])
            sim_struct = self._struct_similarity(query_card, candidate)
            sim_roles = _jaccard(query_card.roles, candidate.roles)
            final = w1 * sim_embedding + w2 * sim_struct + w3 * sim_roles
            scored.append((candidate, final))

        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]
