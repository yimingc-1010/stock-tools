from __future__ import annotations

import pandas as pd


def filter_frame(frame: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    return frame.loc[mask].copy()

