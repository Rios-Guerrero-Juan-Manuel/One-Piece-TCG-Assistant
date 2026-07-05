import asyncio
import contextlib
import logging
import threading
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.application.logging_config import setup_logging
from app.application.wire_events import wire_event_bus
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
    except Exception:
        logger.error("Card auto-load failed", exc_info=True)
    finally:
        session.close()


async def _ensure_cards_loaded() -> None:
    await asyncio.to_thread(_sync_ensure_cards_loaded)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_db_safe()
    wire_event_bus()
    get_scheduler().start()
    task = asyncio.create_task(_ensure_cards_loaded())
    yield
    _shutdown_event.set()
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


frontend_dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", SPAStaticFiles(directory=str(frontend_dist), html=True), name="frontend")
