# Phase 1: Data Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver Universe/Security Master, incremental batch price ingestion for 1,700+ symbols, and real adjustment factor data — the prerequisite foundation for all screening and backtesting work.

**Architecture:** Universe provider fetches the full TWSE+TPEx stock list from FinMind and stores it in a `SecurityMasterDataset`; the batch pipeline reads that list, incrementally updates each symbol's daily prices from FinMind using a rate-limited thread pool, and logs failures without aborting; the adjustment provider fetches dividend events from FinMind and computes per-event multiplicative factors.

**Tech Stack:** Python 3.10, pandas, pyarrow/parquet, requests, `concurrent.futures.ThreadPoolExecutor`

---

## File Map

### New files
| File | Responsibility |
|---|---|
| `src/stock_tools/data/providers/universe.py` | `UniverseProvider`: fetches TaiwanStockInfo from FinMind, normalises to security master schema |
| `src/stock_tools/data/datasets/universe.py` | `SecurityMasterDataset`: save/load/get_active_symbols — replaces empty stub |
| `src/stock_tools/data/providers/adjustment.py` | `FinMindAdjustmentProvider`: fetches TaiwanStockDividend, computes per-event adjustment factors |
| `src/stock_tools/data/pipeline/__init__.py` | empty |
| `src/stock_tools/data/pipeline/batch_ingest.py` | `BatchPriceIngestor`, `IngestSummary` |
| `scripts/batch_ingest.py` | CLI entry point |
| `tests/unit/test_universe_provider.py` | mocked provider tests |
| `tests/unit/test_universe_dataset.py` | dataset save/load/get_active_symbols tests |
| `tests/unit/test_adjustment_provider.py` | mocked provider tests |
| `tests/unit/test_batch_ingest.py` | ingestor unit tests with mocked provider |

### Modified files
| File | Change |
|---|---|
| `src/stock_tools/data/storage/parquet.py` | add `security_master_path()`, `write_security_master()`, `read_security_master()` |

---

## Task 1: Extend ParquetStore with security master methods

**Files:**
- Modify: `src/stock_tools/data/storage/parquet.py`
- Test: `tests/unit/test_universe_dataset.py` (partial — storage paths only)

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_universe_dataset.py
import pytest
import pandas as pd
from pathlib import Path
from stock_tools.data.storage.parquet import ParquetStore


