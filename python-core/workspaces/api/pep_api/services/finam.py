from asyncio import sleep
from datetime import datetime, timedelta

from attrs import define, field
from loguru import logger
from polars import DataFrame
from tqdm import tqdm

from pep_api.adapters.finam import FinamAPIClient
from pep_api.schemas.finam import (
    FinamBarsEndpointSchema,
    FinamBarsHeadersSchema,
    FinamBarsInputSchema,
    FinamBarsOutputSchema,
    FinamBarsParametersSchema,
    FinamSessionsJsonSchema,
    FinamSessionsOutputSchema,
)


logger.remove()
logger.add(lambda message: tqdm.write(message), colorize=True)


@define(slots=True, auto_attribs=True, kw_only=True)
class FinamService:
    _client: FinamAPIClient = field(init=False, factory=FinamAPIClient)

    async def get_ohlcv(self, input_schema: FinamBarsInputSchema) -> DataFrame:
        session: FinamSessionsOutputSchema = await self._client.sessions(
            json_schema=FinamSessionsJsonSchema(secret=input_schema.secret)
        )

        number_of_batches: int = max(1, int(input_schema.delta.total_seconds() / input_schema.limit.total_seconds()))

        bars: list[FinamBarsOutputSchema] = []
        for _ in tqdm(range(number_of_batches)):
            end_time: datetime = min(input_schema.start_time + input_schema.limit, input_schema.end_time)
            batch: list[FinamBarsOutputSchema] = await self._client.bars(
                endpoint_schema=FinamBarsEndpointSchema(ticker=input_schema.ticker),
                parameters_schema=FinamBarsParametersSchema(
                    timeframe=input_schema.timeframe, start_time=input_schema.start_time, end_time=end_time
                ),
                headers_schema=FinamBarsHeadersSchema(authorization=session.token),
            )
            if not batch:
                break
            bars.extend(batch)

            next_start_time: datetime = batch[-1].timestamp + timedelta(seconds=1)
            if next_start_time > input_schema.end_time:
                break
            input_schema.start_time = next_start_time
            await sleep(0.5)
        return DataFrame([bar.model_dump() for bar in bars])
