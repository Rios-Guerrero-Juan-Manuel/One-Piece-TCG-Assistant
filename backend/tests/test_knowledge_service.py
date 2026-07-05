from app.application.services.knowledge_service import KnowledgeService
from app.infrastructure.persistence.models import (
    InsightORM,
    MatchORM,
    MatchStatsORM,
    MatchTurnORM,
)


def _setup(db_session):
    db_session.query(MatchTurnORM).delete()
    db_session.query(MatchStatsORM).delete()
    db_session.query(MatchORM).delete()
    db_session.query(InsightORM).filter(
        InsightORM.type == "insight"
    ).delete()
    db_session.commit()


def _add_matches(session, count, result="win", leader="OP16-079", offset=0):
    for i in range(count):
        idx = i + offset
        m = MatchORM(
            match_id=f"test_{leader}_{idx}",
            source_file=f"test{idx}.log",
            leader_self=leader,
            leader_opp="OP16-022",
            opponent_user="opponent",
            result=result,
            reason="concede",
            duration_turns=8,
        )
        session.add(m)
        session.add(MatchTurnORM(
            match_id=f"test_{leader}_{idx}",
            turn_no=1,
            player_idx=0,
            don_drawn=2,
            don_unused=0,
            cards_played=["OP16-091"],
            attacks=[],
            counters=[],
            errors=[],
            state_end={"hand": 5, "board": 1, "life": 4},
        ))
    session.commit()


def test_winrate_insight_generated(db_session, session_factory):
    _setup(db_session)
    _add_matches(db_session, 10, result="win")
    _add_matches(db_session, 3, result="loss", offset=10)

    service = KnowledgeService(session_factory)
    insights = service.generate_insights()
    winrate_insight = [i for i in insights if i["doc_id"] == "insight_winrate"]
    assert len(winrate_insight) == 1
    assert "winrate" in winrate_insight[0]["content"].lower()


def test_low_winrate_insight(db_session, session_factory):
    _setup(db_session)
    _add_matches(db_session, 2, result="win")
    _add_matches(db_session, 8, result="loss", offset=2)

    service = KnowledgeService(session_factory)
    insights = service.generate_insights()
    winrate_insight = [i for i in insights if i["doc_id"] == "insight_winrate"]
    assert len(winrate_insight) == 1
    assert "below average" in winrate_insight[0]["content"].lower()


def test_best_leader_insight(db_session, session_factory):
    _setup(db_session)
    _add_matches(db_session, 7, result="win", leader="OP16-079")
    _add_matches(db_session, 3, result="loss", leader="OP16-079", offset=7)

    service = KnowledgeService(session_factory)
    insights = service.generate_insights()
    best_insight = [
        i for i in insights if i["doc_id"] == "insight_leader_best"
    ]
    assert len(best_insight) == 1
    assert "OP16-079" in best_insight[0]["content"]
    assert "best leader" in best_insight[0]["content"].lower()


def test_worst_leader_insight(db_session, session_factory):
    _setup(db_session)
    _add_matches(db_session, 7, result="win", leader="OP16-079")
    _add_matches(db_session, 4, result="loss", leader="OP16-080", offset=7)

    service = KnowledgeService(session_factory)
    insights = service.generate_insights()
    worst_insight = [
        i for i in insights if i["doc_id"] == "insight_leader_worst"
    ]
    assert len(worst_insight) == 1
    assert "OP16-080" in worst_insight[0]["content"]
    assert "weakest" in worst_insight[0]["content"].lower()


def test_leader_summary_insight(db_session, session_factory):
    _setup(db_session)
    _add_matches(db_session, 7, result="win", leader="OP16-079")
    _add_matches(db_session, 4, result="loss", leader="OP16-080", offset=7)

    service = KnowledgeService(session_factory)
    insights = service.generate_insights()
    summary = [
        i for i in insights if i["doc_id"] == "insight_leader_summary"
    ]
    assert len(summary) == 1
    assert summary[0]["expandable"] is True
    assert "OP16-079" in summary[0]["content"]
    assert "OP16-080" in summary[0]["content"]


def test_stale_insights_cleaned(db_session, session_factory):
    _setup(db_session)
    _add_matches(db_session, 10, result="win", leader="OP16-079")

    service = KnowledgeService(session_factory)
    service.generate_insights()
    assert any(
        d.doc_id == "insight_leader_best"
        for d in db_session.query(InsightORM).filter(
            InsightORM.type == "insight"
        )
    )

    _add_matches(db_session, 10, result="win", leader="OP15-058", offset=10)
    db_session.query(MatchORM).filter(
        MatchORM.leader_self == "OP16-079"
    ).delete()
    db_session.commit()

    service.generate_insights()
    docs = db_session.query(InsightORM).filter(
        InsightORM.type == "insight"
    )
    doc_ids = [d.doc_id for d in docs]
    assert "insight_leader_best" in doc_ids
    assert not any("OP16-079" in d.content for d in docs)


def test_don_efficiency_insight(db_session, session_factory):
    _setup(db_session)
    _add_matches(db_session, 8, result="win")
    # Add turns with high DON unused
    for i in range(8):
        db_session.add(MatchTurnORM(
            match_id=f"test_OP16-079_{i}",
            turn_no=2,
            player_idx=0,
            don_drawn=5,
            don_unused=4,
            cards_played=[],
            attacks=[],
            counters=[],
            errors=[],
            state_end={"hand": 6, "board": 2, "life": 4},
        ))
    db_session.commit()

    service = KnowledgeService(session_factory)
    insights = service.generate_insights()
    don_insight = [
        i for i in insights if i["doc_id"] == "insight_don_efficiency"
    ]
    assert len(don_insight) == 1
    assert "DON" in don_insight[0]["content"]


def test_most_played_cards_insight(db_session, session_factory):
    _setup(db_session)
    _add_matches(db_session, 8, result="win")

    service = KnowledgeService(session_factory)
    insights = service.generate_insights()
    played_insight = [
        i for i in insights if i["doc_id"] == "insight_most_played"
    ]
    assert len(played_insight) == 1
    assert "OP16-091" in played_insight[0]["content"]


def test_no_insights_with_empty_data(db_session, session_factory):
    _setup(db_session)
    _add_matches(db_session, 2, result="win")

    service = KnowledgeService(session_factory)
    insights = service.generate_insights()
    assert len(insights) == 0


def test_insights_persisted_to_db(db_session, session_factory):
    _setup(db_session)
    _add_matches(db_session, 10, result="win")

    service = KnowledgeService(session_factory)
    service.generate_insights()

    docs = (
        db_session.query(InsightORM)
        .filter(InsightORM.type == "insight")
        .all()
    )
    assert len(docs) >= 3
    titles = [d.title for d in docs]
    assert any("Winrate" in t for t in titles)


def test_get_insights(db_session, session_factory):
    _setup(db_session)
    _add_matches(db_session, 10, result="win")

    service = KnowledgeService(session_factory)
    service.generate_insights()
    insights = service.get_insights()
    assert len(insights) >= 3
    assert all("doc_id" in i for i in insights)
    assert all("content" in i for i in insights)
