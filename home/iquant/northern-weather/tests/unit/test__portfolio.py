from datetime import date

import polars as pl
import pytest

from messoyakha_northern_weather.entrypoints.portfolio import adjusted_close_prices, returns


class TestPortfolioReturns:
    def test_returns_align_dividend_dates_and_sparse_prices(self) -> None:
        ohlcv = pl.DataFrame(
            {
                "timestamp": [
                    date(2024, 1, 1),
                    date(2024, 1, 2),
                    date(2024, 1, 3),
                    date(2024, 1, 1),
                    date(2024, 1, 2),
                    date(2024, 1, 3),
                ],
                "ticker": ["AAA", "AAA", "AAA", "BBB", "BBB", "BBB"],
                "close": [100.0, 90.0, 92.0, 50.0, 50.5, 51.0],
            }
        )
        dividends = pl.DataFrame(
            {
                "timestamp": [date(2024, 1, 2)],
                "ticker": ["AAA"],
                "dividend": [10.0],
            }
        )

        adjusted = adjusted_close_prices(ohlcv, dividends)
        result = returns(ohlcv, dividends)

        assert adjusted.loc[date(2024, 1, 2), "AAA"] == pytest.approx(100.0)
        assert result.index.tolist() == [date(2024, 1, 2), date(2024, 1, 3)]
        assert result["AAA"].tolist() == pytest.approx([0.0, 92.0 / 90.0 - 1.0])
