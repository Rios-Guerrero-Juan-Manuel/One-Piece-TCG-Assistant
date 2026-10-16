from pydantic import BaseModel


class SettingsResponse(BaseModel):
    settings: dict[str, str]


class SettingsUpdateRequest(BaseModel):
    settings: dict[str, str]


class LogsDirValidationRequest(BaseModel):
    path: str


class LogsDirValidationResponse(BaseModel):
    exists: bool
    is_dir: bool
    files_found: int
    autosaved_found: int
    hint: str | None = None
