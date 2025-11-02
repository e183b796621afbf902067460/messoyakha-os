from httpx import Response

from src.adapters.clients.common.api_base import APIClientBase
from src.schemas.domain.binance import BinanceKlinesInputSchema, BinanceKlinesOutputSchema


class _BinanceAPIClientExceptionBase(Exception):
    """Base Binance client exception to inherit from."""


class _BinanceAPIClientInvalidMethod(_BinanceAPIClientExceptionBase):
    """Raises only and only if invalid method was passed."""


class BinanceAPIClientBase(APIClientBase):

    _ping_endpoint: str
    _klines_endpoint: str

    async def ping(self) -> None:
        ping: Response | None = await self._get(endpoint=self._ping_endpoint)

        if ping is None:
            raise _BinanceAPIClientInvalidMethod(f"Invalid method was passed to `{self._ping_endpoint}` endpoint.")

    async def klines(self, input_schema: BinanceKlinesInputSchema) -> list[BinanceKlinesOutputSchema]:
        klines: Response | None = await self._get(
            endpoint=self._klines_endpoint, parameters=input_schema.model_dump(by_alias=True)
        )

        if klines is None:
            raise _BinanceAPIClientInvalidMethod(f"Invalid method was passed to `{self._klines_endpoint}` endpoint.")

        return [
            BinanceKlinesOutputSchema.from_kline(
                kline=kline, ticker=input_schema.ticker, section=input_schema.section, interval=input_schema.interval
            )
            for kline in klines.json()
        ]


class BinanceSpotAPIClient(BinanceAPIClientBase):

    _ping_endpoint: str = "/api/v3/ping"

    # https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints#klinecandlestick-data
    _klines_endpoint: str = "/api/v3/klines"


class BinanceUsdtmAPIClient(BinanceAPIClientBase):

    _ping_endpoint: str = "/fapi/v1/ping"

    # https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data
    _klines_endpoint: str = "/fapi/v1/klines"
