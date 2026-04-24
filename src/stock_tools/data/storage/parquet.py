from __future__ import annotations

from pathlib import Path

import pandas as pd


class ParquetStore:
    """Small convenience wrapper for dataset-oriented Parquet storage."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir

    def write_frame(self, relative_path: str | Path, frame: pd.DataFrame) -> Path:
        path = self.root_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False)
        return path

    def read_frame(self, relative_path: str | Path) -> pd.DataFrame:
        return pd.read_parquet(self.root_dir / relative_path)

    def raw_daily_prices_path(self, symbol: str) -> Path:
        return self.root_dir / "raw" / "prices" / "daily" / f"{symbol}.parquet"

    def daily_prices_path(self, symbol: str) -> Path:
        return self.root_dir / "curated" / "prices" / "daily" / f"{symbol}.parquet"

    def adjustment_factors_path(self, symbol: str) -> Path:
        return (
            self.root_dir
            / "curated"
            / "corporate_actions"
            / "adjustment_factors"
            / f"{symbol}.parquet"
        )

    def write_raw_daily_prices(self, symbol: str, frame: pd.DataFrame) -> Path:
        path = self.raw_daily_prices_path(symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False)
        return path

    def read_raw_daily_prices(self, symbol: str) -> pd.DataFrame:
        return pd.read_parquet(self.raw_daily_prices_path(symbol))

    def write_daily_prices(self, symbol: str, frame: pd.DataFrame) -> Path:
        path = self.daily_prices_path(symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False)
        return path

    def read_daily_prices(self, symbol: str) -> pd.DataFrame:
        return pd.read_parquet(self.daily_prices_path(symbol))

    def write_adjustment_factors(self, symbol: str, frame: pd.DataFrame) -> Path:
        path = self.adjustment_factors_path(symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False)
        return path

    def read_adjustment_factors(self, symbol: str) -> pd.DataFrame:
        return pd.read_parquet(self.adjustment_factors_path(symbol))

    def security_master_path(self) -> Path:
        return self.root_dir / "curated" / "security_master" / "master.parquet"

    def write_security_master(self, frame: pd.DataFrame) -> Path:
        path = self.security_master_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False)
        return path

    def read_security_master(self) -> pd.DataFrame:
        return pd.read_parquet(self.security_master_path())
