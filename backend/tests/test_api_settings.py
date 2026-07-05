def test_get_settings(client, db_session):
    response = client.get("/api/settings")
    assert response.status_code == 200
    assert "settings" in response.json()


def test_update_settings(client, db_session):
    response = client.put("/api/settings", json={"settings": {"language": "en"}})
    assert response.status_code == 200
    data = response.json()
    assert data["settings"]["language"] == "en"
