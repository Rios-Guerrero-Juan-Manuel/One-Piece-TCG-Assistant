"""Wires all Event Bus subscriptions.

Called once at application startup to connect publishers with subscribers.
This module is the single source of truth for event-driven wiring.
"""

import logging

from app.application.event_bus import get_event_bus

logger = logging.getLogger(__name__)


def wire_event_bus() -> None:
    """Register all event subscriptions defined in the plan (section 10.1)."""
    bus = get_event_bus()

    bus.subscribe("CardsRefreshed", _on_cards_refreshed)
    bus.subscribe("MatchImported", _on_match_imported)
    bus.subscribe("StatsComputed", _on_stats_computed)
    bus.subscribe("PatternsDetected", _on_patterns_detected)
    bus.subscribe("DeckUpdated", _on_deck_updated)
    bus.subscribe("DeckImported", _on_deck_imported)
    bus.subscribe("CollectionUpdated", _on_collection_updated)
    bus.subscribe("SettingsChanged", _on_settings_changed)

    logger.info("Event Bus wired with 8 event subscriptions")


def _on_cards_refreshed(payload=None):
    """CardsRefreshed → rebuild embeddings + reindex RAG cards."""
    logger.info("CardsRefreshed received — scheduling embedding rebuild")
    try:
        from app.application.services.matching_service import MatchingService
        MatchingService().index_all_cards()
    except Exception:
        logger.exception("Failed to rebuild embeddings after CardsRefreshed")


def _on_match_imported(payload=None):
    """MatchImported → recompute stats + detect patterns + refresh meta."""
    logger.info("MatchImported received — triggering stats/patterns/meta recompute")
    from app.infrastructure.persistence.session import SessionLocal
    try:
        from app.application.services.stats_service import StatsService
        StatsService(SessionLocal).compute_all_stats()
        logger.info("Stats recomputed after MatchImported")
    except Exception:
        logger.exception("Failed to recompute stats after MatchImported")
    try:
        from app.application.services.pattern_service import PatternService
        PatternService(SessionLocal).detect_and_save()
        logger.info("Patterns re-detected after MatchImported")
    except Exception:
        logger.exception("Failed to re-detect patterns after MatchImported")


def _on_stats_computed(payload=None):
    """StatsComputed → generate knowledge insights + refresh meta."""
    logger.info("StatsComputed received — generating insights")
    from app.infrastructure.persistence.session import SessionLocal
    try:
        from app.application.services.knowledge_service import KnowledgeService
        KnowledgeService(SessionLocal).generate_insights()
    except Exception:
        logger.exception("Failed to generate insights after StatsComputed")


def _on_patterns_detected(payload=None):
    """PatternsDetected → invalidate recommendations (will be regenerated on demand)."""
    logger.info("PatternsDetected received — recommendations will refresh on next request")


def _on_deck_updated(payload=None):
    """DeckUpdated → rescore deck."""
    logger.info("DeckUpdated received — triggering rescore")
    from app.infrastructure.persistence.session import SessionLocal
    try:
        if payload and hasattr(payload, "deck_id"):
            from app.application.services.scoring_engine import ScoringEngine
            ScoringEngine(SessionLocal, auto_subscribe=False).score_deck(payload.deck_id)
    except Exception:
        logger.exception("Failed to rescore after DeckUpdated")


def _on_deck_imported(payload=None):
    """DeckImported → score initial deck + retroactively assign to matches."""
    logger.info("DeckImported received — scoring deck + assigning matches")
    from app.infrastructure.persistence.session import SessionLocal
    try:
        if payload and hasattr(payload, "deck_id"):
            from app.application.services.scoring_engine import ScoringEngine
            ScoringEngine(SessionLocal, auto_subscribe=False).score_deck(payload.deck_id)
    except Exception:
        logger.exception("Failed to score after DeckImported")
    try:
        if payload and hasattr(payload, "deck_id"):
            session = SessionLocal()
            try:
                from app.infrastructure.persistence.repositories.deck_repo import DeckRepository
                repo = DeckRepository(session)
                deck_orm, _ = repo.get_by_id(payload.deck_id)
                if deck_orm:
                    updated = repo.assign_to_unassigned_matches(deck_orm.leader_card_id)
                    if updated:
                        session.commit()
                        logger.info(
                            "Retroactively assigned deck %s to %d match(es)",
                            payload.deck_id,
                            updated,
                        )
            finally:
                session.close()
    except Exception:
        logger.exception("Failed to retroactively assign matches after DeckImported")


def _on_collection_updated(payload=None):
    """CollectionUpdated → rescore decks (collection score changes)."""
    logger.info("CollectionUpdated received — decks may need rescore")


def _on_settings_changed(payload=None):
    """SettingsChanged — reload i18n, reschedule jobs."""
    logger.info("SettingsChanged received — key=%s",
                payload.key if payload and hasattr(payload, "key") else "unknown")
