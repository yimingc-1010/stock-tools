from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Iterable

import pandas as pd


def _normalize_day(value: date | datetime | pd.Timestamp | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, str):
        return pd.Timestamp(value).date()
    return value


@dataclass(frozen=True)
class TradingCalendar:
    """Simple trading calendar with injectable closures and make-up trading days."""

    holidays: frozenset[date] = field(default_factory=frozenset)
    extra_open_days: frozenset[date] = field(default_factory=frozenset)
    open_weekdays: frozenset[int] = field(default_factory=lambda: frozenset({0, 1, 2, 3, 4}))

    def is_trading_day(self, value: date | datetime | pd.Timestamp | str) -> bool:
        day = _normalize_day(value)
        if day in self.extra_open_days:
            return True
        if day in self.holidays:
            return False
        return day.weekday() in self.open_weekdays

    def sessions_between(
        self,
        start: date | datetime | pd.Timestamp | str,
        end: date | datetime | pd.Timestamp | str,
    ) -> pd.DatetimeIndex:
        start_day = _normalize_day(start)
        end_day = _normalize_day(end)
        if end_day < start_day:
            raise ValueError("end must be on or after start")

        days = pd.date_range(start_day, end_day, freq="D")
        sessions = [ts for ts in days if self.is_trading_day(ts)]
        return pd.DatetimeIndex(sessions)

    def next_session(
        self,
        value: date | datetime | pd.Timestamp | str,
        *,
        inclusive: bool = False,
    ) -> date:
        day = _normalize_day(value)
        if inclusive and self.is_trading_day(day):
            return day

        cursor = day + timedelta(days=1)
        while not self.is_trading_day(cursor):
            cursor += timedelta(days=1)
        return cursor

    def previous_session(
        self,
        value: date | datetime | pd.Timestamp | str,
        *,
        inclusive: bool = False,
    ) -> date:
        day = _normalize_day(value)
        if inclusive and self.is_trading_day(day):
            return day

        cursor = day - timedelta(days=1)
        while not self.is_trading_day(cursor):
            cursor -= timedelta(days=1)
        return cursor

    @classmethod
    def from_overrides(
        cls,
        *,
        holidays: Iterable[date] = (),
        extra_open_days: Iterable[date] = (),
    ) -> "TradingCalendar":
        return cls(
            holidays=frozenset(holidays),
            extra_open_days=frozenset(extra_open_days),
        )


def build_twse_calendar() -> TradingCalendar:
    """Return a TWSE calendar shell to be extended with official exchange closures."""

    return TradingCalendar()

