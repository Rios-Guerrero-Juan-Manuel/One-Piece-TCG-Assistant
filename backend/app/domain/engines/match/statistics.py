from app.domain.models import Match


class StatisticsEngine:
    """Computes aggregate statistics from match data."""

    def compute_stats(self, matches: list[Match]) -> dict:
        total = len(matches)
        if total == 0:
            return self._empty_stats()

        wins = 0
        leader_wins: dict[str, int] = {}
        leader_totals: dict[str, int] = {}
        matchup_wins: dict[str, int] = {}
        matchup_totals: dict[str, int] = {}
        deck_wins: dict[str, int] = {}
        deck_totals: dict[str, int] = {}
        deck_opp_wins: dict[str, dict[str, int]] = {}
        deck_opp_totals: dict[str, dict[str, int]] = {}
        leaders_used: dict[str, int] = {}

        duration_sum = 0
        duration_count = 0
        don_unused_sum = 0
        turn_count = 0
        card_counts: dict[str, int] = {}

        for match in matches:
            self_idx, self_leader, opp_leader, deck_id = self._extract_self_and_opp(match)

            if self_leader is not None:
                leaders_used[self_leader] = leaders_used.get(self_leader, 0) + 1
                leader_totals[self_leader] = leader_totals.get(self_leader, 0) + 1
                matchup_key = self._matchup_key(self_leader, opp_leader)
                matchup_totals[matchup_key] = matchup_totals.get(matchup_key, 0) + 1

            if deck_id is not None:
                deck_totals[deck_id] = deck_totals.get(deck_id, 0) + 1
                if opp_leader is not None:
                    deck_opp_totals.setdefault(deck_id, {})
                    deck_opp_totals[deck_id][opp_leader] = (
                        deck_opp_totals[deck_id].get(opp_leader, 0) + 1
                    )

            is_win = (
                self_idx is not None
                and match.winner_idx is not None
                and match.winner_idx == self_idx
            )
            if is_win:
                wins += 1
                if self_leader is not None:
                    leader_wins[self_leader] = leader_wins.get(self_leader, 0) + 1
                    matchup_key = self._matchup_key(self_leader, opp_leader)
                    matchup_wins[matchup_key] = matchup_wins.get(matchup_key, 0) + 1
                if deck_id is not None:
                    deck_wins[deck_id] = deck_wins.get(deck_id, 0) + 1
                    if opp_leader is not None:
                        deck_opp_wins.setdefault(deck_id, {})
                        deck_opp_wins[deck_id][opp_leader] = (
                            deck_opp_wins[deck_id].get(opp_leader, 0) + 1
                        )

            if match.duration_turns is not None:
                duration_sum += match.duration_turns
                duration_count += 1

            for turn in match.turns:
                don_unused_sum += turn.don_unused_at_end
                turn_count += 1
                for action in turn.actions:
                    if action.type == "deploy" and action.card_id:
                        card_counts[action.card_id] = card_counts.get(action.card_id, 0) + 1

        winrate = round((wins / total) * 100, 2)
        winrate_by_leader = {
            leader: round((leader_wins.get(leader, 0) / leader_totals[leader]) * 100, 2)
            for leader in leader_totals
        }
        winrate_by_matchup = {
            matchup: round((matchup_wins.get(matchup, 0) / matchup_totals[matchup]) * 100, 2)
            for matchup in matchup_totals
        }
        avg_duration = round(duration_sum / duration_count, 2) if duration_count > 0 else 0
        avg_don_unused = round(don_unused_sum / turn_count, 2) if turn_count > 0 else 0
        sorted_cards = sorted(card_counts.items(), key=lambda x: (-x[1], x[0]))
        most_played_cards = [
            {"card_id": cid, "count": cnt} for cid, cnt in sorted_cards[:10]
        ]

        winrate_by_deck = {
            deck: round((deck_wins.get(deck, 0) / deck_totals[deck]) * 100, 2)
            for deck in deck_totals
        }

        winrate_by_deck_vs_opp_leader = {
            deck: {
                opp: round(
                    (deck_opp_wins.get(deck, {}).get(opp, 0) / total) * 100, 2
                )
                for opp, total in deck_opp_totals[deck].items()
            }
            for deck in deck_opp_totals
        }
        deck_vs_opp_leader_totals = {
            deck: dict(totals) for deck, totals in deck_opp_totals.items()
        }

        return {
            "total_matches": total,
            "winrate": winrate,
            "winrate_by_leader": winrate_by_leader,
            "leader_wins": dict(leader_wins),
            "leader_totals": dict(leader_totals),
            "winrate_by_matchup": winrate_by_matchup,
            "winrate_by_deck": winrate_by_deck,
            "winrate_by_deck_vs_opp_leader": winrate_by_deck_vs_opp_leader,
            "deck_vs_opp_leader_totals": deck_vs_opp_leader_totals,
            "avg_duration_turns": avg_duration,
            "most_played_cards": most_played_cards,
            "avg_don_unused": avg_don_unused,
            "leaders_used": leaders_used,
        }

    @staticmethod
    def _empty_stats() -> dict:
        return {
            "total_matches": 0,
            "winrate": 0,
            "winrate_by_leader": {},
            "leader_wins": {},
            "leader_totals": {},
            "winrate_by_matchup": {},
            "winrate_by_deck": {},
            "winrate_by_deck_vs_opp_leader": {},
            "deck_vs_opp_leader_totals": {},
            "avg_duration_turns": 0,
            "most_played_cards": [],
            "avg_don_unused": 0,
            "leaders_used": {},
        }

    @staticmethod
    def _extract_self_and_opp(
        match: Match,
    ) -> tuple[int | None, str | None, str | None, str | None]:
        self_idx = None
        self_leader = None
        opp_leader = None
        deck_id = getattr(match, "deck_id_self", None)
        for i, p in enumerate(match.players):
            if p.is_self:
                self_idx = i
                self_leader = p.leader_card_id
            else:
                opp_leader = p.leader_card_id
        return self_idx, self_leader, opp_leader, deck_id

    @staticmethod
    def _matchup_key(self_leader: str | None, opp_leader: str | None) -> str:
        self_part = self_leader or "Unknown"
        opp_part = opp_leader or "Unknown"
        return f"{self_part}_vs_{opp_part}"
