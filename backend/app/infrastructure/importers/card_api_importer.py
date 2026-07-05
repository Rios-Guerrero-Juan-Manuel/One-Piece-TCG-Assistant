import argparse
import json
import logging
import re
import time

from app.application.event_bus import get_event_bus
from app.domain.engines.deck.role_classifier import RoleClassifier
from app.domain.events import CardsRefreshed
from app.domain.models import Card
from app.infrastructure.api_client.optcg_api_client import OptcgApiClient
from app.infrastructure.importers.keyword_extractor import KeywordExtractor
from app.infrastructure.persistence.repositories.card_repo import CardRepository
from app.infrastructure.persistence.session import SessionLocal, init_db

logger = logging.getLogger(__name__)

KNOWN_TRAITS = [
    "Animal Kingdom Pirates", "The Four Emperors", "The Seven Warlords of the Sea",
    "The Vinsmoke Family", "Straw Hat Crew", "Whitebeard Pirates", "Blackbeard Pirates",
    "Big Mom Pirates", "Red-Haired Pirates", "Heart Pirates", "Kid Pirates",
    "Firetank Pirates", "Fallen Monk Pirates", "On-Air Pirates", "Bonney Pirates",
    "Hawkins Pirates", "Drake Pirates", "Barto Club", "Beautiful Pirates",
    "Revolutionary Army", "Cross Guild", "Baroque Works", "Donquixote Pirates",
    "Buggy Pirates", "Buggy's Delivery", "Arlong Pirates", "Foxy Pirates",
    "Bellamy Pirates", "Roger Pirates", "Spade Pirates", "Rumbar Pirates",
    "Rolling Pirates", "Treasure Pirates", "World Pirates", "Caribou Pirates",
    "Peachbeard Pirates", "Fake Straw Hat Crew", "Trump Pirates",
    "Happosui Army", "Galley-La Company", "The Franky Family", "The Flying Fish Riders",
    "Kuja Pirates", "Navy", "Navy SWORD", "Navy Admiral", "Former Navy",
    "World Government", "Celestial Dragons", "Five Elders", "CP0", "CP6", "CP7",
    "CP8", "CP9", "Biological Weapon", "Scientist", "Journalist",
    "Land of Wano", "Kouzuki Clan", "Kurozumi Clan", "The Akazaya Nine",
    "Dressrosa", "Alabasta", "Drum Kingdom", "East Blue", "Sky Island",
    "Fish-Man Island", "Egghead", "Punk Hazard", "Water Seven", "Whole Cake Island",
    "Impel Down", "Jailer Beast", "Thriller Bark Pirates", "Minks",
    "Supernovas", "Giant", "New Giant Pirate Crew", "New Giant Pirates",
    "FILM", "ODYSSEY", "GERMA 66", "Kingdom of GERMA", "The Sun Pirates",
    "Merfolk", "Animal", "Music", "Sprite", "Neptunian",
    "Frost Moon Village", "Windmill Village", "Goa Kingdom",
    "The Moon", "Space Pirates", "The House of Lambs",
    "Mountain Bandits", "Monkey Mountain Alliance",
    "Former Rocks Pirates", "Former Roger Pirates", "Former Rumbar Pirates",
    "Former Whitebeard Pirates", "Former CP9", "Former Arlong Pirates",
    "Former Big Mom Pirates", "Former Rolling Pirates",
    "The Pirates Fest", "Neo Navy", "Golden Lion Pirates",
    "Eldoraggo Crew", "Gasparde Pirates", "Accino Family",
    "Alvida Pirates", "Black Cat Pirates", "Krieg Pirates",
    "Gyro Pirates", "Weevil's Mother", "The Victims' Club",
    "The Owner of Cindry's Shadow",
]


def split_traits(sub_types: str) -> list[str]:
    if not sub_types or sub_types in ("NULL", "?"):
        return []
    traits: list[str] = []
    remaining = sub_types.strip()
    sorted_traits = sorted(KNOWN_TRAITS, key=len, reverse=True)
    while remaining:
        found = False
        for trait in sorted_traits:
            if remaining.startswith(trait):
                traits.append(trait)
                remaining = remaining[len(trait):].strip()
                found = True
                break
        if not found:
            if "/" in remaining:
                parts = [p.strip() for p in remaining.split("/") if p.strip()]
                traits.extend(parts)
                remaining = ""
            else:
                parts = remaining.split()
                if len(parts) > 1:
                    traits.extend(parts)
                else:
                    traits.append(remaining)
                remaining = ""
    return list(dict.fromkeys(traits))


def split_colors(color_str: str) -> list[str]:
    if not color_str:
        return []
    colors = color_str.strip().split()
    return colors


def is_alt_art(card: dict) -> bool:
    image_id = card.get("card_image_id", "")
    name = card.get("card_name", "")
    alt_indicators = [
        "_p1", "_p2", "_p3", "_p4", "_p5", "Alternate Art",
        "(Winner)", "(Textured)", "(Special Edition)",
    ]
    return any(ind in image_id or ind in name for ind in alt_indicators)


def detect_unlimited_copies(card_text: str) -> bool:
    if not card_text:
        return False
    return bool(re.search(r"any number of this card", card_text, re.IGNORECASE))


def clean_card_name(card_id: str, raw_name: str) -> str:
    """Replace the trailing "(NNN)" set-number suffix from optcgapi.com with
    the full card_id.

    The upstream API returns names like ``"Yamato (079)"`` where ``079`` is the
    card number within its set. We prefer the unambiguous full id, e.g.
    ``"Yamato (OP16-079)"``. Names without a trailing numeric suffix are left
    untouched.
    """
    if not raw_name:
        return raw_name
    return re.sub(r"\s*\((\d+)\)\s*$", f" ({card_id})", raw_name)


