from app.application.services.scoring_engine import ScoringEngine
from app.infrastructure.persistence.repositories.card_repo import CardRepository
from app.infrastructure.persistence.repositories.collection_repo import CollectionRepository
from app.infrastructure.persistence.repositories.deck_repo import DeckRepository


def _make_card(session, card_id, **overrides):
    repo = CardRepository(session)
    defaults = {
        "card_id": card_id,
        "name": card_id,
        "cost": 2,
        "power": 1000,
        "counter": 0,
        "type": "Character",
        "color": ["Red"],
        "traits": ["Supernovas"],
        "attribute": "Strike",
        "keywords": [],
        "roles": [],
        "effect": "",
        "life": None,
        "set_id": "TEST",
        "set_name": "Test Set",
        "rarity": "C",
        "image_url": "",
        "unlimited_copies": False,
        "language": "en",
    }
    defaults.update(overrides)
    repo.upsert(defaults)


def _make_deck(session, deck_id, leader_id, cards):
    repo = DeckRepository(session)
    repo.upsert(
        {
            "deck_id": deck_id,
            "name": deck_id,
            "leader_card_id": leader_id,
            "source": None,
            "event": None,
            "date": None,
        },
        cards,
    )


def _setup_optimal_deck(db_session):
    _make_card(
        db_session,
        "LEADER-001",
        cost=None,
        power=5000,
        counter=0,
        type="Leader",
        color=["Red"],
        traits=["Supernovas"],
        life=5,
    )

    card_defs = [
        ("C-001", 2, ["Red"], ["Supernovas"], ["searcher"]),
        ("C-002", 3, ["Red"], ["Supernovas"], ["engine"]),
        ("C-003", 2, ["Red"], ["Supernovas"], ["early_blocker"]),
        ("C-004", 3, ["Red"], ["Supernovas"], ["removal"]),
        ("C-005", 1, ["Red"], ["Supernovas"], ["searcher"]),
        ("C-006", 2, ["Red"], ["Supernovas"], []),
        ("C-007", 3, ["Red"], ["Supernovas"], ["engine"]),
        ("C-008", 4, ["Red"], ["Supernovas"], []),
        ("C-009", 0, ["Red"], ["Supernovas"], []),
        ("C-010", 2, ["Red"], ["Supernovas"], ["searcher"]),
        ("C-011", 4, ["Red"], ["Supernovas"], ["removal"]),
        ("C-012", 5, ["Red"], ["Supernovas"], []),
        ("C-013", 6, ["Red"], ["Supernovas"], ["boss"]),
    ]

    for card_id, cost, color, traits, roles in card_defs:
        _make_card(db_session, card_id, cost=cost, color=color, traits=traits, roles=roles)

    deck_cards = [
        ("C-001", 4),
        ("C-002", 4),
        ("C-003", 4),
        ("C-004", 3),
        ("C-005", 4),
        ("C-006", 4),
        ("C-007", 4),
        ("C-008", 4),
        ("C-009", 4),
        ("C-010", 4),
        ("C-011", 3),
        ("C-012", 4),
        ("C-013", 3),
    ]

    for card_id, qty in deck_cards:
        CollectionRepository(db_session).set_owned(card_id, qty)

    _make_deck(db_session, "OPT-DECK", "LEADER-001", deck_cards)
    db_session.commit()


def _setup_broken_deck(db_session):
    _make_card(
        db_session,
        "LEADER-002",
        cost=None,
        power=5000,
        counter=0,
        type="Leader",
        color=["Blue"],
        traits=["Sky Island"],
        life=5,
    )

    card_ids = [f"B-{i:03d}" for i in range(1, 51)]
    for idx, card_id in enumerate(card_ids):
        colors = [["Red"], ["Green"], ["Yellow"], ["Purple"], ["Black"]][
            idx % 5
        ]
        traits = [["Supernovas"], ["Straw Hat Pirates"], ["Fish-Man"], ["East Blue"]][
            idx % 4
        ]
        _make_card(
            db_session,
            card_id,
            cost=8,
            color=colors,
            traits=traits,
            roles=[],
        )

    deck_cards = [(cid, 1) for cid in card_ids]
    _make_deck(db_session, "BROKEN-DECK", "LEADER-002", deck_cards)
    db_session.commit()


