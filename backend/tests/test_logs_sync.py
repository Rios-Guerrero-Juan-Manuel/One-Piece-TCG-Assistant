import json
import os
from pathlib import Path

import pytest

from app.application.event_bus import get_event_bus
from app.application.services.logs_sync_service import (
    LAST_SYNC_KEY,
    LAST_SYNC_RESULT_KEY,
    LogsSyncService,
)
from app.infrastructure.importers.match_importer import MatchImporter
from app.infrastructure.persistence.models import MatchORM
from app.infrastructure.persistence.repositories.settings_repo import SettingsRepository

SAMPLE_LOG = """\
Waiting for a Connection with Room ID:TEST
[Player1] Has Connected
[Player1] Leader is Yamato ["OP16-079">OP16-079]
[Player2] Has Connected
[Player2] Leader is Enel ["OP15-058">OP15-058]
[Player2] Chose to go First
[Player2] Draw 1 Don
RZ1|1|2|Don|4|5|5|0|1|1|0|0|0
[Player2] End Turn
[Player1] Draw 2 Don
RZ1|2|1|Don|4|9|5|0|1|1|0|0|0
RZ1|3|1|Don|4|8|5|1|1|1|0|0|0
[Player1] End Turn
[Player2] Draw 2 Don
RZ1|4|2|Don|4|4|5|0|1|1|0|0|0
RZ1|5|2|Don|4|3|5|1|1|1|0|0|0
[Player2] End Turn
"""


@pytest.fixture
def logs_dir(tmp_path: Path) -> Path:
    d = tmp_path / "CombatLogs"
    d.mkdir()
    (d / "2026-06-23T18_20_36.txt").write_text(SAMPLE_LOG, encoding="utf-8")
    (d / "2026-06-24T10_00_00.log").write_text(SAMPLE_LOG, encoding="utf-8")
    autosaved = d / "AutoSaved"
    autosaved.mkdir()
    (autosaved / "2026-06-25T09_30_00.log").write_text(SAMPLE_LOG, encoding="utf-8")
    return d


def _set_setting(session, key: str, value: str) -> None:
    SettingsRepository(session).set(key, value)


def _get_setting(session_factory, key: str):
    session = session_factory()
    try:
        return SettingsRepository(session).get(key)
    finally:
        session.close()


def _match_count(session_factory) -> int:
    session = session_factory()
    try:
        return len(list(session.query(MatchORM).all()))
    finally:
        session.close()


def test_import_directory_imports_new_files_only(session_factory, logs_dir):
    importer = MatchImporter()

    result = importer.import_directory(
        directory=logs_dir, self_user="Player1", skip_existing=True
    )
    assert result == {"imported": 3, "skipped": 0, "errors": 0, "total": 3}
    assert _match_count(session_factory) == 3

    # Second sync: everything already imported -> nothing reprocessed.
    result = importer.import_directory(
        directory=logs_dir, self_user="Player1", skip_existing=True
    )
    assert result == {"imported": 0, "skipped": 3, "errors": 0, "total": 3}
    assert _match_count(session_factory) == 3

    # A new log appears -> only that one is imported.
    new_file = logs_dir / "2026-06-26T22_10_05.txt"
    new_file.write_text(SAMPLE_LOG, encoding="utf-8")
    result = importer.import_directory(
        directory=logs_dir, self_user="Player1", skip_existing=True
    )
    assert result == {"imported": 1, "skipped": 3, "errors": 0, "total": 4}
    assert _match_count(session_factory) == 4


def test_import_directory_without_skip_reimports(session_factory, logs_dir):
    importer = MatchImporter()
    first = importer.import_directory(
        directory=logs_dir, self_user="Player1", skip_existing=False
    )
    second = importer.import_directory(
        directory=logs_dir, self_user="Player1", skip_existing=False
    )
    assert first["imported"] == 3
    assert second["imported"] == 3
    assert _match_count(session_factory) == 3


def test_sync_not_configured_is_noop(session_factory):
    summary = LogsSyncService(session_factory=session_factory).sync()
    assert summary == {"status": "not_configured"}
    assert _get_setting(session_factory, LAST_SYNC_KEY) is None


