from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import HTTPStatusError, Request, Response

from pep_api.adapters.binance import BinanceSpotAPIClient
from pep_api.schemas.binance import BinanceKlinesOutputSchema, BinanceKlinesParametersSchema


class TestBinanceSpotAPIClient:
	"""Tests for BinanceSpotAPIClient."""

	@pytest.fixture
	def client(self) -> BinanceSpotAPIClient:
		"""Create a BinanceSpotAPIClient with a mock session."""
		return BinanceSpotAPIClient(session=AsyncMock())  # type: ignore[arg-name, missing-argument]

	@pytest.mark.parametrize(
		"interval",
		[
			"1h",
			"2h",
		],
	)
	async def test_klines_returns_ohlcv_data(
		self,
		client: BinanceSpotAPIClient,
		interval: str,
	) -> None:
		"""Test that klines returns properly parsed OHLCV data."""
		start_time = datetime(2026, 4, 10, 0, 0, 0, tzinfo=timezone.utc)
		end_time = datetime(2026, 4, 10, 2, 0, 0, tzinfo=timezone.utc)
		parameters_schema = BinanceKlinesParametersSchema(
			ticker="BTCUSDT",
			section="spot",
			interval=interval,
			start_time=start_time,
			end_time=end_time,
		)

		raw_klines = [
			[
				1744320000000,
				"95164.01",
				"95691.00",
				"94833.00",
				"95320.00",
				"1234.56",
				1744406399999,
				"9876.54",
				100,
				"5432.10",
				"3210.00",
				"0",
			],
			[
				1744406400000,
				"95320.00",
				"96000.00",
				"95000.00",
				"95700.00",
				"2345.67",
				1744492799999,
				"8765.43",
				200,
				"4321.00",
				"2100.00",
				"0",
			],
		]

		mock_response = Response(
			status_code=200,
			json=raw_klines,
			request=mock_request,
		)
		mock_session.request = AsyncMock(return_value=mock_response)

		result = await client.klines(parameters_schema=parameters_schema)

		assert len(result) == 2
		assert all(isinstance(kline, BinanceKlinesOutputSchema) for kline in result)
		assert result[0].ticker == "BTCUSDT"
		assert result[0].section == "spot"
		assert result[0].interval == interval
		assert result[0].open == 95164.01
		assert result[0].high == 95691.00
		assert result[0].low == 94833.00
		assert result[0].close == 95320.00
		assert result[0].volume == 1234.56
		assert result[1].ticker == "BTCUSDT"
		assert result[1].close == 95700.00

	async def test_ping_returns_none_on_success(
		self,
		client: BinanceSpotAPIClient,
		mock_session: AsyncMock,
		mock_request: Request,
	) -> None:
		"""Test that ping returns None on successful API call."""
		mock_response = Response(status_code=200, request=mock_request)
		mock_session.request = AsyncMock(return_value=mock_response)

		result = await client.ping()

		assert result is None
		mock_session.request.assert_called_once()
		call_kwargs = mock_session.request.call_args.kwargs
		assert call_kwargs["method"] == "GET"
