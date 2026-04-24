from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

import pandas as pd

from stock_tools.data.providers.base import DailyPriceProvider
from stock_tools.data.storage.parquet import ParquetStore

logger = logging.getLogger(__name__)


@dataclass
class IngestSummary:
    total: int
    succeeded: int
    failed: int
    skipped: int
    failed_symbols: list[str] = field(default_factory=list)


class BatchPriceIngestor:
    def __init__(
        self,
        provider: DailyPriceProvider,
        store: ParquetStore,
        *,
        max_workers: int = 3,
        request_delay: float = 0.5,
        success_threshold: float = 0.98,
        historical_start: str = "2010-01-01",
    ) -> None:
        self.provider = provider
        self.store = store
        self.max_workers = max_workers
        self.request_delay = request_delay
        self.success_threshold = success_threshold
        self.historical_start = historical_start

    def run(self, symbols: list[str], *, end_date: str) -> IngestSummary:
        succeeded = 0
        failed = 0
        skipped = 0
        failed_symbols: list[str] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._ingest_symbol, sym, end_date): sym
                for sym in symbols
            }
            for future in as_completed(futures):
                sym = futures[future]
                try:
                    result = future.result()
                    if result == "skipped":
                        skipped += 1
                    else:
                        succeeded += 1
                except Exception as exc:
                    logger.warning("Failed to ingest %s: %s", sym, exc)
                    failed += 1
                    failed_symbols.append(sym)

        total = len(symbols)
        summary = IngestSummary(
            total=total,
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            failed_symbols=failed_symbols,
        )

        if total > 0 and failed > 0:
            success_rate = (succeeded + skipped) / total
            if success_rate < self.success_threshold:
                raise RuntimeError(
                    f"Batch ingest success rate {success_rate:.1%} below threshold "
                    f"{self.success_threshold:.1%}. Failed: {failed_symbols[:10]}"
                )

        return summary

    def _ingest_symbol(self, symbol: str, end_date: str) -> str:
        path = self.store.daily_prices_path(symbol)
        start_date = self.historical_start
        existing: pd.DataFrame | None = None

        if path.exists():
            existing = self.store.read_daily_prices(symbol)
            last_date = pd.to_datetime(existing["date"]).max()
            next_date = last_date + pd.Timedelta(days=1)
            if next_date > pd.Timestamp(end_date):
                return "skipped"
            start_date = next_date.strftime("%Y-%m-%d")

        time.sleep(self.request_delay)
        new_frame = self.provider.fetch_daily_prices(
            symbol, start_date=start_date, end_date=end_date
        )

        if new_frame.empty:
            return "skipped"

        if existing is not None:
            combined = pd.concat([existing, new_frame], ignore_index=True)
            combined = combined.drop_duplicates(subset=["symbol", "date"])
            combined = combined.sort_values("date").reset_index(drop=True)
        else:
            combined = new_frame

        self.store.write_daily_prices(symbol, combined)
        return "ok"
