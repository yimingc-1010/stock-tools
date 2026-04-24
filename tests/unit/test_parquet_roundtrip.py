from __future__ import annotations

from pathlib import Path

import pandas as pd

from stock_tools.data.datasets.adjustments import AdjustmentFactorDataset
from stock_tools.data.datasets.prices import DailyPriceDataset
from stock_tools.data.datasets.roundtrip import (
    build_empty_adjustment_factor_frame,
    roundtrip_prices_and_adjustments,
)
from stock_tools.data.storage.parquet import ParquetStore

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def _daily_price_frame(symbol: str) -> pd.DataFrame:
    frame = pd.read_csv(FIXTURE_DIR / "daily_prices_2330.csv")
    frame["symbol"] = symbol
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


def _adjustment_frame(symbol: str) -> pd.DataFrame:
    frame = pd.read_csv(FIXTURE_DIR / "adjustment_factors_2330.csv")
    frame["symbol"] = symbol
    frame["effective_date"] = pd.to_datetime(frame["effective_date"])
    return frame


def test_parquet_round_trip_for_prices_and_adjustments(tmp_path: Path) -> None:
    store = ParquetStore(root_dir=tmp_path)
    prices = DailyPriceDataset(store)
    adjustments = AdjustmentFactorDataset(store)

    symbol = "2330"
    price_frame = _daily_price_frame(symbol)
    adjustment_frame = _adjustment_frame(symbol)

    prices.save(symbol=symbol, frame=price_frame)
    adjustments.save(symbol=symbol, frame=adjustment_frame)

    loaded_prices = prices.load(symbol=symbol)
    loaded_adjustments = adjustments.load(symbol=symbol)

    pd.testing.assert_frame_equal(loaded_prices, price_frame)
    pd.testing.assert_frame_equal(loaded_adjustments, adjustment_frame)


def test_roundtrip_flow_returns_reloaded_frames_and_separate_paths(tmp_path: Path) -> None:
    store = ParquetStore(root_dir=tmp_path)
    symbol = "2330"
    prices = _daily_price_frame(symbol)
    adjustments = build_empty_adjustment_factor_frame()

    result = roundtrip_prices_and_adjustments(
        store=store,
        symbol=symbol,
        daily_prices=prices,
        adjustment_factors=adjustments,
    )

    pd.testing.assert_frame_equal(result.daily_prices, prices)
    pd.testing.assert_frame_equal(result.adjustment_factors, adjustments)
    expected_daily_path = tmp_path / "curated" / "prices" / "daily" / f"{symbol}.parquet"
    assert result.daily_prices_path == expected_daily_path
    assert result.adjustment_factors_path == (
        tmp_path
        / "curated"
        / "corporate_actions"
        / "adjustment_factors"
        / f"{symbol}.parquet"
    )


def test_prices_and_adjustments_are_saved_to_separate_paths(tmp_path: Path) -> None:
    store = ParquetStore(root_dir=tmp_path)

    symbol = "2330"
    price_path = store.write_daily_prices(symbol, _daily_price_frame(symbol))
    adjustment_path = store.write_adjustment_factors(symbol, _adjustment_frame(symbol))

    assert price_path == tmp_path / "curated" / "prices" / "daily" / f"{symbol}.parquet"
    assert adjustment_path == (
        tmp_path
        / "curated"
        / "corporate_actions"
        / "adjustment_factors"
        / f"{symbol}.parquet"
    )
    assert price_path != adjustment_path
