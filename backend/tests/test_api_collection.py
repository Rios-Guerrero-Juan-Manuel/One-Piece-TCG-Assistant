from app.infrastructure.persistence.repositories.card_repo import CardRepository


def setup_cards(session):
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
    session.commit()


def test_get_empty_collection(client, db_session):
    response = client.get("/api/collection")
    assert response.status_code == 200
    assert "items" in response.json()


def test_update_owned(client, db_session):
    setup_cards(db_session)
    response = client.post("/api/collection", json={"card_id": "OP16-079", "owned": 3})
    assert response.status_code == 200
    assert response.json()["owned"] == 3


def test_import_collection(client, db_session):
    setup_cards(db_session)
    response = client.post("/api/collection/import", json={"items": {"OP16-079": 2}})
    assert response.status_code == 200
    assert response.json()["imported"] == 1


def test_export_collection(client, db_session):
    setup_cards(db_session)
    client.post("/api/collection", json={"card_id": "OP16-079", "owned": 4})
    response = client.get("/api/collection/export")
    assert response.status_code == 200
    data = response.json()
    assert "OP16-079" in data
    assert data["OP16-079"] == 4
