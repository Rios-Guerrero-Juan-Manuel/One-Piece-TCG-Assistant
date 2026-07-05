import logging
import math
import re
from dataclasses import dataclass, field

from app.infrastructure.api_client.optcg_meta_client import (
    OptcgMetaClient,
    build_card_image_url,
)

logger = logging.getLogger(__name__)

MIN_MATCHES_THRESHOLD = 25
MIN_MATCHUP_GAMES = 10
MIN_MATCHUP_COVERAGE = 8

_TIER_ORDER = ["S", "A", "B", "C", "D"]

_VIEW_THRESHOLDS = {
    "winrate": [("S", 53.0), ("A", 51.0), ("B", 49.0), ("C", 47.0)],
}

_PERCENTILE_BOUNDS = {
    "overall": [("S", 0.10), ("A", 0.30), ("B", 0.60), ("C", 0.85)],
    "steady": [("S", 0.10), ("A", 0.30), ("B", 0.60), ("C", 0.85)],
}


def _strip_prefix(raw: str) -> str:
    return re.sub(r"^\d+x", "", raw)


@dataclass
class LeaderStat:
    card_id: str
    name: str
    image_url: str
    wins: int
    losses: int
    matches: int
    winrate: float
    bayesian_winrate: float
    tier: str = ""
    presence: float = 0.0
    avg_matchup_wr: float = 50.0
    balance_score: float = 50.0
    overall_score: float = 50.0


@dataclass
class GlobalMetaResult:
    leaders: list[LeaderStat] = field(default_factory=list)
    tiers: dict[str, list[str]] = field(default_factory=lambda: {k: [] for k in _TIER_ORDER})
    total_matches: int = 0
    total_wins: int = 0
    total_losses: int = 0
    timestamp: str = ""
    region: str = ""
    ranking: str = ""
    game_mode: str = ""


