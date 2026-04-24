from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DatasetSchema:
    name: str
    required_columns: tuple[str, ...]


DAILY_PRICE_SCHEMA = DatasetSchema(
    name="daily_prices",
    required_columns=("symbol", "date", "open", "high", "low", "close", "volume", "turnover"),
)

ADJUSTMENT_FACTOR_SCHEMA = DatasetSchema(
    name="adjustment_factors",
    required_columns=("symbol", "effective_date", "adjustment_factor", "event_type"),
)

FUNDAMENTAL_SCHEMA = DatasetSchema(
    name="fundamentals",
    required_columns=("symbol", "report_period", "announcement_date", "metric", "value"),
)

SECURITY_MASTER_SCHEMA = DatasetSchema(
    name="security_master",
    required_columns=("symbol", "name", "security_type", "market", "list_date", "delist_date"),
)


def validate_required_columns(frame: pd.DataFrame, schema: DatasetSchema) -> None:
    missing = [column for column in schema.required_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{schema.name} is missing required columns: {missing}")

