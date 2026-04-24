from __future__ import annotations

from pathlib import Path

import pandas as pd

from stock_tools.data.storage.parquet import ParquetStore


def test_security_master_roundtrip(tmp_path: Path) -> None:
    store = ParquetStore(tmp_path)
    frame = pd.DataFrame({
        "symbol": ["2330", "3008"],
        "name": ["台積電", "大立光"],
        "security_type": ["stock", "stock"],
        "market": ["TWSE", "TWSE"],
        "list_date": pd.to_datetime(["1994-09-05", "2002-04-17"]),
        "delist_date": pd.NaT,
    })
    store.write_security_master(frame)
    loaded = store.read_security_master()
    assert list(loaded["symbol"]) == ["2330", "3008"]
    assert store.security_master_path().exists()
