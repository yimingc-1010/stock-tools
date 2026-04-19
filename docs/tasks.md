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
| ST-002 | Remove launch-directory dependency from default data paths | Review | High | Codex | `feat/main-structure` | Stable project-root discovery is intact and the follow-up fix restores a `mypy`-clean build |
| ST-003 | Build FinMind daily price provider proof of concept | Planned | High | Unassigned | `feat/main-structure` | Pull one symbol and normalize to the daily price contract |
| ST-004 | Add Parquet round-trip flow for daily prices and adjustment factors | Planned | High | Unassigned | `feat/main-structure` | Persist raw prices separately from adjustment data |
| ST-005 | Expand TWSE calendar beyond weekday defaults | Planned | Medium | Unassigned | `feat/main-structure` | Add official closures and exchange-specific overrides |
| ST-006 | Add fixed local fixtures for data-layer tests | Planned | Medium | Unassigned | `feat/main-structure` | Keep unit tests fully offline and reproducible |
| ST-007 | Create end-to-end research notebook | Planned | Medium | Unassigned | `feat/main-structure` | Validate fetch -> store -> load -> plot workflow |
| ST-008 | Decide whether to rename default branch to `main` | Planned | Low | Unassigned | `feat/main-structure` | Current local default branch is still `master`, active work is on `feat/main-structure` |
