from app.domain.engines.recommendation.recommendation_engine import RecommendationEngine
from app.domain.models import Card, Deck


def _card(
    card_id: str,
    cost: int = 3,
    power: int = 5000,
    counter: int = 0,
    ctype: str = "Character",
    color: list[str] | None = None,
    traits: list[str] | None = None,
    keywords: list[str] | None = None,
    roles: list[str] | None = None,
) -> Card:
    return Card(
        card_id=card_id,
        name=f"Test {card_id}",
        cost=cost,
        power=power,
        counter=counter,
        type=ctype,
        color=color or ["Red"],
        traits=traits or [],
        attribute="Strike",
        keywords=keywords or [],
        roles=roles or [],
        effect="Test effect",
        life=None,
        set_id="OP-16",
        set_name="Test",
        rarity="C",
        image_url="",
        unlimited_copies=False,
    )


def _leader(card_id: str = "OP16-079", color: list[str] | None = None) -> Card:
    return Card(
        card_id=card_id,
        name="Test Leader",
        cost=None,
        power=5000,
        counter=0,
        type="Leader",
        color=color or ["Red"],
        traits=["Land of Wano"],
        attribute="Strike",
        keywords=[],
        roles=[],
        effect="Leader effect",
        life=5,
        set_id="OP-16",
        set_name="Test",
        rarity="L",
        image_url="",
        unlimited_copies=False,
    )


def _deck(
    deck_id: str = "d1",
    leader_id: str = "OP16-079",
    cards: list[tuple[str, int]] | None = None,
) -> Deck:
    return Deck(
        deck_id=deck_id,
        name="Test Deck",
        leader_card_id=leader_id,
        source=None,
        event=None,
        date=None,
        cards=cards or [("C1", 4), ("C2", 4), ("C3", 4)],
    )


def test_empty_patterns_returns_nothing():
    engine = RecommendationEngine()
    deck = _deck()
    cards = {
        "OP16-079": _leader(),
        "C1": _card("C1", roles=["engine"]),
        "C2": _card("C2", roles=["tempo"]),
        "C3": _card("C3", roles=["boss"]),
    }
    recs = engine.recommend(deck, cards, {}, [])
    assert recs == []


def test_no_leader_returns_empty():
    engine = RecommendationEngine()
    deck = _deck()
    recs = engine.recommend(deck, {}, {}, [])
    assert recs == []


def test_don_inefficient_pattern_recommends_ramp_or_engine():
    engine = RecommendationEngine()
    leader = _leader()
    deck = _deck(cards=[("C1", 4), ("C2", 4), ("C3", 4)])
    cards = {
        "OP16-079": leader,
        "C1": _card("C1", cost=3, roles=["tempo"]),
        "C2": _card("C2", cost=4, roles=["boss"]),
        "C3": _card("C3", cost=5, roles=["boss"]),
        "GOOD1": _card("GOOD1", cost=3, roles=["ramp", "engine"]),
    }
    patterns = [{"pattern_id": "don_inefficient", "severity": "high", "description": "DON unused"}]
    collection = {"GOOD1": 2}
    recs = engine.recommend(deck, cards, collection, patterns)
    assert len(recs) > 0
    assert any(r.card_in == "GOOD1" for r in recs)


def test_low_blockers_gap_detected():
    engine = RecommendationEngine()
    leader = _leader()
    deck = _deck(cards=[("C1", 4), ("C2", 4), ("C3", 4)])
    cards = {
        "OP16-079": leader,
        "C1": _card("C1", cost=2, roles=["tempo"]),
        "C2": _card("C2", cost=4, roles=["boss"]),
        "C3": _card("C3", cost=5, roles=["boss"]),
        "BLK1": _card("BLK1", cost=2, roles=["early_blocker", "2k_counter"], counter=2000),
    }
    collection = {"BLK1": 4}
    recs = engine.recommend(deck, cards, collection, [])
    assert len(recs) > 0
    assert any(r.card_in == "BLK1" for r in recs)
    blocker_rec = [r for r in recs if r.card_in == "BLK1"][0]
    gained = blocker_rec.rationale_payload.get("roles_gained", [])
    assert "early_blocker" in gained or "2k_counter" in gained


def test_low_counters_gap_detected():
    engine = RecommendationEngine()
    leader = _leader()
    deck = _deck(cards=[("C1", 4), ("C2", 4), ("C3", 4)])
    cards = {
        "OP16-079": leader,
        "C1": _card("C1", cost=2, roles=["tempo"]),
        "C2": _card("C2", cost=4, roles=["boss"]),
        "C3": _card("C3", cost=5, roles=["boss"]),
        "CNT1": _card("CNT1", cost=2, roles=["2k_counter"], counter=2000),
    }
    collection = {"CNT1": 4}
    recs = engine.recommend(deck, cards, collection, [])
    assert len(recs) > 0
    assert any(r.card_in == "CNT1" for r in recs)


