from asyncio import sleep
from datetime import datetime, timedelta

from attrs import define, field
from loguru import logger
from polars import DataFrame, col
from tqdm import tqdm

from messoyakha_moex_iss_sdk.adapters.moex import MOEXAPIClient, MOEXStockIndexAPIClient, MOEXStockSharesAPIClient
from messoyakha_moex_iss_sdk.schemas.history_security import (
    MOEXHistorySecurityHTTPEndpointSchema,
    MOEXHistorySecurityInputSchemaBase,
    MOEXHistorySecurityOutputSchema,
    MOEXHistorySecurityParametersSchema,
    MOEXSpotHistorySecurityInputSchema,
)
from messoyakha_moex_iss_sdk.schemas.history_security_total import (
    MOEXHistorySecurityTotalHTTPEndpointSchema,
    MOEXHistorySecurityTotalInputSchema,
    MOEXHistorySecurityTotalOutputSchema,
    MOEXHistorySecurityTotalParametersSchema,
)
from messoyakha_moex_iss_sdk.schemas.listed_from import MOEXListedFromHTTPEndpointSchema, MOEXListedFromInputSchema


logger.remove()
logger.add(lambda message: tqdm.write(message), colorize=True)


@define(slots=True, auto_attribs=True, kw_only=True)
class _MOEXService:
    _client: MOEXAPIClient = field(init=False)

    async def _get_ohlcv(self, input_schema: MOEXHistorySecurityInputSchemaBase) -> DataFrame:
        number_of_batches: int = max(1, int(input_schema.delta.total_seconds() / input_schema.limit.total_seconds()))

        history_securities: list[MOEXHistorySecurityOutputSchema] = []
        for _ in tqdm(range(number_of_batches)):
            end_time: datetime = min(input_schema.start_time + input_schema.limit, input_schema.end_time)

            batch: list[MOEXHistorySecurityOutputSchema] = await self._client.history_security(
                endpoint_schema=MOEXHistorySecurityHTTPEndpointSchema(
                    ticker=input_schema.ticker,
                ),
                parameters_schema=MOEXHistorySecurityParametersSchema(
                    currency=input_schema.currency,
                    product=input_schema.product,
                    interval=input_schema.interval,
                    start_time=input_schema.start_time,
                    end_time=end_time,
                ),
            )
            if not batch:
                break
            history_securities.extend(batch)

            next_start_time: datetime = batch[-1].timestamp + timedelta(days=1)
            if next_start_time > input_schema.end_time:
                break
            input_schema.start_time = next_start_time
            await sleep(1)
        return (
            DataFrame([candle.model_dump() for candle in history_securities], infer_schema_length=None)
            .unique()
            .sort(by=col("timestamp"))
        )

    async def get_first_trade_date(self, input_schema: MOEXListedFromInputSchema) -> datetime:
        return await self._client.listed_from(
            endpoint_schema=MOEXListedFromHTTPEndpointSchema(
                ticker=input_schema.ticker,
            ),
        )


@define(slots=True, auto_attribs=True, kw_only=True)
class MOEXStockIndexService(_MOEXService):
    _client: MOEXAPIClient = field(init=False, factory=MOEXStockIndexAPIClient)

    async def get_ohlcv(self, input_schema: MOEXSpotHistorySecurityInputSchema) -> DataFrame:
        return await super()._get_ohlcv(input_schema=input_schema)


@define(slots=True, auto_attribs=True, kw_only=True)
class MOEXStockSharesService(_MOEXService):
    _client: MOEXStockSharesAPIClient = field(init=False, factory=MOEXStockSharesAPIClient)  # type: ignore[bad-override]

    async def get_ohlcv(self, input_schema: MOEXSpotHistorySecurityInputSchema) -> DataFrame:
        return await super()._get_ohlcv(input_schema=input_schema)

    async def get_total_supply(self, input_schema: MOEXHistorySecurityTotalInputSchema) -> DataFrame:
        history_security_totals: list[MOEXHistorySecurityTotalOutputSchema] = await self._client.history_security_total(
            endpoint_schema=MOEXHistorySecurityTotalHTTPEndpointSchema(
                ticker=input_schema.ticker,
            ),
            parameters_schema=MOEXHistorySecurityTotalParametersSchema(
                currency=input_schema.currency,
                start_time=input_schema.start_time,
                end_time=input_schema.end_time,
            ),
        )
        return DataFrame([item.model_dump() for item in history_security_totals], infer_schema_length=None).sort(
            by=col("timestamp")
        )
