# Screener & Backtest System Design

**Date:** 2026-04-23
**Status:** Approved

## Context

The stock-tools project currently has a working data layer for single-symbol daily prices (FinMind provider + Parquet storage). The next phase extends this into a multi-symbol screening and backtesting system, intended to serve as supporting tools for an agent / Telegram bot.

## Goals

- Daily batch ingestion of price data for all TWSE + TPEx listed stocks (~1,700 symbols)
- Technical screener tool that returns a filtered, serializable candidate list
- Fundamental screener tool (second priority)
- Chip screener tool (third priority)
- Backtesting tool wrapping vectorbt, with Taiwan market cost model

## Non-Goals

- Real-time / intraday data
- Order management or live trading
- Custom backtest engine (vectorbt is the chosen adapter)
- Plugin-driven screener configuration (YAGNI)

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Agent / Telegram Bot                               │
├─────────────┬───────────────────────────────────────┤
│  Screener   │  Backtest Tool                        │
│  Tools      │  (vectorbt adapter)                   │
├─────────────┴───────────────────────────────────────┤
│  Indicators Layer                                   │
│  (technical / fundamental / chip)                   │
├─────────────────────────────────────────────────────┤
│  Datasets Layer                                     │
│  prices / adjustments / universe / fundamentals /   │
│  institutional / margin                             │
├─────────────────────────────────────────────────────┤
│  Batch Pipeline                                     │
│  rate-limited incremental ingestion                 │
├─────────────────────────────────────────────────────┤
│  Providers                                          │
│  FinMind: price / universe / fundamentals / chip    │
├─────────────────────────────────────────────────────┤
│  Storage: Parquet                                   │
└─────────────────────────────────────────────────────┘
```

**Principle:** Each layer only exposes clean interfaces to the layer above. Screener / Backtest tools never call providers directly — they read from datasets only.

## Universe / Security Master

**Provider:** FinMind `TaiwanStockInfo`
**Dataset:** implements `src/stock_tools/data/datasets/universe.py`
**Storage:** `data/curated/security_master/master.parquet`

Key interface:
```python
SecurityMasterDataset.save(frame: pd.DataFrame) -> None
SecurityMasterDataset.load() -> pd.DataFrame
SecurityMasterDataset.get_active_symbols(date: str) -> list[str]
```

`get_active_symbols` filters on `list_date <= date` and (`delist_date` is NaT or `delist_date > date`). This ensures point-in-time safety for both screener and backtest.

## Batch Pipeline

**Location:** `src/stock_tools/data/pipeline/batch_ingest.py`
**Script:** `scripts/batch_ingest.py --date YYYY-MM-DD`

Behaviour:
- Loads full symbol list from `SecurityMasterDataset`
- For each symbol, reads last stored date from local Parquet; fetches only missing range
- Concurrency: configurable (default 3 workers), with per-request delay (default 0.5s)
- Failed symbols are logged and skipped; pipeline always completes
- Prints summary: succeeded / failed / skipped counts

The pipeline is the only component that calls providers. All downstream layers read from local storage.

## Technical Indicators

**Location:** `src/stock_tools/research/indicators.py` (extend existing)

| Indicator | Function signature |
|---|---|
| EMA | `ema(series, window) -> Series` |
| RSI | `rsi(series, window=14) -> Series` |
| MACD | `macd(series, fast, slow, signal) -> (macd, signal, hist)` |
| KD | `kdj(high, low, close, n=9) -> (k, d)` |
| Bollinger | `bollinger(series, window=20, std=2) -> (upper, mid, lower)` |

All functions accept `pd.Series` / `pd.DataFrame`, return `pd.Series` or named tuple. No side effects.

## Technical Screener Tool

**Location:** `src/stock_tools/research/screeners.py` (extend existing)

```python
screener = TechnicalScreener(price_dataset, universe_dataset)
result: pd.DataFrame = screener.run(
    date="2026-04-23",
    conditions={
        "rsi_below": 30,
        "price_above_ema": 20,
        "macd_golden_cross": True,
    }
)
```

- `date` drives `get_active_symbols` for universe, and selects the lookback window from local prices
- Conditions are a plain dict; unsupported keys raise `ValueError`
- Output is a DataFrame with fixed columns: `symbol, close, <indicator columns>, matched_conditions`
- Output is `.to_dict(orient="records")` serializable for agent/bot consumption
- No network calls inside `run()`

## Fundamental Screener (Phase 4)

**Provider:** FinMind financial statements (`TaiwanStockFinancialStatements`, `TaiwanStockBalanceSheet`, `TaiwanStockCashFlowsStatement`)
**Dataset:** implements `src/stock_tools/data/datasets/fundamentals.py`

Uses `announcement_date` (not `report_period`) for point-in-time safety — no look-ahead on earnings.

```python
screener = FundamentalScreener(fundamental_dataset, universe_dataset)
result = screener.run(date="2026-04-23", conditions={"pe_below": 15, "roe_above": 0.15})
```

## Chip Screener (Phase 5)

**Providers:**
- FinMind `TaiwanStockInstitutionalInvestors` → institutional investors (三大法人)
- FinMind `TaiwanStockMarginPurchaseShortSale` → margin / short

```python
screener = ChipScreener(institutional_dataset, margin_dataset, universe_dataset)
result = screener.run(date="2026-04-23", conditions={"foreign_net_buy_days": 3})
```

## Backtest Tool

**Location:** `src/stock_tools/backtest/adapters/vectorbt_adapter.py`

```python
result: dict = run_backtest(
    symbols=["2330", "2317"],
    signal_fn=my_signal_fn,      # (prices: DataFrame) -> bool DataFrame
    start_date="2024-01-01",
    end_date="2026-04-23",
    initial_capital=1_000_000,
    fee_rate=0.001425,
    tax_rate=0.003,
)
# result keys: total_return, sharpe_ratio, max_drawdown, calmar_ratio, win_rate, trade_count
```

- `signal_fn` is the sole strategy entry point; output from `TechnicalScreener` can be wrapped into one
- Prices are adjusted using `AdjustmentFactorDataset` before passing to vectorbt
- `backtest/metrics.py` extended with `sharpe_ratio`, `calmar_ratio`, `win_rate`
- Result dict is JSON-serializable

## Performance Metrics Extensions

Add to `src/stock_tools/backtest/metrics.py`:
- `sharpe_ratio(returns, risk_free_rate=0.0) -> float`
- `calmar_ratio(total_return, max_drawdown) -> float`
- `win_rate(trades: pd.DataFrame) -> float`

## Task Plan

### Phase 1: Data Foundation
| ID | Task |
|---|---|
| ST-009 | Universe / Security Master provider + dataset |
| ST-010 | Batch price ingestion pipeline |
| ST-011 | Real adjustment factor provider (FinMind TaiwanStockPriceAdj) |

### Phase 2: Technical Screening
| ID | Task |
|---|---|
| ST-012 | Technical indicators (EMA, RSI, MACD, KD, Bollinger) |
| ST-013 | Technical screener tool |

### Phase 3: Backtest
| ID | Task |
|---|---|
| ST-014 | vectorbt adapter |
| ST-015 | Performance metrics extensions (Sharpe, Calmar, win_rate) |

### Phase 4: Fundamental Screening
| ID | Task |
|---|---|
| ST-016 | Fundamental provider (FinMind financial statements) |
| ST-017 | Fundamental dataset + screener tool |

### Phase 5: Chip Screening
| ID | Task |
|---|---|
| ST-018 | Institutional investors provider + dataset |
| ST-019 | Margin / short provider + dataset |
| ST-020 | Chip screener tool |

## Dependencies

- ST-010 blocked by ST-009 (needs universe to get symbol list)
- ST-013 blocked by ST-012 (needs indicators)
- ST-014 blocked by ST-011 (needs adjusted prices)
- ST-017 blocked by ST-016
- ST-020 blocked by ST-018, ST-019
