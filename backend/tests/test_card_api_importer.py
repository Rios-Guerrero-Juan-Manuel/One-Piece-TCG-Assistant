from app.infrastructure.importers.card_api_importer import (
    clean_card_name,
    detect_unlimited_copies,
    is_alt_art,
    normalize_card,
    split_colors,
    split_traits,
)


def test_normalize_card_leader():
    api_card = {
        "card_set_id": "OP16-079",
        "card_name": "Yamato",
        "card_text": (
            "[Blocker] (When this character is attacked, "
            "you can rest this character to stop the attack.)"
        ),
        "set_id": "OP16",
        "set_name": "Emperor's New World",
        "rarity": "Leader",
        "card_color": "Blue",
        "card_type": "Leader",
        "life": "5",
        "card_cost": "5",
        "card_power": "5000",
        "counter_amount": "0",
        "attribute": "Slash",
        "sub_types": "Land of Wano Straw Hat Crew",
        "card_image": "https://www.optcgapi.com/images/OP16-079.jpg",
    }
    result = normalize_card(api_card)
    assert result is not None
    assert result["card_id"] == "OP16-079"
    assert result["name"] == "Yamato"
    assert result["color"] == ["Blue"]
    assert result["type"] == "Leader"
    assert result["life"] == 5
    assert result["cost"] == 5
    assert result["power"] == 5000
    assert result["counter"] == 0
    assert result["attribute"] == "Slash"
    assert "Land of Wano" in result["traits"]
    assert "Straw Hat Crew" in result["traits"]
    assert "blocker" in result["keywords"]
    assert result["language"] == "en"
    assert result["set_id"] == "OP16"


def test_normalize_card_name_strips_number_suffix():
    api_card = {
        "card_set_id": "OP16-098",
        "card_name": "Yamato (098)",
        "card_text": "",
        "set_id": "OP16",
        "set_name": "Emperor's New World",
        "rarity": "C",
        "card_color": "Red",
        "card_type": "Character",
        "card_cost": "5",
        "card_power": "5000",
        "counter_amount": "0",
        "sub_types": "Land of Wano",
        "card_image": "https://www.optcgapi.com/images/OP16-098.jpg",
    }
    result = normalize_card(api_card)
    assert result is not None
    assert result["name"] == "Yamato (OP16-098)"


def test_clean_card_name_replaces_suffix():
    assert clean_card_name("OP16-098", "Yamato (098)") == "Yamato (OP16-098)"
    assert clean_card_name("ST01-001", "Luffy (001)") == "Luffy (ST01-001)"


def test_clean_card_name_no_suffix_unchanged():
    assert clean_card_name("OP16-079", "Yamato") == "Yamato"
    assert clean_card_name("OP16-079", "") == ""


def test_is_alt_art_p1():
    card = {"card_image_id": "OP01-001_p1", "card_name": "Luffy"}
    assert is_alt_art(card) is True


def test_is_alt_art_alternate_art():
    card = {"card_image_id": "OP01-001", "card_name": "Luffy (Alternate Art)"}
    assert is_alt_art(card) is True


def test_is_alt_art_normal():
    card = {"card_image_id": "OP01-001", "card_name": "Luffy"}
    assert is_alt_art(card) is False


def test_detect_unlimited_copies_positive():
    text = "You may include any number of this card in your deck."
    assert detect_unlimited_copies(text) is True


def test_detect_unlimited_copies_negative():
    text = "This card is a normal character with no special rules."
    assert detect_unlimited_copies(text) is False


def test_split_traits_multi():
    traits = split_traits("Land of Wano Straw Hat Crew")
    assert traits == ["Land of Wano", "Straw Hat Crew"]


def test_split_traits_single():
    traits = split_traits("Navy")
    assert traits == ["Navy"]


def test_split_traits_empty():
    assert split_traits("") == []
    assert split_traits("NULL") == []


def test_split_colors_multi():
    colors = split_colors("Red Blue")
    assert colors == ["Red", "Blue"]
    assert split_colors("") == []
