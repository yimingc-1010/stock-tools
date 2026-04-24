from __future__ import annotations

from pathlib import Path

import pandas as pd

from stock_tools.data.datasets.universe import SecurityMasterDataset
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
    assert store.security_master_path().exists()
    loaded = store.read_security_master()
    pd.testing.assert_frame_equal(
        loaded.reset_index(drop=True), frame.reset_index(drop=True)
    )


def _sample_master() -> pd.DataFrame:
    return pd.DataFrame({
        "symbol": ["2330", "3008", "9999"],
        "name": ["台積電", "大立光", "已下市股"],
        "security_type": ["stock", "stock", "stock"],
        "market": ["TWSE", "TWSE", "TWSE"],
        "list_date": pd.to_datetime(["1994-09-05", "2002-04-17", "2000-01-01"]),
        "delist_date": pd.to_datetime([pd.NaT, pd.NaT, "2010-06-30"]),
    })


def test_save_and_load(tmp_path: Path) -> None:
    store = ParquetStore(tmp_path)
    ds = SecurityMasterDataset(store)
    ds.save(_sample_master())
    loaded = ds.load()
    assert list(loaded["symbol"]) == ["2330", "3008", "9999"]


def test_get_active_symbols_excludes_delisted(tmp_path: Path) -> None:
    store = ParquetStore(tmp_path)
    ds = SecurityMasterDataset(store)
    ds.save(_sample_master())
    active = ds.get_active_symbols("2026-01-01")
    assert "2330" in active
    assert "3008" in active
    assert "9999" not in active


def test_get_active_symbols_with_nat_list_date(tmp_path: Path) -> None:
    store = ParquetStore(tmp_path)
    ds = SecurityMasterDataset(store)
    frame = _sample_master().copy()
    frame["list_date"] = pd.NaT  # provider didn't supply list_date
    ds.save(frame)
    active = ds.get_active_symbols("2026-01-01")
    assert "2330" in active
    assert "9999" not in active  # still excluded by delist_date


def test_get_active_symbols_excludes_on_delist_day(tmp_path: Path) -> None:
    store = ParquetStore(tmp_path)
    ds = SecurityMasterDataset(store)
    frame = _sample_master().copy()
    frame.loc[frame["symbol"] == "9999", "delist_date"] = pd.Timestamp("2020-06-30")
    ds.save(frame)
    active = ds.get_active_symbols("2020-06-30")
    assert "9999" not in active  # delist_date == query date -> not active
    active_before = ds.get_active_symbols("2020-06-29")
    assert "9999" in active_before  # day before delist -> still active
