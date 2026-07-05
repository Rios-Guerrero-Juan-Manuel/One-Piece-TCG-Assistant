from pathlib import Path

import pytest

from app.domain.models import Match
from app.domain.parser.match_parser import MatchParser

LOGS_DIR = Path(__file__).resolve().parents[2] / "Datos" / "CombatLogs"


def _parse_variant_b():
    log_path = LOGS_DIR / "2026-06-29T16_18_16.txt"
    if not log_path.exists():
        return None
    text = log_path.read_text(encoding="utf-8")
    parser = MatchParser()
    return parser.parse(text, self_user="SelfPlayer#0000")


def _parse_variant_a():
    auto_saved = LOGS_DIR / "AutoSaved"
    log_files = sorted(auto_saved.glob("*.log"))
    if not log_files:
        return None
    text = log_files[0].read_text(encoding="utf-8")
    parser = MatchParser()
    return parser.parse(text, self_user="SelfPlayer#0000")


def _skip_if_no_data(match):
    if match is None:
        pytest.skip("Test log data not available (Datos/ excluded from repo)")


def test_parses_variant_b_log():
    match = _parse_variant_b()
    _skip_if_no_data(match)
    assert len(match.players) == 2
    assert len(match.players[0].user) > 0
    assert len(match.players[1].user) > 0
    assert match.players[0].leader_card_id == "OP16-079"
    assert match.players[1].leader_card_id == "OP16-022"
    assert match.players[0].is_self is True
    assert match.players[1].is_self is False


def test_variant_b_winner_concede():
    match = _parse_variant_b()
    _skip_if_no_data(match)
    assert match.reason == "concede"
    assert match.winner_idx is not None


def test_variant_b_has_turns():
    match = _parse_variant_b()
    _skip_if_no_data(match)
    assert len(match.turns) > 0
    assert match.duration_turns == len(match.turns)


def test_parses_variant_a_log():
    match = _parse_variant_a()
    _skip_if_no_data(match)
    assert len(match.players) == 2
    assert all(p.leader_card_id for p in match.players)


def test_variant_a_has_turns():
    match = _parse_variant_a()
    _skip_if_no_data(match)
    assert len(match.turns) > 0


def test_zerowidth_space_normalization():
    match = _parse_variant_b()
    _skip_if_no_data(match)
    for p in match.players:
        assert "\u200b" not in p.user


def test_all_logs_parse_without_error():
    all_files = list(LOGS_DIR.glob("*.txt")) + list(
        (LOGS_DIR / "AutoSaved").glob("*")
    )
    if not all_files:
        pytest.skip("Test log data not available (Datos/ excluded from repo)")
    parser = MatchParser()
    for f in sorted(all_files):
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8")
        match = parser.parse(text, self_user="SelfPlayer#0000")
        assert isinstance(match, Match)
        assert len(match.players) >= 1


DON_LOG = """\
Waiting for a Connection with Room ID:TEST
[Player1] Has Connected
[Player1] Leader is Yamato ["OP16-079">OP16-079]
[Player2] Has Connected
[Player2] Leader is Enel ["OP15-058">OP15-058]
[Player2] Chose to go First
[Player2] Draw 1 Don
RZ1|1|2|Don|4|5|5|0|1|1|0|0|0
[Player2] End Turn
[Player1] Draw 2 Don
RZ1|2|1|Don|4|9|5|0|1|1|0|0|0
RZ1|3|1|Don|4|8|5|1|1|1|0|0|0
[Player1] End Turn
[Player2] Draw 2 Don
RZ1|4|2|Don|4|4|5|0|1|1|0|0|0
RZ1|5|2|Don|4|3|5|1|1|1|0|0|0
[Player2] End Turn
"""


def test_don_drawn_counts_real_draws():
    match = MatchParser().parse(DON_LOG, self_user="Player1")
    by_player = {1: [], 2: []}
    for t in match.turns:
        by_player.setdefault(t.player_idx, []).append(t)
    # Player2 (Enel): turn1 drew 1, turn3 drew 2
    assert by_player[2][0].don_drawn == 1
    assert by_player[2][1].don_drawn == 2
    # Player1 (Yamato): turn2 drew 2
    assert by_player[1][0].don_drawn == 2


def test_don_field_accumulates():
    match = MatchParser().parse(DON_LOG, self_user="Player1")
    by_player = {1: [], 2: []}
    for t in match.turns:
        by_player.setdefault(t.player_idx, []).append(t)
    # Player2 (Enel) cap = 6: 1 drawn -> field 1; +2 drawn -> field 3
    assert by_player[2][0].don_unused_at_end == 1
    assert by_player[2][1].don_unused_at_end == 3
    # Player1 (Yamato) cap = 10: 2 drawn -> field 2
    assert by_player[1][0].don_unused_at_end == 2


def test_don_enel_cap_is_six():
    match = MatchParser().parse(DON_LOG, self_user="Player1")
    # Player2 has drawn 3 DON total but field is 3, not 7 -> proves cap = 6
    enel_turns = [t for t in match.turns if t.player_idx == 2]
    assert enel_turns[-1].don_unused_at_end == 3
