import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.application.event_bus import get_event_bus
from app.application.services.knowledge_service import KnowledgeService
from app.application.services.meta_engine import MetaEngine
from app.application.services.stats_service import StatsService
from app.infrastructure.importers.card_api_importer import CardApiImporter
from app.infrastructure.persistence.session import SessionLocal

logger = logging.getLogger(__name__)


class JobScheduler:
    """Schedules background jobs for data refresh, stats, meta, and cleanup."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._register_jobs()

    def _register_jobs(self) -> None:
        scheduler = self.scheduler

        scheduler.add_job(
            self._refresh_api_cards,
            "cron",
            day_of_week="sun",
            hour=4,
            minute=0,
            id="refresh_api_cards",
            replace_existing=True,
        )

        scheduler.add_job(
            self._recompute_stats,
            "cron",
            hour=6,
            minute=0,
            id="recompute_stats",
            replace_existing=True,
        )

        scheduler.add_job(
            self._refresh_meta,
            "cron",
            hour=6,
            minute=15,
            id="refresh_meta",
            replace_existing=True,
        )

        scheduler.add_job(
            self._generate_knowledge,
            "cron",
            day_of_week="mon",
            hour=7,
            minute=0,
            id="generate_knowledge",
            replace_existing=True,
        )

        scheduler.add_job(
            self._rebuild_embeddings,
            "cron",
            day_of_week="sun",
            hour=4,
            minute=30,
            id="rebuild_embeddings",
            replace_existing=True,
        )

        scheduler.add_job(
            self._import_new_logs,
            "cron",
            hour=12,
            minute=0,
            id="import_new_logs",
            replace_existing=True,
        )

        scheduler.add_job(
            self._refresh_prices,
            "cron",
            hour=5,
            minute=30,
            id="refresh_prices",
            replace_existing=True,
        )

    async def _refresh_api_cards(self) -> None:
        try:
            from datetime import UTC, datetime

            from app.infrastructure.persistence.repositories.settings_repo import (
                SettingsRepository,
            )

            importer = CardApiImporter()
            importer.import_incremental()
            session = SessionLocal()
            try:
                repo = SettingsRepository(session)
                repo.set(
                    "last_card_refresh",
                    datetime.now(UTC).isoformat(),
                )
            finally:
                session.close()
            logger.info("Incremental card refresh completed")
            get_event_bus().publish("CardsRefreshed", {})
        except Exception:
            logger.error("Card refresh failed", exc_info=True)

    async def _recompute_stats(self) -> None:
        try:
            service = StatsService(SessionLocal)
            service.compute_all_stats()
            logger.info("Stats recomputed")
            get_event_bus().publish(
                "StatsComputed",
                {"match_count": 0},
            )
        except Exception:
            logger.error("Stats recompute failed", exc_info=True)

    async def _refresh_meta(self) -> None:
        try:
            engine = MetaEngine(SessionLocal)
            engine.compute_meta()
            logger.info("Meta refreshed")
        except Exception:
            logger.error("Meta refresh failed", exc_info=True)

    async def _generate_knowledge(self) -> None:
        try:
            service = KnowledgeService(SessionLocal)
            service.generate_insights()
            logger.info("Knowledge insights generated")
        except Exception:
            logger.error("Knowledge generation failed", exc_info=True)

    async def _rebuild_embeddings(self) -> None:
        try:
            from app.application.services.matching_service import MatchingService
            count = MatchingService().index_all_cards()
            logger.info("Embeddings rebuilt: %d cards", count)
        except Exception:
            logger.error("Embeddings rebuild failed", exc_info=True)

    async def _import_new_logs(self) -> None:
        try:
            from app.core.config import settings
            from app.infrastructure.persistence.repositories.settings_repo import (
                SettingsRepository,
            )

            session = SessionLocal()
            try:
                repo = SettingsRepository(session)
                self_user = repo.get("self_user", settings.self_user) or None
            finally:
                session.close()

            if not self_user:
                logger.warning(
                    "Skipping log import — self_user is not configured. "
                    "Set it in Settings to enable automatic imports."
                )
                return

            from app.infrastructure.importers.match_importer import MatchImporter
            importer = MatchImporter()
            result = importer.import_directory(self_user=self_user)
            logger.info(
                "Logs imported: %d new, %d errors of %d total",
                result.get("imported", 0),
                result.get("errors", 0),
                result.get("total", 0),
            )
        except Exception:
            logger.error("Log import failed", exc_info=True)

    async def _refresh_prices(self) -> None:
        try:
            from app.application.services.price_service import PriceService
            service = PriceService(SessionLocal())
            count = service.refresh()
            logger.info("Prices refreshed: %d rows", count)
        except Exception:
            logger.error("Price refresh failed", exc_info=True)

    def start(self) -> None:
        self.scheduler.start()
        logger.info("Job scheduler started")

    def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)
        logger.info("Job scheduler stopped")


_job_scheduler = JobScheduler()


def get_scheduler() -> JobScheduler:
    return _job_scheduler
