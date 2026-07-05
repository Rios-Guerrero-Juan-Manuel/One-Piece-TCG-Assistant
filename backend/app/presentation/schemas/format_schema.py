from pydantic import BaseModel, ConfigDict


class FormatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    format_name: str
    banned_cards: list[str] = []
    banned_sets: list[str] = []
    banned_blocks: list[int | str] = []
    banned_pair1: list[str] = []
    banned_pair2: list[str] = []


class FormatListResponse(BaseModel):
    formats: list[FormatResponse]
