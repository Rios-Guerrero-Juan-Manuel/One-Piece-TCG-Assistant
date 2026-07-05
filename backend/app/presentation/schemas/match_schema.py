from pydantic import BaseModel, ConfigDict


class MatchListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    match_id: str
    source_file: str
    leader_self: str
    leader_opp: str
    opponent_user: str | None = None
    result: str
    reason: str | None = None
    duration_turns: int | None = None
    deck_id_self: str | None = None
    deck_id_opp: str | None = None
    played_at: str | None = None


class MatchListResponse(BaseModel):
    matches: list[MatchListItemResponse]
    total: int


class CounterItem(BaseModel):
    card_id: str | None = None
    name: str | None = None
    value: int | None = None
    actor: str | None = None


class AttackItem(BaseModel):
    attacker: str | None = None
    attacker_name: str | None = None
    target: str | None = None
    target_name: str | None = None
    attacker_power: int | None = None
    defender_power: int | None = None
    result: str | None = None
    damage: int | None = None
    counters: list[CounterItem] = []


class CardPlayedItem(BaseModel):
    card_id: str | None = None
    name: str | None = None


class TurnResponse(BaseModel):
    turn_no: int
    player_idx: int
    don_drawn: int
    don_unused: int
    cards_played: list[CardPlayedItem] = []
    attacks: list[AttackItem] = []
    counters: list[CounterItem] = []
    errors: list[str] = []
    state_end: dict = {}


class MatchDetailResponse(BaseModel):
    match_id: str
    room_id: str | None = None
    version: str | None = None
    source_file: str
    leader_self: str
    leader_opp: str
    opponent_user: str | None = None
    result: str
    reason: str | None = None
    duration_turns: int | None = None
    deck_id_self: str | None = None
    deck_id_opp: str | None = None
    self_player_idx: int | None = None
    turns: list[TurnResponse] = []
    card_names: dict[str, str] = {}


class MatchImportResponse(BaseModel):
    match_id: str
    source_file: str
    result: str
    turns: int
    leader_self: str
    leader_opp: str
    deck_id_self: str | None = None
    deck_id_opp: str | None = None


class FileImportResult(BaseModel):
    filename: str
    success: bool
    match_id: str | None = None
    turns: int | None = None
    error: str | None = None


class BatchImportResponse(BaseModel):
    imported: int
    errors: int
    total: int
    results: list[FileImportResult] = []


class MatchDeckAssignmentRequest(BaseModel):
    deck_id_self: str | None = None
    deck_id_opp: str | None = None