def test_security_master_roundtrip(tmp_path):
    store = ParquetStore(tmp_path)
    frame = pd.DataFrame({
        "symbol": ["2330", "3008"],
        "name": ["台積電", "大立光"],
        "security_type": ["stock", "stock"],
        "market": ["TWSE", "TWSE"],
        "list_date": pd.to_datetime(["1994-09-05", "2002-04-17"]),
        "delist_date": pd.NaT,
    })
    store.write_security_master(frame)
    loaded = store.read_security_master()
    assert list(loaded["symbol"]) == ["2330", "3008"]
    assert store.security_master_path().exists()
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/unit/test_universe_dataset.py::test_security_master_roundtrip -v
```
Expected: `AttributeError: 'ParquetStore' object has no attribute 'write_security_master'`

- [ ] **Step 3: Add methods to ParquetStore**

Add to `src/stock_tools/data/storage/parquet.py` after the `read_adjustment_factors` method:

```python
    def security_master_path(self) -> Path:
        return self.root_dir / "curated" / "security_master" / "master.parquet"

    def write_security_master(self, frame: pd.DataFrame) -> Path:
        path = self.security_master_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False)
        return path

    def read_security_master(self) -> pd.DataFrame:
        return pd.read_parquet(self.security_master_path())
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/unit/test_universe_dataset.py::test_security_master_roundtrip -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/stock_tools/data/storage/parquet.py tests/unit/test_universe_dataset.py
git commit -m "feat(ST-009): add security master read/write to ParquetStore"
```

---

## Task 2: Implement UniverseProvider

**Files:**
- Create: `src/stock_tools/data/providers/universe.py`
- Modify: `tests/unit/test_universe_provider.py`

FinMind endpoint: `GET https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInfo&token=<token>`

Response shape:
```json
{
  "status": 200,
  "data": [
    {"stock_id": "2330", "stock_name": "台積電", "type": "twse", "date": "2024-01-01", "industry_category": "半導體業", "market_category": "上市"}
  ]
}
```

Column mapping:
- `stock_id` → `symbol`
- `stock_name` → `name`
- `type` (`twse`/`otc`/`rotc`) → `market` (`TWSE`/`TPEx`/`TPEx`)
- `security_type` = `"stock"` (fixed for v1)
- `list_date` = `pd.NaT` (not provided by this endpoint — v1 limitation)
- `delist_date` = `pd.NaT` (endpoint only returns currently listed stocks)

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_universe_provider.py
from unittest.mock import patch, MagicMock
import pandas as pd
import pytest
from stock_tools.data.providers.universe import UniverseProvider

MOCK_RESPONSE = {
    "status": 200,
    "data": [
        {"stock_id": "2330", "stock_name": "台積電", "type": "twse", "date": "2024-01-01", "industry_category": "半導體業", "market_category": "上市"},
        {"stock_id": "6488", "stock_name": "環球晶", "type": "otc", "date": "2024-01-01", "industry_category": "半導體業", "market_category": "上櫃"},
    ]
}


def _mock_get(response_data):
    mock_resp = MagicMock()
    mock_resp.json.return_value = response_data
    mock_resp.raise_for_status.return_value = None
    return mock_resp


@patch("stock_tools.data.providers.universe.requests.get")
def test_fetch_normalises_columns(mock_get):
    mock_get.return_value = _mock_get(MOCK_RESPONSE)
    provider = UniverseProvider()
    frame = provider.fetch_all()
    assert list(frame.columns) == ["symbol", "name", "security_type", "market", "list_date", "delist_date"]
    assert frame["market"].tolist() == ["TWSE", "TPEx"]
    assert (frame["security_type"] == "stock").all()


@patch("stock_tools.data.providers.universe.requests.get")
def test_fetch_raises_on_api_error(mock_get):
    mock_get.return_value = _mock_get({"status": 402, "msg": "invalid token"})
    provider = UniverseProvider()
    with pytest.raises(RuntimeError, match="FinMind API error"):
        provider.fetch_all()


@patch("stock_tools.data.providers.universe.requests.get")
def test_fetch_empty_payload(mock_get):
    mock_get.return_value = _mock_get({"status": 200, "data": []})
    provider = UniverseProvider()
    frame = provider.fetch_all()
    assert frame.empty
    assert list(frame.columns) == ["symbol", "name", "security_type", "market", "list_date", "delist_date"]
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/unit/test_universe_provider.py -v
```
Expected: `ModuleNotFoundError: No module named 'stock_tools.data.providers.universe'`

- [ ] **Step 3: Implement UniverseProvider**

Create `src/stock_tools/data/providers/universe.py`:

```python
from __future__ import annotations

from typing import Any

import pandas as pd
import requests


_MARKET_MAP = {"twse": "TWSE", "otc": "TPEx", "rotc": "TPEx"}


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
            raise RuntimeError(f"FinMind API error status={status} msg={payload.get('msg')!r}")
        return self._normalise(payload)

    def _normalise(self, payload: dict[str, Any]) -> pd.DataFrame:
        rows = payload.get("data", [])
        empty = pd.DataFrame(
            columns=["symbol", "name", "security_type", "market", "list_date", "delist_date"]
        )
        if not rows:
            return empty
        frame = pd.DataFrame(rows)
        frame = frame.rename(columns={"stock_id": "symbol", "stock_name": "name"})
        frame["market"] = frame["type"].map(_MARKET_MAP).fillna("OTHER")
        frame["security_type"] = "stock"
        frame["list_date"] = pd.NaT
        frame["delist_date"] = pd.NaT
        return frame[["symbol", "name", "security_type", "market", "list_date", "delist_date"]].copy()
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/unit/test_universe_provider.py -v
```
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/stock_tools/data/providers/universe.py tests/unit/test_universe_provider.py
git commit -m "feat(ST-009): add UniverseProvider for FinMind TaiwanStockInfo"
```

---

## Task 3: Implement SecurityMasterDataset

**Files:**
- Modify: `src/stock_tools/data/datasets/universe.py`
- Modify: `tests/unit/test_universe_dataset.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_universe_dataset.py`:

```python
from stock_tools.data.datasets.universe import SecurityMasterDataset


