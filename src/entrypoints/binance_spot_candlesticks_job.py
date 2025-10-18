from asyncio import run

from httpx import AsyncClient as HTTPAsyncClient
from httpx import AsyncHTTPTransport

from src.adapters.clients.binance import BinanceSpotAPIClient
from src.entrypoints.common.binance_candlesticks_base import main

if __name__ == "__main__":

    binance_spot_client: BinanceSpotAPIClient = BinanceSpotAPIClient(
        session=HTTPAsyncClient(
            base_url="https://api.binance.com",
            timeout=60,
            transport=AsyncHTTPTransport(retries=3, http2=True),
            follow_redirects=True,
        )
    )
    run(main(exchange="Binance", section="SPOT", client=binance_spot_client))
