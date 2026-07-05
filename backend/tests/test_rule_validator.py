from app.domain.engines.deck.rule_validator import RuleValidator
from app.domain.models import Card, Deck


def make_card(
    card_id: str,
    color: str = "Black",
    cost: int | None = 2,
    type: str = "Character",
    roles: list[str] | None = None,
    keywords: list[str] | None = None,
    set_id: str = "OP-16",
    unlimited_copies: bool = False,
) -> Card:
    return Card(
        card_id=card_id,
        name=f"Test {card_id}",
        cost=cost,
        power=1000,
        counter=1000,
        type=type,
        color=[color],
        traits=[],
        attribute=None,
        keywords=keywords or [],
        roles=roles or [],
        effect="",
        life=None,
        set_id=set_id,
        set_name="Test",
        rarity="C",
        image_url="",
        unlimited_copies=unlimited_copies,
    )


def make_leader(card_id: str = "OP16-079", color: str = "Black") -> Card:
    return Card(
        card_id=card_id,
        name="Leader",
        cost=None,
        power=5000,
        counter=0,
        type="Leader",
        color=[color],
        traits=[],
        attribute=None,
        keywords=[],
        roles=[],
        effect="",
        life=5,
        set_id="OP-16",
        set_name="Test",
        rarity="L",
        image_url="",
        unlimited_copies=False,
    )


def make_deck(leader_id: str, cards_list: list[tuple[str, int]]) -> Deck:
    return Deck(
        deck_id="test-deck",
        name="Test Deck",
        leader_card_id=leader_id,
        source=None,
        event=None,
        date=None,
        cards=cards_list,
    )


def build_deck_cards(n: int, start: int = 1) -> list[tuple[str, int]]:
    """Build deck cards summing to n, using max 4 copies per card_id."""
    cards = []
    full_groups = n // 4
    remainder = n % 4
    for i in range(full_groups):
        cards.append((f"OP16-{start + i:03d}", 4))
    if remainder:
        cards.append((f"OP16-{start + full_groups:03d}", remainder))
    return cards


def build_cards_dict(card_ids: list[str], **kwargs) -> dict[str, Card]:
    return {cid: make_card(cid, **kwargs) for cid in card_ids}


def test_valid_deck_passes():
    leader = make_leader()
    deck_cards = build_deck_cards(50)
    cards = {leader.card_id: leader, **build_cards_dict([cid for cid, _ in deck_cards])}
    deck = make_deck(leader.card_id, deck_cards)

    result = RuleValidator().validate(deck, cards)
    assert result.errors == []


def test_banned_card_fails():
    leader = make_leader()
    deck_cards = build_deck_cards(50)
    banned_id = deck_cards[0][0]
    cards = {leader.card_id: leader, **build_cards_dict([cid for cid, _ in deck_cards])}
    deck = make_deck(leader.card_id, deck_cards)

    format_bans = {
        "banned_cards": [banned_id],
        "banned_sets": [],
        "banned_blocks": [],
        "banned_pair1": [],
        "banned_pair2": [],
    }

    result = RuleValidator().validate(deck, cards, format_bans)
    assert any("banned" in e.lower() for e in result.errors)


def test_too_many_copies_fails():
    leader = make_leader()
    rest = build_deck_cards(45, start=100)
    deck_cards = [("OP16-001", 5)] + rest
    cards = {leader.card_id: leader, "OP16-001": make_card("OP16-001")}
    cards.update({cid: make_card(cid) for cid, _ in rest})
    deck = make_deck(leader.card_id, deck_cards)

    result = RuleValidator().validate(deck, cards)
    assert any("copies" in e.lower() or "max 4" in e.lower() for e in result.errors)


def test_unlimited_copies_ok():
    leader = make_leader()
    rest = build_deck_cards(42, start=200)
    deck_cards = [("OP16-042", 8)] + rest
    cards = {leader.card_id: leader}
    cards["OP16-042"] = make_card("OP16-042", unlimited_copies=True)
    cards.update({cid: make_card(cid) for cid, _ in rest})
    deck = make_deck(leader.card_id, deck_cards)

    result = RuleValidator().validate(deck, cards)
    assert not any("copies" in e.lower() or "max 4" in e.lower() for e in result.errors)


def test_color_mismatch_fails():
    leader = make_leader(color="Black")
    deck_cards = build_deck_cards(50)
    first_id = deck_cards[0][0]
    cards = {leader.card_id: leader}
    cards[first_id] = make_card(first_id, color="Red")
    for cid, _ in deck_cards[1:]:
        cards[cid] = make_card(cid, color="Black")
    deck = make_deck(leader.card_id, deck_cards)

    result = RuleValidator().validate(deck, cards)
    assert any("color" in e.lower() for e in result.errors)


def test_restricted_pair_fails():
    leader = make_leader()
    rest = build_deck_cards(42, start=300)
    deck_cards = [("OP05-001", 4), ("OP05-002", 4)] + rest
    cards = {leader.card_id: leader}
    cards["OP05-001"] = make_card("OP05-001")
    cards["OP05-002"] = make_card("OP05-002")
    cards.update({cid: make_card(cid) for cid, _ in rest})
    deck = make_deck(leader.card_id, deck_cards)

    format_bans = {
        "banned_cards": [],
        "banned_sets": [],
        "banned_blocks": [],
        "banned_pair1": ["OP05-001"],
        "banned_pair2": ["OP05-002"],
    }

    result = RuleValidator().validate(deck, cards, format_bans)
    assert any("pair" in e.lower() or "restricted" in e.lower() for e in result.errors)


def test_structure_wrong_count():
    leader = make_leader()
    deck_cards = build_deck_cards(49)
    cards = {leader.card_id: leader, **build_cards_dict([cid for cid, _ in deck_cards])}
    deck = make_deck(leader.card_id, deck_cards)

    result = RuleValidator().validate(deck, cards)
    assert any("50" in e for e in result.errors)


def test_warnings_emitted():
    leader = make_leader()
    deck_cards = build_deck_cards(50)
    cards = {leader.card_id: leader}
    for cid, _ in deck_cards:
        cards[cid] = make_card(cid, cost=7)
    deck = make_deck(leader.card_id, deck_cards)

    result = RuleValidator().validate(deck, cards)
    assert len(result.warnings) > 0
    assert any("curva" in w.lower() for w in result.warnings)