def _sample_master() -> pd.DataFrame:
    return pd.DataFrame({
        "symbol": ["2330", "3008", "9999"],
        "name": ["台積電", "大立光", "已下市股"],
        "security_type": ["stock", "stock", "stock"],
        "market": ["TWSE", "TWSE", "TWSE"],
        "list_date": pd.to_datetime(["1994-09-05", "2002-04-17", "2000-01-01"]),
        "delist_date": pd.to_datetime([pd.NaT, pd.NaT, "2010-06-30"]),
    })


def test_save_and_load(tmp_path):
    store = ParquetStore(tmp_path)
    ds = SecurityMasterDataset(store)
    ds.save(_sample_master())
    loaded = ds.load()
    assert list(loaded["symbol"]) == ["2330", "3008", "9999"]


def test_get_active_symbols_excludes_delisted(tmp_path):
    store = ParquetStore(tmp_path)
    ds = SecurityMasterDataset(store)
    ds.save(_sample_master())
    active = ds.get_active_symbols("2026-01-01")
    assert "2330" in active
    assert "3008" in active
    assert "9999" not in active


def test_get_active_symbols_with_nat_list_date(tmp_path):
    store = ParquetStore(tmp_path)
    ds = SecurityMasterDataset(store)
    frame = _sample_master().copy()
    frame["list_date"] = pd.NaT  # provider didn't supply list_date
    ds.save(frame)
    active = ds.get_active_symbols("2026-01-01")
    assert "2330" in active
    assert "9999" not in active  # still excluded by delist_date
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/unit/test_universe_dataset.py -v
```
Expected: `ImportError: cannot import name 'SecurityMasterDataset'`

- [ ] **Step 3: Implement SecurityMasterDataset**

Replace `src/stock_tools/data/datasets/universe.py` with:

```python
from __future__ import annotations

import pandas as pd

from stock_tools.core.schemas import SECURITY_MASTER_SCHEMA, validate_required_columns
from stock_tools.data.storage.parquet import ParquetStore


class SecurityMasterDataset:
    def __init__(self, store: ParquetStore) -> None:
        self.store = store

    def save(self, frame: pd.DataFrame) -> None:
        validate_required_columns(frame, SECURITY_MASTER_SCHEMA)
        self.store.write_security_master(frame)

    def load(self) -> pd.DataFrame:
        frame = self.store.read_security_master()
        validate_required_columns(frame, SECURITY_MASTER_SCHEMA)
        return frame

    def get_active_symbols(self, date: str) -> list[str]:
        frame = self.load()
        as_of = pd.Timestamp(date)
        list_date = pd.to_datetime(frame["list_date"])
        delist_date = pd.to_datetime(frame["delist_date"])
        listed = list_date.isna() | (list_date <= as_of)
        not_delisted = delist_date.isna() | (delist_date > as_of)
        return frame.loc[listed & not_delisted, "symbol"].tolist()
