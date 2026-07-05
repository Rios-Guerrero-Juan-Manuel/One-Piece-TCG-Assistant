"""Script para limpiar datos de la BD real (matches, decks, stats, etc.)."""
from app.infrastructure.persistence.models import (
    CardORM,
    CollectionORM,
    DeckCardORM,
    DeckORM,
    DeckScoreORM,
    FormatORM,
    InsightORM,
    MatchORM,
    MatchStatsORM,
    MatchTurnORM,
    MetaSnapshotORM,
    PatternORM,
    RecommendationORM,
    SettingsORM,
)
from app.infrastructure.persistence.session import SessionLocal, init_db


def clean_database():
    """Delete all data from the database."""
    init_db()
    session = SessionLocal()
    try:
        for model in [
            RecommendationORM,
            PatternORM,
            MatchStatsORM,
            MatchTurnORM,
            MatchORM,
            DeckScoreORM,
            DeckCardORM,
            DeckORM,
            CollectionORM,
            CardORM,
            InsightORM,
            FormatORM,
            MetaSnapshotORM,
            SettingsORM,
        ]:
            count = session.query(model).count()
            if count > 0:
                session.query(model).delete()
                print(f"Deleted {count} rows from {model.__tablename__}")
        session.commit()
        print("Database cleaned successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error cleaning database: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    clean_database()
