from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

from stock_tools.core.config import Settings, discover_project_root


def test_settings_have_repo_relative_defaults() -> None:
    settings = Settings()
    assert settings.data_dir == settings.project_root / "data"
    assert settings.raw_data_dir == settings.data_dir / "raw"
    assert settings.curated_data_dir == settings.data_dir / "curated"


def test_project_root_is_discovered_from_repo_subdirectory(monkeypatch: MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(repo_root / "tests")

    assert discover_project_root() == repo_root
    assert Settings().data_dir == repo_root / "data"


def test_custom_data_dir_drives_nested_storage_paths(tmp_path: Path) -> None:
    settings = Settings(project_root=tmp_path, data_dir=tmp_path / "custom-data")

    assert settings.data_dir == tmp_path / "custom-data"
    assert settings.raw_data_dir == tmp_path / "custom-data" / "raw"
    assert settings.curated_data_dir == tmp_path / "custom-data" / "curated"