def test_sync_invalid_path_records_status(session_factory, db_session):
    _set_setting(db_session, "logs_dir", "Z:/no/such/dir")

    summary = LogsSyncService(session_factory=session_factory).sync()

    assert summary["status"] == "invalid_path"
    stored = json.loads(_get_setting(session_factory, LAST_SYNC_RESULT_KEY))
    assert stored["status"] == "invalid_path"
    assert _get_setting(session_factory, LAST_SYNC_KEY) is not None


def test_sync_requires_self_user(session_factory, db_session, logs_dir):
    _set_setting(db_session, "logs_dir", str(logs_dir))

    summary = LogsSyncService(session_factory=session_factory).sync()

    assert summary["status"] == "no_self_user"
    assert _match_count(session_factory) == 0


def test_sync_imports_and_records_status(session_factory, db_session, logs_dir):
    _set_setting(db_session, "self_user", "Player1")
    _set_setting(db_session, "logs_dir", str(logs_dir))

    received: list = []
    get_event_bus().subscribe("MatchImported", received.append)

    summary = LogsSyncService(session_factory=session_factory).sync()

    assert summary["status"] == "ok"
    assert summary["imported"] == 3
    assert summary["skipped"] == 0
    assert _match_count(session_factory) == 3

    stored = json.loads(_get_setting(session_factory, LAST_SYNC_RESULT_KEY))
    assert stored["status"] == "ok"
    assert stored["imported"] == 3

    assert any(getattr(e, "match_id", None) == "batch" for e in received)

    # Idempotent: syncing again changes nothing (but updates the timestamp).
    summary = LogsSyncService(session_factory=session_factory).sync()
    assert summary["status"] == "ok"
    assert summary["imported"] == 0
    assert summary["skipped"] == 3
    assert _match_count(session_factory) == 3


def test_validate_logs_dir_endpoint(client, logs_dir):
    response = client.post(
        "/api/settings/validate-logs-dir", json={"path": str(logs_dir)}
    )
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "exists": True,
        "is_dir": True,
        "files_found": 2,
        "autosaved_found": 1,
        "hint": None,
    }

    # Relative missing path -> plain not_found on any platform.
    missing = client.post(
        "/api/settings/validate-logs-dir", json={"path": "no/such/dir"}
    )
    assert missing.status_code == 200
    assert missing.json() == {
        "exists": False,
        "is_dir": False,
        "files_found": 0,
        "autosaved_found": 0,
        "hint": "not_found",
    }


def test_validate_logs_dir_hint_not_a_directory(client, logs_dir):
    plain_file = logs_dir.parent / "not_a_dir.txt"
    plain_file.write_text("x", encoding="utf-8")

    response = client.post(
        "/api/settings/validate-logs-dir", json={"path": str(plain_file)}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["exists"] is True
    assert data["is_dir"] is False
    assert data["hint"] == "not_a_directory"


def test_validate_logs_dir_hint_windows_path_on_linux_server(client, monkeypatch):
    monkeypatch.setattr(os, "name", "posix")

    response = client.post(
        "/api/settings/validate-logs-dir", json={"path": "E:\\Games\\CombatLogs"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["exists"] is False
    assert data["hint"] == "windows_path_on_server"


def test_validate_logs_dir_hint_posix_path_on_windows_server(client, monkeypatch):
    monkeypatch.setattr(os, "name", "nt")

    response = client.post(
        "/api/settings/validate-logs-dir", json={"path": "/optcg-no-such-path/logs"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["exists"] is False
    assert data["hint"] == "posix_path_on_windows_server"


def test_import_directory_endpoint_requires_logs_dir(client):
    response = client.post("/api/matches/import-directory")
    assert response.status_code == 400


def test_import_directory_endpoint_syncs(client, db_session, logs_dir):
    save = client.put(
        "/api/settings",
        json={"settings": {"self_user": "Player1", "logs_dir": str(logs_dir)}},
    )
    assert save.status_code == 200

    first = client.post("/api/matches/import-directory")
    assert first.status_code == 200
    data = first.json()
    assert data["imported"] == 3
    assert data["skipped"] == 0
    assert data["total"] == 3

    listing = client.get("/api/matches")
    assert listing.json()["total"] == 3

    second = client.post("/api/matches/import-directory")
    assert second.status_code == 200
    assert second.json()["imported"] == 0
    assert second.json()["skipped"] == 3
