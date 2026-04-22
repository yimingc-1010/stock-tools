# Task Board

This file is the shared repository task board for coordinated work across Codex and Claude.

## Statuses

- `Planned`: scoped but not started
- `In Progress`: actively being worked on
- `Blocked`: cannot proceed until another dependency or decision is resolved
- `Review`: implementation exists and is waiting for review or validation
- `Done`: completed and accepted

## Working Rules

- Give every task a stable ID in the form `ST-###`
- Reference the task ID in commits when practical, for example `feat(ST-002): add provider fetch flow`
- Update this board when work starts, pauses, moves to review, or finishes
- Use the `Owner` column to show who is currently driving the task
- Keep longer decision context in `docs/dev-log/`

## Board

| ID | Task | Status | Priority | Owner | Branch | Notes |
|---|---|---|---|---|---|---|
| ST-001 | Establish initial project scaffold | Done | High | Codex | `feat/main-structure` | Initial package layout, docs, config, tests, and tooling are in place |
| ST-002 | Remove launch-directory dependency from default data paths | Done | High | Codex | `feat/main-structure` | Stable project-root discovery is intact and the follow-up fix restores a `mypy`-clean build |
| ST-003 | Build FinMind daily price provider proof of concept | Done | High | Codex | `feat/main-structure` | Pull one symbol and normalize to the daily price contract; provider contract tests and `scripts/finmind_daily_price_poc.py` added |
| ST-004 | Add Parquet round-trip flow for daily prices and adjustment factors | Done | High | Codex | `feat/main-structure` | Persist raw prices separately from adjustment data; added round-trip dataset flow/tests and `scripts/parquet_roundtrip_poc.py` |
| ST-005 | Expand TWSE calendar beyond weekday defaults | Done | Medium | Codex | `feat/main-structure` | Add official closures and exchange-specific overrides |
| ST-006 | Add fixed local fixtures for data-layer tests | Done | Medium | Codex | `feat/main-structure` | Added `tests/fixtures/*.csv` and wired round-trip tests to fixed local fixtures |
| ST-007 | Create end-to-end research notebook | Done | Medium | Codex | `feat/main-structure` | Added `notebooks/end_to_end_research.ipynb` for fetch -> store -> load -> plot validation |
| ST-008 | Decide whether to rename default branch to `main` | Done | Low | Codex | `feat/main-structure` | Decision captured in `docs/branch-decision.md`: keep `master` for now and revisit after remote policy is stable |
| ST-009 | Universe / Security Master provider + dataset | Planned | High | — | — | FinMind `TaiwanStockInfo` provider; implement `universe.py`; `get_active_symbols(date)` for point-in-time safety |
| ST-010 | Batch price ingestion pipeline | Planned | High | — | — | Incremental update for 1,700+ symbols; rate-limited (3 workers, 0.5s delay); blocked by ST-009 |
| ST-011 | Real adjustment factor provider | Planned | High | — | — | FinMind `TaiwanStockPriceAdj`; replace empty stub with actual corporate-action data |
| ST-012 | Technical indicators | Planned | High | — | — | EMA, RSI, MACD, KD, Bollinger in `research/indicators.py` |
| ST-013 | Technical screener tool | Planned | High | — | — | `TechnicalScreener.run(date, conditions)` returning serializable DataFrame; blocked by ST-012 |
| ST-014 | vectorbt adapter | Planned | Medium | — | — | `run_backtest(symbols, signal_fn, ...)` with Taiwan cost model; blocked by ST-011 |
| ST-015 | Performance metrics extensions | Planned | Medium | — | — | `sharpe_ratio`, `calmar_ratio`, `win_rate` in `backtest/metrics.py` |
| ST-016 | Fundamental provider | Planned | Medium | — | — | FinMind financial statements (損益表、資產負債表、現金流量表) |
| ST-017 | Fundamental dataset + screener | Planned | Medium | — | — | Implement `fundamentals.py`; `FundamentalScreener.run(date, conditions)`; blocked by ST-016 |
| ST-018 | Institutional investors provider + dataset | Planned | Low | — | — | FinMind `TaiwanStockInstitutionalInvestors` (三大法人) |
| ST-019 | Margin / short provider + dataset | Planned | Low | — | — | FinMind `TaiwanStockMarginPurchaseShortSale` (融資融券) |
| ST-020 | Chip screener tool | Planned | Low | — | — | `ChipScreener.run(date, conditions)`; blocked by ST-018, ST-019 |
