from __future__ import annotations

from typing import Any

import pytest

from stock_tools.data.providers.finmind import FinMindPriceProvider


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self) -> dict[str, Any]:
        return self._payload


def test_fetch_daily_prices_normalizes_response(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_get(url: str, params: dict[str, Any], timeout: int) -> _FakeResponse:
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return _FakeResponse(
            {
                "status": 200,
                "data": [
                    {
                        "date": "2024-01-03",
                        "open": 10.0,
                        "max": 12.0,
                        "min": 9.5,
                        "close": 11.0,
                        "Trading_Volume": 100,
                        "Trading_money": 1100,
                    },
                    {
                        "date": "2024-01-02",
                        "open": 9.0,
                        "max": 10.0,
                        "min": 8.5,
                        "close": 9.5,
                        "Trading_Volume": 90,
                        "Trading_money": 900,
                    },
                ],
            }
        )

    monkeypatch.setattr("stock_tools.data.providers.finmind.requests.get", fake_get)

    provider = FinMindPriceProvider(api_token="secret", timeout=12)
    frame = provider.fetch_daily_prices(
        symbol="2330",
        start_date="2024-01-01",
        end_date="2024-01-31",
    )

    assert captured["url"] == provider.base_url
    assert captured["timeout"] == 12
    assert captured["params"] == {
        "dataset": "TaiwanStockPrice",
        "data_id": "2330",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "token": "secret",
    }

    expected_columns = ["symbol", "date", "open", "high", "low", "close", "volume", "turnover"]
    assert frame.columns.tolist() == expected_columns
    assert frame["symbol"].tolist() == ["2330", "2330"]
    assert frame["date"].dt.strftime("%Y-%m-%d").tolist() == ["2024-01-02", "2024-01-03"]
    assert frame["high"].tolist() == [10.0, 12.0]
    assert frame["low"].tolist() == [8.5, 9.5]
    assert frame["volume"].tolist() == [90, 100]
    assert frame["turnover"].tolist() == [900, 1100]


def test_fetch_daily_prices_raises_on_api_error_status(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, params: dict[str, Any], timeout: int) -> _FakeResponse:
        del url, params, timeout
        return _FakeResponse({"status": 402, "msg": "quota exceeded", "data": []})

    monkeypatch.setattr("stock_tools.data.providers.finmind.requests.get", fake_get)

    provider = FinMindPriceProvider()
    with pytest.raises(RuntimeError, match="status=402"):
        provider.fetch_daily_prices(symbol="2330")


def test_normalize_price_frame_raises_when_required_columns_are_missing() -> None:
    provider = FinMindPriceProvider()

    with pytest.raises(ValueError, match="missing required columns"):
        provider.normalize_price_frame(
            symbol="2330",
            payload={
                "data": [
                    {
                        "date": "2024-01-02",
                        "open": 10.0,
                        "max": 10.5,
                        "min": 9.5,
                        "close": 10.0,
                    }
                ]
            },
        )


def test_normalize_price_frame_returns_contract_columns_for_empty_payload() -> None:
    provider = FinMindPriceProvider()
    frame = provider.normalize_price_frame(symbol="2330", payload={"data": []})

    assert frame.empty
    expected_columns = ["symbol", "date", "open", "high", "low", "close", "volume", "turnover"]
    assert frame.columns.tolist() == expected_columns
