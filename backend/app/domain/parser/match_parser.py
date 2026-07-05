import re
import unicodedata

from app.domain.models import Action, Match, Player, Turn

CARD_ID_RE = re.compile(r"[A-Z]{1,4}\d{0,2}-\d{3}")
RZ1_RE = re.compile(r"^RZ1\|(.+)$")
_TAG_RE = re.compile(r"<[^>]+>")


def _normalize_user(user: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKC", user)
        if unicodedata.category(ch) != "Cf"
    )


def _user_is_self(self_user: str, log_user: str) -> bool:
    """Check whether a log username corresponds to the configured self user.

    OPTCG Sim usernames carry a discriminator suffix (``Name#12345``) and the
    raw log embeds an invisible zero-width space before the ``#``. Both values
    are expected to be *normalized* (Cf chars stripped) before calling this.

    If the configured ``self_user`` includes a ``#``, require an exact match.
    Otherwise compare only the name portion before the discriminator, so that
    ``SELF_USER=Player1`` matches ``Player1#1234``.
    """
    if not self_user or not log_user:
        return False
    if "#" in self_user:
        return self_user == log_user
    return log_user.split("#", 1)[0] == self_user


def _extract_card_ids(text: str) -> list[str]:
    # Strip OPTCG Sim markup tags (<mark><link="OP16-079">OP16-079</link></mark>)
    # so each card id is matched once, not twice. List-style lines
    # (Hand/Board/Trash: [ID,ID,...]) carry no tags and are unaffected.
    return CARD_ID_RE.findall(_TAG_RE.sub("", text))


def _extract_user(line: str) -> str | None:
    m = re.match(r"\[([^\]]+)\]", line)
    if m:
        return _normalize_user(m.group(1))
    return None


class _PlayerState:
    def __init__(self):
        self.user: str | None = None
        self.leader_id: str | None = None
        self.goes_first: bool = False
        self.is_self: bool = False
        self.life: int | None = None
        self.hand: list[str] = []
        self.board: list[str] = []
        self.trash: list[str] = []
        self.don_active: int = 0
        self.don_rested: int = 0
        self.don_attached: int = 0
        self.deck_count: int | None = None
        self.don_deck_remaining: int | None = None
        self.don_cap: int | None = None

    @property
    def don_on_field(self) -> int:
        """Total DON on this player's side (drawn, not returned to the deck)."""
        if self.don_cap is None or self.don_deck_remaining is None:
            return 0
        return max(self.don_cap - self.don_deck_remaining, 0)

    def snapshot(self) -> dict:
        return {
            "hand": list(self.hand),
            "board": list(self.board),
            "trash": list(self.trash),
            "life": self.life,
            "don_active": self.don_active,
            "don_rested": self.don_rested,
            "don_attached": self.don_attached,
            "don_on_field": self.don_on_field,
        }


