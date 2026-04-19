from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_repo_marker(start: Path) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() or (candidate / ".git").exists():
            return candidate
    return None


def discover_project_root() -> Path:
    cwd_root = _find_repo_marker(Path.cwd())
    if cwd_root is not None:
        return cwd_root

    module_root = _find_repo_marker(Path(__file__))
    if module_root is not None:
        return module_root

    return Path.cwd()


def _default_data_dir() -> Path:
    return discover_project_root() / "data"


def _default_raw_data_dir() -> Path:
    return _default_data_dir() / "raw"


def _default_curated_data_dir() -> Path:
    return _default_data_dir() / "curated"


class Settings(BaseSettings):
    """Application settings loaded from environment variables or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="STOCK_TOOLS_",
        extra="ignore",
    )

    project_root: Path = Field(default_factory=discover_project_root)
    data_dir: Path = Field(default_factory=_default_data_dir)
    raw_data_dir: Path = Field(default_factory=_default_raw_data_dir)
    curated_data_dir: Path = Field(default_factory=_default_curated_data_dir)
    cache_ttl_seconds: int = Field(default=86_400)
    default_market: str = Field(default="TW")
    finmind_api_token: str | None = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def populate_path_defaults(cls, data: Any) -> Any:
        if data is None:
            values: dict[str, Any] = {}
        elif isinstance(data, dict):
            values = dict(data)
        else:
            return data

        project_root = Path(values.get("project_root") or discover_project_root()).resolve()
        data_dir = Path(values.get("data_dir") or project_root / "data").resolve()
        raw_data_dir = Path(values.get("raw_data_dir") or data_dir / "raw").resolve()
        curated_data_dir = Path(values.get("curated_data_dir") or data_dir / "curated").resolve()

        values["project_root"] = project_root
        values["data_dir"] = data_dir
        values["raw_data_dir"] = raw_data_dir
        values["curated_data_dir"] = curated_data_dir
        return values


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
