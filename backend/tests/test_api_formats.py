from app.infrastructure.persistence.repositories.format_repo import FormatRepository


def setup_formats(session):
    repo = FormatRepository(session)
    repo.upsert({
        "format_name": "Western",
        "banned_cards": ["OP01-001"],
        "banned_sets": [],
        "banned_blocks": [],
        "banned_pair1": ["OP05-001"],
        "banned_pair2": ["OP05-002"],
    })
    session.commit()


def test_list_formats(client, db_session):
    setup_formats(db_session)
    response = client.get("/api/formats")
    assert response.status_code == 200
    data = response.json()
    assert "formats" in data
    assert len(data["formats"]) >= 1
    western = next(
        (f for f in data["formats"] if f["format_name"] == "Western"), None
    )
    assert western is not None
    assert "OP01-001" in western["banned_cards"]