def normalize_card(api_card: dict) -> dict | None:
    if is_alt_art(api_card):
        return None
    card_id = api_card.get("card_set_id", "")
    if not card_id:
        return None
    card_text = api_card.get("card_text") or ""
    keywords = KeywordExtractor.extract(card_text)
    color = split_colors(api_card.get("card_color") or "")
    traits = split_traits(api_card.get("sub_types") or "")

    def parse_int(val) -> int | None:
        if val is None or val == "":
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    cost = parse_int(api_card.get("card_cost"))
    power = parse_int(api_card.get("card_power"))
    life = parse_int(api_card.get("life"))
    counter = parse_int(api_card.get("counter_amount")) or 0

    domain_card = Card(
        card_id=card_id,
        name=clean_card_name(card_id, api_card.get("card_name", "")),
        cost=cost,
        power=power,
        counter=counter,
        type=api_card.get("card_type", ""),
        color=color,
        traits=traits,
        attribute=api_card.get("attribute"),
        keywords=keywords,
        roles=[],
        effect=card_text,
        life=life,
        set_id=api_card.get("set_id", ""),
        set_name=api_card.get("set_name", ""),
        rarity=api_card.get("rarity", ""),
        image_url=api_card.get("card_image", ""),
        unlimited_copies=detect_unlimited_copies(card_text),
    )
    roles = RoleClassifier.classify(domain_card)
    domain_card.roles = roles

    return {
        "card_id": card_id,
        "name": clean_card_name(card_id, api_card.get("card_name", "")),
        "cost": cost,
        "power": power,
        "counter": counter,
        "type": api_card.get("card_type", ""),
        "color": color,
        "traits": traits,
        "attribute": api_card.get("attribute"),
        "keywords": keywords,
        "roles": roles,
        "effect": card_text,
        "effect_flags": None,
        "life": life,
        "set_id": api_card.get("set_id", ""),
        "set_name": api_card.get("set_name", ""),
        "rarity": api_card.get("rarity", ""),
        "image_url": api_card.get("card_image") or "",
        "unlimited_copies": domain_card.unlimited_copies,
        "language": "en",
    }


class CardApiImporter:
    def __init__(self, client: OptcgApiClient | None = None, delay: float = 1.0):
        self.client = client or OptcgApiClient(delay=delay)
        self.delay = delay

    def import_full(self, should_stop=None) -> dict:
        init_db()
        seen_ids: set[str] = set()
        all_cards: list[dict] = []

        logger.info("Fetching all sets...")
        sets = self.client.get_all_sets()
        logger.info("Found %d sets", len(sets))

        for s in sets:
            if should_stop and should_stop():
                logger.info("Import cancelled before fetching set %s", s.get("set_id"))
                return {"total": 0, "sets": len(sets)}
            set_id = s["set_id"]
            logger.info("Fetching set %s...", set_id)
            try:
                cards = self.client.get_set_cards(set_id)
            except Exception:
                logger.exception("Failed to fetch set %s, trying bulk fallback", set_id)
                continue
            for card in cards:
                normalized = normalize_card(card)
                if normalized and normalized["card_id"] not in seen_ids:
                    seen_ids.add(normalized["card_id"])
                    all_cards.append(normalized)
            time.sleep(self.delay)

        logger.info("Fetching ST cards...")
        try:
            st_cards = self.client.get_all_st_cards()
        except Exception:
            logger.exception("Failed to fetch ST cards")
            st_cards = []
        for card in st_cards:
            normalized = normalize_card(card)
            if normalized and normalized["card_id"] not in seen_ids:
                seen_ids.add(normalized["card_id"])
                all_cards.append(normalized)

        logger.info("Fetching promos...")
        try:
            promo_cards = self.client.get_all_promos()
        except Exception:
            logger.exception("Failed to fetch promos")
            promo_cards = []
        for card in promo_cards:
            normalized = normalize_card(card)
            if normalized and normalized["card_id"] not in seen_ids:
                seen_ids.add(normalized["card_id"])
                all_cards.append(normalized)

        logger.info("Total unique cards: %d", len(all_cards))
        saved = self._save_all(all_cards)

        get_event_bus().publish(
            "CardsRefreshed",
            CardsRefreshed(new_count=saved, updated_count=saved),
        )
        return {"total": saved, "sets": len(sets)}

    def import_incremental(self) -> dict:
        init_db()
        seen_ids: set[str] = set()
        new_cards: list[dict] = []

        logger.info("Fetching all cards (bulk) for incremental upsert...")
        try:
            cards = self.client.get_all_set_cards_bulk()
        except Exception:
            logger.exception("Failed to fetch bulk cards")
            return {"total": 0}

        for card in cards:
            normalized = normalize_card(card)
            if normalized and normalized["card_id"] not in seen_ids:
                seen_ids.add(normalized["card_id"])
                new_cards.append(normalized)

        saved = self._save_all(new_cards)
        get_event_bus().publish(
            "CardsRefreshed",
            CardsRefreshed(new_count=saved, updated_count=saved),
        )
        return {"total": saved}

    def _save_all(self, cards: list[dict]) -> int:
        init_db()
        session = SessionLocal()
        try:
            repo = CardRepository(session)
            count = repo.bulk_upsert(cards)
            session.commit()
            return count
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    importer = CardApiImporter(delay=args.delay)
    if args.full:
        result = importer.import_full()
        print(json.dumps(result, indent=2))
    elif args.incremental:
        result = importer.import_incremental()
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()
