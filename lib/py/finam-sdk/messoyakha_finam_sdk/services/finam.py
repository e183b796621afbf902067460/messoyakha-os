from asyncio import sleep
from datetime import datetime, timedelta

from attrs import define, field
from loguru import logger
from polars import DataFrame, col
from tqdm import tqdm

from messoyakha_finam_sdk.adapters.finam import FinamAPIClient, FinamMISXFuturesAPIClient, FinamMISXSpotAPIClient
from messoyakha_finam_sdk.schemas.bars import (
    FinamBarsHeadersSchema,
    FinamBarsHTTPEndpointSchema,
    FinamBarsInputSchema,
    FinamBarsMISXFuturesInputSchema,
    FinamBarsMISXSpotInputSchema,
    FinamBarsOutputSchema,
    FinamBarsParametersSchema,
    FinamMISXFuturesBarsParametersSchema,
    FinamMISXSpotBarsParametersSchema,
)
from messoyakha_finam_sdk.schemas.clock import FinamClockHeadersSchema, FinamPingInputSchema
from messoyakha_finam_sdk.schemas.sessions import FinamSessionsJsonSchema, FinamSessionsOutputSchema


logger.remove()
logger.add(lambda message: tqdm.write(message), colorize=True)


@define(slots=True, auto_attribs=True, kw_only=True)
class _FinamService:
    _client: FinamAPIClient = field(init=False)

    async def ping(self, input_schema: FinamPingInputSchema) -> None:
        session: FinamSessionsOutputSchema = await self._client.sessions(
            json_schema=FinamSessionsJsonSchema(secret=input_schema.secret)
        )
        await self._client.clock(headers_schema=FinamClockHeadersSchema(authorization=session.token))

    async def _get_ohlcv(
        self,
        input_schema: FinamBarsInputSchema,
        _parameters_schema: type[FinamBarsParametersSchema],
    ) -> DataFrame:
        session: FinamSessionsOutputSchema = await self._client.sessions(
            json_schema=FinamSessionsJsonSchema(secret=input_schema.secret)
        )

        number_of_batches: int = max(1, int(input_schema.delta.total_seconds() / input_schema.limit.total_seconds()))

        bars: list[FinamBarsOutputSchema] = []
        for _ in tqdm(range(number_of_batches)):
            end_time: datetime = min(input_schema.start_time + input_schema.limit, input_schema.end_time)
            batch: list[FinamBarsOutputSchema] = await self._client.bars(
                endpoint_schema=FinamBarsHTTPEndpointSchema(ticker=input_schema.ticker, venue=input_schema.venue),
                parameters_schema=_parameters_schema(
                    currency=input_schema.currency,
                    interval=input_schema.interval,
                    start_time=input_schema.start_time,
                    end_time=end_time,
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
            await sleep(1)
        return DataFrame([bar.model_dump() for bar in bars]).unique().sort(by=col("timestamp"))


@define(slots=True, auto_attribs=True, kw_only=True)
class FinamMISXSpotService(_FinamService):
    _client: FinamAPIClient = field(init=False, factory=FinamMISXSpotAPIClient)

    async def get_ohlcv(self, input_schema: FinamBarsMISXSpotInputSchema) -> DataFrame:
        return await super()._get_ohlcv(input_schema=input_schema, _parameters_schema=FinamMISXSpotBarsParametersSchema)


@define(slots=True, auto_attribs=True, kw_only=True)
class FinamMISXFuturesService(_FinamService):
    _client: FinamAPIClient = field(init=False, factory=FinamMISXFuturesAPIClient)

    async def get_ohlcv(self, input_schema: FinamBarsMISXFuturesInputSchema) -> DataFrame:
        return await super()._get_ohlcv(
            input_schema=input_schema, _parameters_schema=FinamMISXFuturesBarsParametersSchema
        )
