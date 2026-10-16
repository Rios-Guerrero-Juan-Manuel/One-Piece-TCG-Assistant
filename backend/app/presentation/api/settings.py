import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.application.event_bus import get_event_bus
from app.core.config import settings as app_settings
from app.domain.events import SettingsChanged
from app.infrastructure.persistence.repositories.settings_repo import SettingsRepository
from app.infrastructure.persistence.session import get_db
from app.presentation.schemas.settings_schema import (
    LogsDirValidationRequest,
    LogsDirValidationResponse,
    SettingsResponse,
    SettingsUpdateRequest,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings(db: Session = Depends(get_db)):
    repo = SettingsRepository(db)
    result = repo.get_all()
    result.setdefault("self_user", app_settings.self_user)
    result.setdefault("language", app_settings.language)
    return SettingsResponse(settings=result)


@router.put("", response_model=SettingsResponse)
async def update_settings(req: SettingsUpdateRequest, db: Session = Depends(get_db)):
    repo = SettingsRepository(db)
    for key, value in req.settings.items():
        repo.set(key, value)
        get_event_bus().publish(
            "SettingsChanged",
            SettingsChanged(key=key, value=value),
        )
    db.commit()
    result = repo.get_all()
    result.setdefault("self_user", app_settings.self_user)
    result.setdefault("language", app_settings.language)
    return SettingsResponse(settings=result)


def _count_log_files(directory: Path) -> tuple[int, int]:
    """Count ``.txt``/``.log`` files in a directory and its ``AutoSaved`` subfolder."""
    root = 0
    autosaved = 0
    if directory.is_dir():
        root = sum(
            1
            for f in directory.iterdir()
            if f.is_file() and f.suffix in (".txt", ".log")
        )
        sub = directory / "AutoSaved"
        if sub.is_dir():
            autosaved = sum(
                1
                for f in sub.iterdir()
                if f.is_file() and f.suffix in (".txt", ".log")
            )
    return root, autosaved


_WINDOWS_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")


def _path_hint(path: str, exists: bool, is_dir: bool) -> str | None:
    """Return a diagnostic code when the path cannot be used as a logs dir.

    The interesting case is a platform mismatch: the user typed a path that is
    valid on their machine (e.g. ``E:\\...``) but the backend runs somewhere
    else (Raspberry Pi, Docker) where that path can never exist.
    """
    if is_dir:
        return None
    if exists:
        return "not_a_directory"
    looks_windows = bool(_WINDOWS_PATH_RE.match(path)) or path.startswith("\\\\")
    looks_posix = path.startswith("/")
    if looks_windows and not os.name == "nt":
        return "windows_path_on_server"
    if looks_posix and os.name == "nt":
        return "posix_path_on_windows_server"
    return "not_found"


@router.post("/validate-logs-dir", response_model=LogsDirValidationResponse)
async def validate_logs_dir(req: LogsDirValidationRequest):
    """Check a simulator logs folder without saving it.

    Reports how many importable log files were found (root + ``AutoSaved/``).
    When the path cannot be used, ``hint`` explains why (``not_a_directory``,
    ``windows_path_on_server``, ``posix_path_on_windows_server`` or
    ``not_found``).
    """
    path = req.path.strip()
    exists = bool(path) and Path(path).exists()
    is_dir = bool(path) and Path(path).is_dir()
    root, autosaved = _count_log_files(Path(path)) if is_dir else (0, 0)
    return LogsDirValidationResponse(
        exists=exists,
        is_dir=is_dir,
        files_found=root,
        autosaved_found=autosaved,
        hint=_path_hint(path, exists, is_dir),
    )