class MatchParser:
    def parse(self, log_text: str, self_user: str | None = None) -> Match:
        lines = log_text.splitlines()
        norm_self = _normalize_user(self_user) if self_user else None

        players: dict[int, _PlayerState] = {1: _PlayerState(), 2: _PlayerState()}
        user_to_idx: dict[str, int] = {}
        room_id: str | None = None
        version: str | None = None
        match_id: str | None = None

        turns: list[Turn] = []
        current_actions: list[Action] = []
        turn_no = 0
        current_player_idx: int | None = None
        turn_don_drawn: dict[int, int] = {1: 0, 2: 0}
        rz1_to_idx: dict[int, int] = {}
        don_text_player_idx: int | None = None
        last_drawn_card: str | None = None
        last_drawn_pidx: int | None = None
        last_rz1: dict[str, str] | None = None
        winner_idx: int | None = None
        reason: str | None = None
        last_attacker_idx: int | None = None
        last_attack_defender_idx: int | None = None
        last_attack_target_is_leader: bool = False
        just_ended_turn: bool = False
        source_file = ""

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("RZ1|"):
                rz1_parts = line.split("|")
                last_rz1 = {
                    "seq": rz1_parts[1] if len(rz1_parts) > 1 else "",
                    "player": rz1_parts[2] if len(rz1_parts) > 2 else "",
                    "card": rz1_parts[3] if len(rz1_parts) > 3 else "",
                    "action": rz1_parts[4] if len(rz1_parts) > 4 else "",
                    "c5": rz1_parts[5] if len(rz1_parts) > 5 else "",
                    "c6": rz1_parts[6] if len(rz1_parts) > 6 else "",
                    "c7": rz1_parts[7] if len(rz1_parts) > 7 else "",
                    "c8": rz1_parts[8] if len(rz1_parts) > 8 else "",
                    "c9": rz1_parts[9] if len(rz1_parts) > 9 else "",
                    "c10": rz1_parts[10] if len(rz1_parts) > 10 else "",
                    "c11": rz1_parts[11] if len(rz1_parts) > 11 else "",
                    "c12": rz1_parts[12] if len(rz1_parts) > 12 else "",
                }
                if last_rz1.get("seq") == "HDR":
                    if len(rz1_parts) > 3:
                        version = rz1_parts[2]

                # Build RZ1→parser index mapping from card draw correlation.
                # Text "Drew card from deck: ID" precedes the matching RZ1
                # record, so last_drawn_card/pidx are already set.
                rz1_card_val = last_rz1.get("card", "")
                if (
                    last_drawn_card is not None
                    and last_drawn_pidx is not None
                    and rz1_card_val == last_drawn_card
                    and rz1_card_val != "Don"
                ):
                    try:
                        rp = int(last_rz1.get("player", "0"))
                    except ValueError:
                        rp = 0
                    if rp not in rz1_to_idx:
                        rz1_to_idx[rp] = last_drawn_pidx

                if last_rz1.get("card") == "Don":
                    try:
                        action_code = int(last_rz1.get("action", "0"))
                    except ValueError:
                        action_code = 0
                    try:
                        rz1_player = int(last_rz1.get("player", "0"))
                    except ValueError:
                        rz1_player = 0

                    # Build RZ1→parser index mapping from DON draw text
                    if don_text_player_idx is not None and rz1_player not in rz1_to_idx:
                        rz1_to_idx[rz1_player] = don_text_player_idx

                    parser_idx = rz1_to_idx.get(rz1_player, rz1_player)
                    if parser_idx not in players:
                        continue

                    ps = players[parser_idx]

                    if action_code == 4:
                        # DON draw: 1 DON enters play as active
                        try:
                            deck_remaining = int(last_rz1.get("c5", "0"))
                        except ValueError:
                            deck_remaining = 0
                        if ps.don_cap is None:
                            ps.don_cap = deck_remaining + 1
                        ps.don_deck_remaining = deck_remaining
                        try:
                            rested_flag = int(last_rz1.get("c10", "0"))
                        except ValueError:
                            rested_flag = 0
                        if rested_flag:
                            ps.don_rested += 1
                        else:
                            ps.don_active += 1
                        turn_don_drawn[parser_idx] = (
                            turn_don_drawn.get(parser_idx, 0) + 1
                        )
                    elif action_code == 5:
                        # DON move — c6 is the zone code
                        try:
                            zone = int(last_rz1.get("c6", "0"))
                        except ValueError:
                            zone = 0
                        if zone == 5:
                            # Cost area: active → rested
                            if ps.don_active > 0:
                                ps.don_active -= 1
                                ps.don_rested += 1
                            elif ps.don_attached > 0:
                                ps.don_attached -= 1
                                ps.don_rested += 1
                        elif zone == 9:
                            # Attach to character/leader
                            if ps.don_active > 0:
                                ps.don_active -= 1
                                ps.don_attached += 1
                        elif zone == 4:
                            # Remove DON ("Minus 1 Don")
                            if ps.don_attached > 0:
                                ps.don_attached -= 1
                            elif ps.don_rested > 0:
                                ps.don_rested -= 1
                    elif action_code == 9:
                        # DON returns from leader/character at turn start
                        if ps.don_attached > 0:
                            ps.don_attached -= 1
                            ps.don_active += 1
                continue

            user = _extract_user(line)
            if user and user not in user_to_idx:
                idx = 1 if not players[1].user else 2
                players[idx].user = user
                user_to_idx[user] = idx
                if norm_self and _user_is_self(norm_self, _normalize_user(user)):
                    players[idx].is_self = True

            if user:
                pidx = user_to_idx.get(user)
            else:
                pidx = None

            if "Has Connected" in line or "Has Connected" in line:
                pass
            elif "Waiting for a Connection" in line:
                m = re.search(r"Room ID:(\S+)", line)
                if m:
                    room_id = m.group(1)
            elif "Attempting to connect to" in line:
                m = re.search(r"to (\S+)", line)
                if m:
                    room_id = m.group(1)
            elif "Version is" in line:
                m = re.search(r"Version is (\S+)", line)
                if m:
                    version = m.group(1)
            elif "Leader is" in line:
                card_ids = _extract_card_ids(line)
                if card_ids and pidx:
                    players[pidx].leader_id = card_ids[0]
            elif "Chose to go Second" in line:
                if pidx:
                    players[pidx].goes_first = False
            elif "Chose to go First" in line:
                if pidx:
                    players[pidx].goes_first = True
            elif "Will select turn order" in line:
                pass
            elif line.startswith("Waiting") or "select turn order" in line:
                pass
            elif "Drew card from deck" in line:
                card_ids = _extract_card_ids(line)
                if card_ids and pidx:
                    players[pidx].hand.append(card_ids[0])
                    last_drawn_card = card_ids[0]
                    last_drawn_pidx = pidx
                    current_actions.append(Action(
                        type="draw", actor=user, card_id=card_ids[0],
                        cost=None, power=None, counter_value=None,
                        effect_text=None, result=None,
                    ))
            elif "Draw 1 Card" in line:
                pass
            elif "Draw 2 Don" in line or "Draw 1 Don" in line:
                if pidx is not None:
                    don_text_player_idx = pidx
            elif "Hand before Mulligan" in line:
                card_ids = _extract_card_ids(line)
                if pidx:
                    players[pidx].hand = list(card_ids)
            elif "Hand after Mulligan" in line:
                card_ids = _extract_card_ids(line)
                if pidx:
                    players[pidx].hand = list(card_ids)
            elif line.startswith(f"[{user}] Hand:") if user else False:
                card_ids = _extract_card_ids(line)
                if pidx:
                    players[pidx].hand = list(card_ids)
                    if just_ended_turn and turns:
                        key = "hand" if pidx == turns[-1].player_idx else "opp_hand"
                        turns[-1].state_end[key] = list(card_ids)
            elif "Hand:" in line and user:
                card_ids = _extract_card_ids(line)
                if pidx:
                    players[pidx].hand = list(card_ids)
                    if just_ended_turn and turns:
                        key = "hand" if pidx == turns[-1].player_idx else "opp_hand"
                        turns[-1].state_end[key] = list(card_ids)
            elif "Board:" in line and user:
                card_ids = _extract_card_ids(line)
                if pidx:
                    players[pidx].board = list(card_ids)
                    if just_ended_turn and turns:
                        key = "board" if pidx == turns[-1].player_idx else "opp_board"
                        turns[-1].state_end[key] = list(card_ids)
            elif "Trash:" in line and user:
                card_ids = _extract_card_ids(line)
                if pidx:
                    players[pidx].trash = list(card_ids)
                    if just_ended_turn and turns:
                        key = "trash" if pidx == turns[-1].player_idx else "opp_trash"
                        turns[-1].state_end[key] = list(card_ids)
            elif "Life:" in line and user:
                m = re.search(r"Life:\s*(\d+)", line)
                if m and pidx:
                    life_val = int(m.group(1))
                    players[pidx].life = life_val
                    if just_ended_turn and turns:
                        key = "life" if pidx == turns[-1].player_idx else "opp_life"
                        turns[-1].state_end[key] = life_val
            elif "Mulligan" in line:
                pass
            elif "Deploy" in line:
                card_ids = _extract_card_ids(line)
                if card_ids and pidx:
                    cid = card_ids[0]
                    if cid in players[pidx].hand:
                        players[pidx].hand.remove(cid)
                    players[pidx].board.append(cid)
                    current_actions.append(Action(
                        type="deploy", actor=user, card_id=card_ids[0],
                        cost=None, power=None, counter_value=None,
                        effect_text=None, result=None,
                    ))
            elif "Attach" in line and "Don" in line:
                current_actions.append(Action(
                    type="don_attach", actor=user, card_id=None,
                    cost=None, power=None, counter_value=None,
                    effect_text=line, result=None,
                ))
            elif "attacking" in line:
                card_ids = _extract_card_ids(line)
                atk_id = card_ids[0] if card_ids else None
                def_id = card_ids[1] if len(card_ids) > 1 else None
                current_actions.append(Action(
                    type="attack", actor=user, card_id=atk_id,
                    target_card_id=def_id, cost=None, power=None,
                    counter_value=None, effect_text=None, result=None,
                ))
                if pidx:
                    last_attacker_idx = pidx
                    defender_idx = 2 if pidx == 1 else 1
                    last_attack_defender_idx = defender_idx
                    defender = players.get(defender_idx)
                    last_attack_target_is_leader = (
                        def_id is not None
                        and defender is not None
                        and defender.leader_id == def_id
                    )
            elif "vs" in line and "[" in line:
                powers = re.findall(r"\[(\d+)\]", line)
                card_ids = _extract_card_ids(line)
                if card_ids and len(card_ids) >= 2:
                    current_actions.append(Action(
                        type="attack_resolve", actor=user,
                        card_id=card_ids[0], target_card_id=card_ids[1],
                        cost=None, power=int(powers[0]) if powers else None,
                        counter_value=int(powers[1]) if len(powers) > 1 else None,
                        effect_text=None, result=None,
                    ))
            elif "hit for" in line and "damage" in line:
                m_dmg = re.search(r"hit for\s+(\d+)\s+damage", line, re.IGNORECASE)
                dmg_amount = int(m_dmg.group(1)) if m_dmg else 1
                current_actions.append(Action(
                    type="damage", actor=user, card_id=None,
                    target_card_id=None, cost=None, power=None,
                    counter_value=None, amount=dmg_amount,
                    effect_text=None, result="damage",
                ))
                if (
                    last_attack_target_is_leader
                    and last_attack_defender_idx is not None
                ):
                    defender = players.get(last_attack_defender_idx)
                    if defender and defender.life is not None:
                        defender.life = max(defender.life - dmg_amount, 0)
            elif "Attack Fails" in line:
                current_actions.append(Action(
                    type="attack_fail", actor=user, card_id=None,
                    target_card_id=None, cost=None, power=None,
                    counter_value=None, effect_text=None,
                    result="failed",
                ))
            elif "Destroyed" in line:
                current_actions.append(Action(
                    type="destroy", actor=user, card_id=None,
                    target_card_id=None, cost=None, power=None,
                    counter_value=None, effect_text=None,
                    result="destroyed",
                ))
            elif "Discard" in line and "Counter" in line:
                card_ids = _extract_card_ids(line)
                m = re.search(r"Counter\s+(\d+)", line)
                counter_val = int(m.group(1)) if m else None
                current_actions.append(Action(
                    type="counter", actor=user,
                    card_id=card_ids[0] if card_ids else None,
                    cost=None, power=None, counter_value=counter_val,
                    effect_text=None, result=None,
                ))
            elif "Activate Trigger" in line:
                card_ids = _extract_card_ids(line)
                current_actions.append(Action(
                    type="trigger", actor=user,
                    card_id=card_ids[0] if card_ids else None,
                    cost=None, power=None, counter_value=None,
                    effect_text="trigger", result=None,
                ))
            elif ":" in line and user and any(
                kw in line for kw in [
                    "Draw", "Trash", "Reveal", "Rest", "Give Rush",
                    "Deployed", "Minus", "Buff", "KO", "Banish",
                    "Search", "Play", "Add", "Don",
                ]
            ):
                card_ids = _extract_card_ids(line)
                current_actions.append(Action(
                    type="effect", actor=user,
                    card_id=card_ids[0] if card_ids else None,
                    cost=None, power=None, counter_value=None,
                    effect_text=line, result=None,
                ))
            elif "End Turn" in line:
                turn_no += 1
                if pidx is None and current_player_idx is not None:
                    pidx = current_player_idx
                if pidx is not None:
                    current_player_idx = 1 - pidx + 2
                else:
                    if current_player_idx is None:
                        current_player_idx = 1
                    else:
                        current_player_idx = (
                            1 if current_player_idx == 2 else 2
                        )

                acting_player = pidx if pidx is not None else (current_player_idx or 1)
                opp_player = 2 if acting_player == 1 else 1

                drawn = turn_don_drawn.get(acting_player, 0)
                on_field = players[acting_player].don_on_field
                snap = players[acting_player].snapshot()
                opp = players.get(opp_player)
                if opp:
                    snap["opp_hand"] = list(opp.hand)
                    snap["opp_board"] = list(opp.board)
                    snap["opp_trash"] = list(opp.trash)
                    snap["opp_life"] = opp.life
                    snap["opp_don_active"] = opp.don_active
                    snap["opp_don_rested"] = opp.don_rested
                    snap["opp_don_on_field"] = opp.don_on_field
                turns.append(Turn(
                    turn_no=turn_no,
                    player_idx=acting_player,
                    don_drawn=drawn,
                    don_available=max(on_field - drawn, 0),
                    don_unused_at_end=on_field,
                    actions=list(current_actions),
                    errors=[],
                    state_end=snap,
                ))
                current_actions = []
                turn_don_drawn[acting_player] = 0
                don_text_player_idx = None
                just_ended_turn = True
                # Refresh next player's rested DON at start of their turn
                players[opp_player].don_active += players[opp_player].don_rested
                players[opp_player].don_rested = 0
            elif "Concedes" in line or "Abandonn" in line:
                pidx_concede = user_to_idx.get(user)
                if pidx_concede:
                    winner_idx = 2 if pidx_concede == 1 else 1
                else:
                    winner_idx = last_attacker_idx
                reason = "concede"
            elif "Out of Cards" in line or "Loses the Game" in line:
                pidx_lose = user_to_idx.get(user)
                if pidx_lose:
                    winner_idx = 2 if pidx_lose == 1 else 1
                else:
                    winner_idx = last_attacker_idx
                reason = "deck_out"
            elif "GameOver" in line:
                if last_attacker_idx is not None:
                    winner_idx = last_attacker_idx
                reason = "gameover"
            elif "Downloaded the Combat Log" in line:
                pass
            elif "OpponentDisconnect" in line or "Opponent Has Disconnected" in line:
                if winner_idx is None:
                    for idx, ps in players.items():
                        if ps.is_self:
                            winner_idx = idx
                            break
                    if winner_idx is None:
                        winner_idx = last_attacker_idx
                if reason is None:
                    reason = "disconnect"
            elif "Quits" in line:
                if user:
                    quit_idx = user_to_idx.get(user)
                    if quit_idx and winner_idx is None:
                        winner_idx = 2 if quit_idx == 1 else 1
                        reason = "quit"
            elif "PlayerTurn_Action" in line:
                pass

            if just_ended_turn and user:
                is_state_line = any(
                    kw in line for kw in
                    ["Hand:", "Board:", "Trash:", "Life:", "End Turn"]
                )
                if not is_state_line:
                    just_ended_turn = False

            if user and pidx:
                current_player_idx = pidx

        match_id = room_id or f"match_{len(turns)}"

        if winner_idx is None:
            p1_life = players[1].life
            p2_life = players[2].life
            if p1_life is not None and p2_life is not None:
                if p1_life == 0 and p2_life > 0:
                    winner_idx = 2
                    reason = "life"
                elif p2_life == 0 and p1_life > 0:
                    winner_idx = 1
                    reason = "life"
                elif p1_life == 0 and p2_life == 0:
                    if last_attacker_idx is not None:
                        winner_idx = last_attacker_idx
                        reason = "life"

        player_list = []
        for idx in [1, 2]:
            ps = players[idx]
            if ps.user:
                player_list.append(Player(
                    user=ps.user,
                    leader_card_id=ps.leader_id or "",
                    goes_first=ps.goes_first,
                    is_self=ps.is_self,
                ))

        domain_match = Match(
            match_id=match_id,
            room_id=room_id,
            version=version,
            source_file=source_file,
            players=player_list,
            turns=turns,
            winner_idx=winner_idx,
            reason=reason,
            duration_turns=len(turns) if turns else None,
        )
        return domain_match