def _setup_curve_deck(db_session):
    _make_card(
        db_session,
        "LEADER-003",
        cost=None,
        power=5000,
        counter=0,
        type="Leader",
        color=["Red"],
        traits=["Supernovas"],
        life=5,
    )

    curve_cards = [
        ("CV-001", 0, 2),
        ("CV-002", 1, 4),
        ("CV-003", 1, 4),
        ("CV-004", 2, 4),
        ("CV-005", 2, 4),
        ("CV-006", 2, 4),
        ("CV-007", 3, 4),
        ("CV-008", 3, 4),
        ("CV-009", 3, 4),
        ("CV-010", 4, 4),
        ("CV-011", 4, 4),
        ("CV-012", 5, 3),
        ("CV-013", 5, 3),
        ("CV-014", 6, 2),
        ("CV-015", 7, 2),
        ("CV-016", 8, 2),
    ]

    for card_id, cost, qty in curve_cards:
        _make_card(db_session, card_id, cost=cost, color=["Red"], traits=["Supernovas"])

    deck_cards = [(cid, q) for cid, _, q in curve_cards]
    _make_deck(db_session, "CURVE-DECK", "LEADER-003", deck_cards)
    db_session.commit()


def _setup_synergy_deck(db_session):
    _make_card(
        db_session,
        "LEADER-004",
        cost=None,
        power=5000,
        counter=0,
        type="Leader",
        color=["Red"],
        traits=["Supernovas"],
        life=5,
    )

    synergy_cards = [
        ("S-001", 2, ["Red"], ["Supernovas"], ["engine"]),
        ("S-002", 2, ["Red"], ["Supernovas"], ["early_blocker"]),
        ("S-003", 3, ["Red"], ["Supernovas"], ["removal"]),
        ("S-004", 3, ["Red"], ["Supernovas"], ["searcher"]),
        ("S-005", 2, ["Red"], ["Supernovas"], []),
        ("S-006", 3, ["Red"], ["Supernovas"], []),
        ("S-007", 4, ["Red"], ["Supernovas"], []),
        ("S-008", 1, ["Red"], ["Supernovas"], []),
        ("S-009", 5, ["Red"], ["Supernovas"], []),
        ("S-010", 2, ["Red"], ["Supernovas"], []),
        ("S-011", 3, ["Red"], ["Supernovas"], []),
        ("S-012", 4, ["Red"], ["Supernovas"], []),
        ("S-013", 6, ["Red"], ["Supernovas"], []),
    ]

    for card_id, cost, color, traits, roles in synergy_cards:
        _make_card(db_session, card_id, cost=cost, color=color, traits=traits, roles=roles)

    deck_cards = [
        ("S-001", 4),
        ("S-002", 4),
        ("S-003", 4),
        ("S-004", 4),
        ("S-005", 4),
        ("S-006", 4),
        ("S-007", 4),
        ("S-008", 4),
        ("S-009", 4),
        ("S-010", 4),
        ("S-011", 4),
        ("S-012", 4),
        ("S-013", 6),
    ]
    _make_deck(db_session, "SYN-DECK", "LEADER-004", deck_cards)
    db_session.commit()


def test_score_optimal_deck(db_session, session_factory):
    _setup_optimal_deck(db_session)
    engine = ScoringEngine(session_factory, auto_subscribe=False)
    score = engine.score_deck("OPT-DECK")
    assert score.overall > 60
    assert score.version == 1
    assert "consistency" in score.breakdown
    assert "curve" in score.breakdown
    assert "collection" in score.breakdown
    assert "synergy" in score.breakdown
    assert "matchups" in score.breakdown


def test_score_broken_deck(db_session, session_factory):
    _setup_broken_deck(db_session)
    engine = ScoringEngine(session_factory, auto_subscribe=False)
    score = engine.score_deck("BROKEN-DECK")
    assert score.overall < 40
    assert score.breakdown["curve"] <= 10
    assert score.breakdown["synergy"] <= 15


def test_collection_score(db_session, session_factory):
    _setup_optimal_deck(db_session)
    engine = ScoringEngine(session_factory, auto_subscribe=False)
    score = engine.score_deck("OPT-DECK")
    assert score.breakdown["collection"] == 100


def test_curve_analysis(db_session, session_factory):
    _setup_curve_deck(db_session)
    engine = ScoringEngine(session_factory, auto_subscribe=False)
    score = engine.score_deck("CURVE-DECK")
    assert score.breakdown["curve"] > 70


def test_synergy_color_match(db_session, session_factory):
    _setup_synergy_deck(db_session)
    engine = ScoringEngine(session_factory, auto_subscribe=False)
    score = engine.score_deck("SYN-DECK")
    assert score.breakdown["synergy"] > 80


def test_deck_not_found(session_factory):
    engine = ScoringEngine(session_factory, auto_subscribe=False)
    try:
        engine.score_deck("NONEXISTENT-999")
        assert False, "Should have raised ValueError"  # noqa: B011
    except ValueError:
        pass


def test_score_persisted(db_session, session_factory):
    from app.infrastructure.persistence.models import DeckScoreORM

    _setup_optimal_deck(db_session)
    engine = ScoringEngine(session_factory, auto_subscribe=False)
    engine.score_deck("OPT-DECK")

    record = db_session.get(DeckScoreORM, "OPT-DECK")
    assert record is not None
    assert record.overall > 60
    assert record.version == 1
    assert "consistency" in record.breakdown
