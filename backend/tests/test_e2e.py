"""End-to-end integration tests verifying the full pipeline.

Flow tested:
    cards → deck → match → stats → patterns → knowledge → recommendations
"""


from app.infrastructure.persistence.models import (
    CardORM,
    CollectionORM,
    DeckCardORM,
    DeckORM,
    MatchORM,
    MatchStatsORM,
    MatchTurnORM,
    PatternORM,
    RecommendationORM,
)


def _seed_cards(session):
    """Seed cards: 1 leader + 12 characters + 4 candidate cards."""
    cards = [
        ("OP16-079", "Yamato", None, 5000, 0, "Leader", ["Black"], [], [], [], 5),
        ("OP16-001", "Char 1", 2, 1000, 1000, "Character", ["Black"], [], [], ["tempo"], None),
        ("OP16-002", "Char 2", 3, 3000, 0, "Character", ["Black"], [], [], ["boss"], None),
        ("OP16-003", "Char 3", 4, 4000, 0, "Character", ["Black"], [], [], ["boss"], None),
        ("OP16-004", "Char 4", 5, 5000, 0, "Character", ["Black"], [], [], ["boss"], None),
        ("OP16-005", "Char 5", 2, 2000, 2000, "Character", ["Black"], [], [], ["tempo"], None),
        ("OP16-006", "Char 6", 3, 3000, 0, "Character", ["Black"], [], [], ["boss"], None),
        ("OP16-007", "Char 7", 4, 4000, 0, "Character", ["Black"], [], [], ["boss"], None),
        ("OP16-008", "Char 8", 5, 5000, 0, "Character", ["Black"], [], [], ["boss"], None),
        ("OP16-009", "Char 9", 6, 6000, 0, "Character", ["Black"], [], [], ["boss"], None),
        ("OP16-010", "Char 10", 7, 7000, 0, "Character", ["Black"], [], [], ["boss"], None),
        ("OP16-011", "Char 11", 8, 8000, 0, "Character", ["Black"], [], [], ["boss"], None),
        ("OP16-012", "Char 12", 9, 9000, 0, "Character", ["Black"], [], [], ["boss"], None),
        ("OP16-013", "Char 13", 2, 1000, 1000, "Character", ["Black"], [], [], ["tempo"], None),
        ("GOOD-001", "Blocker", 2, 1000, 2000, "Character",
         ["Black"], [], ["blocker"], ["early_blocker", "2k_counter"], None),
        ("GOOD-002", "Engine", 3, 3000, 0, "Character",
         ["Black"], [], ["draw"], ["engine", "searcher"], None),
        ("GOOD-003", "Ramp", 2, 2000, 0, "Character", ["Black"], [], ["don"], ["ramp"], None),
    ]
    for cid, name, cost, power, counter, ctype, color, traits, kw, roles, life in cards:
        session.add(CardORM(
            card_id=cid,
            name=name,
            cost=cost,
            power=power,
            counter=counter,
            type=ctype,
            color=color,
            traits=traits,
            attribute="Strike",
            keywords=kw,
            roles=roles,
            effect=f"{name} effect",
            life=life,
            set_id="OP-16",
            set_name="Test",
            rarity="C",
            image_url="",
            unlimited_copies=False,
        ))


def _seed_deck(session):
    """Seed a deck with 50 cards + 1 leader."""
    deck_id = "e2e_deck"
    session.add(DeckORM(
        deck_id=deck_id,
        name="E2E Test Deck",
        leader_card_id="OP16-079",
        source="test",
        event=None,
        date=None,
    ))
    deck_cards = [("OP16-001", 4), ("OP16-002", 4), ("OP16-003", 4),
                  ("OP16-004", 4), ("OP16-005", 4), ("OP16-006", 4),
                  ("OP16-007", 4), ("OP16-008", 4), ("OP16-009", 4),
                  ("OP16-010", 4), ("OP16-011", 4), ("OP16-012", 4),
                  ("OP16-013", 2)]
    for card_id, qty in deck_cards:
        session.add(DeckCardORM(deck_id=deck_id, card_id=card_id, qty=qty))
    return deck_id


def _seed_collection(session):
    """Seed collection: player owns the GOOD candidate cards."""
    session.add(CollectionORM(card_id="GOOD-001", owned=4))
    session.add(CollectionORM(card_id="GOOD-002", owned=2))
    session.add(CollectionORM(card_id="GOOD-003", owned=3))


