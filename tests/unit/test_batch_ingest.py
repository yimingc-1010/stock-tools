from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from stock_tools.data.datasets.prices import DailyPriceDataset
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
    dataset = DailyPriceDataset(store)
    mock_provider = MagicMock()
    mock_provider.fetch_daily_prices.return_value = _make_price_frame(
        "2330", ["2026-04-01", "2026-04-02"]
    )
    ingestor = BatchPriceIngestor(mock_provider, dataset, request_delay=0)
    summary = ingestor.run(["2330"], end_date="2026-04-02")
    assert summary.succeeded == 1
    assert summary.failed == 0
    assert summary.skipped == 0
    assert store.daily_prices_path("2330").exists()
    mock_provider.fetch_daily_prices.assert_called_once_with(
        "2330", start_date="2010-01-01", end_date="2026-04-02"
    )


def test_ingest_new_symbol_uses_custom_historical_start(tmp_path: Path) -> None:
    store = ParquetStore(tmp_path)
    dataset = DailyPriceDataset(store)
    mock_provider = MagicMock()
    mock_provider.fetch_daily_prices.return_value = _make_price_frame(
        "2330", ["2020-01-02", "2026-04-02"]
    )
    ingestor = BatchPriceIngestor(
        mock_provider, dataset, request_delay=0, historical_start="2020-01-01"
    )
    summary = ingestor.run(["2330"], end_date="2026-04-02")
    assert summary.succeeded == 1
    mock_provider.fetch_daily_prices.assert_called_once_with(
        "2330", start_date="2020-01-01", end_date="2026-04-02"
    )


def test_ingest_incremental_update(tmp_path: Path) -> None:
    store = ParquetStore(tmp_path)
    dataset = DailyPriceDataset(store)
    existing = _make_price_frame("2330", ["2026-04-01"])
    store.write_daily_prices("2330", existing)

    mock_provider = MagicMock()
    mock_provider.fetch_daily_prices.return_value = _make_price_frame(
        "2330", ["2026-04-02"]
    )
    ingestor = BatchPriceIngestor(mock_provider, dataset, request_delay=0)
    ingestor.run(["2330"], end_date="2026-04-02")

    loaded = store.read_daily_prices("2330")
    assert len(loaded) == 2
    mock_provider.fetch_daily_prices.assert_called_once_with(
        "2330", start_date="2026-04-02", end_date="2026-04-02"
    )


def test_ingest_skips_up_to_date_symbol(tmp_path: Path) -> None:
    store = ParquetStore(tmp_path)
    dataset = DailyPriceDataset(store)
    existing = _make_price_frame("2330", ["2026-04-02"])
    store.write_daily_prices("2330", existing)

    mock_provider = MagicMock()
    ingestor = BatchPriceIngestor(mock_provider, dataset, request_delay=0)
    summary = ingestor.run(["2330"], end_date="2026-04-02")

    assert summary.skipped == 1
    mock_provider.fetch_daily_prices.assert_not_called()


def test_ingest_continues_after_failure(tmp_path: Path) -> None:
    store = ParquetStore(tmp_path)
    dataset = DailyPriceDataset(store)
    mock_provider = MagicMock()
    mock_provider.fetch_daily_prices.side_effect = [
        RuntimeError("API error"),
        _make_price_frame("3008", ["2026-04-02"]),
    ]
    ingestor = BatchPriceIngestor(
        mock_provider,
        dataset,
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
    dataset = DailyPriceDataset(store)
    mock_provider = MagicMock()
    mock_provider.fetch_daily_prices.side_effect = RuntimeError("error")
    ingestor = BatchPriceIngestor(
        mock_provider,
        dataset,
        max_workers=1,
        request_delay=0,
        success_threshold=0.98,
    )
    with pytest.raises(RuntimeError, match="success rate"):
        ingestor.run(["2330", "3008"], end_date="2026-04-02")


def test_throttle_enforces_global_rate_limit(tmp_path: Path) -> None:
    """With 2 workers and 0.2s delay, 4 sequential fetches must take >= 0.6s total
    (3 gaps of 0.2s each). Per-thread sleep would only produce 0.2s total."""
    store = ParquetStore(tmp_path)
    dataset = DailyPriceDataset(store)

    mock_provider = MagicMock()
    mock_provider.fetch_daily_prices.return_value = _make_price_frame(
        "X", ["2026-04-02"]
    )
    ingestor = BatchPriceIngestor(
        mock_provider, dataset, max_workers=2, request_delay=0.2
    )

    start = time.monotonic()
    ingestor.run(["A", "B", "C", "D"], end_date="2026-04-02")
    elapsed = time.monotonic() - start

    # 4 calls, global throttle of 0.2s -> first call fires immediately,
    # the other 3 each wait 0.2s -> >= 0.6s total.
    # Allow some wiggle room: expect >= 0.5s to avoid flakiness.
    assert elapsed >= 0.5, f"Rate limiting too fast: {elapsed:.3f}s"
