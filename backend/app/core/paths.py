"""Centralized filesystem paths.

- ``app_root()`` is the directory holding bundled read-only resources:
  the project root in a repo checkout, or the portable bundle root when the
  app is shipped as a Windows portable folder (frontend/, Datos/, alembic/,
  models/ live next to app/).
- ``data_dir()`` is where user data (SQLite DB, ChromaDB, .env, logs) is
  written. Defaults to ``backend/data`` in development (unchanged legacy
  behavior) and can be redirected with the ``OPTCG_DATA_DIR`` environment
  variable — the portable bundle sets it to ``%LOCALAPPDATA%\\OnePieceTCGAssistant``.
"""

import os
import sys
from pathlib import Path


def app_root() -> Path:
    """Root directory for bundled read-only resources.

    In a repo checkout that is the project root (backend/../../). In the
    portable bundle ``app/`` sits directly in the bundle root, one level
    shallower — so the root is detected by looking for the resource
    directories (frontend/dist, Datos, alembic) rather than assuming a fixed
    depth.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    module_path = Path(__file__).resolve()
    for candidate in (module_path.parents[3], module_path.parents[2]):
        if (
            (candidate / "frontend" / "dist").is_dir()
            or (candidate / "Datos").is_dir()
            or (candidate / "backend" / "app").is_dir()
            or (candidate / "app" / "core" / "paths.py").is_file()
        ):
            return candidate
    return module_path.parents[3]


def backend_dir() -> Path:
    """The ``backend/`` directory (repo checkout layout)."""
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    """Directory for user-writable data (DB, vector store, logs, .env)."""
    override = os.environ.get("OPTCG_DATA_DIR", "").strip()
    if override:
        return Path(override)
    return backend_dir() / "data"


def default_portable_data_dir() -> Path:
    """Default user-data location for the Windows portable bundle."""
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        return Path(local_app) / "OnePieceTCGAssistant"
    return Path.home() / ".optcg-assistant"


def alembic_dir() -> Path:
    """Locate the alembic migration scripts (dev repo or portable bundle)."""
    for candidate in (backend_dir() / "alembic", app_root() / "alembic"):
        if (candidate / "env.py").exists():
            return candidate
    return backend_dir() / "alembic"
