from attrs import define, field
from polars import DataFrame, col

from messoyakha_smart_lab_sdk.adapters.smart_lab import SmartLabCrawleeWebClient
from messoyakha_smart_lab_sdk.schemas.net_income import (
    SmartLabNetIncomeEndpointSchema,
    SmartLabNetIncomeInputSchema,
    SmartLabNetIncomeOutputSchema,
)


@define(slots=True, auto_attribs=True, kw_only=True)
class SmartLabService:
    _client: SmartLabCrawleeWebClient = field(init=False, factory=SmartLabCrawleeWebClient)

    async def crawl_net_incomes(self, input_schema: SmartLabNetIncomeInputSchema) -> DataFrame:
        net_incomes: list[SmartLabNetIncomeOutputSchema] = await self._client.net_income(
            endpoint_schema=SmartLabNetIncomeEndpointSchema(ticker=input_schema.ticker)
        )
        return DataFrame([net_income.model_dump() for net_income in net_incomes]).unique().sort(by=col("timestamp"))
