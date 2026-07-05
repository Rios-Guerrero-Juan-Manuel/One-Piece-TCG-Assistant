import json
from pathlib import Path
from unittest import mock

import pytest

from app.infrastructure.importers.format_importer import FormatImporter

FORMATS_DIR = Path(__file__).resolve().parents[2] / "Datos" / "1.40a" / "Formats"


def test_format_importer_reads_files():
    if not FORMATS_DIR.exists():
        pytest.skip("Formats directory not found")
    files = list(FORMATS_DIR.glob("*.json"))
    assert len(files) == 4


def test_format_importer_banned_pairs():
    if not FORMATS_DIR.exists():
        pytest.skip("Formats directory not found")
    western_file = FORMATS_DIR / "Western.json"
    if not western_file.exists():
        pytest.skip("Western.json not found")
    data = json.loads(western_file.read_text(encoding="utf-8"))
    assert "bannedPair1" in data
    assert "bannedPair2" in data
    assert isinstance(data["bannedPair1"], list)
    assert isinstance(data["bannedPair2"], list)


def test_format_importer_import_all_mock(tmp_path):
    fmt_file = tmp_path / "TestFormat.json"
    fmt_file.write_text(
        json.dumps(
            {
                "bannedCards": ["OP01-001"],
                "bannedSets": ["ST01"],
                "bannedBlocks": [1],
                "bannedPair1": ["EB04-058"],
                "bannedPair2": ["OP07-115"],
            }
        ),
        encoding="utf-8",
    )

    captured = []

    class FakeRepo:
        def __init__(self, session):
            pass

        def upsert(self, format_data):
            captured.append(format_data)
            return mock.MagicMock()

    class FakeSession:
        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    with (
        mock.patch("app.infrastructure.importers.format_importer.init_db"),
        mock.patch(
            "app.infrastructure.importers.format_importer.SessionLocal",
            return_value=FakeSession(),
        ),
        mock.patch(
            "app.infrastructure.importers.format_importer.FormatRepository",
            FakeRepo,
        ),
    ):
        importer = FormatImporter(formats_dir=tmp_path)
        results = importer.import_all()

    assert "TestFormat" in results
    assert len(captured) == 1
    assert captured[0]["banned_cards"] == ["OP01-001"]
    assert captured[0]["banned_pair1"] == ["EB04-058"]
    assert captured[0]["banned_pair2"] == ["OP07-115"]
