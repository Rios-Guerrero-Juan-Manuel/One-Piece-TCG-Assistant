from app.domain.models import Card


class RoleClassifier:
    @staticmethod
    def classify(card: Card) -> list[str]:
        roles: list[str] = []

        if card.counter == 2000:
            roles.append("2k_counter")
        if card.counter == 1000:
            roles.append("1k_counter")
        if "blocker" in card.keywords and (card.cost or 0) <= 3:
            roles.append("early_blocker")

        if any(k in card.keywords for k in ["draw", "search", "reveal"]):
            roles.append("engine")
        if any(k in card.keywords for k in ["ko", "banish", "trash"]):
            roles.append("removal")

        if (card.cost or 0) >= 7 and (card.power or 0) >= 8000 and card.type == "Character":
            roles.append("boss")
        if (card.power or 0) > (card.cost or 0) * 1500 and card.type == "Character":
            roles.append("tempo")

        if "ramp" in card.keywords:
            roles.append("ramp")
        if "search" in card.keywords:
            roles.append("searcher")
        if "don_support" in card.keywords:
            roles.append("don_support")
        if "finisher" in card.keywords:
            roles.append("finisher")
        if card.type == "Stage" or "utility" in card.keywords:
            roles.append("utility")

        return roles
