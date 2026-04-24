#!/usr/bin/env python3
"""Batch ingest daily prices for all active TWSE+TPEx symbols."""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from stock_tools.core.config import Settings
from stock_tools.data.datasets.universe import SecurityMasterDataset
from stock_tools.data.pipeline.batch_ingest import BatchPriceIngestor
from stock_tools.data.providers.finmind import FinMindPriceProvider
from stock_tools.data.storage.parquet import ParquetStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch ingest daily prices")
    parser.add_argument("--date", default=str(date.today()), help="End date YYYY-MM-DD")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--threshold", type=float, default=0.98)
    args = parser.parse_args()

    settings = Settings()
    store = ParquetStore(settings.data_dir)
    universe = SecurityMasterDataset(store)
    symbols = universe.get_active_symbols(args.date)
    provider = FinMindPriceProvider(api_token=settings.finmind_api_token)
    ingestor = BatchPriceIngestor(
        provider,
        store,
        max_workers=args.workers,
        request_delay=args.delay,
        success_threshold=args.threshold,
    )

    print(f"Ingesting {len(symbols)} symbols up to {args.date} ...")
    try:
        summary = ingestor.run(symbols, end_date=args.date)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(
        f"Done. total={summary.total} succeeded={summary.succeeded} "
        f"failed={summary.failed} skipped={summary.skipped}"
    )
    if summary.failed_symbols:
        print(f"Failed symbols: {summary.failed_symbols}")


if __name__ == "__main__":
    main()
