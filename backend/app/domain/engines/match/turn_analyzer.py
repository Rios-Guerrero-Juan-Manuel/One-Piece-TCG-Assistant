from app.domain.models import Turn


class TurnAnalyzer:
    """Analyzes match turns and detects suboptimal decisions."""

    def _analyze_single(self, turn: Turn) -> list[str]:
        """Analyze a single turn and return list of issues found."""
        issues: list[str] = []

        deploy_count = sum(1 for a in turn.actions if a.type == "deploy")

        for action in turn.actions:
            if action.type == "deploy":
                continue
            if action.type == "attack_resolve":
                power = action.power
                defender = action.counter_value
                if (
                    power is not None
                    and defender is not None
                    and power < defender
                ):
                    issues.append(
                        f"Inefficient attack: {action.card_id} ({power}) "
                        f"vs {action.target_card_id} ({defender})"
                    )
            elif action.type == "counter":
                counter_value = action.counter_value
                attacking_power = action.power
                if (
                    counter_value is not None
                    and counter_value == 1000
                    and attacking_power is not None
                    and attacking_power > 5000
                ):
                    issues.append(
                        f"Low counter ({counter_value}) against "
                        f"high power attack"
                    )

        hand = turn.state_end.get("hand")
        if isinstance(hand, list):
            hand_size = len(hand)
            if hand_size > 7:
                issues.append(f"Large hand: {hand_size} cards")

        if deploy_count > 4:
            issues.append(
                f"Over-commit: {deploy_count} characters deployed in one turn"
            )

        if turn.turn_no <= 2 and deploy_count == 0:
            issues.append(
                f"No characters deployed in early turn {turn.turn_no}"
            )

        return issues

    def analyze_turn(self, turn: Turn) -> list[str]:
        """Analyze a single turn (backward compat wrapper)."""
        issues = self._analyze_single(turn)
        turn.errors = issues
        return issues

    def analyze_turns(self, turns: list[Turn]) -> None:
        """Analyze all turns with cross-turn context.

        Extends per-turn analysis with floated DON detection:
        if a player ends their turn with active DON that is still
        active at the end of the opponent's following turn, that DON
        was never used for defense and is considered floated.
        """
        for i, turn in enumerate(turns):
            issues = self._analyze_single(turn)

            # Cross-turn floated DON detection
            if i + 1 < len(turns):
                next_turn = turns[i + 1]
                don_active = turn.state_end.get("don_active", 0)
                opp_don_active_next = next_turn.state_end.get(
                    "opp_don_active", 0
                )
                if don_active > 0 and opp_don_active_next >= don_active:
                    issues.append(
                        f"Floated DON: {don_active} active DON "
                        f"left unused during opponent's turn"
                    )

            turn.errors = issues
