from __future__ import annotations

import pandas as pd


def total_return(equity_curve: pd.Series) -> float:
    if equity_curve.empty:
        return 0.0
    start = float(equity_curve.iloc[0])
    end = float(equity_curve.iloc[-1])
    if start == 0:
        raise ValueError("starting equity must be non-zero")
    return end / start - 1.0


def max_drawdown(equity_curve: pd.Series) -> float:
    if equity_curve.empty:
        return 0.0
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1.0
    return float(drawdown.min())

