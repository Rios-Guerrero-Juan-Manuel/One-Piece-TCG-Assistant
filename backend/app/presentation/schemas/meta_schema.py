from pydantic import BaseModel, ConfigDict


class MetaReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    popular_decks: list[dict]
    winrates: dict[str, float]
    most_used_cards: list[dict]
    emerging_cards: list[dict]
    declining_cards: list[dict]
    matchup_table: dict[str, dict]
    meta_summary: dict


class PopularDeckEntry(BaseModel):
    leader_card_id: str
    deck_count: int
    deck_names: list[str]


class GlobalLeaderStat(BaseModel):
    card_id: str
    name: str
    image_url: str
    wins: int
    losses: int
    matches: int
    winrate: float
    bayesian_winrate: float
    tier: str
    avg_matchup_wr: float
    balance_score: float
    overall_score: float


class GlobalMetaResponse(BaseModel):
    leaders: list[GlobalLeaderStat]
    tiers: dict[str, list[str]]
    total_matches: int
    total_wins: int
    total_losses: int
    timestamp: str
    region: str
    ranking: str
    game_mode: str
    source: str = "optcg.one"
