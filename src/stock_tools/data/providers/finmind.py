from __future__ import annotations

from typing import Any

import pandas as pd
import requests

from stock_tools.data.providers.base import DailyPriceProvider


class FinMindPriceProvider(DailyPriceProvider):
    """Thin adapter around the FinMind Taiwan stock daily price endpoint."""

    base_url = "https://api.finmindtrade.com/api/v4/data"
    dataset_name = "TaiwanStockPrice"

    def __init__(self, *, api_token: str | None = None, timeout: int = 30) -> None:
        self.api_token = api_token
        self.timeout = timeout

    def fetch_daily_prices(
        self,
        symbol: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        params = {
            "dataset": self.dataset_name,
            "data_id": symbol,
        }
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if self.api_token:
            params["token"] = self.api_token

        response = requests.get(self.base_url, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        return self.normalize_price_frame(symbol=symbol, payload=payload)

    def normalize_price_frame(self, *, symbol: str, payload: dict[str, Any]) -> pd.DataFrame:
        rows = payload.get("data", [])
        frame = pd.DataFrame(rows)
        if frame.empty:
            return pd.DataFrame(
                columns=["symbol", "date", "open", "high", "low", "close", "volume", "turnover"]
            )

        renamed = frame.rename(
            columns={
                "max": "high",
                "min": "low",
                "Trading_Volume": "volume",
                "Trading_money": "turnover",
            }
        )
        renamed["symbol"] = symbol
        ordered = renamed[["symbol", "date", "open", "high", "low", "close", "volume", "turnover"]]
        ordered["date"] = pd.to_datetime(ordered["date"])
        return ordered.sort_values("date").reset_index(drop=True)