```

- [ ] **Step 4: Run all universe tests to verify they pass**

```
pytest tests/unit/test_universe_dataset.py tests/unit/test_universe_provider.py -v
```
Expected: all PASS

- [ ] **Step 5: Run full test suite**

```
pytest -q
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/stock_tools/data/datasets/universe.py tests/unit/test_universe_dataset.py
git commit -m "feat(ST-009): implement SecurityMasterDataset with get_active_symbols"
```

---

## Task 4: Implement FinMindAdjustmentProvider (ST-011)

**Files:**
- Create: `src/stock_tools/data/providers/adjustment.py`
- Create: `tests/unit/test_adjustment_provider.py`

FinMind endpoint: `GET https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockDividend&data_id=2330&token=<token>`

Response shape:
```json
{
  "status": 200,
  "data": [
    {
      "stock_id": "2330",
      "date": "2023-06-15",
      "ExDividendDate": "2023-07-18",
      "CashDividend": 3.0,
      "StockDividend": 0.0
    }
  ]
}
```

Adjustment factor formula:
- `stock_factor = 1000 / (1000 + StockDividend)` when `StockDividend > 0`, else `1.0`
- `cash_factor`: requires prior close price — computed as `(close_prev - CashDividend) / close_prev` when `price_frame` is provided, else `1.0` (documented v1 limitation)
- `factor = stock_factor * cash_factor`

Output schema: `symbol, effective_date, adjustment_factor, event_type`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_adjustment_provider.py
from unittest.mock import patch, MagicMock
import pandas as pd
import pytest
from stock_tools.data.providers.adjustment import FinMindAdjustmentProvider

MOCK_DIVIDEND_RESPONSE = {
    "status": 200,
    "data": [
        {
            "stock_id": "2330",
            "date": "2023-06-15",
            "ExDividendDate": "2023-07-18",
            "CashDividend": 3.0,
            "StockDividend": 0.0,
        },
        {
            "stock_id": "2330",
            "date": "2022-06-10",
            "ExDividendDate": "2022-07-13",
            "CashDividend": 0.0,
            "StockDividend": 50.0,
        },
    ],
}


def _mock_get(data):
    m = MagicMock()
    m.json.return_value = data
    m.raise_for_status.return_value = None
    return m


@patch("stock_tools.data.providers.adjustment.requests.get")
def test_fetch_returns_required_columns(mock_get):
    mock_get.return_value = _mock_get(MOCK_DIVIDEND_RESPONSE)
    provider = FinMindAdjustmentProvider()
    frame = provider.fetch_adjustment_factors("2330")
    assert list(frame.columns) == ["symbol", "effective_date", "adjustment_factor", "event_type"]


@patch("stock_tools.data.providers.adjustment.requests.get")
def test_stock_dividend_factor(mock_get):
    mock_get.return_value = _mock_get(MOCK_DIVIDEND_RESPONSE)
    provider = FinMindAdjustmentProvider()
    frame = provider.fetch_adjustment_factors("2330")
    stock_row = frame[frame["effective_date"] == pd.Timestamp("2022-07-13")].iloc[0]
    expected_factor = 1000 / (1000 + 50.0)
    assert abs(stock_row["adjustment_factor"] - expected_factor) < 1e-9


@patch("stock_tools.data.providers.adjustment.requests.get")
def test_cash_dividend_with_price_frame(mock_get):
    mock_get.return_value = _mock_get(MOCK_DIVIDEND_RESPONSE)
    price_frame = pd.DataFrame({
        "symbol": ["2330"] * 3,
        "date": pd.to_datetime(["2023-07-14", "2023-07-17", "2023-07-18"]),
        "close": [550.0, 548.0, 545.0],
    })
    provider = FinMindAdjustmentProvider()
    frame = provider.fetch_adjustment_factors("2330", price_frame=price_frame)
    cash_row = frame[frame["effective_date"] == pd.Timestamp("2023-07-18")].iloc[0]
    expected_factor = (548.0 - 3.0) / 548.0  # close on day before ex-date
    assert abs(cash_row["adjustment_factor"] - expected_factor) < 1e-9


@patch("stock_tools.data.providers.adjustment.requests.get")
def test_api_error_raises(mock_get):
    mock_get.return_value = _mock_get({"status": 402, "msg": "quota exceeded"})
    provider = FinMindAdjustmentProvider()
    with pytest.raises(RuntimeError, match="FinMind API error"):
        provider.fetch_adjustment_factors("2330")


@patch("stock_tools.data.providers.adjustment.requests.get")
def test_empty_payload(mock_get):
    mock_get.return_value = _mock_get({"status": 200, "data": []})
    provider = FinMindAdjustmentProvider()
    frame = provider.fetch_adjustment_factors("2330")
    assert frame.empty
    assert list(frame.columns) == ["symbol", "effective_date", "adjustment_factor", "event_type"]
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/unit/test_adjustment_provider.py -v
```
Expected: `ModuleNotFoundError: No module named 'stock_tools.data.providers.adjustment'`

