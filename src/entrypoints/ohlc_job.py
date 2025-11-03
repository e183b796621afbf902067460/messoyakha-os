from asyncio import run
from typing import Literal

from attr import attrib, attrs
from httpx import AsyncClient as HTTPAsyncClient
from httpx import AsyncHTTPTransport

from src.adapters.clients.binance import BinanceAPIClientBase, BinanceSpotAPIClient, BinanceUsdtmAPIClient
from src.entrypoints.commmon.ohlc_base import main
from src.services.domain.binance import BinanceService
from src.settings import settings

_SPOT_BINANCE_SECTION: Literal["SPOT"] = "SPOT"
_USDTM_BINANCE_SECTION: Literal["USDT-M"] = "USDT-M"


# TODO: create abstract factory for different exchanges
@attrs(slots=True, auto_attribs=True, kw_only=True)
class _BinanceAPIClientFactory:
    _factory: dict[str, BinanceAPIClientBase] = attrib(init=False, default={})

    def _add_binance_api_client(self, binance_section: str, binance_api_client: BinanceAPIClientBase) -> None:
        self._factory[binance_section] = binance_api_client

    def __attrs_post_init__(self) -> None:
        self._add_binance_api_client(
            binance_section=_SPOT_BINANCE_SECTION,
            binance_api_client=BinanceSpotAPIClient(
                session=HTTPAsyncClient(
                    base_url="https://api.binance.com",
                    timeout=60,
                    transport=AsyncHTTPTransport(retries=3, http2=True),
                    follow_redirects=True,
                )
            ),
        )
        self._add_binance_api_client(
            binance_section=_USDTM_BINANCE_SECTION,
            binance_api_client=BinanceUsdtmAPIClient(
                session=HTTPAsyncClient(
                    base_url="https://fapi.binance.com",
                    timeout=60,
                    transport=AsyncHTTPTransport(retries=3, http2=True),
                    follow_redirects=True,
                )
            ),
        )

    def get_binance_api_client(self, binance_section: str) -> BinanceAPIClientBase | None:
        return self._factory.get(binance_section)


if __name__ == "__main__":
    binance_api_client_factory: _BinanceAPIClientFactory = _BinanceAPIClientFactory()
    api_client: BinanceAPIClientBase | None = binance_api_client_factory.get_binance_api_client(
        binance_section=settings.SECTION
    )
    if api_client is None:
        raise KeyError("There is no such a client.")
    run(main=api_client.ping())
    binance_api_service: BinanceService = BinanceService(client=api_client)
    run(main=main(service=binance_api_service))
