from __future__ import annotations

import argparse

from stock_tools.core.config import Settings
from stock_tools.data.datasets.roundtrip import (
    build_empty_adjustment_factor_frame,
    roundtrip_prices_and_adjustments,
)
from stock_tools.data.providers.finmind import FinMindPriceProvider
from stock_tools.data.storage.parquet import ParquetStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run daily-price and adjustment-factor Parquet round-trip proof of concept"
    )
    parser.add_argument("--symbol", default="2330", help="Taiwan stock symbol (default: 2330)")
    parser.add_argument("--start-date", default="2024-01-01", help="YYYY-MM-DD")
    parser.add_argument("--end-date", default="2024-01-31", help="YYYY-MM-DD")
    parser.add_argument(
        "--token",
        default=None,
        help="FinMind API token. If omitted, reads STOCK_TOOLS_FINMIND_API_TOKEN from Settings.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings()
    token = args.token or settings.finmind_api_token

    provider = FinMindPriceProvider(api_token=token)
    store = ParquetStore(root_dir=settings.data_dir)

    daily_prices = provider.fetch_daily_prices(
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    adjustment_factors = build_empty_adjustment_factor_frame()

    result = roundtrip_prices_and_adjustments(
        store=store,
        symbol=args.symbol,
        daily_prices=daily_prices,
        adjustment_factors=adjustment_factors,
    )

    print(f"Daily prices rows: {len(result.daily_prices)}")
    print(f"Adjustment factor rows: {len(result.adjustment_factors)}")
    print(f"Raw daily prices file: {result.raw_daily_prices_path}")
    print(f"Daily prices file: {result.daily_prices_path}")
    print(f"Adjustment factors file: {result.adjustment_factors_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
