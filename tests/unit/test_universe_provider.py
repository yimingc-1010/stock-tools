from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from stock_tools.data.providers.universe import UniverseProvider

MOCK_RESPONSE = {
    "status": 200,
    "data": [
        {
            "stock_id": "2330",
            "stock_name": "台積電",
            "type": "twse",
            "date": "2024-01-01",
            "industry_category": "半導體業",
            "market_category": "上市",
        },
        {
            "stock_id": "6488",
            "stock_name": "環球晶",
            "type": "otc",
            "date": "2024-01-01",
            "industry_category": "半導體業",
            "market_category": "上櫃",
        },
        {
            "stock_id": "5483",
            "stock_name": "中美晶",
            "type": "rotc",
            "date": "2024-01-01",
            "industry_category": "半導體業",
            "market_category": "興櫃",
        },
    ],
}


def _mock_get(response_data: dict[str, object]) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.json.return_value = response_data
    mock_resp.raise_for_status.return_value = None
    return mock_resp


@patch("stock_tools.data.providers.universe.requests.get")
def test_fetch_normalises_columns(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_get(MOCK_RESPONSE)
    provider = UniverseProvider()
    frame = provider.fetch_all()
    assert list(frame.columns) == [
        "symbol",
        "name",
        "security_type",
        "market",
        "list_date",
        "delist_date",
    ]
    assert frame["symbol"].tolist() == ["2330", "6488", "5483"]
    assert frame["name"].tolist() == ["台積電", "環球晶", "中美晶"]
    assert frame["market"].tolist() == ["TWSE", "TPEx", "TPEx"]
    assert (frame["security_type"] == "stock").all()


@patch("stock_tools.data.providers.universe.requests.get")
def test_fetch_raises_on_api_error(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_get({"status": 402, "msg": "invalid token"})
    provider = UniverseProvider()
    with pytest.raises(RuntimeError, match="FinMind API error"):
        provider.fetch_all()


@patch("stock_tools.data.providers.universe.requests.get")
def test_fetch_empty_payload(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_get({"status": 200, "data": []})
    provider = UniverseProvider()
    frame = provider.fetch_all()
    assert frame.empty
    assert list(frame.columns) == [
        "symbol",
        "name",
        "security_type",
        "market",
        "list_date",
        "delist_date",
    ]


@patch("stock_tools.data.providers.universe.requests.get")
def test_fetch_maps_unknown_type_to_other(mock_get: MagicMock) -> None:
    mock_get.return_value = _mock_get(
        {
            "status": 200,
            "data": [
                {
                    "stock_id": "9999",
                    "stock_name": "未知類型",
                    "type": "foo",
                    "date": "2024-01-01",
                    "industry_category": "其他",
                    "market_category": "其他",
                },
            ],
        }
    )
    provider = UniverseProvider()
    frame = provider.fetch_all()
    assert frame["market"].tolist() == ["OTHER"]
