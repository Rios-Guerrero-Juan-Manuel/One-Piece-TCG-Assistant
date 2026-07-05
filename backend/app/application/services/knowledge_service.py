import hashlib
import logging

from app.application.services.stats_service import StatsService

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Generates statistically verified insights from match data.

    Insights are NOT LLM hallucinations — they are computed from real stats.
    Each insight is persisted in the insights table.
    """

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def generate_insights(self) -> list[dict]:
        from app.infrastructure.persistence.models import InsightORM

        stats_service = StatsService(self.session_factory)
        stats = stats_service.compute_all_stats()

        insights = self._build_insights(stats)
        session = self.session_factory()
        try:
            new_ids = {doc["doc_id"] for doc in insights}
            stale = (
                session.query(InsightORM)
                .filter(
                    InsightORM.type == "insight",
                    ~InsightORM.doc_id.in_(new_ids),
                )
                .all()
            )
            for doc in stale:
                session.delete(doc)
            for doc in insights:
                content_hash = hashlib.sha256(
                    doc["content"].encode()
                ).hexdigest()[:16]
                existing = session.get(InsightORM, doc["doc_id"])
                if existing:
                    existing.title = doc["title"]
                    existing.content = doc["content"]
                    existing.hash = content_hash
                else:
                    session.add(InsightORM(
                        doc_id=doc["doc_id"],
                        source="auto",
                        title=doc["title"],
                        type="insight",
                        content=doc["content"],
                        hash=content_hash,
                    ))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        return insights

    def get_insights(self) -> list[dict]:
        from app.infrastructure.persistence.models import InsightORM

        session = self.session_factory()
        try:
            docs = (
                session.query(InsightORM)
                .filter(InsightORM.type == "insight")
                .all()
            )
            return [
                {
                    "doc_id": d.doc_id,
                    "title": d.title,
                    "content": d.content,
                    "hash": d.hash,
                    "expandable": d.doc_id.endswith("_summary"),
                }
                for d in docs
            ]
        finally:
            session.close()

    def _build_insights(self, stats: dict) -> list[dict]:
        insights: list[dict] = []
        total = stats.get("total_matches", 0)

        if total < 5:
            return insights

        winrate = stats.get("winrate", 0)
        winrate_text = (
            f"Your overall winrate is {winrate}% across {total} matches. "
        )
        if winrate < 40:
            winrate_text += "This is below average — consider adjusting your deck."
        elif winrate > 60:
            winrate_text += "Strong performance — your strategy is effective."
        insights.append({
            "doc_id": "insight_winrate",
            "title": f"Overall Winrate: {winrate}%",
            "content": winrate_text,
        })

        leaders_used = stats.get("leaders_used", {})
        winrate_by_leader = stats.get("winrate_by_leader", {})
        leader_wins = stats.get("leader_wins", {})

        qualified = [
            (leader, count)
            for leader, count in leaders_used.items()
            if count >= 3 and leader in winrate_by_leader
        ]
        qualified.sort(key=lambda x: winrate_by_leader[x[0]], reverse=True)

        if qualified:
            best_leader, best_count = qualified[0]
            best_wr = winrate_by_leader[best_leader]
            best_wins = leader_wins.get(best_leader, 0)
            best_losses = best_count - best_wins
            insights.append({
                "doc_id": "insight_leader_best",
                "title": f"Best Leader: {best_leader} ({best_wr}% WR)",
                "content": (
                    f"Your best leader is {best_leader} with a {best_wr}% winrate "
                    f"({best_wins}W / {best_losses}L) over {best_count} matches."
                ),
            })

        if len(qualified) >= 2:
            worst_leader, worst_count = qualified[-1]
            worst_wr = winrate_by_leader[worst_leader]
            worst_wins = leader_wins.get(worst_leader, 0)
            worst_losses = worst_count - worst_wins
            worst_text = (
                f"Your weakest leader is {worst_leader} with a {worst_wr}% winrate "
                f"({worst_wins}W / {worst_losses}L) over {worst_count} matches."
            )
            if worst_wr < 35:
                worst_text += " Consider switching leaders or refining the deck."
            insights.append({
                "doc_id": "insight_leader_worst",
                "title": f"Worst Leader: {worst_leader} ({worst_wr}% WR)",
                "content": worst_text,
            })

        if qualified:
            lines = []
            for leader, count in qualified:
                wr = winrate_by_leader[leader]
                wins = leader_wins.get(leader, 0)
                losses = count - wins
                lines.append(
                    f"{leader}: {wr}% WR ({wins}W / {losses}L) over {count} matches"
                )
            insights.append({
                "doc_id": "insight_leader_summary",
                "title": "Leader Performance Summary",
                "content": "\n".join(lines),
                "expandable": True,
            })

        matchup = stats.get("winrate_by_matchup", {})
        worst_key = None
        worst_wr = 100
        for key, wr in matchup.items():
            if wr < worst_wr and wr < 50:
                parts = key.split("_vs_")
                if len(parts) == 2:
                    worst_key = key
                    worst_wr = wr
        if worst_key:
            parts = worst_key.split("_vs_")
            insights.append({
                "doc_id": "insight_worst_matchup",
                "title": f"Worst Matchup: {parts[0]} vs {parts[1]}",
                "content": (
                    f"Your weakest matchup is {parts[0]} vs {parts[1]} "
                    f"({worst_wr}% winrate). Consider tech cards for this matchup."
                ),
            })

        avg_don = stats.get("avg_don_unused", 0)
        don_text = (
            f"You leave an average of {avg_don} DON unused per turn. "
        )
        if avg_don > 2:
            don_text += "Consider adding more proactive plays to utilize DON efficiently."
        else:
            don_text += "Your DON efficiency is excellent."
        insights.append({
            "doc_id": "insight_don_efficiency",
            "title": f"DON Efficiency: {avg_don} avg unused",
            "content": don_text,
        })

        avg_duration = stats.get("avg_duration_turns", 0)
        if avg_duration > 0:
            dur_text = f"Your matches average {avg_duration} turns. "
            if avg_duration > 12:
                dur_text += (
                    "Longer than typical — consider more aggressive "
                    "closing conditions."
                )
            elif avg_duration < 6:
                dur_text += (
                    "Very fast — ensure you have sufficient early "
                    "game stability."
                )
            insights.append({
                "doc_id": "insight_duration",
                "title": f"Match Duration: {avg_duration} avg turns",
                "content": dur_text,
            })

        most_played = stats.get("most_played_cards", [])
        if most_played:
            top3 = most_played[:3]
            card_str = ", ".join(
                f"{c['card_id']} ({c['count']}x)" for c in top3
            )
            insights.append({
                "doc_id": "insight_most_played",
                "title": "Most Played Cards",
                "content": f"Your most played cards are: {card_str}.",
            })

        return insights
