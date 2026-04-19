# stock-tools

Taiwan stock research toolkit focused on a data-first workflow:

- `data`: providers, storage, and dataset access
- `core`: calendar, config, and schema helpers
- `research`: indicators, screeners, and signal generation
- `backtest`: adapters and performance metrics

## Workflow

Each development session starts with a development log entry under `docs/dev-log/`.

## FinMind daily price provider POC

Use the script wrapper to fetch and normalize one symbol:

`python3 scripts/finmind_daily_price_poc.py --symbol 2330 --start-date 2024-01-02 --end-date 2024-01-10`

## Parquet round-trip POC (daily prices + adjustment factors)

Use the script wrapper to fetch one symbol, persist raw + curated daily prices, and persist
adjustment factors in a separate dataset file:

`python3 scripts/parquet_roundtrip_poc.py --symbol 2330 --start-date 2024-01-02 --end-date 2024-01-10`

## Task execution loop (implement -> review -> test)

Run an interactive loop that processes `docs/tasks.md` in order. For each unfinished task, it
waits for implementation, then runs review/test gates (`pytest`, `ruff`, `mypy`) and marks the
task `Done` only when all checks pass.

`python3 scripts/task_review_test_loop.py`

## End-to-end research notebook

Use `notebooks/end_to_end_research.ipynb` to walk through fetch -> store -> load -> plot for one
symbol using the current data-layer contracts.

