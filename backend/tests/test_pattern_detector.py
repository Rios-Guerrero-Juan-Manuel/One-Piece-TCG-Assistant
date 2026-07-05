from app.domain.engines.match.pattern_detector import PatternDetector
from app.domain.models import Action, Match, Player, Turn


def _player(leader: str = "OP01-001", is_self: bool = True, user: str = "self") -> Player:
    return Player(
        user=user,
        leader_card_id=leader,
        goes_first=is_self,
        is_self=is_self,
    )


def _players() -> list[Player]:
    return [
        _player(is_self=True, user="self"),
        _player("OP01-002", is_self=False, user="opp"),
    ]


def _turn(
    turn_no: int = 1,
    player_idx: int = 1,
    don_unused: int = 0,
    don_drawn: int = 2,
    actions: list[Action] | None = None,
    state_end: dict | None = None,
) -> Turn:
    return Turn(
        turn_no=turn_no,
        player_idx=player_idx,
        don_drawn=don_drawn,
        don_available=don_drawn,
        don_unused_at_end=don_unused,
        actions=actions or [],
        errors=[],
        state_end=state_end or {},
    )


def _match(
    match_id: str = "m1",
    winner_idx: int | None = 0,
    duration_turns: int | None = 6,
    turns: list[Turn] | None = None,
) -> Match:
    return Match(
        match_id=match_id,
        room_id=None,
        version=None,
        source_file="t.log",
        players=_players(),
        turns=turns or [],
        winner_idx=winner_idx,
        reason=None,
        duration_turns=duration_turns,
    )


def _ids(patterns: list[dict]) -> set[str]:
    return {p["pattern_id"] for p in patterns}


def _healthy_turns(n: int) -> list[Turn]:
    return [
        _turn(
            turn_no=i,
            actions=[Action(type="deploy", card_id="C1")],
            state_end={"hand": ["C1"]},
        )
        for i in range(1, n + 1)
    ]


def test_early_loss_detected():
    losses = [
        _match(f"l{i}", winner_idx=1, duration_turns=4, turns=_healthy_turns(4))
        for i in range(4)
    ]
    win = _match("w1", winner_idx=0, duration_turns=10, turns=_healthy_turns(10))
    patterns = PatternDetector().detect_patterns(losses + [win])
    ids = _ids(patterns)
    assert "weakness_vs_aggro" in ids
    hit = [p for p in patterns if p["pattern_id"] == "weakness_vs_aggro"][0]
    assert hit["severity"] == "high"
    assert hit["filter"]["type"] == "early_loss"
    assert hit["filter"]["pct"] == 100.0
    assert "early_defeats" not in ids


def test_no_early_loss():
    matches = [
        _match("w1", winner_idx=0, duration_turns=10, turns=_healthy_turns(10)),
        _match("l1", winner_idx=1, duration_turns=8, turns=_healthy_turns(8)),
        _match("l2", winner_idx=1, duration_turns=9, turns=_healthy_turns(9)),
    ]
    ids = _ids(PatternDetector().detect_patterns(matches))
    assert "weakness_vs_aggro" not in ids
    assert "early_defeats" not in ids


def test_low_early_pressure():
    turns = []
    for i in range(1, 7):
        acts = [] if i <= 2 else [Action(type="deploy", card_id="C1")]
        turns.append(
            _turn(turn_no=i, actions=acts, state_end={"hand": ["C1"]})
        )
    matches = [_match("m1", winner_idx=0, duration_turns=6, turns=turns)]
    patterns = PatternDetector().detect_patterns(matches)
    ids = _ids(patterns)
    assert "low_early_pressure" in ids
    hit = [p for p in patterns if p["pattern_id"] == "low_early_pressure"][0]
    assert hit["severity"] == "medium"
    assert hit["filter"]["pct"] == 100.0


def test_large_hand_detected():
    big_hand = {"hand": [f"C{i}" for i in range(8)]}
    turns = [
        _turn(
            turn_no=i,
            actions=[Action(type="deploy", card_id="C1")],
            state_end=big_hand,
        )
        for i in range(1, 7)
    ]
    matches = [_match("m1", winner_idx=0, duration_turns=6, turns=turns)]
    patterns = PatternDetector().detect_patterns(matches)
    ids = _ids(patterns)
    assert "excess_dead_cards" in ids
    hit = [p for p in patterns if p["pattern_id"] == "excess_dead_cards"][0]
    assert hit["severity"] == "medium"
    assert hit["filter"]["avg"] == 8.0


def test_don_inefficient_detected():
    turns = [
        _turn(
            turn_no=i,
            don_unused=4 if i % 2 == 0 else 3,
            actions=[Action(type="deploy", card_id="C1")],
            state_end={"hand": ["C1"]},
        )
        for i in range(1, 7)
    ]
    matches = [_match("m1", winner_idx=0, duration_turns=6, turns=turns)]
    patterns = PatternDetector().detect_patterns(matches)
    ids = _ids(patterns)
    assert "don_inefficiency" in ids
    hit = [p for p in patterns if p["pattern_id"] == "don_inefficiency"][0]
    assert hit["severity"] == "medium"
    assert hit["filter"]["avg"] == 3.5


def test_very_early_loss():
    matches = [
        _match("l1", winner_idx=1, duration_turns=3, turns=_healthy_turns(3)),
        _match("l2", winner_idx=1, duration_turns=10, turns=_healthy_turns(10)),
        _match("l3", winner_idx=1, duration_turns=10, turns=_healthy_turns(10)),
        _match("w1", winner_idx=0, duration_turns=10, turns=_healthy_turns(10)),
    ]
    patterns = PatternDetector().detect_patterns(matches)
    ids = _ids(patterns)
    assert "early_defeats" in ids
    hit = [p for p in patterns if p["pattern_id"] == "early_defeats"][0]
    assert hit["severity"] == "high"
    assert hit["filter"]["type"] == "very_early_loss"
    assert "weakness_vs_aggro" not in ids


def test_counter_dependency():
    turns = []
    for i in range(1, 7):
        acts = [Action(type="deploy", card_id="C1")]
        if i == 3:
            acts.append(Action(type="counter", card_id="C2", counter_value=2000))
        turns.append(
            _turn(turn_no=i, actions=acts, state_end={"hand": ["C1"]})
        )
    matches = [_match("m1", winner_idx=0, duration_turns=6, turns=turns)]
    patterns = PatternDetector().detect_patterns(matches)
    ids = _ids(patterns)
    assert "counter_dependency" in ids
    hit = [p for p in patterns if p["pattern_id"] == "counter_dependency"][0]
    assert hit["severity"] == "low"
    assert hit["filter"]["pct"] == 100.0


def test_no_patterns_clean():
    turns = [
        _turn(
            turn_no=i,
            don_unused=0,
            actions=[Action(type="deploy", card_id="C1")],
            state_end={"hand": [f"C{j}" for j in range(5)]},
        )
        for i in range(1, 11)
    ]
    matches = [
        _match(
            f"m{i}",
            winner_idx=0 if i % 2 == 0 else 1,
            duration_turns=10,
            turns=turns,
        )
        for i in range(1, 5)
    ]
    patterns = PatternDetector().detect_patterns(matches)
    assert patterns == []


def test_empty_matches():
    assert PatternDetector().detect_patterns([]) == []
