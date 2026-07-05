from app.domain.models import Match


class PatternDetector:
    """Detects behavioral patterns from match history (domain pure logic)."""

    def detect_patterns(self, matches: list[Match]) -> list[dict]:
        """Analyze matches and detect behavioral patterns. Returns list of pattern dicts."""
        if not matches:
            return []
        patterns: list[dict] = []
        patterns.extend(self._detect_early_loss(matches))
        patterns.extend(self._detect_low_early_pressure(matches))
        patterns.extend(self._detect_large_hand(matches))
        patterns.extend(self._detect_don_inefficient(matches))
        patterns.extend(self._detect_very_early_loss(matches))
        patterns.extend(self._detect_counter_heavy(matches))
        return patterns

    @staticmethod
    def _self_idx(match: Match) -> int | None:
        for i, p in enumerate(match.players):
            if p.is_self:
                return i
        return None

    def _losses(self, matches: list[Match]) -> list[Match]:
        out: list[Match] = []
        for m in matches:
            self_idx = self._self_idx(m)
            if m.winner_idx is None or self_idx is None:
                continue
            if m.winner_idx != self_idx:
                out.append(m)
        return out

    def _detect_early_loss(self, matches: list[Match]) -> list[dict]:
        losses = self._losses(matches)
        if not losses:
            return []
        early = sum(
            1 for m in losses if m.duration_turns is not None and m.duration_turns < 5
        )
        pct = round((early / len(losses)) * 100, 1)
        if pct > 40:
            return [
                {
                    "pattern_id": "weakness_vs_aggro",
                    "filter": {"type": "early_loss", "threshold": 5, "pct": pct},
                    "description": (
                        f"Losing {pct}% of matches before turn 5 "
                        f"— vulnerable to aggressive decks"
                    ),
                    "severity": "high",
                }
            ]
        return []

    def _detect_low_early_pressure(self, matches: list[Match]) -> list[dict]:
        early_turns = 0
        no_deploy = 0
        for m in matches:
            for t in m.turns:
                if t.turn_no <= 2:
                    early_turns += 1
                    if not any(a.type == "deploy" for a in t.actions):
                        no_deploy += 1
        if early_turns == 0:
            return []
        pct = round((no_deploy / early_turns) * 100, 1)
        if pct > 50:
            return [
                {
                    "pattern_id": "low_early_pressure",
                    "filter": {"type": "low_early_pressure", "pct": pct},
                    "description": (
                        f"No characters deployed in first 2 turns {pct}% of the time"
                    ),
                    "severity": "medium",
                }
            ]
        return []

    def _detect_large_hand(self, matches: list[Match]) -> list[dict]:
        hand_sizes: list[int] = []
        for m in matches:
            for t in m.turns:
                hand = t.state_end.get("hand")
                if isinstance(hand, list):
                    hand_sizes.append(len(hand))
        if not hand_sizes:
            return []
        avg = round(sum(hand_sizes) / len(hand_sizes), 1)
        if avg > 7:
            return [
                {
                    "pattern_id": "excess_dead_cards",
                    "filter": {"type": "large_hand", "avg": avg},
                    "description": f"Average hand size {avg} — potential dead cards",
                    "severity": "medium",
                }
            ]
        return []

    def _detect_don_inefficient(self, matches: list[Match]) -> list[dict]:
        don_vals = [t.don_unused_at_end for m in matches for t in m.turns]
        if not don_vals:
            return []
        avg = round(sum(don_vals) / len(don_vals), 1)
        if avg > 2:
            return [
                {
                    "pattern_id": "don_inefficiency",
                    "filter": {"type": "don_inefficient", "avg": avg},
                    "description": (
                        f"Average {avg} DON unused per turn — wasted resources"
                    ),
                    "severity": "medium",
                }
            ]
        return []

    def _detect_very_early_loss(self, matches: list[Match]) -> list[dict]:
        losses = self._losses(matches)
        if not losses:
            return []
        very_early = sum(
            1 for m in losses if m.duration_turns is not None and m.duration_turns <= 3
        )
        pct = round((very_early / len(losses)) * 100, 1)
        if pct > 30:
            return [
                {
                    "pattern_id": "early_defeats",
                    "filter": {"type": "very_early_loss", "threshold": 3, "pct": pct},
                    "description": (
                        f"Losing {pct}% of matches by turn 3 — deck too slow"
                    ),
                    "severity": "high",
                }
            ]
        return []

    def _detect_counter_heavy(self, matches: list[Match]) -> list[dict]:
        counters = 0
        defenses = 0
        for m in matches:
            for t in m.turns:
                for a in t.actions:
                    if a.type == "counter":
                        counters += 1
                        defenses += 1
                    elif a.type in ("block", "defense"):
                        defenses += 1
        if defenses == 0:
            return []
        pct = round((counters / defenses) * 100, 1)
        if pct > 60:
            return [
                {
                    "pattern_id": "counter_dependency",
                    "filter": {"type": "counter_heavy", "pct": pct},
                    "description": (
                        f"Heavy counter usage ({pct}%) — may lack board presence"
                    ),
                    "severity": "low",
                }
            ]
        return []
