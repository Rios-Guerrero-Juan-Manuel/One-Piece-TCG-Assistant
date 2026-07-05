import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.application.services.meta_engine import MetaEngine
from app.infrastructure.persistence.models import (
    Base,
    DeckORM,
    MatchORM,
    MatchTurnORM,
)

UTC = datetime.UTC


def _factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _add_match(
    session,
    match_id,
    leader_self,
    leader_opp,
    result,
    turns=None,
    imported_at=None,
):
    session.add(
        MatchORM(
            match_id=match_id,
            source_file="test.log",
            leader_self=leader_self,
            leader_opp=leader_opp,
            result=result,
            imported_at=imported_at or datetime.datetime.now(UTC),
        ),
    )
    for idx, cards_played in enumerate(turns or []):
        session.add(
            MatchTurnORM(
                match_id=match_id,
                turn_no=idx + 1,
                player_idx=0,
                don_drawn=0,
                don_unused=0,
                cards_played=cards_played,
                attacks=[],
                counters=[],
                errors=[],
                state_end={},
            ),
        )
    session.commit()


def _add_deck(session, deck_id, name, leader_id):
    session.add(
        DeckORM(
            deck_id=deck_id,
            name=name,
            leader_card_id=leader_id,
            source=None,
            event=None,
            date=None,
        ),
    )
    session.commit()


# ---------------------------------------------------------------- popular decks
def test_popular_decks():
    factory = _factory()
    session = factory()
    try:
        _add_deck(session, "d1", "Red Rush", "L-RED")
        _add_deck(session, "d2", "Red Burn", "L-RED")
        _add_deck(session, "d3", "Blue Stomp", "L-BLUE")
    finally:
        session.close()

    report = MetaEngine(factory).compute_meta()
    popular = {d["leader_card_id"]: d for d in report["popular_decks"]}
    assert popular["L-RED"]["deck_count"] == 2
    assert set(popular["L-RED"]["deck_names"]) == {"Red Rush", "Red Burn"}
    assert popular["L-BLUE"]["deck_count"] == 1
    # Sorted by deck_count descending
    assert report["popular_decks"][0]["leader_card_id"] == "L-RED"


# --------------------------------------------------------------- winrates
def test_winrates_by_leader():
    factory = _factory()
    session = factory()
    try:
        _add_match(session, "m1", "L-RED", "L-BLUE", "win")
        _add_match(session, "m2", "L-RED", "L-GREEN", "win")
        _add_match(session, "m3", "L-RED", "L-BLACK", "loss")
        _add_match(session, "m4", "L-BLUE", "L-RED", "loss")
    finally:
        session.close()

    report = MetaEngine(factory).compute_meta()
    assert report["winrates"]["L-RED"] == pytest.approx(200 / 3, abs=0.1)
    assert report["winrates"]["L-BLUE"] == pytest.approx(0.0)


# --------------------------------------------------------- most used cards
def test_most_used_cards():
    factory = _factory()
    session = factory()
    try:
        _add_match(
            session,
            "m1",
            "L-RED",
            "L-BLUE",
            "win",
            turns=[["C1", "C2"], ["C1", "C3"]],
        )
        _add_match(
            session,
            "m2",
            "L-RED",
            "L-GREEN",
            "loss",
            turns=[["C1", "C3"]],
        )
    finally:
        session.close()

    report = MetaEngine(factory).compute_meta()
    cards = {c["card_id"]: c["count"] for c in report["most_used_cards"]}
    assert cards["C1"] == 3
    assert cards["C3"] == 2
    assert cards["C2"] == 1
    # Sorted by count descending
    assert report["most_used_cards"][0]["card_id"] == "C1"


# -------------------------------------------------------------- matchup table
def test_matchup_table():
    factory = _factory()
    session = factory()
    try:
        _add_match(session, "m1", "L-RED", "L-BLUE", "win")
        _add_match(session, "m2", "L-RED", "L-BLUE", "win")
        _add_match(session, "m3", "L-RED", "L-BLUE", "loss")
        _add_match(session, "m4", "L-RED", "L-GREEN", "loss")
    finally:
        session.close()

    report = MetaEngine(factory).compute_meta()
    table = report["matchup_table"]
    assert table["L-RED"]["L-BLUE"] == pytest.approx(200 / 3, abs=0.1)
    assert table["L-RED"]["L-GREEN"] == pytest.approx(0.0)


# ---------------------------------------------------------- emerging cards
def test_emerging_cards():
    factory = _factory()
    session = factory()
    try:
        old_time = datetime.datetime(2024, 1, 1, tzinfo=UTC)
        new_time = datetime.datetime(2024, 6, 1, tzinfo=UTC)
        # Older matches only use "C-OLD"
        _add_match(
            session,
            "m1",
            "L-RED",
            "L-BLUE",
            "win",
            turns=[["C-OLD"]],
            imported_at=old_time,
        )
        _add_match(
            session,
            "m2",
            "L-RED",
            "L-BLUE",
            "win",
            turns=[["C-OLD"]],
            imported_at=old_time,
        )
        # Newer matches use "C-OLD" plus emerging "C-NEW"
        _add_match(
            session,
            "m3",
            "L-RED",
            "L-BLUE",
            "loss",
            turns=[["C-OLD", "C-NEW"]],
            imported_at=new_time,
        )
        _add_match(
            session,
            "m4",
            "L-RED",
            "L-BLUE",
            "loss",
            turns=[["C-NEW"]],
            imported_at=new_time,
        )
    finally:
        session.close()

    report = MetaEngine(factory).compute_meta()
    emerging = {c["card_id"]: c["count"] for c in report["emerging_cards"]}
    assert "C-NEW" in emerging
    assert emerging["C-NEW"] == 2
    assert "C-OLD" not in emerging


