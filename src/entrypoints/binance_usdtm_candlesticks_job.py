from asyncio import run

from httpx import AsyncClient as HTTPAsyncClient
from httpx import AsyncHTTPTransport

from src.adapters.clients.binance import BinanceUsdtmAPIClient
from src.entrypoints.common.binance_candlesticks_base import main

if __name__ == "__main__":

    binance_usdtm_client: BinanceUsdtmAPIClient = BinanceUsdtmAPIClient(
        session=HTTPAsyncClient(
            base_url="https://fapi.binance.com",
            timeout=60,
            transport=AsyncHTTPTransport(retries=3, http2=True),
            follow_redirects=True,
        )
    )
    run(main(exchange="Binance", section="USDTM", client=binance_usdtm_client))
