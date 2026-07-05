import csv as csv_module
import io

from app.application.services.collection_csv_import import parse_collection_csv
from app.infrastructure.persistence.repositories.card_repo import CardRepository

CSV_FIELDS = [
    "Portfolio Name", "Category", "Set", "Product Name", "Card Number",
    "Rarity", "Variance", "Grade", "Card Condition", "Average Cost Paid",
    "Quantity", "Market Price (As of 2026-06-30)", "Price Override",
    "Watchlist", "Date Added", "Notes",
]


def _build_csv(rows):
    buf = io.StringIO()
    writer = csv_module.DictWriter(buf, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for row in rows:
        full = {f: "" for f in CSV_FIELDS}
        full.update(row)
        writer.writerow(full)
    return buf.getvalue()


def _op_row(card_number="OP16-079", product_name="Yamato", quantity="1", **extra):
    row = {
        "Category": "One Piece",
        "Product Name": product_name,
        "Card Number": card_number,
        "Quantity": quantity,
    }
    row.update(extra)
    return row


def seed_card(session, card_id="OP16-079"):
    CardRepository(session).upsert({
        "card_id": card_id,
        "name": card_id,
        "cost": None,
        "power": 0,
        "counter": 0,
        "type": "Character",
        "color": ["Red"],
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


def _collection_map(client):
    data = client.get("/api/collection").json()
    return {it["card_id"]: it["owned"] for it in data["items"]}


# --- pure parser tests ---


def test_parse_keeps_english_one_piece():
    items, report = parse_collection_csv(_build_csv([_op_row("OP16-079", "Yamato", "3")]))
    assert items == {"OP16-079": 3}
    assert report.skipped_other_tcg == 0


def test_parse_filters_other_tcg():
    rows = [
        _op_row(),
        {
            "Category": "Pokemon",
            "Card Number": "024/068",
            "Product Name": "Articuno",
            "Quantity": "1",
        },
    ]
    items, report = parse_collection_csv(_build_csv(rows))
    assert items == {"OP16-079": 1}
    assert report.skipped_other_tcg == 1


def test_parse_filters_japanese():
    items, report = parse_collection_csv(_build_csv([_op_row("OP07-023", "Caribou (JP)", "1")]))
    assert items == {}
    assert report.skipped_japanese == 1


def test_parse_skips_empty_card_number():
    items, report = parse_collection_csv(_build_csv([_op_row("", "DON!! Card (Luffy)", "2")]))
    assert items == {}
    assert report.skipped_no_card_number == 1


def test_parse_aggregates_alternate_arts():
    rows = [
        _op_row("OP16-032", "Boa Hancock", "2"),
        _op_row("OP16-032", "Boa Hancock (Alternate Art)", "1"),
    ]
    items, _ = parse_collection_csv(_build_csv(rows))
    assert items == {"OP16-032": 3}


def test_parse_en_jp_same_number_keeps_only_en():
    rows = [
        _op_row("OP08-041", "Aphelandra", "1"),
        _op_row("OP08-041", "Aphelandra (JP)", "1"),
    ]
    items, report = parse_collection_csv(_build_csv(rows))
    assert items == {"OP08-041": 1}
    assert report.skipped_japanese == 1


def test_parse_handles_quoted_commas():
    items, _ = parse_collection_csv(_build_csv([_op_row("OP15-021", "Just Watch Me, Ace!!!", "2")]))
    assert items == {"OP15-021": 2}


def test_parse_strips_bom():
    items, _ = parse_collection_csv("\ufeff" + _build_csv([_op_row()]))
    assert items == {"OP16-079": 1}


def test_parse_empty_quantity_defaults_to_zero():
    row = _op_row()
    row["Quantity"] = ""
    items, _ = parse_collection_csv(_build_csv([row]))
    assert items == {"OP16-079": 0}


# --- endpoint tests ---


def _post_csv(client, csv_text):
    return client.post(
        "/api/collection/import-csv",
        files={"file": ("export.csv", csv_text, "text/csv")},
    )


def test_csv_import_sets_owned(client, db_session):
    seed_card(db_session, "OP16-079")
    resp = _post_csv(client, _build_csv([_op_row("OP16-079", "Yamato", "3")]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 1
    assert body["total_owned"] == 3
    assert _collection_map(client) == {"OP16-079": 3}


def test_csv_import_replaces_existing(client, db_session):
    seed_card(db_session, "OP16-079")
    seed_card(db_session, "OP16-080")
    client.post("/api/collection", json={"card_id": "OP16-079", "owned": 5})
    client.post("/api/collection", json={"card_id": "OP16-080", "owned": 9})
    resp = _post_csv(client, _build_csv([_op_row("OP16-079", "Yamato", "2")]))
    assert resp.status_code == 200
    assert resp.json()["removed"] == 1
    assert _collection_map(client) == {"OP16-079": 2}


def test_csv_import_aggregates_alternate_arts(client, db_session):
    seed_card(db_session, "OP16-032")
    rows = [
        _op_row("OP16-032", "Boa Hancock", "2"),
        _op_row("OP16-032", "Boa Hancock (Alternate Art)", "1"),
    ]
    resp = _post_csv(client, _build_csv(rows))
    assert resp.json()["total_owned"] == 3
    assert _collection_map(client) == {"OP16-032": 3}


def test_csv_import_skips_japanese_and_other_tcg(client, db_session):
    seed_card(db_session, "OP16-079")
    rows = [
        _op_row("OP16-079", "Yamato", "1"),
        _op_row("OP07-023", "Caribou (JP)", "1"),
        {
            "Category": "Pokemon",
            "Card Number": "024/068",
            "Product Name": "Articuno",
            "Quantity": "1",
        },
    ]
    resp = _post_csv(client, _build_csv(rows))
    body = resp.json()
    assert body["imported"] == 1
    assert body["skipped_japanese"] == 1
    assert body["skipped_other_tcg"] == 1
    assert _collection_map(client) == {"OP16-079": 1}


def test_csv_import_reports_missing_after_mocked_sync(client, db_session, monkeypatch):
    seed_card(db_session, "OP16-079")
    monkeypatch.setattr("app.presentation.api.collection._sync_missing_cards", lambda: None)
    rows = [_op_row("OP16-079", "Yamato", "1"), _op_row("OP99-999", "Ghost", "1")]
    resp = _post_csv(client, _build_csv(rows))
    body = resp.json()
    assert body["imported"] == 1
    assert body["missing_card_ids"] == ["OP99-999"]
    assert body["synced"] is True
    assert body["sync_failed"] is False
    assert _collection_map(client) == {"OP16-079": 1}


def test_csv_import_empty_payload_preserves_collection(client, db_session):
    seed_card(db_session, "OP16-079")
    client.post("/api/collection", json={"card_id": "OP16-079", "owned": 4})
    csv_text = ",".join(CSV_FIELDS) + "\n"
    resp = _post_csv(client, csv_text)
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 0
    assert body["removed"] == 0
    assert _collection_map(client) == {"OP16-079": 4}