class GlobalMetaService:
    def __init__(self, client: OptcgMetaClient | None = None):
        self.client = client or OptcgMetaClient()

    def get_global_meta(
        self,
        region: str = "west",
        view: str = "overall",
        turn_order: str = "combined",
    ) -> GlobalMetaResult:
        raw = self.client.get_stats(region)
        cards_data = self.client.get_cards_data()
        return self._build(raw, cards_data, region, view, turn_order)

    def get_matchup_matrix(
        self,
        region: str = "west",
        turn_order: str = "combined",
    ) -> dict:
        raw = self.client.get_stats(region)
        leaders = raw.get("leaders_presence", [])
        card_ids: list[str] = []
        lookup: dict[str, dict] = {}
        for entry in leaders:
            cid = _strip_prefix(entry.get("leader", ""))
            if entry.get("first_wins", 0) + entry.get("first_losses", 0) + \
               entry.get("second_wins", 0) + entry.get("second_losses", 0) < MIN_MATCHES_THRESHOLD:
                continue
            if cid not in lookup:
                lookup[cid] = entry
                card_ids.append(cid)

        matrix: dict[str, dict[str, float | None]] = {}
        for cid in card_ids:
            entry = lookup[cid]
            subjects = entry.get("subject", [])
            row: dict[str, float | None] = {}
            for i, subj_raw in enumerate(subjects):
                opp_id = _strip_prefix(subj_raw)
                if opp_id == cid:
                    continue
                if opp_id not in lookup:
                    continue
                fw = entry.get("subject_first_wins", [])
                fl = entry.get("subject_first_losses", [])
                sw = entry.get("subject_second_wins", [])
                sl = entry.get("subject_second_losses", [])
                w, lo = self._pick_turn(i, fw, fl, sw, sl, turn_order)
                total = w + lo
                if total < MIN_MATCHUP_GAMES:
                    row[opp_id] = None
                else:
                    row[opp_id] = round(w / total * 100, 1)
            matrix[cid] = row
        return matrix

    def _build(
        self,
        raw: dict,
        cards_data: dict[str, dict],
        region: str,
        view: str,
        turn_order: str,
    ) -> GlobalMetaResult:
        leaders_raw = raw.get("leaders_presence", [])
        base_url = self.client.base_url
        stats_list: list[LeaderStat] = []

        for entry in leaders_raw:
            fw = entry.get("first_wins", 0)
            fl = entry.get("first_losses", 0)
            sw = entry.get("second_wins", 0)
            sl = entry.get("second_losses", 0)
            wins, losses = self._sum_turn(fw, fl, sw, sl, turn_order)
            matches = wins + losses
            if matches < MIN_MATCHES_THRESHOLD:
                continue
            cid = _strip_prefix(entry.get("leader", ""))
            if cid.startswith("Mobile"):
                continue
            card_info = cards_data.get(cid, {})
            name = card_info.get("name", cid)
            wr = wins / matches * 100 if matches > 0 else 0.0
            bayes = (wins + 15) / (matches + 30) * 100

            subjects = entry.get("subject", [])
            sfw = entry.get("subject_first_wins", [])
            sfl = entry.get("subject_first_losses", [])
            ssw = entry.get("subject_second_wins", [])
            ssl = entry.get("subject_second_losses", [])
            matchup_wrs: list[float] = []
            for i, subj_raw in enumerate(subjects):
                opp_id = _strip_prefix(subj_raw)
                if opp_id == cid:
                    continue
                mw, ml = self._pick_turn(i, sfw, sfl, ssw, ssl, turn_order)
                m_total = mw + ml
                if m_total >= MIN_MATCHUP_GAMES:
                    matchup_wrs.append(mw / m_total * 100)

            avg_mwr = sum(matchup_wrs) / len(matchup_wrs) if matchup_wrs else 50.0
            if len(matchup_wrs) > 1:
                mean = avg_mwr
                variance = sum((x - mean) ** 2 for x in matchup_wrs) / len(matchup_wrs)
                std = math.sqrt(variance)
            else:
                std = 0.0
            balance = avg_mwr - 1.5 * std
            overall = 0.6 * bayes + 0.4 * balance

            stat = LeaderStat(
                card_id=cid,
                name=name,
                image_url=build_card_image_url(base_url, cid),
                wins=wins,
                losses=losses,
                matches=matches,
                winrate=round(wr, 1),
                bayesian_winrate=round(bayes, 1),
                avg_matchup_wr=round(avg_mwr, 1),
                balance_score=round(balance, 1),
                overall_score=round(overall, 1),
            )
            stats_list.append(stat)

        total_matches = sum(s.matches for s in stats_list)
        total_wins = sum(s.wins for s in stats_list)
        total_losses = sum(s.losses for s in stats_list)

        tiers = self._compute_tiers(stats_list, view)
        for stat in stats_list:
            stat.tier = ""
        for tier_name, ids in tiers.items():
            for cid in ids:
                for s in stats_list:
                    if s.card_id == cid:
                        s.tier = tier_name
                        break

        return GlobalMetaResult(
            leaders=stats_list,
            tiers=tiers,
            total_matches=total_matches,
            total_wins=total_wins,
            total_losses=total_losses,
            timestamp=raw.get("timestamp", ""),
            region=region,
            ranking=raw.get("ranking", ""),
            game_mode=raw.get("game_mode", ""),
        )

    def _compute_tiers(
        self, stats: list[LeaderStat], view: str
    ) -> dict[str, list[str]]:
        tiers: dict[str, list[str]] = {k: [] for k in _TIER_ORDER}
        if not stats:
            return tiers

        if view in _PERCENTILE_BOUNDS:
            if view == "overall":
                ranked = sorted(stats, key=lambda s: s.overall_score, reverse=True)
            else:
                ranked = sorted(stats, key=lambda s: s.balance_score, reverse=True)
            n = len(ranked)
            bounds = _PERCENTILE_BOUNDS[view]
            idx = 0
            for tier_name, pct in bounds:
                cutoff = max(1, int(round(n * pct)))
                slice_ids = [s.card_id for s in ranked[idx : idx + (cutoff - idx)]]
                tiers[tier_name] = slice_ids
                idx = cutoff
            tiers["D"] = [s.card_id for s in ranked[idx:]]
        else:
            thresholds = _VIEW_THRESHOLDS.get("winrate")
            for s in sorted(stats, key=lambda x: x.winrate, reverse=True):
                assigned = "D"
                for tier_name, threshold in thresholds:
                    if s.winrate >= threshold:
                        assigned = tier_name
                        break
                tiers[assigned].append(s.card_id)

        return tiers

    @staticmethod
    def _sum_turn(fw, fl, sw, sl, turn_order: str) -> tuple[int, int]:
        if turn_order == "first":
            return fw, fl
        if turn_order == "second":
            return sw, sl
        return fw + sw, fl + sl

    @staticmethod
    def _pick_turn(i, fw, fl, sw, sl, turn_order: str) -> tuple[int, int]:
        def _safe(arr, idx):
            return arr[idx] if idx < len(arr) else 0
        if turn_order == "first":
            return _safe(fw, i), _safe(fl, i)
        if turn_order == "second":
            return _safe(sw, i), _safe(sl, i)
        return _safe(fw, i) + _safe(sw, i), _safe(fl, i) + _safe(sl, i)
