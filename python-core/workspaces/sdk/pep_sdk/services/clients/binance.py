from asyncio import sleep
from datetime import datetime, timedelta

from attrs import define, field
from loguru import logger
from numpy import floor
from polars import DataFrame, col
from tqdm import tqdm

from pep_sdk.adapters.clients.binance import BinanceAPIClient, BinanceSpotAPIClient, BinanceUSDTMAPIClient
from pep_sdk.schemas.clients.binance.klines import (
    BinanceKlinesInputSchema,
    BinanceKlinesOutputSchema,
    BinanceKlinesParametersSchema,
)


logger.remove()
logger.add(lambda message: tqdm.write(message), colorize=True)


@define(slots=True, auto_attribs=True, kw_only=True)
class _BinanceServiceBase:
    _client: BinanceAPIClient = field(init=False)

    async def ping(self) -> None:
        await self._client.ping()

    async def get_ohlcv(self, input_schema: BinanceKlinesInputSchema) -> DataFrame:
        number_of_batches: int = int(floor(input_schema.delta.total_seconds() / input_schema.interval_seconds))

        klines: list[BinanceKlinesOutputSchema] = []
        for _ in tqdm(range(number_of_batches)):
            batch: list[BinanceKlinesOutputSchema] = await self._client.klines(
                parameters_schema=BinanceKlinesParametersSchema(**input_schema.model_dump())
            )
            if not batch:
                break
            klines.extend(batch)

            next_start_time: datetime = batch[-1].timestamp + timedelta(milliseconds=1)
            if next_start_time > input_schema.end_time:
                break
            input_schema.start_time = next_start_time
            await sleep(0.25)
        return DataFrame([kline.model_dump() for kline in klines]).unique().sort(by=col("timestamp"))


@define(slots=True, auto_attribs=True, kw_only=True)
class BinanceSpotService(_BinanceServiceBase):
    _client: BinanceAPIClient = field(init=False, factory=BinanceSpotAPIClient)


@define(slots=True, auto_attribs=True, kw_only=True)
class BinanceUSDTMService(_BinanceServiceBase):
    _client: BinanceAPIClient = field(init=False, factory=BinanceUSDTMAPIClient)
