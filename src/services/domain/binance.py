from datetime import datetime, timedelta
from time import sleep

from numpy import floor
from polars import DataFrame

from src.adapters.clients.binance import BinanceAPIClientBase
from src.schemas.domain.binance import BinanceKlinesInputSchema, BinanceKlinesOutputSchema
from src.services.common.api_base import APIBaseService


# pylint: disable=too-many-return-statements
def _convert_binance_interval_to_seconds(interval: str) -> float:
    if interval == "30m":
        return timedelta(minutes=30).total_seconds()  # noqa: WPS432
    if interval == "1h":
        return timedelta(hours=1).total_seconds()
    if interval == "2h":
        return timedelta(hours=2).total_seconds()
    if interval == "4h":
        return timedelta(hours=4).total_seconds()
    if interval == "1d":
        return timedelta(days=1).total_seconds()
    if interval == "1w":
        return timedelta(weeks=1).total_seconds()
    raise ValueError(f"Invalid interval `{interval}` were passed.")


# pylint: enable=too-many-return-statements


class BinanceService(APIBaseService):
    _client: BinanceAPIClientBase

    async def get_ohlc(self, input_schema: BinanceKlinesInputSchema) -> DataFrame:
        klines: list[BinanceKlinesOutputSchema] = []

        number_of_batches: int = int(
            floor(
                input_schema.delta.total_seconds()
                / _convert_binance_interval_to_seconds(interval=input_schema.interval)
            )
        )
        for _ in range(number_of_batches):
            batch: list[BinanceKlinesOutputSchema] = await self._client.klines(input_schema=input_schema)
            if not batch:
                break

            next_start_time: datetime = batch[-1].close_time + timedelta(milliseconds=1)
            input_schema = BinanceKlinesInputSchema(
                ticker=input_schema.ticker,
                section=input_schema.section,
                interval=input_schema.interval,
                start_time=next_start_time,
                end_time=input_schema.end_time,
            )

            klines.extend(batch)
            sleep(0.25)  # noqa: WPS432
        return DataFrame([kline.model_dump() for kline in klines])
