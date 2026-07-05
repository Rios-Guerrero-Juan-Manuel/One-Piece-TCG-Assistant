from pydantic import BaseModel, ConfigDict


class CardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    card_id: str
    name: str
    cost: int | None = None
    power: int | None = None
    counter: int = 0
    type: str
    color: list[str] = []
    traits: list[str] = []
    attribute: str | None = None
    keywords: list[str] = []
    roles: list[str] = []
    effect: str = ""
    life: int | None = None
    set_id: str = ""
    set_name: str = ""
    rarity: str = ""
    image_url: str | None = None
    unlimited_copies: bool = False
    language: str = "en"


class CardListResponse(BaseModel):
    cards: list[CardResponse]
    total: int


class CardSearchResponse(BaseModel):
    results: list[CardResponse]


class CardSimilarityResponse(BaseModel):
    card_id: str
    name: str
    score: float


class CardSimilarListResponse(BaseModel):
    query_card_id: str
    results: list[CardSimilarityResponse]
