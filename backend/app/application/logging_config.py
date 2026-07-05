"""Application logging configuration.

Sets up two file handlers with rotation:
  - error.log: WARNING+ level (errors, exceptions)
  - app.log: INFO+ level (general application flow)

Both rotate at 10MB, keeping 5 backup files.
"""

import logging
import logging.handlers

from app.core.config import BASE_DIR

_LOG_DIR = BASE_DIR / "data" / "logs"
_MAX_BYTES = 10 * 1024 * 1024  # 10MB
_BACKUP_COUNT = 5
_CONFIGURED = False


def setup_logging() -> None:
    """Configure root logger with console + rotating file handlers."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    error_log_path = _LOG_DIR / "error.log"
    app_log_path = _LOG_DIR / "app.log"

    error_handler = logging.handlers.RotatingFileHandler(
        error_log_path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))

    app_handler = logging.handlers.RotatingFileHandler(
        app_log_path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(error_handler)
    root.addHandler(app_handler)
    root.addHandler(console_handler)

    _CONFIGURED = True
