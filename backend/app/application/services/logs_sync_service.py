import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.event_bus import get_event_bus
from app.domain.events import MatchImported
from app.infrastructure.importers.match_importer import MatchImporter, extract_match_date
from app.infrastructure.persistence.models import MatchORM
from app.infrastructure.persistence.repositories.deck_repo import DeckRepository
from app.infrastructure.persistence.repositories.settings_repo import SettingsRepository

logger = logging.getLogger(__name__)

LAST_SYNC_KEY = "last_logs_sync"
LAST_SYNC_RESULT_KEY = "last_logs_sync_result"

STATUS_OK = "ok"
STATUS_NOT_CONFIGURED = "not_configured"
STATUS_INVALID_PATH = "invalid_path"
STATUS_NO_SELF_USER = "no_self_user"
STATUS_ERROR = "error"


class LogsSyncService:
    """Imports new match logs from the simulator folder configured in Settings.

    The folder is stored in the ``logs_dir`` setting. Every sync only processes
    files not yet imported (dedup by match id = file stem) and records the
    outcome in ``last_logs_sync`` / ``last_logs_sync_result`` so the UI can
    show when the last sync ran and what it did.
    """

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    def _make_session(self) -> Session:
        from app.infrastructure.persistence.session import SessionLocal

        factory = self._session_factory or SessionLocal
        return factory()

    def sync(self) -> dict:
        """Run one sync cycle. Always returns a summary dict; never raises."""
        try:
            return self._sync()
        except Exception:
            logger.exception("Logs sync failed")
            summary = {
                "status": STATUS_ERROR,
                "imported": 0,
                "skipped": 0,
                "errors": 0,
                "total": 0,
            }
            self._save_result(summary)
            return summary

    def _sync(self) -> dict:
        session = self._make_session()
        try:
            repo = SettingsRepository(session)
            logs_dir = (repo.get("logs_dir") or "").strip()
            self_user = (repo.get("self_user") or "").strip() or None
        finally:
            session.close()

        if not logs_dir:
            return {"status": STATUS_NOT_CONFIGURED}

        directory = Path(logs_dir)
        if not directory.is_dir():
            logger.warning("Configured logs_dir does not exist: %s", logs_dir)
            return self._finish({"status": STATUS_INVALID_PATH, "path": logs_dir})

        if not self_user:
            logger.info("Logs sync skipped — self_user not configured")
            return self._finish({"status": STATUS_NO_SELF_USER, "path": logs_dir})

        importer = MatchImporter()
        result = importer.import_directory(
            directory=directory,
            self_user=self_user,
            skip_existing=True,
        )

        if result["imported"] > 0:
            self._post_import()

        return self._finish({
            "status": STATUS_OK,
            "path": logs_dir,
            **result,
        })

    def _post_import(self) -> None:
        """Auto-assign decks to freshly imported matches and notify the bus."""
        session = self._make_session()
        try:
            all_matches = list(session.scalars(select(MatchORM)))
            for m in all_matches:
                if m.deck_id_self is None and m.leader_self:
                    match_date = extract_match_date(m.source_file) if m.source_file else None
                    m.deck_id_self = DeckRepository(session).auto_assign_deck(
                        m.leader_self, match_date
                    )
            session.commit()
        except Exception:
            session.rollback()
            logger.error("Deck auto-assign after logs sync failed", exc_info=True)
        finally:
            session.close()

        get_event_bus().publish("MatchImported", MatchImported(match_id="batch"))

    def _finish(self, summary: dict) -> dict:
        logger.info(
            "Logs sync [%s]: imported=%s skipped=%s errors=%s total=%s",
            summary.get("status"),
            summary.get("imported", 0),
            summary.get("skipped", 0),
            summary.get("errors", 0),
            summary.get("total", 0),
        )
        self._save_result(summary)
        return summary

    def _save_result(self, summary: dict) -> None:
        session = self._make_session()
        try:
            repo = SettingsRepository(session)
            repo.set(LAST_SYNC_KEY, datetime.now(UTC).isoformat())
            repo.set(LAST_SYNC_RESULT_KEY, json.dumps(summary, ensure_ascii=False))
        except Exception:
            session.rollback()
            logger.error("Failed to persist logs sync status", exc_info=True)
        finally:
            session.close()
