from pydantic import BaseModel, ConfigDict


class MostPlayedCard(BaseModel):
    card_id: str
    count: int


class StatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_matches: int
    winrate: float
    winrate_by_leader: dict[str, float]
    leader_wins: dict[str, int] = {}
    leader_totals: dict[str, int] = {}
    winrate_by_matchup: dict[str, float]
    winrate_by_deck: dict[str, float] = {}
    winrate_by_deck_vs_opp_leader: dict[str, dict[str, float]] = {}
    deck_vs_opp_leader_totals: dict[str, dict[str, int]] = {}
    avg_duration_turns: float
    most_played_cards: list[MostPlayedCard]
    avg_don_unused: float
    leaders_used: dict[str, int]
    card_names: dict[str, str] = {}
    deck_names: dict[str, str] = {}


class MatchupStatsResponse(BaseModel):
    self_leader: str
    opp_leader: str
    winrate: float
