import pytest

from app.domain.engines.match.statistics import StatisticsEngine
from app.domain.models import Action, Match, Player, Turn


def make_player(
    leader_card_id: str,
    is_self: bool = True,
    user: str = "self",
) -> Player:
    return Player(
        user=user,
        leader_card_id=leader_card_id,
        goes_first=is_self,
        is_self=is_self,
    )


def make_turn(
    turn_no: int = 1,
    player_idx: int = 1,
    don_drawn: int = 2,
    don_available: int = 2,
    don_unused_at_end: int = 0,
    actions: list[Action] | None = None,
    state_end: dict | None = None,
) -> Turn:
    return Turn(
        turn_no=turn_no,
        player_idx=player_idx,
        don_drawn=don_drawn,
        don_available=don_available,
        don_unused_at_end=don_unused_at_end,
        actions=actions or [],
        errors=[],
        state_end=state_end or {},
    )


def make_match(
    match_id: str = "match-1",
    self_leader: str = "OP16-001",
    opp_leader: str = "OP16-002",
    winner_idx: int | None = 0,
    duration_turns: int | None = 10,
    turns: list[Turn] | None = None,
    deck_id_self: str | None = None,
) -> Match:
    players = [
        make_player(self_leader, is_self=True, user="self"),
        make_player(opp_leader, is_self=False, user="opp"),
    ]
    return Match(
        match_id=match_id,
        room_id=None,
        version=None,
        source_file="test.log",
        players=players,
        turns=turns or [],
        winner_idx=winner_idx,
        reason=None,
        duration_turns=duration_turns,
        deck_id_self=deck_id_self,
    )


def test_winrate_calculation():
    matches = [
        make_match("m1", winner_idx=0),
        make_match("m2", winner_idx=0),
        make_match("m3", winner_idx=1),
    ]
    stats = StatisticsEngine().compute_stats(matches)
    assert stats["total_matches"] == 3
    assert stats["winrate"] == pytest.approx(66.67, abs=0.01)


def test_winrate_by_leader():
    matches = [
        make_match("m1", self_leader="OP16-001", winner_idx=0),
        make_match("m2", self_leader="OP16-001", winner_idx=1),
        make_match("m3", self_leader="OP16-003", winner_idx=0),
    ]
    stats = StatisticsEngine().compute_stats(matches)
    assert stats["winrate_by_leader"]["OP16-001"] == 50.0
    assert stats["winrate_by_leader"]["OP16-003"] == 100.0
    assert stats["leader_wins"]["OP16-001"] == 1
    assert stats["leader_wins"]["OP16-003"] == 1
    assert stats["leader_totals"]["OP16-001"] == 2
    assert stats["leader_totals"]["OP16-003"] == 1


def test_winrate_by_matchup():
    matches = [
        make_match("m1", self_leader="OP16-001", opp_leader="OP16-002", winner_idx=0),
        make_match("m2", self_leader="OP16-001", opp_leader="OP16-002", winner_idx=1),
        make_match("m3", self_leader="OP16-001", opp_leader="OP16-003", winner_idx=0),
    ]
    stats = StatisticsEngine().compute_stats(matches)
    assert stats["winrate_by_matchup"]["OP16-001_vs_OP16-002"] == 50.0
    assert stats["winrate_by_matchup"]["OP16-001_vs_OP16-003"] == 100.0


def test_avg_duration():
    matches = [
        make_match("m1", duration_turns=10),
        make_match("m2", duration_turns=20),
        make_match("m3", duration_turns=15),
    ]
    stats = StatisticsEngine().compute_stats(matches)
    assert stats["avg_duration_turns"] == pytest.approx(15.0, abs=0.01)


def test_most_played_cards():
    turn1 = make_turn(actions=[
        Action(type="deploy", card_id="OP16-001"),
        Action(type="deploy", card_id="OP16-002"),
    ])
    turn2 = make_turn(actions=[
        Action(type="deploy", card_id="OP16-001"),
        Action(type="deploy", card_id="OP16-003"),
    ])
    match = make_match(turns=[turn1, turn2])
    stats = StatisticsEngine().compute_stats([match])
    cards = {c["card_id"]: c["count"] for c in stats["most_played_cards"]}
    assert cards["OP16-001"] == 2
    assert cards["OP16-002"] == 1
    assert cards["OP16-003"] == 1


def test_empty_matches():
    stats = StatisticsEngine().compute_stats([])
    assert stats["total_matches"] == 0
    assert stats["winrate"] == 0
    assert stats["winrate_by_leader"] == {}
    assert stats["leader_wins"] == {}
    assert stats["leader_totals"] == {}
    assert stats["winrate_by_matchup"] == {}
    assert stats["avg_duration_turns"] == 0
    assert stats["most_played_cards"] == []
    assert stats["avg_don_unused"] == 0
    assert stats["leaders_used"] == {}


