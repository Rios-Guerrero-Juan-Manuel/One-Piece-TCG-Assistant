"""Programmatic database migrations.

Applies alembic migrations to head without the CLI. Used by the portable
bundle launcher (``run_app.py``) so the user data DB is created/upgraded
automatically on startup. Development continues to rely on
``alembic upgrade head`` / ``init_db()`` (``create_all``).
"""

import logging

logger = logging.getLogger(__name__)


def run_migrations(db_path=None) -> None:
    """Upgrade the database to the latest revision.

    Raises on failure so callers can decide how to handle it.
    """
    from alembic.config import Config

    from alembic import command
    from app.core.config import settings
    from app.core.paths import alembic_dir

    path = db_path or settings.db_path

    cfg = Config()
    cfg.set_main_option("script_location", str(alembic_dir()))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{path}")

    command.upgrade(cfg, "head")
    logger.info("Database migrations applied (db=%s)", path)


def stamp_head(db_path=None) -> None:
    """Mark an existing (create_all-created) database as being at head.

    Databases created via ``create_all`` have no ``alembic_version`` row, so
    a later ``upgrade head`` would try to re-create existing tables and fail.
    Stamping aligns the version table with the current schema so future
    migrations apply incrementally.
    """
    from alembic.config import Config

    from alembic import command
    from app.core.config import settings
    from app.core.paths import alembic_dir

    path = db_path or settings.db_path

    cfg = Config()
    cfg.set_main_option("script_location", str(alembic_dir()))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{path}")

    command.stamp(cfg, "head")
    logger.info("Database stamped at head (db=%s)", path)
