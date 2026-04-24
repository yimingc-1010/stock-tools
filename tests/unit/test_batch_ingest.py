from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from stock_tools.data.pipeline.batch_ingest import BatchPriceIngestor
from stock_tools.data.storage.parquet import ParquetStore


def _make_price_frame(symbol: str, dates: list[str]) -> pd.DataFrame:
    n = len(dates)
    return pd.DataFrame(
        {
            "symbol": [symbol] * n,
            "date": pd.to_datetime(dates),
            "open": [100.0] * n,
            "high": [105.0] * n,
            "low": [98.0] * n,
            "close": [102.0] * n,
            "volume": [1000] * n,
            "turnover": [102000] * n,
        }
    )


def test_ingest_new_symbol(tmp_path: Path) -> None:
    store = ParquetStore(tmp_path)
    mock_provider = MagicMock()
    mock_provider.fetch_daily_prices.return_value = _make_price_frame(
        "2330", ["2026-04-01", "2026-04-02"]
    )
    ingestor = BatchPriceIngestor(mock_provider, store, request_delay=0)
    summary = ingestor.run(["2330"], end_date="2026-04-02")
    assert summary.succeeded == 1
    assert summary.failed == 0
    assert summary.skipped == 0
    assert store.daily_prices_path("2330").exists()


def test_ingest_incremental_update(tmp_path: Path) -> None:
    store = ParquetStore(tmp_path)
    existing = _make_price_frame("2330", ["2026-04-01"])
    store.write_daily_prices("2330", existing)

    mock_provider = MagicMock()
    mock_provider.fetch_daily_prices.return_value = _make_price_frame(
        "2330", ["2026-04-02"]
    )
    ingestor = BatchPriceIngestor(mock_provider, store, request_delay=0)
    ingestor.run(["2330"], end_date="2026-04-02")

    loaded = store.read_daily_prices("2330")
    assert len(loaded) == 2
    mock_provider.fetch_daily_prices.assert_called_once_with(
        "2330", start_date="2026-04-02", end_date="2026-04-02"
    )


def test_ingest_skips_up_to_date_symbol(tmp_path: Path) -> None:
    store = ParquetStore(tmp_path)
    existing = _make_price_frame("2330", ["2026-04-02"])
    store.write_daily_prices("2330", existing)

    mock_provider = MagicMock()
    ingestor = BatchPriceIngestor(mock_provider, store, request_delay=0)
    summary = ingestor.run(["2330"], end_date="2026-04-02")

    assert summary.skipped == 1
    mock_provider.fetch_daily_prices.assert_not_called()


def test_ingest_continues_after_failure(tmp_path: Path) -> None:
    store = ParquetStore(tmp_path)
    mock_provider = MagicMock()
    mock_provider.fetch_daily_prices.side_effect = [
        RuntimeError("API error"),
        _make_price_frame("3008", ["2026-04-02"]),
    ]
    ingestor = BatchPriceIngestor(
        mock_provider,
        store,
        max_workers=1,
        request_delay=0,
        success_threshold=0.5,
    )
    summary = ingestor.run(["2330", "3008"], end_date="2026-04-02")

    assert summary.failed == 1
    assert summary.succeeded == 1
    assert "2330" in summary.failed_symbols


def test_ingest_raises_when_below_success_threshold(tmp_path: Path) -> None:
    store = ParquetStore(tmp_path)
    mock_provider = MagicMock()
    mock_provider.fetch_daily_prices.side_effect = RuntimeError("error")
    ingestor = BatchPriceIngestor(
        mock_provider,
        store,
        max_workers=1,
        request_delay=0,
        success_threshold=0.98,
    )
    with pytest.raises(RuntimeError, match="success rate"):
        ingestor.run(["2330", "3008"], end_date="2026-04-02")
