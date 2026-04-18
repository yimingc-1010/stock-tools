from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="STOCK_TOOLS_",
        extra="ignore",
    )

    data_dir: Path = Field(default_factory=lambda: Path.cwd() / "data")
    raw_data_dir: Path = Field(default_factory=lambda: Path.cwd() / "data" / "raw")
    curated_data_dir: Path = Field(default_factory=lambda: Path.cwd() / "data" / "curated")
    cache_ttl_seconds: int = Field(default=86_400)
    default_market: str = Field(default="TW")
    finmind_api_token: str | None = Field(default=None)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

