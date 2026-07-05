from app.domain.engines.match.turn_analyzer import TurnAnalyzer
from app.domain.models import Action, Turn


def make_turn(
    turn_no: int = 5,
    player_idx: int = 0,
    don_drawn: int = 2,
    don_available: int = 4,
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


def test_floated_don_detected():
    # Active DON at end of turn still active after opponent's turn -> floated.
    turn = make_turn(
        don_drawn=2,
        state_end={"don_active": 2},
    )
    next_turn = make_turn(
        turn_no=6,
        player_idx=1,
        don_drawn=0,
        state_end={"opp_don_active": 2},
    )
    analyzer = TurnAnalyzer()
    analyzer.analyze_turns([turn, next_turn])
    assert any("Floated DON" in i for i in turn.errors)


def test_floated_don_not_detected_when_used_for_defense():
    # DON was used during opponent's turn -> not floated.
    turn = make_turn(
        don_drawn=2,
        state_end={"don_active": 2},
    )
    next_turn = make_turn(
        turn_no=6,
        player_idx=1,
        don_drawn=0,
        state_end={"opp_don_active": 0},
    )
    analyzer = TurnAnalyzer()
    analyzer.analyze_turns([turn, next_turn])
    assert not any("Floated DON" in i for i in turn.errors)


def test_floated_don_not_detected_with_no_active():
    turn = make_turn(
        don_drawn=2,
        state_end={"don_active": 0},
    )
    next_turn = make_turn(
        turn_no=6,
        player_idx=1,
        state_end={"opp_don_active": 0},
    )
    analyzer = TurnAnalyzer()
    analyzer.analyze_turns([turn, next_turn])
    assert not any("Floated DON" in i for i in turn.errors)


def test_inefficient_attack_detected():
    actions = [
        Action(
            type="attack_resolve",
            card_id="OP16-001",
            target_card_id="OP16-002",
            power=3000,
            counter_value=5000,
        )
    ]
    turn = make_turn(actions=actions)
    issues = TurnAnalyzer().analyze_turn(turn)
    assert any("Inefficient attack" in i for i in issues)


def test_large_hand_detected():
    turn = make_turn(state_end={"hand": [f"c{i}" for i in range(8)]})
    issues = TurnAnalyzer().analyze_turn(turn)
    assert any("Large hand" in i for i in issues)


def test_low_counter_detected():
    actions = [
        Action(type="counter", counter_value=1000, power=6000),
    ]
    turn = make_turn(actions=actions)
    issues = TurnAnalyzer().analyze_turn(turn)
    assert any("Low counter" in i for i in issues)


def test_over_commit_detected():
    actions = [Action(type="deploy", card_id=f"OP16-00{i}") for i in range(5)]
    turn = make_turn(actions=actions)
    issues = TurnAnalyzer().analyze_turn(turn)
    assert any("Over-commit" in i for i in issues)
    assert any("5 characters" in i for i in issues)


def test_under_commit_early():
    turn = make_turn(turn_no=2)
    issues = TurnAnalyzer().analyze_turn(turn)
    assert any("early turn 2" in i for i in issues)


def test_clean_turn_no_issues():
    actions = [
        Action(
            type="attack_resolve",
            card_id="OP16-001",
            target_card_id="OP16-002",
            power=6000,
            counter_value=5000,
        ),
        Action(type="deploy", card_id="OP16-003"),
    ]
    turn = make_turn(don_unused_at_end=0, actions=actions, state_end={"hand": ["c1", "c2"]})
    issues = TurnAnalyzer().analyze_turn(turn)
    assert issues == []
    assert turn.errors == []
