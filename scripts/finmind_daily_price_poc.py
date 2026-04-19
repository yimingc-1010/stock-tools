from __future__ import annotations

import argparse

from stock_tools.core.config import Settings
from stock_tools.core.schemas import DAILY_PRICE_SCHEMA, validate_required_columns
from stock_tools.data.providers.finmind import FinMindPriceProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run FinMind daily price provider proof of concept"
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
    frame = provider.fetch_daily_prices(
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    validate_required_columns(frame, DAILY_PRICE_SCHEMA)

    print(
        f"Fetched {len(frame)} rows for {args.symbol} from {args.start_date} to {args.end_date}."
    )
    if frame.empty:
        print("No rows returned.")
    else:
        print(frame.head(5).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
