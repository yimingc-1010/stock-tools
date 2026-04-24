from __future__ import annotations

from dataclasses import dataclass
from os import PathLike

import pandas as pd

from stock_tools.data.datasets.adjustments import AdjustmentFactorDataset
from stock_tools.data.datasets.prices import DailyPriceDataset
from stock_tools.data.storage.parquet import ParquetStore


@dataclass(frozen=True)
class RoundTripResult:
    raw_daily_prices_path: PathLike[str] | str
    daily_prices_path: PathLike[str] | str
    adjustment_factors_path: PathLike[str] | str
    daily_prices: pd.DataFrame
    adjustment_factors: pd.DataFrame


def build_empty_adjustment_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": pd.Series(dtype="object"),
            "effective_date": pd.Series(dtype="datetime64[ns]"),
            "adjustment_factor": pd.Series(dtype="float64"),
            "event_type": pd.Series(dtype="object"),
        }
    )


def roundtrip_prices_and_adjustments(
    *,
    store: ParquetStore,
    symbol: str,
    daily_prices: pd.DataFrame,
    adjustment_factors: pd.DataFrame,
) -> RoundTripResult:
    prices = DailyPriceDataset(store)
    adjustments = AdjustmentFactorDataset(store)

    raw_daily_prices_path = store.write_raw_daily_prices(symbol=symbol, frame=daily_prices)
    prices.save(symbol=symbol, frame=daily_prices)
    adjustments.save(symbol=symbol, frame=adjustment_factors)

    loaded_prices = prices.load(symbol=symbol)
    loaded_adjustments = adjustments.load(symbol=symbol)

    return RoundTripResult(
        raw_daily_prices_path=raw_daily_prices_path,
        daily_prices_path=store.daily_prices_path(symbol),
        adjustment_factors_path=store.adjustment_factors_path(symbol),
        daily_prices=loaded_prices,
        adjustment_factors=loaded_adjustments,
    )
