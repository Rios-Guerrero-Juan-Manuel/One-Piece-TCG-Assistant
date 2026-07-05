import re


class DeckImporter:
    @staticmethod
    def parse_deck_text(text: str) -> tuple[str, list[tuple[str, int]]]:
        leader_card_id: str = ""
        card_map: dict[str, int] = {}
        pattern = re.compile(r"^(\d+)x([A-Z0-9]+-\d+)$")

        for line in text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            match = pattern.match(line)
            if not match:
                continue
            qty = int(match.group(1))
            card_id = match.group(2)
            if qty == 1 and not leader_card_id:
                leader_card_id = card_id
            else:
                card_map[card_id] = card_map.get(card_id, 0) + qty

        cards = list(card_map.items())
        return leader_card_id, cards
