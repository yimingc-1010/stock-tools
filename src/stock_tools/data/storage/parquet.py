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

    def write_daily_prices(self, symbol: str, frame: pd.DataFrame) -> Path:
        return self.write_frame(Path("curated") / "prices" / "daily" / f"{symbol}.parquet", frame)

    def read_daily_prices(self, symbol: str) -> pd.DataFrame:
        return self.read_frame(Path("curated") / "prices" / "daily" / f"{symbol}.parquet")

    def write_adjustment_factors(self, symbol: str, frame: pd.DataFrame) -> Path:
        path = Path("curated") / "corporate_actions" / "adjustment_factors" / f"{symbol}.parquet"
        return self.write_frame(path, frame)

    def read_adjustment_factors(self, symbol: str) -> pd.DataFrame:
        path = Path("curated") / "corporate_actions" / "adjustment_factors" / f"{symbol}.parquet"
        return self.read_frame(path)

