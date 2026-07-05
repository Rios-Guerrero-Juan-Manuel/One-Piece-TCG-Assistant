from app.domain.engines.deck.card_matcher import _jaccard
from app.domain.models import Card, Deck, Recommendation


class RecommendationEngine:
    """Combines patterns + deck gaps + collection + meta to propose card changes.

    The engine is pure logic — no I/O, no DB, no LLM. It receives already-loaded
    data and produces Recommendation objects. The LLM only explains/justifies
    the output; it never decides.
    """

    def recommend(
        self,
        deck: Deck,
        cards: dict[str, Card],
        collection: dict[str, int],
        patterns: list[dict],
        meta: dict | None = None,
    ) -> list[Recommendation]:
        leader = cards.get(deck.leader_card_id)
        if leader is None:
            return []

        deck_card_ids = {cid for cid, _ in deck.cards}
        problems = self._identify_problems(patterns, deck, cards)
        if not problems:
            return []

        candidates = self._collect_candidates(
            cards, collection, deck_card_ids, leader
        )
        if not candidates:
            return []

        recs: list[Recommendation] = []
        seen: set[str] = set()

        for problem in problems:
            target_roles = problem.get("target_roles", [])
            for card_in in candidates:
                if not self._matches_problem_roles(card_in, target_roles):
                    continue
                card_out = self._pick_card_to_replace(deck, cards, card_in, leader)
                if card_out is None:
                    continue
                key = f"{card_out}->{card_in.card_id}"
                if key in seen:
                    continue
                seen.add(key)
                score = self._score_substitution(
                    card_out, card_in, deck, leader
                )
                if score < 30:
                    continue
                recs.append(Recommendation(
                    card_out=card_out.card_id,
                    card_in=card_in.card_id,
                    qty=1,
                    score=score,
                    rationale_payload=self._build_rationale(
                        card_out, card_in, problem, score
                    ),
                ))

        recs.sort(key=lambda r: r.score, reverse=True)
        return recs[:10]

    def _identify_problems(
        self,
        patterns: list[dict],
        deck: Deck,
        cards: dict[str, Card],
    ) -> list[dict]:
        problems: list[dict] = []
        for p in patterns:
            pid = p.get("pattern_id", "")
            severity = p.get("severity", "low")
            if severity == "high" or severity == "medium":
                problems.append(self._problem_from_pattern(pid, p))
        problems.extend(self._deck_gap_problems(deck, cards))
        return problems

    def _problem_from_pattern(self, pattern_id: str, pattern: dict) -> dict:
        problems_map = {
            "don_inefficient": {
                "id": "don_inefficient",
                "description": pattern.get("description", "DON left unused"),
                "target_roles": ["ramp", "tempo", "engine"],
            },
            "early_loss": {
                "id": "early_loss",
                "description": pattern.get("description", "Losing too early"),
                "target_roles": ["early_blocker", "2k_counter", "1k_counter"],
            },
            "low_early_pressure": {
                "id": "low_early_pressure",
                "description": pattern.get("description", "Low early pressure"),
                "target_roles": ["tempo", "engine", "searcher"],
            },
            "large_hand": {
                "id": "large_hand",
                "description": pattern.get("description", "Cards stuck in hand"),
                "target_roles": ["engine", "searcher", "tempo"],
            },
            "counter_dependency": {
                "id": "counter_dependency",
                "description": pattern.get("description", "Over-reliant on counter"),
                "target_roles": ["early_blocker", "removal", "tempo"],
            },
        }
        return problems_map.get(pattern_id, {
            "id": pattern_id,
            "description": pattern.get("description", "Generic pattern"),
            "target_roles": [],
        })

    def _deck_gap_problems(
        self, deck: Deck, cards: dict[str, Card]
    ) -> list[dict]:
        problems: list[dict] = []
        role_counts: dict[str, int] = {}
        total_cards = 0
        for card_id, qty in deck.cards:
            card = cards.get(card_id)
            if card is None:
                continue
            total_cards += qty
            for role in card.roles:
                role_counts[role] = role_counts.get(role, 0) + qty

        blockers = role_counts.get("early_blocker", 0)
        if blockers < 4:
            problems.append({
                "id": "low_blockers",
                "description": f"Only {blockers} early blockers in deck (recommended: 4+)",
                "target_roles": ["early_blocker", "2k_counter"],
            })

        counters = role_counts.get("2k_counter", 0) + role_counts.get("1k_counter", 0)
        if counters < 8:
            problems.append({
                "id": "low_counters",
                "description": f"Only {counters} counter cards (recommended: 8+)",
                "target_roles": ["2k_counter", "1k_counter"],
            })

        engines = role_counts.get("engine", 0) + role_counts.get("searcher", 0)
        if engines < 4:
            problems.append({
                "id": "low_engine",
                "description": f"Only {engines} draw/search cards (recommended: 4+)",
                "target_roles": ["engine", "searcher"],
            })

        high_cost = sum(
            qty for cid, qty in deck.cards
            if cards.get(cid) and (cards[cid].cost or 0) >= 7
        )
        if high_cost > 6:
            problems.append({
                "id": "too_many_high_cost",
                "description": f"{high_cost} high-cost cards (7+ DON). Consider trimming.",
                "target_roles": ["tempo", "engine"],
            })

        return problems

    def _collect_candidates(
        self,
        cards: dict[str, Card],
        collection: dict[str, int],
        deck_card_ids: set[str],
        leader: Card,
    ) -> list[Card]:
        candidates: list[Card] = []
        leader_colors = set(leader.color)

        if collection:
            candidate_ids = [cid for cid, owned in collection.items() if owned > 0]
        else:
            candidate_ids = list(cards.keys())

        for card_id in candidate_ids:
            if card_id in deck_card_ids:
                continue
            card = cards.get(card_id)
            if card is None:
                continue
            if card.type == "Leader":
                continue
            if card.type == "DON":
                continue
            card_colors = set(card.color)
            if not card_colors.issubset(leader_colors) and not card_colors & leader_colors:
                continue
            candidates.append(card)
        return candidates

    def _matches_problem_roles(self, card: Card, target_roles: list[str]) -> bool:
        if not target_roles:
            return True
        return any(r in card.roles for r in target_roles)

    def _pick_card_to_replace(
        self,
        deck: Deck,
        cards: dict[str, Card],
        card_in: Card,
        leader: Card,
    ) -> Card | None:
        best_card: Card | None = None
        best_score = -1.0
        for card_id, qty in deck.cards:
            card = cards.get(card_id)
            if card is None:
                continue
            if card.type == "Leader":
                continue
            if card.card_id == card_in.card_id:
                continue
            role_overlap = _jaccard(card.roles, card_in.roles)
            cost_diff = abs(
                (card.cost or 0) - (card_in.cost or 0)
            )
            cost_penalty = cost_diff * 0.15
            score = role_overlap - cost_penalty
            if score > best_score:
                best_score = score
                best_card = card
        return best_card

    def _score_substitution(
        self,
        card_out: Card,
        card_in: Card,
        deck: Deck,
        leader: Card,
    ) -> int:
        role_overlap = _jaccard(card_out.roles, card_in.roles)
        kw_overlap = _jaccard(card_out.keywords, card_in.keywords)
        type_match = 100.0 if card_out.type == card_in.type else 50.0
        cost_out = card_out.cost or 0
        cost_in = card_in.cost or 0
        cost_score = max(0, 100 - abs(cost_out - cost_in) * 20)
        color_leader = 100.0 if set(card_in.color).issubset(set(leader.color)) else 50.0
        trait_leader = _jaccard(card_in.traits, leader.traits) * 100
        role_gain = self._role_gain_score(card_out, card_in)

        raw = (
            0.20 * role_overlap * 100
            + 0.15 * kw_overlap * 100
            + 0.15 * type_match
            + 0.15 * cost_score
            + 0.10 * color_leader
            + 0.10 * trait_leader
            + 0.15 * role_gain
        )
        return max(0, min(100, round(raw)))

    def _role_gain_score(self, card_out: Card, card_in: Card) -> float:
        out_roles = set(card_out.roles)
        in_roles = set(card_in.roles)
        gained = in_roles - out_roles
        valuable = {"early_blocker", "2k_counter", "engine", "searcher", "removal", "ramp"}
        gain = len(gained & valuable)
        lost = len(out_roles - in_roles)
        return min(100, max(0, 50 + gain * 25 - lost * 15))

    def _build_rationale(
        self,
        card_out: Card,
        card_in: Card,
        problem: dict,
        score: int,
    ) -> dict:
        return {
            "problem": problem.get("id", "unknown"),
            "description": problem.get("description", ""),
            "card_out": card_out.card_id,
            "card_out_name": card_out.name,
            "card_in": card_in.card_id,
            "card_in_name": card_in.name,
            "roles_gained": list(set(card_in.roles) - set(card_out.roles)),
            "role_overlap": list(set(card_in.roles) & set(card_out.roles)),
            "roles_lost": list(set(card_out.roles) - set(card_in.roles)),
            "cost_delta": (card_in.cost or 0) - (card_out.cost or 0),
            "score": score,
        }
