from app.domain.models import Card, Deck, ValidationResult


class RuleValidator:
    def validate(
        self,
        deck: Deck,
        cards: dict[str, Card],
        format_bans: dict | None = None,
    ) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Structure: exactly 50 cards + 1 leader
        total = sum(qty for _, qty in deck.cards)
        if total != 50:
            errors.append(f"Deck must have exactly 50 cards, found {total}")

        # 2. Copies: max 4 per card_id (unlimited_copies exception)
        for card_id, qty in deck.cards:
            card = cards.get(card_id)
            if card and not card.unlimited_copies and qty > 4:
                errors.append(f"Too many copies of {card_id}: {qty} (max 4)")

        # 3. Colors: all card colors must be subset of leader's colors
        leader = cards.get(deck.leader_card_id)
        if not leader:
            errors.append(f"Leader card not found: {deck.leader_card_id}")
        else:
            leader_colors = set(leader.color)
            for card_id, _ in deck.cards:
                card = cards.get(card_id)
                if card:
                    card_colors = set(card.color)
                    if not card_colors.issubset(leader_colors):
                        extra = card_colors - leader_colors
                        errors.append(
                            f"Card {card_id} has colors {extra} "
                            f"not in leader colors {leader_colors}"
                        )

        # 4-7. Format bans
        if format_bans:
            banned_cards = format_bans.get("banned_cards", [])
            banned_sets = format_bans.get("banned_sets", [])
            banned_blocks = format_bans.get("banned_blocks", [])
            banned_pair1 = format_bans.get("banned_pair1", [])
            banned_pair2 = format_bans.get("banned_pair2", [])

            deck_card_ids = {card_id for card_id, _ in deck.cards}

            # 4. Banned cards
            for card_id in deck_card_ids:
                if card_id in banned_cards:
                    errors.append(f"Banned card: {card_id}")

            # 5. Banned sets
            for card_id, _ in deck.cards:
                card = cards.get(card_id)
                if card and card.set_id in banned_sets:
                    errors.append(
                        f"Card {card_id} is from banned set {card.set_id}"
                    )

            # 6. Banned blocks
            for card_id, _ in deck.cards:
                card = cards.get(card_id)
                if card:
                    block = _extract_block(card.set_id)
                    if block is not None and block in banned_blocks:
                        errors.append(
                            f"Card {card_id} is from banned block {block}"
                        )

            # 7. Restricted pairs
            for i in range(min(len(banned_pair1), len(banned_pair2))):
                p1 = banned_pair1[i]
                p2 = banned_pair2[i]
                if p1 in deck_card_ids and p2 in deck_card_ids:
                    errors.append(
                        f"Restricted pair: {p1} and {p2} "
                        f"cannot be used together"
                    )

        # 8. Warnings
        # Cost curve analysis
        if total > 0:
            high_cost = 0
            for card_id, qty in deck.cards:
                card = cards.get(card_id)
                if card and card.cost is not None and card.cost >= 5:
                    high_cost += qty
            if high_cost / total > 0.6:
                warnings.append(
                    "Curva alta: más del 60% de cartas tienen coste >= 5"
                )

        # Blockers
        blocker_count = 0
        for card_id, _ in deck.cards:
            card = cards.get(card_id)
            if card:
                if "early_blocker" in card.roles or "blocker" in card.keywords:
                    blocker_count += 1
        if blocker_count < 2:
            warnings.append(
                "Pocos blockers tempranos: menos de 2 cartas con blocker"
            )

        # Draw / search
        draw_count = 0
        for card_id, _ in deck.cards:
            card = cards.get(card_id)
            if card:
                if "searcher" in card.roles or "engine" in card.roles:
                    draw_count += 1
        if draw_count < 3:
            warnings.append(
                "Poco robo de cartas: menos de 3 cartas con searcher/engine"
            )

        return ValidationResult(errors=errors, warnings=warnings)


def _extract_block(set_id: str) -> int | None:
    parts = set_id.split("-")
    for part in reversed(parts):
        if part.isdigit():
            return int(part)
    return None
