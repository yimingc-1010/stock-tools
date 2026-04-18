from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class DailyPriceProvider(ABC):
    @abstractmethod
    def fetch_daily_prices(
        self,
        symbol: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Fetch daily price history for a single symbol."""

