from app.infrastructure.persistence.repositories.format_repo import FormatRepository


def setup_cards(session):
    from app.infrastructure.persistence.repositories.card_repo import CardRepository

    repo = CardRepository(session)
    repo.upsert({
        "card_id": "OP16-079",
        "name": "Yamato",
        "cost": None,
        "power": 5000,
        "counter": 0,
        "type": "Leader",
        "color": ["Black"],
        "traits": [],
        "attribute": "Strike",
        "keywords": [],
        "roles": [],
        "effect": "test",
        "life": 5,
        "set_id": "OP-16",
        "set_name": "test",
        "rarity": "L",
        "image_url": "",
        "unlimited_copies": False,
        "language": "en",
    })
    for i in range(1, 14):
        cid = f"OP16-{i:03d}"
        repo.upsert({
            "card_id": cid,
            "name": f"Card {i}",
            "cost": 2,
            "power": 1000,
            "counter": 1000,
            "type": "Character",
            "color": ["Black"],
            "traits": [],
            "attribute": None,
            "keywords": [],
            "roles": [],
            "effect": "",
            "life": None,
            "set_id": "OP-16",
            "set_name": "test",
            "rarity": "C",
            "image_url": "",
            "unlimited_copies": False,
            "language": "en",
        })
    session.commit()


def setup_formats(session):
    repo = FormatRepository(session)
    repo.upsert({
        "format_name": "Western",
        "banned_cards": [],
        "banned_sets": [],
        "banned_blocks": [],
        "banned_pair1": [],
        "banned_pair2": [],
    })
    session.commit()


DECK_TEXT = (
    "1xOP16-079\n"
    + "\n".join(f"4xOP16-{i:03d}" for i in range(1, 13))
    + "\n2xOP16-013"
)


def test_list_decks(client, db_session):
    setup_cards(db_session)
    client.post(
        "/api/decks/import",
        json={"name": "Test Deck", "text": DECK_TEXT},
    )
    response = client.get("/api/decks")
    assert response.status_code == 200
    data = response.json()
    assert "decks" in data
    assert len(data["decks"]) >= 1


def test_import_deck(client, db_session):
    setup_cards(db_session)
    response = client.post(
        "/api/decks/import",
        json={"name": "Imported Deck", "text": DECK_TEXT},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["deck_id"]
    assert data["name"] == "Imported Deck"
    assert data["leader_card_id"] == "OP16-079"
    assert data["card_count"] == 50


def test_validate_deck(client, db_session):
    setup_cards(db_session)
    setup_formats(db_session)
    resp = client.post(
        "/api/decks/import",
        json={"name": "Valid Deck", "text": DECK_TEXT},
    )
    deck_id = resp.json()["deck_id"]
    response = client.post(f"/api/decks/{deck_id}/validate?format_name=Western")
    assert response.status_code == 200
    data = response.json()
    assert "errors" in data
    assert "warnings" in data


def test_list_decks_shows_version(client, db_session):
    setup_cards(db_session)
    client.post(
        "/api/decks/import",
        json={"name": "Versioned Deck", "text": DECK_TEXT},
    )
    response = client.get("/api/decks")
    data = response.json()
    assert data["decks"][0]["version"] == 1


def test_import_deck_new_version(client, db_session):
    setup_cards(db_session)
    resp1 = client.post(
        "/api/decks/import",
        json={"name": "My Yamato", "text": DECK_TEXT, "mode": "new"},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["version"] == 1

    resp2 = client.post(
        "/api/decks/import",
        json={"name": "My Yamato", "text": DECK_TEXT, "mode": "new_version"},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["version"] == 2
    assert data2["deck_id"] == "OP16-079_v2"
    assert data2["name"] == "My Yamato v2"
    assert data2["leader_card_id"] == "OP16-079"


def test_get_deck_versions(client, db_session):
    setup_cards(db_session)
    client.post(
        "/api/decks/import",
        json={"name": "Deck A", "text": DECK_TEXT, "mode": "new"},
    )
    client.post(
        "/api/decks/import",
        json={"name": "Deck A", "text": DECK_TEXT, "mode": "new_version"},
    )
    client.post(
        "/api/decks/import",
        json={"name": "Deck A", "text": DECK_TEXT, "mode": "new_version"},
    )
    response = client.get("/api/decks/leader/OP16-079/versions")
    assert response.status_code == 200
    data = response.json()
    assert data["leader_card_id"] == "OP16-079"
    assert len(data["versions"]) == 3
    assert data["versions"][0]["version"] == 3
    assert data["versions"][1]["version"] == 2
    assert data["versions"][2]["version"] == 1


def test_import_new_version_with_explicit_leader(client, db_session):
    setup_cards(db_session)
    client.post(
        "/api/decks/import",
        json={"name": "My Yamato", "text": DECK_TEXT, "mode": "new"},
    )
    resp = client.post(
        "/api/decks/import",
        json={
            "text": DECK_TEXT,
            "mode": "new_version",
            "leader_card_id": "OP16-079",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == 2
    assert data["name"] == "My Yamato v2"
    assert data["leader_card_id"] == "OP16-079"


def test_import_new_version_leader_mismatch(client, db_session):
    setup_cards(db_session)
    client.post(
        "/api/decks/import",
        json={"name": "My Yamato", "text": DECK_TEXT, "mode": "new"},
    )
    resp = client.post(
        "/api/decks/import",
        json={
            "text": DECK_TEXT,
            "mode": "new_version",
            "leader_card_id": "OP16-099",
        },
    )
    assert resp.status_code == 400
    assert "does not match" in resp.json()["detail"]
