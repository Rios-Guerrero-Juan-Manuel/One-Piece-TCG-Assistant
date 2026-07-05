from pydantic import BaseModel, ConfigDict


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rec_id: str
    deck_id: str | None = None
    card_out: str | None
    card_in: str
    qty: int
    score: int
    rationale: dict
    created_at: str | None = None
