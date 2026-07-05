"""Delete all match-related data while preserving decks, cards, and collection.

Cleans: matches, match turns, match stats, meta snapshots, patterns, and
recommendations. Keeps: cards, decks, deck cards, deck scores, collection,
formats, insights, and settings.
"""
from app.infrastructure.persistence.models import (
    MatchORM,
    MatchStatsORM,
    MatchTurnORM,
    MetaSnapshotORM,
    PatternORM,
    RecommendationORM,
)
from app.infrastructure.persistence.session import SessionLocal, init_db


def clean_matches():
    init_db()
    session = SessionLocal()
    try:
        for model in [
            RecommendationORM,
            PatternORM,
            MatchStatsORM,
            MatchTurnORM,
            MatchORM,
            MetaSnapshotORM,
        ]:
            count = session.query(model).delete()
            if count > 0:
                print(f"Deleted {count} rows from {model.__tablename__}")
        session.commit()
        print("Match data cleaned. Decks, cards, and collection preserved.")
    except Exception as e:
        session.rollback()
        print(f"Error cleaning matches: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    clean_matches()
