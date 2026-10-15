from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.paths import data_dir


class Settings(BaseSettings):
    db_path: Path = data_dir() / "optcg.db"
    api_base_url: str = "https://www.optcgapi.com"
    optcg_meta_base_url: str = "https://www.optcg.one"
    meta_cache_ttl_seconds: int = 21600

    language: str = "en"
    self_user: str = ""

    model_config = SettingsConfigDict(
        env_file=data_dir() / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