def test_leaders_used():
    matches = [
        make_match("m1", self_leader="OP16-001"),
        make_match("m2", self_leader="OP16-001"),
        make_match("m3", self_leader="OP16-003"),
    ]
    stats = StatisticsEngine().compute_stats(matches)
    assert stats["leaders_used"]["OP16-001"] == 2
    assert stats["leaders_used"]["OP16-003"] == 1


def test_avg_don_unused():
    turn1 = make_turn(don_unused_at_end=2)
    turn2 = make_turn(don_unused_at_end=4)
    match = make_match(turns=[turn1, turn2])
    stats = StatisticsEngine().compute_stats([match])
    assert stats["avg_don_unused"] == pytest.approx(3.0, abs=0.01)


def test_most_played_cards_top_10_limit():
    turns = [
        make_turn(actions=[Action(type="deploy", card_id=f"OP16-00{i}")])
        for i in range(1, 13)
    ]
    match = make_match(turns=turns)
    stats = StatisticsEngine().compute_stats([match])
    assert len(stats["most_played_cards"]) == 10


def test_non_deploy_actions_excluded_from_most_played():
    turn = make_turn(actions=[
        Action(type="deploy", card_id="OP16-001"),
        Action(type="attack_resolve", card_id="OP16-002", power=5000, counter_value=3000),
        Action(type="counter", card_id="OP16-003", counter_value=1000),
        Action(type="draw", card_id="OP16-004"),
    ])
    match = make_match(turns=[turn])
    stats = StatisticsEngine().compute_stats([match])
    cards = {c["card_id"] for c in stats["most_played_cards"]}
    assert cards == {"OP16-001"}


def test_winrate_zero_when_all_losses():
    matches = [
        make_match("m1", winner_idx=1),
        make_match("m2", winner_idx=1),
    ]
    stats = StatisticsEngine().compute_stats(matches)
    assert stats["winrate"] == 0
    assert stats["total_matches"] == 2


def test_winner_idx_none_does_not_count_as_win():
    matches = [
        make_match("m1", winner_idx=0),
        make_match("m2", winner_idx=None),
    ]
    stats = StatisticsEngine().compute_stats(matches)
    assert stats["total_matches"] == 2
    assert stats["winrate"] == 50.0


def test_avg_duration_with_none_values():
    matches = [
        make_match("m1", duration_turns=10),
        make_match("m2", duration_turns=None),
        make_match("m3", duration_turns=20),
    ]
    stats = StatisticsEngine().compute_stats(matches)
    assert stats["avg_duration_turns"] == pytest.approx(15.0, abs=0.01)


def test_winrate_by_deck():
    matches = [
        make_match("m1", deck_id_self="OP16-001_v1", winner_idx=0),
        make_match("m2", deck_id_self="OP16-001_v1", winner_idx=0),
        make_match("m3", deck_id_self="OP16-001_v1", winner_idx=1),
        make_match("m4", deck_id_self="OP16-001_v2", winner_idx=1),
    ]
    stats = StatisticsEngine().compute_stats(matches)
    assert "winrate_by_deck" in stats
    assert stats["winrate_by_deck"]["OP16-001_v1"] == pytest.approx(66.67, abs=0.01)
    assert stats["winrate_by_deck"]["OP16-001_v2"] == 0.0


def test_winrate_by_deck_empty():
    stats = StatisticsEngine().compute_stats([])
    assert stats["winrate_by_deck"] == {}


def test_winrate_by_deck_no_deck_assigned():
    matches = [make_match("m1", deck_id_self=None)]
    stats = StatisticsEngine().compute_stats(matches)
    assert stats["winrate_by_deck"] == {}


def test_winrate_by_deck_vs_opp_leader():
    matches = [
        make_match("m1", deck_id_self="OP16-001_v1", opp_leader="OP16-002", winner_idx=0),
        make_match("m2", deck_id_self="OP16-001_v1", opp_leader="OP16-002", winner_idx=1),
        make_match("m3", deck_id_self="OP16-001_v1", opp_leader="OP16-003", winner_idx=0),
        make_match("m4", deck_id_self="OP16-001_v2", opp_leader="OP16-002", winner_idx=1),
    ]
    stats = StatisticsEngine().compute_stats(matches)
    matrix = stats["winrate_by_deck_vs_opp_leader"]
    totals = stats["deck_vs_opp_leader_totals"]
    assert matrix["OP16-001_v1"]["OP16-002"] == 50.0
    assert matrix["OP16-001_v1"]["OP16-003"] == 100.0
    assert matrix["OP16-001_v2"]["OP16-002"] == 0.0
    assert totals["OP16-001_v1"]["OP16-002"] == 2
    assert totals["OP16-001_v1"]["OP16-003"] == 1
    assert totals["OP16-001_v2"]["OP16-002"] == 1


def test_winrate_by_deck_vs_opp_leader_empty():
    stats = StatisticsEngine().compute_stats([])
    assert stats["winrate_by_deck_vs_opp_leader"] == {}
    assert stats["deck_vs_opp_leader_totals"] == {}
