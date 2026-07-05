from app.application.services.recommendation_service import RecommendationService
from app.infrastructure.persistence.models import (
    CardORM,
    CollectionORM,
    DeckCardORM,
    DeckORM,
    PatternORM,
    RecommendationORM,
)


def _setup(db_session):
    db_session.query(RecommendationORM).delete()
    db_session.query(PatternORM).delete()
    db_session.query(DeckCardORM).delete()
    db_session.query(DeckORM).delete()
    db_session.query(CollectionORM).delete()
    db_session.query(CardORM).delete()
    db_session.commit()


def _seed(session, cards_data, deck_cards, collection_items, patterns_data):
    for cid, data in cards_data.items():
        session.add(CardORM(
            card_id=cid,
            name=data.get("name", f"Card {cid}"),
            cost=data.get("cost"),
            power=data.get("power"),
            counter=data.get("counter", 0),
            type=data.get("type", "Character"),
            color=data.get("color", ["Red"]),
            traits=data.get("traits", []),
            attribute=data.get("attribute", "Strike"),
            keywords=data.get("keywords", []),
            roles=data.get("roles", []),
            effect=data.get("effect", "Test effect"),
            life=data.get("life"),
            set_id=data.get("set_id", "OP-16"),
            set_name=data.get("set_name", "Test"),
            rarity=data.get("rarity", "C"),
            image_url="",
            unlimited_copies=False,
        ))
    session.add(DeckORM(
        deck_id="d1",
        name="Test Deck",
        leader_card_id="OP16-079",
        source=None,
        event=None,
        date=None,
    ))
    for card_id, qty in deck_cards:
        session.add(DeckCardORM(deck_id="d1", card_id=card_id, qty=qty))
    for card_id, owned in collection_items:
        session.add(CollectionORM(card_id=card_id, owned=owned))
    for p in patterns_data:
        session.add(PatternORM(
            pattern_id=p["pattern_id"],
            filter=p.get("filter", {}),
            description=p.get("description", ""),
            severity=p.get("severity", "high"),
        ))
    session.commit()


def test_generate_recommendations_persists(db_session, session_factory):
    _setup(db_session)
    cards_data = {
        "OP16-079": {
            "type": "Leader",
            "color": ["Red"],
            "traits": ["Land of Wano"],
            "cost": None,
            "power": 5000,
            "life": 5,
        },
        "C1": {"cost": 3, "roles": ["tempo"], "color": ["Red"]},
        "C2": {"cost": 4, "roles": ["boss"], "color": ["Red"]},
        "C3": {"cost": 5, "roles": ["boss"], "color": ["Red"]},
        "G1": {"cost": 3, "roles": ["engine", "ramp"], "color": ["Red"]},
    }
    deck_cards = [("C1", 4), ("C2", 4), ("C3", 4)]
    collection_items = [("G1", 2)]
    patterns_data = [
        {"pattern_id": "don_inefficient", "severity": "high", "description": "DON unused"},
    ]
    _seed(db_session, cards_data, deck_cards, collection_items, patterns_data)

    service = RecommendationService(session_factory)
    recs = service.generate_recommendations("d1")
    assert len(recs) > 0
    assert any(r["card_in"] == "G1" for r in recs)

    persisted = service.get_recommendations("d1")
    assert len(persisted) > 0
    assert all("rec_id" in r for r in persisted)
    assert all("score" in r for r in persisted)


def test_get_recommendations_empty(db_session, session_factory):
    _setup(db_session)
    db_session.add(DeckORM(
        deck_id="empty_deck",
        name="Empty",
        leader_card_id="OP16-079",
        source=None,
        event=None,
        date=None,
    ))
    db_session.add(CardORM(
        card_id="OP16-079",
        name="Leader",
        cost=None,
        power=5000,
        counter=0,
        type="Leader",
        color=["Red"],
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
    ))
    db_session.commit()

    service = RecommendationService(session_factory)
    recs = service.get_recommendations("empty_deck")
    assert recs == []


def test_generate_no_deck_returns_empty(session_factory):
    service = RecommendationService(session_factory)
    recs = service.generate_recommendations("nonexistent")
    assert recs == []


def test_generate_no_patterns_still_has_gap_recs(db_session, session_factory):
    _setup(db_session)
    cards_data = {
        "OP16-079": {"type": "Leader", "color": ["Red"], "cost": None, "power": 5000, "life": 5},
        "C1": {"cost": 3, "roles": ["tempo"], "color": ["Red"]},
        "C2": {"cost": 4, "roles": ["boss"], "color": ["Red"]},
        "C3": {"cost": 5, "roles": ["boss"], "color": ["Red"]},
        "BLK1": {
            "cost": 2,
            "roles": ["early_blocker", "2k_counter"],
            "counter": 2000,
            "color": ["Red"],
        },
    }
    deck_cards = [("C1", 4), ("C2", 4), ("C3", 4)]
    collection_items = [("BLK1", 4)]
    _seed(db_session, cards_data, deck_cards, collection_items, [])

    service = RecommendationService(session_factory)
    recs = service.generate_recommendations("d1")
    assert len(recs) > 0
    assert any(r["card_in"] == "BLK1" for r in recs)


def test_regenerate_replaces_old(db_session, session_factory):
    _setup(db_session)
    cards_data = {
        "OP16-079": {"type": "Leader", "color": ["Red"], "cost": None, "power": 5000, "life": 5},
        "C1": {"cost": 3, "roles": ["tempo"], "color": ["Red"]},
        "C2": {"cost": 4, "roles": ["boss"], "color": ["Red"]},
        "C3": {"cost": 5, "roles": ["boss"], "color": ["Red"]},
        "G1": {"cost": 3, "roles": ["engine", "ramp"], "color": ["Red"]},
    }
    deck_cards = [("C1", 4), ("C2", 4), ("C3", 4)]
    collection_items = [("G1", 2)]
    patterns_data = [
        {"pattern_id": "don_inefficient", "severity": "high", "description": "DON unused"},
    ]
    _seed(db_session, cards_data, deck_cards, collection_items, patterns_data)

    service = RecommendationService(session_factory)
    recs1 = service.generate_recommendations("d1")
    assert len(recs1) > 0

    recs2 = service.generate_recommendations("d1")
    count2 = len(service.get_recommendations("d1"))
    assert count2 == len(recs2)
