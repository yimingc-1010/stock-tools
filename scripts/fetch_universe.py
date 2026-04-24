#!/usr/bin/env python3
"""Fetch the TWSE+TPEx security master from FinMind and save it locally."""
from __future__ import annotations

import argparse
import logging
import sys

from stock_tools.core.config import Settings
from stock_tools.data.datasets.universe import SecurityMasterDataset
from stock_tools.data.providers.universe import UniverseProvider
from stock_tools.data.storage.parquet import ParquetStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch TWSE+TPEx security master")
    parser.parse_args()

    settings = Settings()
    store = ParquetStore(settings.data_dir)
    provider = UniverseProvider(api_token=settings.finmind_api_token)
    dataset = SecurityMasterDataset(store)

    try:
        frame = provider.fetch_all()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    dataset.save(frame)
    print(f"Saved {len(frame)} symbols to {store.security_master_path()}")


if __name__ == "__main__":
    main()
