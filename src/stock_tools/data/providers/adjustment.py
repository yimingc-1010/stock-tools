from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)


class FinMindAdjustmentProvider:
    base_url = "https://api.finmindtrade.com/api/v4/data"
    dataset_name = "TaiwanStockDividend"

    def __init__(self, *, api_token: str | None = None, timeout: int = 30) -> None:
        self.api_token = api_token
        self.timeout = timeout

    def fetch_adjustment_factors(
        self,
        symbol: str,
        *,
        price_frame: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        params: dict[str, Any] = {"dataset": self.dataset_name, "data_id": symbol}
        if self.api_token:
            params["token"] = self.api_token
        response = requests.get(self.base_url, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        status = payload.get("status")
        if status not in (None, 200):
            raise RuntimeError(
                f"FinMind API error status={status} msg={payload.get('msg')!r}"
            )
        return self._normalise(symbol, payload, price_frame)

    def _normalise(
        self,
        symbol: str,
        payload: dict[str, Any],
        price_frame: pd.DataFrame | None,
    ) -> pd.DataFrame:
        empty = pd.DataFrame(
            columns=["symbol", "effective_date", "adjustment_factor", "event_type"]
        )
        rows = payload.get("data", [])
        if not rows:
            return empty

        frame = pd.DataFrame(rows)
        frame["effective_date"] = pd.to_datetime(frame["ExDividendDate"])
        frame["symbol"] = symbol

        records: list[dict[str, Any]] = []
        for _, row in frame.iterrows():
            stock_div = float(row.get("StockDividend", 0) or 0)
            cash_div = float(row.get("CashDividend", 0) or 0)
            stock_factor = 1000.0 / (1000.0 + stock_div) if stock_div > 0 else 1.0
            cash_factor = self._cash_factor(cash_div, row["effective_date"], price_frame)
            factor = stock_factor * cash_factor
            records.append(
                {
                    "symbol": symbol,
                    "effective_date": row["effective_date"],
                    "adjustment_factor": factor,
                    "event_type": "dividend",
                }
            )

        result = pd.DataFrame(
            records,
            columns=["symbol", "effective_date", "adjustment_factor", "event_type"],
        )
        return result.sort_values("effective_date").reset_index(drop=True)

    def _cash_factor(
        self,
        cash_div: float,
        ex_date: pd.Timestamp,
        price_frame: pd.DataFrame | None,
    ) -> float:
        if cash_div <= 0:
            return 1.0
        if price_frame is None:
            return 1.0  # v1: omit cash factor when price not supplied
        prices_before = price_frame[pd.to_datetime(price_frame["date"]) < ex_date]
        if prices_before.empty:
            return 1.0
        prev_close = float(prices_before.iloc[-1]["close"])
        if prev_close <= 0:
            return 1.0
        if cash_div >= prev_close:
            logger.warning(
                "Cash dividend %.4f >= prior close %.4f on ex-date %s; "
                "skipping cash factor to avoid negative adjustment",
                cash_div, prev_close, ex_date,
            )
            return 1.0
        return (prev_close - cash_div) / prev_close
