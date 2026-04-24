from __future__ import annotations

from typing import Any

import pandas as pd
import requests

from stock_tools.core.schemas import SECURITY_MASTER_SCHEMA, validate_required_columns

_MARKET_MAP = {"twse": "TWSE", "tpex": "TPEx", "emerging": "Emerging"}


class UniverseProvider:
    base_url = "https://api.finmindtrade.com/api/v4/data"
    dataset_name = "TaiwanStockInfo"

    def __init__(self, *, api_token: str | None = None, timeout: int = 30) -> None:
        self.api_token = api_token
        self.timeout = timeout

    def fetch_all(self) -> pd.DataFrame:
        params: dict[str, Any] = {"dataset": self.dataset_name}
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
        return self._normalise(payload)

    def _normalise(self, payload: dict[str, Any]) -> pd.DataFrame:
        rows = payload.get("data", [])
        if not rows:
            return pd.DataFrame(columns=list(SECURITY_MASTER_SCHEMA.required_columns))
        frame = pd.DataFrame(rows)
        frame = frame.rename(columns={"stock_id": "symbol", "stock_name": "name"})
        frame["market"] = frame["type"].map(_MARKET_MAP).fillna("OTHER")
        frame["security_type"] = "stock"
        frame["list_date"] = pd.NaT
        frame["delist_date"] = pd.NaT
        result = frame[list(SECURITY_MASTER_SCHEMA.required_columns)].copy()
        validate_required_columns(result, SECURITY_MASTER_SCHEMA)
        return result
