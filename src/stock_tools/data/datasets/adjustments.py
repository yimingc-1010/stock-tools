from __future__ import annotations

import pandas as pd

from stock_tools.core.schemas import ADJUSTMENT_FACTOR_SCHEMA, validate_required_columns
from stock_tools.data.storage.parquet import ParquetStore


class AdjustmentFactorDataset:
    def __init__(self, store: ParquetStore) -> None:
        self.store = store

    def save(self, symbol: str, frame: pd.DataFrame) -> None:
        validate_required_columns(frame, ADJUSTMENT_FACTOR_SCHEMA)
        self.store.write_adjustment_factors(symbol, frame)

    def load(self, symbol: str) -> pd.DataFrame:
        frame = self.store.read_adjustment_factors(symbol)
        validate_required_columns(frame, ADJUSTMENT_FACTOR_SCHEMA)
        return frame