def _seed_matches(session):
    """Seed 5 win matches and 5 early loss matches with high DON unused."""
    for i in range(5):
        mid = f"e2e_match_win_{i}"
        session.add(MatchORM(
            match_id=mid,
            source_file=f"win_{i}.log",
            leader_self="OP16-079",
            leader_opp="OP16-022",
            opponent_user="opp",
            result="win",
            reason="life0",
            duration_turns=8,
        ))
        session.add(MatchTurnORM(
            match_id=mid, turn_no=1, player_idx=0, don_drawn=2, don_unused=1,
            cards_played=["OP16-001"], attacks=[], counters=[], errors=[],
            state_end={"hand": 5, "board": 1, "life": 4},
        ))
    for i in range(5):
        mid = f"e2e_match_loss_{i}"
        session.add(MatchORM(
            match_id=mid,
            source_file=f"loss_{i}.log",
            leader_self="OP16-079",
            leader_opp="OP16-022",
            opponent_user="opp",
            result="loss",
            reason="life0",
            duration_turns=4,
        ))
        for turn_no in range(1, 5):
            session.add(MatchTurnORM(
                match_id=mid, turn_no=turn_no, player_idx=0,
                don_drawn=turn_no + 1, don_unused=turn_no + 1,
                cards_played=[], attacks=[], counters=[], errors=[],
                state_end={"hand": 8, "board": 0, "life": 4},
            ))


def _setup(db_session):
    """Full setup: clean all tables and seed test data."""
    for model in [RecommendationORM, PatternORM, MatchStatsORM, MatchTurnORM,
                  MatchORM, DeckCardORM, DeckORM, CollectionORM, CardORM]:
        db_session.query(model).delete()
    db_session.commit()
    _seed_cards(db_session)
    deck_id = _seed_deck(db_session)
    _seed_collection(db_session)
    _seed_matches(db_session)
    db_session.commit()
    return deck_id


def test_e2e_stats_pipeline(db_session, session_factory):
    """Cards → Matches → Stats: verify stats compute from seeded matches."""
    _setup(db_session)
    from app.application.services.stats_service import StatsService

    service = StatsService(session_factory)
    stats = service.compute_all_stats()
    assert stats["total_matches"] == 10
    assert stats["winrate"] == 50.0
    assert "OP16-079" in stats["leaders_used"]


def test_e2e_pattern_detection(db_session, session_factory):
    """Matches → Patterns: verify patterns are detected from seeded matches."""
    _setup(db_session)
    from app.application.services.pattern_service import PatternService

    service = PatternService(session_factory)
    patterns = service.detect_and_save()
    assert isinstance(patterns, list)
    assert len(patterns) > 0

    fetched = service.get_patterns()
    assert len(fetched) == len(patterns)


def test_e2e_knowledge_insights(db_session, session_factory):
    """Stats → Knowledge: verify insights are generated from stats."""
    _setup(db_session)
    from app.application.services.knowledge_service import KnowledgeService

    service = KnowledgeService(session_factory)
    insights = service.generate_insights()
    assert isinstance(insights, list)
    assert len(insights) > 0
    winrate_insight = [i for i in insights if i["doc_id"] == "insight_winrate"]
    assert len(winrate_insight) == 1


def test_e2e_recommendations(db_session, session_factory):
    """Patterns + Collection + Deck → Recommendations."""
    deck_id = _setup(db_session)
    from app.application.services.pattern_service import PatternService
    from app.application.services.recommendation_service import RecommendationService

    PatternService(session_factory).detect_and_save()
    service = RecommendationService(session_factory)
    recs = service.generate_recommendations(deck_id)
    assert len(recs) > 0
    assert all(r["score"] >= 0 for r in recs)
    assert all(r["score"] <= 100 for r in recs)


def test_e2e_recommendations_persisted(db_session, session_factory):
    """Recommendations are persisted to DB."""
    deck_id = _setup(db_session)
    from app.application.services.pattern_service import PatternService
    from app.application.services.recommendation_service import RecommendationService

    PatternService(session_factory).detect_and_save()
    service = RecommendationService(session_factory)
    service.generate_recommendations(deck_id)

    fetched = service.get_recommendations(deck_id)
    assert len(fetched) > 0
    assert all("rec_id" in r for r in fetched)
    assert all("card_out" in r for r in fetched)
    assert all("card_in" in r for r in fetched)


def test_e2e_meta_engine(db_session, session_factory):
    """Decks + Matches → Meta: verify meta engine produces report."""
    _setup(db_session)
    from app.application.services.meta_engine import MetaEngine

    engine = MetaEngine(session_factory)
    report = engine.compute_meta()
    assert "popular_decks" in report
    assert "winrates" in report
    assert "meta_summary" in report


def test_e2e_full_pipeline(db_session, session_factory):
    """Full pipeline: cards → deck → matches → stats → patterns → knowledge → recommendations."""
    deck_id = _setup(db_session)

    from app.application.services.knowledge_service import KnowledgeService
    from app.application.services.meta_engine import MetaEngine
    from app.application.services.pattern_service import PatternService
    from app.application.services.recommendation_service import RecommendationService
    from app.application.services.stats_service import StatsService

    stats = StatsService(session_factory).compute_all_stats()
    assert stats["total_matches"] == 10

    patterns = PatternService(session_factory).detect_and_save()
    assert len(patterns) > 0

    insights = KnowledgeService(session_factory).generate_insights()
    assert len(insights) > 0

    meta = MetaEngine(session_factory).compute_meta()
    assert "popular_decks" in meta

    recs = RecommendationService(session_factory).generate_recommendations(deck_id)
    assert len(recs) > 0

    assert all(isinstance(r, dict) for r in recs)
    assert all("card_in" in r for r in recs)
    assert all("rationale" in r for r in recs)
