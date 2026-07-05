import datetime

from app.infrastructure.persistence.models import MatchORM


def setup_match(db_session, leader_self="OP16-079", leader_opp="OP16-080"):
    """Insert a minimal match directly into the DB."""
    match = MatchORM(
        match_id="test-match-001",
        room_id="room123",
        version="1.40a",
        source_file="2026-06-23T18_20_36.txt",
        leader_self=leader_self,
        leader_opp=leader_opp,
        opponent_user="Opponent",
        result="win",
        reason="Opponent Concedes!",
        duration_turns=10,
    )
    db_session.add(match)
    db_session.commit()
    return match


def test_match_list_includes_deck_ids(client, db_session):
    setup_match(db_session)
    response = client.get("/api/matches")
    assert response.status_code == 200
    data = response.json()
    assert len(data["matches"]) == 1
    m = data["matches"][0]
    assert "deck_id_self" in m
    assert "deck_id_opp" in m
    assert m["deck_id_self"] is None
    assert m["deck_id_opp"] is None


def test_match_detail_includes_deck_ids(client, db_session):
    setup_match(db_session)
    response = client.get("/api/matches/test-match-001")
    assert response.status_code == 200
    data = response.json()
    assert "deck_id_self" in data
    assert "deck_id_opp" in data


def test_assign_match_deck(client, db_session):
    setup_match(db_session)
    response = client.put(
        "/api/matches/test-match-001/deck-assignment",
        json={"deck_id_self": "my-deck-1", "deck_id_opp": "opp-deck-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deck_id_self"] == "my-deck-1"
    assert data["deck_id_opp"] == "opp-deck-1"

    verify = client.get("/api/matches/test-match-001")
    assert verify.json()["deck_id_self"] == "my-deck-1"
    assert verify.json()["deck_id_opp"] == "opp-deck-1"


def test_assign_match_deck_partial(client, db_session):
    setup_match(db_session)
    response = client.put(
        "/api/matches/test-match-001/deck-assignment",
        json={"deck_id_self": "my-deck-2"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deck_id_self"] == "my-deck-2"
    assert data["deck_id_opp"] is None


def test_assign_match_deck_not_found(client, db_session):
    response = client.put(
        "/api/matches/nonexistent/deck-assignment",
        json={"deck_id_self": "x"},
    )
    assert response.status_code == 404


def test_auto_assign_match_deck_no_decks(client, db_session):
    setup_match(db_session)
    response = client.post("/api/matches/test-match-001/auto-assign-deck")
    assert response.status_code == 200
    data = response.json()
    assert data["deck_id_self"] is None
    assert data["deck_id_opp"] is None


def test_auto_assign_match_deck_with_deck(client, db_session):
    from app.infrastructure.persistence.models import DeckORM

    setup_match(db_session)
    deck = DeckORM(
        deck_id="OP16-079_v1",
        name="Yamato Deck",
        leader_card_id="OP16-079",
        source=None,
        version=1,
    )
    db_session.add(deck)
    db_session.commit()

    response = client.post("/api/matches/test-match-001/auto-assign-deck")
    assert response.status_code == 200
    data = response.json()
    assert data["deck_id_self"] == "OP16-079_v1"


def test_auto_assign_match_deck_picks_closest_date(client, db_session):
    from app.infrastructure.persistence.models import DeckORM

    setup_match(db_session)

    old_deck = DeckORM(
        deck_id="OP16-079_v1",
        name="Old Yamato",
        leader_card_id="OP16-079",
        source=None,
        version=1,
        created_at=datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC),
    )
    new_deck = DeckORM(
        deck_id="OP16-079_v2",
        name="New Yamato",
        leader_card_id="OP16-079",
        source=None,
        version=2,
        created_at=datetime.datetime(2026, 6, 22, tzinfo=datetime.UTC),
    )
    future_deck = DeckORM(
        deck_id="OP16-079_v3",
        name="Future Yamato",
        leader_card_id="OP16-079",
        source=None,
        version=3,
        created_at=datetime.datetime(2026, 12, 1, tzinfo=datetime.UTC),
    )
    db_session.add_all([old_deck, new_deck, future_deck])
    db_session.commit()

    response = client.post("/api/matches/test-match-001/auto-assign-deck")
    assert response.status_code == 200
    data = response.json()
    assert data["deck_id_self"] == "OP16-079_v2"


def test_assign_to_unassigned_matches_assigns_deck(db_session):
    from app.infrastructure.persistence.models import DeckORM
    from app.infrastructure.persistence.repositories.deck_repo import DeckRepository

    setup_match(db_session)
    deck = DeckORM(
        deck_id="OP16-079_v1",
        name="Yamato Deck",
        leader_card_id="OP16-079",
        source=None,
        version=1,
    )
    db_session.add(deck)
    db_session.commit()

    repo = DeckRepository(db_session)
    updated = repo.assign_to_unassigned_matches("OP16-079")
    db_session.commit()

    assert updated == 1
    match = db_session.get(MatchORM, "test-match-001")
    assert match.deck_id_self == "OP16-079_v1"
    assert match.deck_id_opp is None


def test_assign_to_unassigned_matches_no_overwrite(db_session):
    from app.infrastructure.persistence.models import DeckORM
    from app.infrastructure.persistence.repositories.deck_repo import DeckRepository

    match = setup_match(db_session)
    match.deck_id_self = "OP16-079_v1"
    db_session.commit()

    deck_v2 = DeckORM(
        deck_id="OP16-079_v2",
        name="Yamato Deck v2",
        leader_card_id="OP16-079",
        source=None,
        version=2,
    )
    db_session.add(deck_v2)
    db_session.commit()

    repo = DeckRepository(db_session)
    updated = repo.assign_to_unassigned_matches("OP16-079")
    db_session.commit()

    assert updated == 0
    match = db_session.get(MatchORM, "test-match-001")
    assert match.deck_id_self == "OP16-079_v1"


def test_assign_to_unassigned_matches_not_opponent(db_session):
    from app.infrastructure.persistence.models import DeckORM
    from app.infrastructure.persistence.repositories.deck_repo import DeckRepository

    setup_match(db_session, leader_self="OP16-079", leader_opp="OP16-079")

    deck = DeckORM(
        deck_id="OP16-079_v1",
        name="Yamato Deck",
        leader_card_id="OP16-079",
        source=None,
        version=1,
    )
    db_session.add(deck)
    db_session.commit()

    repo = DeckRepository(db_session)
    updated = repo.assign_to_unassigned_matches("OP16-079")
    db_session.commit()

    assert updated == 1
    match = db_session.get(MatchORM, "test-match-001")
    assert match.deck_id_self == "OP16-079_v1"
    assert match.deck_id_opp is None
