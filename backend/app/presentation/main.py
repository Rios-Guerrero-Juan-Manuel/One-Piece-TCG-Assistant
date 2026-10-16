import asyncio
import contextlib
import logging
import threading
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.application.logging_config import setup_logging
from app.application.wire_events import wire_event_bus
from app.core.paths import app_root
from app.infrastructure.jobs.scheduler import get_scheduler
from app.presentation.api import (
    cards,
    collection,
    decks,
    formats,
    i18n,
    knowledge,
    matches,
    meta,
    recommendations,
    settings,
    stats,
)

logger = logging.getLogger(__name__)

CARD_REFRESH_INTERVAL_DAYS = 7

_shutdown_event = threading.Event()


def _sync_ensure_cards_loaded() -> None:
    """Check DB and run full or incremental card import as needed.

    Runs in a background thread so the event loop stays responsive.
    """
    from app.infrastructure.importers.card_api_importer import CardApiImporter
    from app.infrastructure.persistence.models import CardORM
    from app.infrastructure.persistence.repositories.settings_repo import (
        SettingsRepository,
    )
    from app.infrastructure.persistence.session import SessionLocal, init_db

    if _shutdown_event.is_set():
        return

    init_db()
    session = SessionLocal()
    try:
        card_count = session.query(CardORM).count()
        repo = SettingsRepository(session)

        if card_count == 0:
            if _shutdown_event.is_set():
                return
            logger.info("No cards in DB — running full card import...")
            importer = CardApiImporter()
            importer.import_full(should_stop=_shutdown_event.is_set)
            repo.set("last_card_refresh", datetime.now(UTC).isoformat())
            logger.info("Full card import completed")
            _notify_cards_refreshed()
        else:
            last_str = repo.get("last_card_refresh")
            if last_str:
                last_refresh = datetime.fromisoformat(last_str)
                age = datetime.now(UTC) - last_refresh
                if age > timedelta(days=CARD_REFRESH_INTERVAL_DAYS):
                    logger.info(
                        "Cards last refreshed %s ago — running incremental import...",
                        age,
                    )
                    importer = CardApiImporter()
                    importer.import_incremental()
                    repo.set(
                        "last_card_refresh",
                        datetime.now(UTC).isoformat(),
                    )
                    logger.info("Incremental card import completed")
                    _notify_cards_refreshed()
                else:
                    logger.debug("Cards up to date (last refresh: %s)", last_str)
            else:
                logger.info("No refresh timestamp — running incremental import...")
                importer = CardApiImporter()
                importer.import_incremental()
                repo.set(
                    "last_card_refresh",
                    datetime.now(UTC).isoformat(),
                )
                logger.info("Incremental card import completed")
                _notify_cards_refreshed()
    except Exception:
        logger.error("Card auto-load failed", exc_info=True)
    finally:
        session.close()


def _notify_cards_refreshed() -> None:
    """Publish CardsRefreshed so embeddings/RAG pick up new cards (new sets).

    Without this, cards imported at startup would not be visible to the
    matcher until the weekly scheduler rebuild ran.
    """
    from app.application.event_bus import get_event_bus

    get_event_bus().publish("CardsRefreshed", {})


async def _ensure_cards_loaded() -> None:
    await asyncio.to_thread(_sync_ensure_cards_loaded)


def _sync_startup_logs() -> None:
    """Import new simulator logs from the configured folder (best effort)."""
    if _shutdown_event.is_set():
        return
    try:
        from app.application.services.logs_sync_service import LogsSyncService

        summary = LogsSyncService().sync()
        logger.info("Startup logs sync: %s", summary)
    except Exception:
        logger.error("Startup logs sync failed", exc_info=True)


async def _sync_logs_on_startup() -> None:
    await asyncio.to_thread(_sync_startup_logs)


def _sync_seed_formats() -> None:
    """Seed the formats table from Datos/1.40a/Formats when it is empty.

    FormatImporter was historically only exercised by tests, so production
    databases (Pi, portable bundle) shipped with an empty formats table and
    /api/formats returned nothing. Idempotent: only runs when empty.
    """
    try:
        from app.infrastructure.importers.format_importer import FormatImporter
        from app.infrastructure.persistence.models import FormatORM
        from app.infrastructure.persistence.session import SessionLocal

        session = SessionLocal()
        try:
            count = session.query(FormatORM).count()
        finally:
            session.close()
        if count:
            return
        results = FormatImporter().import_all()
        logger.info("Seeded formats: %s", results)
    except Exception:
        logger.error("Format seed failed", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_db_safe()
    wire_event_bus()
    get_scheduler().start()
    cards_task = asyncio.create_task(_ensure_cards_loaded())
    logs_task = asyncio.create_task(_sync_logs_on_startup())
    formats_task = asyncio.create_task(asyncio.to_thread(_sync_seed_formats))
    yield
    _shutdown_event.set()
    for task in (cards_task, logs_task, formats_task):
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    get_scheduler().shutdown()


def init_db_safe() -> None:
    from app.infrastructure.persistence.session import init_db

    init_db()


app = FastAPI(
    title="One Piece TCG Assistant",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_all_routers = [
    cards,
    collection,
    decks,
    matches,
    stats,
    recommendations,
    meta,
    formats,
    settings,
    i18n,
    knowledge,
]

for router in _all_routers:
    app.include_router(router.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope) -> Response:
        try:
            response = await super().get_response(path, scope)
            if response.status_code != 404:
                return response
        except StarletteHTTPException as ex:
            if ex.status_code != 404:
                raise
        return await super().get_response("index.html", scope)


frontend_dist = app_root() / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", SPAStaticFiles(directory=str(frontend_dist), html=True), name="frontend")
