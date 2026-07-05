from app.infrastructure.persistence.repositories.card_repo import CardRepository


def setup_cards(session):
    repo = CardRepository(session)
    repo.upsert({
        "card_id": "OP16-079",
        "name": "Yamato (079)",
        "cost": None,
        "power": 5000,
        "counter": 0,
        "type": "Leader",
        "color": ["Black"],
        "traits": ["Land of Wano"],
        "attribute": "Strike",
        "keywords": [],
        "roles": [],
        "effect": "When a {Land of Wano} type Character card is played...",
        "life": 5,
        "set_id": "OP-16",
        "set_name": "The Time of Battle",
        "rarity": "L",
        "image_url": "https://optcgapi.com/media/static/Card_Images/OP16-079_9Me7LN0.jpg",
        "unlimited_copies": False,
        "language": "en",
    })
    repo.upsert({
        "card_id": "OP16-081",
        "name": "Otama (081)",
        "cost": 2,
        "power": 0,
        "counter": 2000,
        "type": "Character",
        "color": ["Black"],
        "traits": ["Land of Wano"],
        "attribute": "Strike",
        "keywords": [],
        "roles": ["2k_counter"],
        "effect": "[Activate: Main]",
        "life": None,
        "set_id": "OP-16",
        "set_name": "The Time of Battle",
        "rarity": "C",
        "image_url": "https://optcgapi.com/media/static/Card_Images/OP16-081.jpg",
        "unlimited_copies": False,
        "language": "en",
    })
    session.commit()


def test_list_cards(client, db_session):
    setup_cards(db_session)
    response = client.get("/api/cards?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "cards" in data
    assert "total" in data
    assert data["total"] >= 2


def test_get_card_by_id(client, db_session):
    setup_cards(db_session)
    response = client.get("/api/cards/OP16-079")
    assert response.status_code == 200
    data = response.json()
    assert data["card_id"] == "OP16-079"
    assert data["name"] == "Yamato (079)"


def test_get_card_not_found(client, db_session):
    setup_cards(db_session)
    response = client.get("/api/cards/NONEXIST-999")
    assert response.status_code == 404


def test_search_cards(client, db_session):
    setup_cards(db_session)
    response = client.get("/api/cards/search?q=Yamato")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


def test_filter_by_type(client, db_session):
    setup_cards(db_session)
    response = client.get("/api/cards?type=Leader")
    assert response.status_code == 200
    data = response.json()
    assert all(c["type"] == "Leader" for c in data["cards"])
