from stock_tools.core.config import Settings


def test_settings_have_repo_relative_defaults() -> None:
    settings = Settings()
    assert settings.data_dir.name == "data"
    assert settings.raw_data_dir.name == "raw"
    assert settings.curated_data_dir.name == "curated"

