from app.domain.engines.deck.card_matcher import CardMatcher, _jaccard
from app.domain.models import Card, Deck


class SubstitutionScorer:
    def __init__(self, matcher: CardMatcher | None = None):
        self._matcher = matcher or CardMatcher()

    def score(
        self,
        card_out: Card,
        card_in: Card,
        deck: Deck,
        leader_card: Card,
        embedding_sim: float = 0.0,
    ) -> int:

        sim_efecto = self._sim_effect(card_out, card_in, embedding_sim)
        curva = self._curve_impact(card_out, card_in)
        sinergia = self._synergy(card_in, deck, leader_card)
        impacto = self._expected_impact(card_out, card_in)

        raw = 0.30 * sim_efecto + 0.20 * curva + 0.25 * sinergia + 0.25 * impacto
        return max(0, min(100, round(raw)))

    def _sim_effect(
        self, card_out: Card, card_in: Card, embedding_sim: float
    ) -> float:
        if embedding_sim > 0:
            return embedding_sim * 100
        struct = self._matcher._struct_similarity(card_out, card_in)
        roles = _jaccard(card_out.roles, card_in.roles)
        combined = self._matcher.weights["struct"] * struct + self._matcher.weights["roles"] * roles
        norm = self._matcher.weights["struct"] + self._matcher.weights["roles"]
        return (combined / norm * 100) if norm > 0 else 0.0

    def _curve_impact(self, card_out: Card, card_in: Card) -> float:
        c_out = card_out.cost if card_out.cost is not None else 0
        c_in = card_in.cost if card_in.cost is not None else 0
        diff = abs(c_out - c_in)
        if diff == 0:
            return 100.0
        if diff == 1:
            return 80.0
        if diff == 2:
            return 50.0
        return 20.0

    def _synergy(self, card_in: Card, deck: Deck, leader_card: Card) -> float:
        score = 0.0
        leader_colors = set(leader_card.color)
        card_colors = set(card_in.color)
        if card_colors.issubset(leader_colors):
            score += 50.0
        elif card_colors & leader_colors:
            score += 25.0

        trait_leader = _jaccard(card_in.traits, leader_card.traits)
        score += trait_leader * 25.0
        score += 20.0
        return min(score, 100.0)

    def _expected_impact(self, card_out: Card, card_in: Card) -> float:
        role_overlap = _jaccard(card_out.roles, card_in.roles)
        kw_overlap = _jaccard(card_out.keywords, card_in.keywords)
        type_match = 1.0 if card_out.type == card_in.type else 0.0
        return (role_overlap * 50 + kw_overlap * 30 + type_match * 20)
