from __future__ import annotations

import pandas as pd


def crossover_signal(fast: pd.Series, slow: pd.Series) -> pd.Series:
    crossed = (fast > slow) & (fast.shift(1) <= slow.shift(1))
    return crossed.fillna(False)

