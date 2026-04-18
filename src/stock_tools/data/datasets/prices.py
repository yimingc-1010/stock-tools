from __future__ import annotations

import pandas as pd

from stock_tools.core.schemas import DAILY_PRICE_SCHEMA, validate_required_columns
from stock_tools.data.storage.parquet import ParquetStore


class DailyPriceDataset:
    def __init__(self, store: ParquetStore) -> None:
        self.store = store

    def save(self, symbol: str, frame: pd.DataFrame) -> None:
        validate_required_columns(frame, DAILY_PRICE_SCHEMA)
        self.store.write_daily_prices(symbol, frame)

    def load(self, symbol: str) -> pd.DataFrame:
        frame = self.store.read_daily_prices(symbol)
        validate_required_columns(frame, DAILY_PRICE_SCHEMA)
        return frame

