from attrs import define, field
from polars import DataFrame, col

from pep_sdk.adapters.crawlers.smartlab import SmartLabBSCrawler
from pep_sdk.schemas.crawlers.smartlab import (
    SmartLabNetIncomeEndpointSchema,
    SmartLabNetIncomeInputSchema,
    SmartLabNetIncomeOutputSchema,
)


@define(slots=True, auto_attribs=True, kw_only=True)
class SmartLabService:
    _crawler: SmartLabBSCrawler = field(init=False, factory=SmartLabBSCrawler)

    async def crawl_net_incomes(self, input_schema: SmartLabNetIncomeInputSchema) -> DataFrame:
        net_incomes: list[SmartLabNetIncomeOutputSchema] = await self._crawler.net_income(
            endpoint_schema=SmartLabNetIncomeEndpointSchema(ticker=input_schema.ticker)
        )
        return DataFrame([net_income.model_dump() for net_income in net_incomes]).unique().sort(by=col("timestamp"))
