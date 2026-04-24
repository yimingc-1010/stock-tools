from __future__ import annotations

import pandas as pd

from stock_tools.core.schemas import SECURITY_MASTER_SCHEMA, validate_required_columns
from stock_tools.data.storage.parquet import ParquetStore


class SecurityMasterDataset:
    def __init__(self, store: ParquetStore) -> None:
        self.store = store

    def save(self, frame: pd.DataFrame) -> None:
        validate_required_columns(frame, SECURITY_MASTER_SCHEMA)
        self.store.write_security_master(frame)

    def load(self) -> pd.DataFrame:
        frame = self.store.read_security_master()
        validate_required_columns(frame, SECURITY_MASTER_SCHEMA)
        return frame

    def get_active_symbols(self, date: str) -> list[str]:
        frame = self.load()
        as_of = pd.Timestamp(date)
        list_date = pd.to_datetime(frame["list_date"])
        delist_date = pd.to_datetime(frame["delist_date"])
        listed = list_date.isna() | (list_date <= as_of)
        not_delisted = delist_date.isna() | (delist_date > as_of)
        return frame.loc[listed & not_delisted, "symbol"].tolist()
