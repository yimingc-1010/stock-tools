from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from stock_tools.data.providers.adjustment import FinMindAdjustmentProvider

MOCK_DIVIDEND_RESPONSE = {
    "status": 200,
    "data": [
        {
            "stock_id": "2330",
            "date": "2023-06-15",
            "ExDividendDate": "2023-07-18",
            "CashDividend": 3.0,
            "StockDividend": 0.0,
        },
        {
            "stock_id": "2330",
            "date": "2022-06-10",
            "ExDividendDate": "2022-07-13",
            "CashDividend": 0.0,
            "StockDividend": 50.0,
        },
    ],
}


def _mock_get(data: dict[str, object]) -> MagicMock:
    m = MagicMock()
    m.json.return_value = data
    m.raise_for_status.return_value = None
    return m


@patch("stock_tools.data.providers.adjustment.requests.get")
def test_fetch_returns_required_columns(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_get(MOCK_DIVIDEND_RESPONSE)
    provider = FinMindAdjustmentProvider()
    frame = provider.fetch_adjustment_factors("2330")
    assert list(frame.columns) == ["symbol", "effective_date", "adjustment_factor", "event_type"]


@patch("stock_tools.data.providers.adjustment.requests.get")
def test_stock_dividend_factor(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_get(MOCK_DIVIDEND_RESPONSE)
    provider = FinMindAdjustmentProvider()
    frame = provider.fetch_adjustment_factors("2330")
    stock_row = frame[frame["effective_date"] == pd.Timestamp("2022-07-13")].iloc[0]
    expected_factor = 1000 / (1000 + 50.0)
    assert abs(stock_row["adjustment_factor"] - expected_factor) < 1e-9


@patch("stock_tools.data.providers.adjustment.requests.get")
def test_cash_dividend_with_price_frame(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_get(MOCK_DIVIDEND_RESPONSE)
    price_frame = pd.DataFrame(
        {
            "symbol": ["2330"] * 3,
            "date": pd.to_datetime(["2023-07-14", "2023-07-17", "2023-07-18"]),
            "close": [550.0, 548.0, 545.0],
        }
    )
    provider = FinMindAdjustmentProvider()
    frame = provider.fetch_adjustment_factors("2330", price_frame=price_frame)
    cash_row = frame[frame["effective_date"] == pd.Timestamp("2023-07-18")].iloc[0]
    expected_factor = (548.0 - 3.0) / 548.0  # close on day before ex-date
    assert abs(cash_row["adjustment_factor"] - expected_factor) < 1e-9


@patch("stock_tools.data.providers.adjustment.requests.get")
def test_api_error_raises(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_get({"status": 402, "msg": "quota exceeded"})
    provider = FinMindAdjustmentProvider()
    with pytest.raises(RuntimeError, match="FinMind API error"):
        provider.fetch_adjustment_factors("2330")


@patch("stock_tools.data.providers.adjustment.requests.get")
def test_empty_payload(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_get({"status": 200, "data": []})
    provider = FinMindAdjustmentProvider()
    frame = provider.fetch_adjustment_factors("2330")
    assert frame.empty
    assert list(frame.columns) == ["symbol", "effective_date", "adjustment_factor", "event_type"]


@patch("stock_tools.data.providers.adjustment.requests.get")
def test_cash_dividend_with_price_frame_missing_prior(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_get(MOCK_DIVIDEND_RESPONSE)
    # price_frame only has dates on or after ex-date 2023-07-18
    price_frame = pd.DataFrame({
        "symbol": ["2330"] * 2,
        "date": pd.to_datetime(["2023-07-18", "2023-07-19"]),
        "close": [545.0, 548.0],
    })
    provider = FinMindAdjustmentProvider()
    frame = provider.fetch_adjustment_factors("2330", price_frame=price_frame)
    cash_row = frame[frame["effective_date"] == pd.Timestamp("2023-07-18")].iloc[0]
    # No prior close available -> cash_factor falls back to 1.0
    assert cash_row["adjustment_factor"] == 1.0


@patch("stock_tools.data.providers.adjustment.requests.get")
def test_cash_dividend_with_zero_prev_close(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_get(MOCK_DIVIDEND_RESPONSE)
    price_frame = pd.DataFrame({
        "symbol": ["2330"] * 2,
        "date": pd.to_datetime(["2023-07-14", "2023-07-17"]),
        "close": [550.0, 0.0],  # prior close = 0 (data error / suspended)
    })
    provider = FinMindAdjustmentProvider()
    frame = provider.fetch_adjustment_factors("2330", price_frame=price_frame)
    cash_row = frame[frame["effective_date"] == pd.Timestamp("2023-07-18")].iloc[0]
    # prev_close == 0 -> cash_factor falls back to 1.0
    assert cash_row["adjustment_factor"] == 1.0