def test_color_filter_excludes_wrong_color():
    engine = RecommendationEngine()
    leader = _leader(color=["Red"])
    deck = _deck(cards=[("C1", 4), ("C2", 4), ("C3", 4)])
    cards = {
        "OP16-079": leader,
        "C1": _card("C1", cost=2, roles=["tempo"]),
        "C2": _card("C2", cost=4, roles=["boss"]),
        "C3": _card("C3", cost=5, roles=["boss"]),
        "BLUE1": _card("BLUE1", cost=2, roles=["early_blocker"], color=["Blue"]),
    }
    collection = {"BLUE1": 4}
    recs = engine.recommend(deck, cards, collection, [])
    assert all(r.card_in != "BLUE1" for r in recs)


def test_recommendations_sorted_by_score():
    engine = RecommendationEngine()
    leader = _leader()
    deck = _deck(cards=[("C1", 4), ("C2", 4), ("C3", 4)])
    cards = {
        "OP16-079": leader,
        "C1": _card("C1", cost=3, roles=["tempo"]),
        "C2": _card("C2", cost=4, roles=["boss"]),
        "C3": _card("C3", cost=5, roles=["boss"]),
        "G1": _card("G1", cost=3, roles=["early_blocker", "2k_counter"], counter=2000),
        "G2": _card("G2", cost=3, roles=["engine", "searcher"]),
    }
    collection = {"G1": 4, "G2": 2}
    recs = engine.recommend(deck, cards, collection, [])
    scores = [r.score for r in recs]
    assert scores == sorted(scores, reverse=True)


def test_max_10_recommendations():
    engine = RecommendationEngine()
    leader = _leader()
    deck = _deck(cards=[("C1", 4), ("C2", 4), ("C3", 4)])
    cards = {
        "OP16-079": leader,
        "C1": _card("C1", cost=3, roles=["tempo"]),
        "C2": _card("C2", cost=4, roles=["boss"]),
        "C3": _card("C3", cost=5, roles=["boss"]),
    }
    for i in range(20):
        cards[f"G{i}"] = _card(
            f"G{i}", cost=3, roles=["early_blocker", "2k_counter"], counter=2000
        )
    collection = {f"G{i}": 4 for i in range(20)}
    recs = engine.recommend(deck, cards, collection, [])
    assert len(recs) <= 10


def test_rationale_payload_has_problem_info():
    engine = RecommendationEngine()
    leader = _leader()
    deck = _deck(cards=[("C1", 4), ("C2", 4), ("C3", 4)])
    cards = {
        "OP16-079": leader,
        "C1": _card("C1", cost=3, roles=["tempo"]),
        "C2": _card("C2", cost=4, roles=["boss"]),
        "C3": _card("C3", cost=5, roles=["boss"]),
        "G1": _card("G1", cost=3, roles=["engine", "ramp"]),
    }
    patterns = [
        {"pattern_id": "don_inefficient", "severity": "high", "description": "DON unused too much"},
    ]
    collection = {"G1": 2}
    recs = engine.recommend(deck, cards, collection, patterns)
    assert len(recs) > 0
    r = recs[0]
    assert "problem" in r.rationale_payload
    assert r.rationale_payload["problem"] == "don_inefficient"
    assert "description" in r.rationale_payload


def test_no_candidates_returns_empty():
    engine = RecommendationEngine()
    leader = _leader()
    deck = _deck(cards=[("C1", 4), ("C2", 4), ("C3", 4)])
    cards = {
        "OP16-079": leader,
        "C1": _card("C1", cost=3, roles=["tempo"]),
        "C2": _card("C2", cost=4, roles=["boss"]),
        "C3": _card("C3", cost=5, roles=["boss"]),
    }
    patterns = [{"pattern_id": "don_inefficient", "severity": "high", "description": "DON unused"}]
    collection = {}
    recs = engine.recommend(deck, cards, collection, patterns)
    assert recs == []


def test_low_severity_pattern_not_used():
    engine = RecommendationEngine()
    leader = _leader()
    deck = _deck(cards=[("C1", 4), ("C2", 4), ("C3", 4)])
    cards = {
        "OP16-079": leader,
        "C1": _card("C1", cost=3, roles=["tempo"]),
        "C2": _card("C2", cost=4, roles=["boss"]),
        "C3": _card("C3", cost=5, roles=["boss"]),
        "G1": _card("G1", cost=3, roles=["ramp"]),
    }
    patterns = [{"pattern_id": "don_inefficient", "severity": "low", "description": "DON unused"}]
    collection = {"G1": 2}
    recs = engine.recommend(deck, cards, collection, patterns)
    don_recs = [r for r in recs if r.rationale_payload.get("problem") == "don_inefficient"]
    assert len(don_recs) == 0


def test_deck_already_in_deck_excluded():
    engine = RecommendationEngine()
    leader = _leader()
    deck = _deck(cards=[("C1", 4), ("C2", 4), ("C3", 4)])
    cards = {
        "OP16-079": leader,
        "C1": _card("C1", cost=3, roles=["tempo"]),
        "C2": _card("C2", cost=4, roles=["boss"]),
        "C3": _card("C3", cost=5, roles=["boss"]),
    }
    collection = {"C1": 4}
    recs = engine.recommend(deck, cards, collection, [])
    assert all(r.card_in != "C1" for r in recs)