- [ ] **Step 3: Implement FinMindAdjustmentProvider**

Create `src/stock_tools/data/providers/adjustment.py`:

```python
from __future__ import annotations

from typing import Any

import pandas as pd
import requests


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
            raise RuntimeError(f"FinMind API error status={status} msg={payload.get('msg')!r}")
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

        records = []
        for _, row in frame.iterrows():
            stock_div = float(row.get("StockDividend", 0) or 0)
            cash_div = float(row.get("CashDividend", 0) or 0)
            stock_factor = 1000.0 / (1000.0 + stock_div) if stock_div > 0 else 1.0
            cash_factor = self._cash_factor(cash_div, row["effective_date"], price_frame)
            factor = stock_factor * cash_factor
            event = "dividend"
            records.append({
                "symbol": symbol,
                "effective_date": row["effective_date"],
                "adjustment_factor": factor,
                "event_type": event,
            })

        result = pd.DataFrame(records, columns=["symbol", "effective_date", "adjustment_factor", "event_type"])
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
        return (prev_close - cash_div) / prev_close
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/unit/test_adjustment_provider.py -v
```
Expected: 5 PASS

- [ ] **Step 5: Run full test suite**

```
pytest -q
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/stock_tools/data/providers/adjustment.py tests/unit/test_adjustment_provider.py
git commit -m "feat(ST-011): add FinMindAdjustmentProvider using TaiwanStockDividend"
```

---

## Task 5: Implement BatchPriceIngestor (ST-010)

**Files:**
- Create: `src/stock_tools/data/pipeline/__init__.py`
- Create: `src/stock_tools/data/pipeline/batch_ingest.py`
- Create: `tests/unit/test_batch_ingest.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_batch_ingest.py
from __future__ import annotations
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
import pandas as pd
import pytest
from stock_tools.data.pipeline.batch_ingest import BatchPriceIngestor, IngestSummary
from stock_tools.data.storage.parquet import ParquetStore


def _make_price_frame(symbol: str, dates: list[str]) -> pd.DataFrame:
    n = len(dates)
    return pd.DataFrame({
        "symbol": [symbol] * n,
        "date": pd.to_datetime(dates),
        "open": [100.0] * n,
        "high": [105.0] * n,
        "low": [98.0] * n,
        "close": [102.0] * n,
        "volume": [1000] * n,
        "turnover": [102000] * n,
    })


def test_ingest_new_symbol(tmp_path):
    store = ParquetStore(tmp_path)
    mock_provider = MagicMock()
    mock_provider.fetch_daily_prices.return_value = _make_price_frame(
        "2330", ["2026-04-01", "2026-04-02"]
    )
    ingestor = BatchPriceIngestor(mock_provider, store, request_delay=0)
    summary = ingestor.run(["2330"], end_date="2026-04-02")
    assert summary.succeeded == 1
    assert summary.failed == 0
    assert summary.skipped == 0
    assert store.daily_prices_path("2330").exists()


def test_ingest_incremental_update(tmp_path):
    store = ParquetStore(tmp_path)
    existing = _make_price_frame("2330", ["2026-04-01"])
    store.write_daily_prices("2330", existing)

    mock_provider = MagicMock()
    mock_provider.fetch_daily_prices.return_value = _make_price_frame(
        "2330", ["2026-04-02"]
    )
    ingestor = BatchPriceIngestor(mock_provider, store, request_delay=0)
    ingestor.run(["2330"], end_date="2026-04-02")

    loaded = store.read_daily_prices("2330")
    assert len(loaded) == 2
    mock_provider.fetch_daily_prices.assert_called_once_with(
        "2330", start_date="2026-04-02", end_date="2026-04-02"
    )


def test_ingest_skips_up_to_date_symbol(tmp_path):
    store = ParquetStore(tmp_path)
    existing = _make_price_frame("2330", ["2026-04-02"])
    store.write_daily_prices("2330", existing)

    mock_provider = MagicMock()
    ingestor = BatchPriceIngestor(mock_provider, store, request_delay=0)
    summary = ingestor.run(["2330"], end_date="2026-04-02")

    assert summary.skipped == 1
    mock_provider.fetch_daily_prices.assert_not_called()


def test_ingest_continues_after_failure(tmp_path):
    store = ParquetStore(tmp_path)
    mock_provider = MagicMock()
    mock_provider.fetch_daily_prices.side_effect = [
        RuntimeError("API error"),
        _make_price_frame("3008", ["2026-04-02"]),
    ]
    ingestor = BatchPriceIngestor(mock_provider, store, max_workers=1, request_delay=0)
    summary = ingestor.run(["2330", "3008"], end_date="2026-04-02")

    assert summary.failed == 1
    assert summary.succeeded == 1
    assert "2330" in summary.failed_symbols


def test_ingest_raises_when_below_success_threshold(tmp_path):
    store = ParquetStore(tmp_path)
    mock_provider = MagicMock()
    mock_provider.fetch_daily_prices.side_effect = RuntimeError("error")
    ingestor = BatchPriceIngestor(mock_provider, store, max_workers=1, request_delay=0, success_threshold=0.98)
    with pytest.raises(RuntimeError, match="success rate"):
        ingestor.run(["2330", "3008"], end_date="2026-04-02")
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/unit/test_batch_ingest.py -v
```
Expected: `ModuleNotFoundError: No module named 'stock_tools.data.pipeline'`

