from datetime import date

from stock_tools.core.calendar import TradingCalendar, build_twse_calendar


def test_weekend_is_not_trading_day() -> None:
    calendar = TradingCalendar()
    assert calendar.is_trading_day(date(2026, 4, 18)) is False


def test_holiday_override_blocks_weekday() -> None:
    calendar = TradingCalendar.from_overrides(holidays=[date(2026, 4, 20)])
    assert calendar.is_trading_day(date(2026, 4, 20)) is False


def test_extra_open_day_overrides_weekend() -> None:
    calendar = TradingCalendar.from_overrides(extra_open_days=[date(2026, 4, 18)])
    assert calendar.is_trading_day(date(2026, 4, 18)) is True


def test_next_session_skips_weekend() -> None:
    calendar = TradingCalendar()
    assert calendar.next_session(date(2026, 4, 17)) == date(2026, 4, 20)


def test_twse_calendar_marks_official_holiday_as_closed() -> None:
    calendar = build_twse_calendar()
    assert calendar.is_trading_day(date(2026, 4, 3)) is False


def test_twse_calendar_skips_lunar_new_year_closure_block() -> None:
    calendar = build_twse_calendar()
    assert calendar.next_session(date(2026, 2, 11)) == date(2026, 2, 23)

