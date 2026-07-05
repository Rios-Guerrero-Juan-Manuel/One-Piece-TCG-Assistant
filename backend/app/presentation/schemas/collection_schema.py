from pydantic import BaseModel, ConfigDict


class CollectionItem(BaseModel):
    card_id: str
    owned: int


class CollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[CollectionItem]


class CollectionUpdateRequest(BaseModel):
    card_id: str
    owned: int


class CollectionImportRequest(BaseModel):
    items: dict[str, int]


class CsvImportResponse(BaseModel):
    imported: int
    total_owned: int
    removed: int
    skipped_other_tcg: int
    skipped_japanese: int
    skipped_no_card_number: int
    synced: bool
    sync_failed: bool
    missing_card_ids: list[str]
