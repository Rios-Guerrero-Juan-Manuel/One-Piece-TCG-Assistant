from pydantic import BaseModel, ConfigDict


class DeckCardItem(BaseModel):
    card_id: str
    qty: int


class DeckListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    deck_id: str
    name: str
    leader_card_id: str
    source: str | None = None
    card_count: int
    version: int = 1


class DeckDetailCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    card_id: str
    name: str
    cost: int | None = None
    power: int | None = None
    counter: int = 0
    type: str
    color: list[str] = []
    traits: list[str] = []
    keywords: list[str] = []
    roles: list[str] = []
    effect: str = ""
    image_url: str = ""
    set_id: str = ""
    qty: int = 1


class DeckDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    deck_id: str
    name: str
    leader_card_id: str
    source: str | None = None
    event: str | None = None
    date: str | None = None
    version: int = 1
    cards: list[DeckDetailCardResponse] = []


class DeckImportRequest(BaseModel):
    name: str = ""
    text: str
    source: str | None = None
    mode: str = "new"  # "new" or "new_version"
    leader_card_id: str | None = None  # explicit leader for new_version


class DeckCreateRequest(BaseModel):
    deck_id: str | None = None
    name: str
    leader_card_id: str
    cards: list[DeckCardItem]
    source: str | None = None


class DeckImportResponse(BaseModel):
    deck_id: str
    name: str
    leader_card_id: str
    card_count: int
    version: int = 1


class DeckCreateResponse(BaseModel):
    deck_id: str
    name: str
    leader_card_id: str
    card_count: int


class DeckListResponse(BaseModel):
    decks: list[DeckListItemResponse]


class ValidationResultResponse(BaseModel):
    errors: list[str]
    warnings: list[str]


class DeckScoreResponse(BaseModel):
    deck_id: str
    overall: int
    breakdown: dict[str, int]
    version: int


class SubstitutionSuggestion(BaseModel):
    card_out_id: str
    card_in_id: str
    card_in_name: str
    score: int
    image_url: str | None = None


class MissingCard(BaseModel):
    card_id: str
    name: str
    needed: int
    owned: int
    missing: int
    avg_price: float | None = None
    extended_price: float | None = None


class CompleteDeckResponse(BaseModel):
    missing: list[MissingCard]
    substitutions: list[SubstitutionSuggestion]
    validation: ValidationResultResponse
    total_missing_price: float | None = None


class DeckVersionItem(BaseModel):
    deck_id: str
    name: str
    version: int
    card_count: int
    created_at: str | None = None


class DeckVersionsResponse(BaseModel):
    leader_card_id: str
    versions: list[DeckVersionItem]