- [ ] **Step 3: Create pipeline package**

Create `src/stock_tools/data/pipeline/__init__.py` (empty file).

- [ ] **Step 4: Implement BatchPriceIngestor**

Create `src/stock_tools/data/pipeline/batch_ingest.py`:

```python
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
    ) -> None:
        self.provider = provider
        self.store = store
        self.max_workers = max_workers
        self.request_delay = request_delay
        self.success_threshold = success_threshold

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
        start_date = end_date
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
```

- [ ] **Step 5: Run tests to verify they pass**

```
pytest tests/unit/test_batch_ingest.py -v
```
Expected: 5 PASS

- [ ] **Step 6: Run full test suite**

```
pytest -q
```
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add src/stock_tools/data/pipeline/__init__.py src/stock_tools/data/pipeline/batch_ingest.py tests/unit/test_batch_ingest.py
git commit -m "feat(ST-010): implement BatchPriceIngestor with incremental update and rate limiting"
```

---

## Task 6: Add CLI script and mark tasks Done

**Files:**
- Create: `scripts/batch_ingest.py`
- Modify: `docs/tasks.md`

- [ ] **Step 1: Create CLI script**

Create `scripts/batch_ingest.py`:

```python
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
```

- [ ] **Step 2: Check Settings has finmind_api_token**

Read `src/stock_tools/core/config.py`. If `finmind_api_token` field is missing, add:

```python
finmind_api_token: str | None = None
```

- [ ] **Step 3: Run ruff and mypy**

```
ruff check src tests scripts
mypy src tests scripts
```
Expected: no errors. Fix any issues before proceeding.

- [ ] **Step 4: Update docs/tasks.md**

Set ST-009, ST-010, ST-011 status to `Done`.

- [ ] **Step 5: Final commit**

```bash
git add scripts/batch_ingest.py src/stock_tools/core/config.py docs/tasks.md
git commit -m "feat(ST-009,ST-010,ST-011): add CLI script and close Phase 1 tasks"
```

---

## Validation Checklist

Before considering Phase 1 complete:

- [ ] `pytest -q` — all tests pass
- [ ] `ruff check src tests scripts` — no lint errors
- [ ] `mypy src tests scripts` — no type errors
- [ ] `python scripts/batch_ingest.py --help` — CLI prints usage
- [ ] ST-009, ST-010, ST-011 marked Done in `docs/tasks.md`