# -------------------------------------------------------- declining cards
def test_declining_cards():
    factory = _factory()
    session = factory()
    try:
        old_time = datetime.datetime(2024, 1, 1, tzinfo=UTC)
        new_time = datetime.datetime(2024, 6, 1, tzinfo=UTC)
        _add_match(
            session,
            "m1",
            "L-RED",
            "L-BLUE",
            "win",
            turns=[["C-GONE", "C-KO"]],
            imported_at=old_time,
        )
        _add_match(
            session,
            "m2",
            "L-RED",
            "L-BLUE",
            "win",
            turns=[["C-GONE"]],
            imported_at=old_time,
        )
        _add_match(
            session,
            "m3",
            "L-RED",
            "L-BLUE",
            "loss",
            turns=[["C-KEEP"]],
            imported_at=new_time,
        )
        _add_match(
            session,
            "m4",
            "L-RED",
            "L-BLUE",
            "loss",
            turns=[["C-KEEP"]],
            imported_at=new_time,
        )
    finally:
        session.close()

    report = MetaEngine(factory).compute_meta()
    declining = {c["card_id"]: c["count"] for c in report["declining_cards"]}
    assert "C-GONE" in declining
    assert declining["C-GONE"] == 2
    assert "C-KO" in declining
    assert "C-KEEP" not in declining


# ----------------------------------------------------------- meta summary
def test_meta_summary():
    factory = _factory()
    session = factory()
    try:
        _add_deck(session, "d1", "Red 1", "L-RED")
        _add_deck(session, "d2", "Red 2", "L-RED")
        _add_deck(session, "d3", "Red 3", "L-RED")
        _add_deck(session, "d4", "Blue 1", "L-BLUE")
        _add_match(session, "m1", "L-RED", "L-BLUE", "win")
        _add_match(session, "m2", "L-RED", "L-GREEN", "win")
        _add_match(session, "m3", "L-RED", "L-BLACK", "win")
        _add_match(session, "m4", "L-BLUE", "L-RED", "loss")
        _add_match(session, "m5", "L-BLUE", "L-RED", "loss")
        _add_match(session, "m6", "L-BLUE", "L-RED", "loss")
        # Best performing leader (3 wins) is L-RED
        # Worst matchup is L-BLUE vs L-RED at 0.0
    finally:
        session.close()

    summary = MetaEngine(factory).compute_meta()["meta_summary"]
    assert summary["most_popular_leader"] == "L-RED"
    assert summary["best_performing_leader"] == "L-RED"
    assert summary["worst_matchup"]["self_leader"] == "L-BLUE"
    assert summary["worst_matchup"]["opp_leader"] == "L-RED"
    assert summary["worst_matchup"]["winrate"] == pytest.approx(0.0)


def test_meta_summary_skips_low_volume_leader():
    factory = _factory()
    session = factory()
    try:
        _add_deck(session, "d1", "Red 1", "L-RED")
        _add_deck(session, "d2", "Red 2", "L-RED")
        _add_deck(session, "d3", "Blue 1", "L-BLUE")
        # L-GREEN has only 1 match (a win) below the 3-match threshold
        _add_match(session, "m1", "L-GREEN", "L-BLUE", "win")
        _add_match(session, "m2", "L-RED", "L-BLUE", "loss")
        _add_match(session, "m3", "L-RED", "L-BLUE", "loss")
        _add_match(session, "m4", "L-RED", "L-BLUE", "win")
    finally:
        session.close()

    summary = MetaEngine(factory).compute_meta()["meta_summary"]
    # L-RED (1/3) is eligible; L-GREEN (1/1) is not because total < 3
    assert summary["best_performing_leader"] == "L-RED"


# --------------------------------------------------------- empty data
def test_empty_data():
    factory = _factory()

    report = MetaEngine(factory).compute_meta()
    assert report["popular_decks"] == []
    assert report["winrates"] == {}
    assert report["most_used_cards"] == []
    assert report["emerging_cards"] == []
    assert report["declining_cards"] == []
    assert report["matchup_table"] == {}
    summary = report["meta_summary"]
    assert summary["most_popular_leader"] is None
    assert summary["best_performing_leader"] is None
    assert summary["worst_matchup"] is None


def test_get_latest_snapshot_persists_report():
    factory = _factory()
    session = factory()
    try:
        _add_match(session, "m1", "L-RED", "L-BLUE", "win")
    finally:
        session.close()

    engine = MetaEngine(factory)
    report = engine.compute_meta()
    snapshot = engine.get_latest_snapshot()
    assert snapshot is not None
    assert snapshot["winrates"]["L-RED"] == report["winrates"]["L-RED"]


def test_get_latest_snapshot_returns_none_when_empty():
    factory = _factory()
    assert MetaEngine(factory).get_latest_snapshot() is None
