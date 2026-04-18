# Architecture

## MVP modules

### `core`

- Shared services that should not depend on any provider implementation
- Includes config loading, calendar logic, and DataFrame schema helpers

### `data`

- Owns all external data integration
- `providers/` fetch raw data
- `storage/` persists raw and curated datasets
- `datasets/` exposes stable read/write interfaces to the rest of the codebase

### `research`

- Stateless analytics built on datasets
- Includes indicators, screeners, and signal generation

### `backtest`

- Starts as adapter and metric utilities
- Avoids committing to a custom engine until the data contract is stable

## Data design principles

- Keep prices in raw form and store adjustment factors separately
- Carry `announcement_date` alongside `report_period` for fundamental data
- Preserve delisted symbols in the security master and universe definitions
- Use DataFrames internally; validate column contracts close to dataset boundaries

## Initial dataset contracts

### Daily prices

Required columns:

- `symbol`
- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `turnover`

Optional early columns:

- `trades`
- `market`
- `source`

### Adjustment factors

Required columns:

- `symbol`
- `effective_date`
- `adjustment_factor`
- `event_type`

### Fundamentals

Required columns:

- `symbol`
- `report_period`
- `announcement_date`
- `metric`
- `value`

### Security master / universe

Required columns:

- `symbol`
- `name`
- `security_type`
- `market`
- `list_date`
- `delist_date`

## Near-term roadmap

1. Finish the provider-to-Parquet flow for one symbol
2. Add a notebook for end-to-end validation
3. Introduce a security master dataset and point-in-time helpers
4. Evaluate the first backtest adapter against real research outputs

