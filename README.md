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

